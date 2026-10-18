# Rolt de app uit: lokaal met Docker Compose, of op Azure met Terraform (terraform/).
# Gebruik: python scripts/setup.py          vraagt alles
#          python scripts/setup.py lokaal   lokaal; zonder terminal (zoals in CI) zonder vragen
#          python scripts/setup.py azure    de state-opslag (eenmalig), de image van GitHub, en Terraform
# Werkt op Windows en Linux: geen shell, alleen lijsten van argumenten.

import json
import re
import secrets
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Emoji ook als de uitvoer naar een pipe of bestand gaat: Python voor 3.15 schrijft daar op Windows cp1252.
# Een stream zonder reconfigure (IDLE, een test) kan al Unicode.
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent.parent
ENV = REPO / ".env"
# Deze geheimen moeten in .env staan; ontbreekt er een of is hij leeg, dan maakt setup hem aan.
SECRETS = ("POSTGRES_PASSWORD", "APP_DB_PASSWORD", "FLASK_SECRET_KEY", "DATA_ENCRYPTION_KEY")
# Wat er per doel op de machine moet staan, en waarvoor.
NEEDS = {
    "lokaal": [("docker", "Docker met Compose v2, voor de containers")],
    "azure": [("az", "de Azure CLI, om in te loggen en de Terraform-state op te zetten"),
              ("terraform", "Terraform 1.11 of nieuwer, voor de resources"),
              ("git", "Git, om de image te vinden die GitHub van je app/ bouwde")],
}
# Zonder terminal geen vragen: dan gelden de standaardwaarden.
INTERACTIVE = sys.stdin.isatty()
# Eist een tenant MFA, dan slaat az login hem over (AADSTS50076) en is er geen subscription; --tenant vraagt er wel om.
AZ_LOGIN_HELP = """Eerst even inloggen bij Azure: je bent nog niet ingelogd, of er is geen subscription gevonden.
   az login
   Zegt az login "Authentication failed against tenant <ID>" met AADSTS50076? Dan wil die tenant een
   tweede stap (MFA). Log dan in bij die tenant, en keur het goed in je authenticator-app:
   az login --tenant <ID>
   Daarna opnieuw: python scripts/setup.py azure"""
# Een e-mailadres, als allowlist (MIT-22); dezelfde regel als de validatie van alert_email in terraform/variables.tf.
EMAIL = r"[^@\s]+@[^@\s]+\.[A-Za-z]{2,}"


# Stoppen met de melding, met witregels eromheen zodat hij opvalt; zelfde vorm als azuresetup_v2.py.
def stop(message, icon="❌"):
    sys.exit(f"\n{icon} {message}\n\n🛑 Stoppen.\n")


# Een vraag met een standaardwaarde; alleen een antwoord dat helemaal op pattern past (allowlist, MIT-22).
# Geen invoer (EOF) telt als geen terminal: op Windows lijkt ook NUL er een.
def ask(question, default, pattern):
    global INTERACTIVE
    while True:
        try:
            answer = input(f"{question} [{default}]: ").strip() or default
        except EOFError:
            print()
            INTERACTIVE = False
            return default
        if re.fullmatch(pattern, answer):
            return answer
        print("🤔 Dat antwoord ken ik niet; probeer het nog eens.")


def yes(question):
    return ask(f"{question} (j/n)", "n", r"[jJnN]").lower() == "j"


# Stopt met een lijst van wat ontbreekt, voordat er iets gebeurt.
def check_tools(target):
    print("🔍 Even kijken of alles er is...")
    missing = [f"   ❓ {tool}: {why}" for tool, why in NEEDS[target] if not shutil.which(tool)]
    if missing:
        stop("Nog niet gevonden:\n" + "\n".join(missing) + "\n   💡 Installeer wat ontbreekt en start dit script daarna opnieuw.")
    for tool, why in NEEDS[target]:
        print(f"   ✅ {tool}: {why}")


def read_env():
    return ENV.read_text(encoding="utf-8").splitlines() if ENV.exists() else []


# Alleen de eigenaar mag .env lezen (0600), al vóór het schrijven; anders leest elke gebruiker van de machine
# de sleutels mee (MIT-32). Op Windows zet chmod alleen het alleen-lezen-vlag, en dat blijft uit.
def write_env(lines):
    ENV.touch(mode=0o600, exist_ok=True)
    ENV.chmod(0o600)
    ENV.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="")


# Vult ontbrekende of lege geheimen in .env aan met 256 willekeurige bits; toont ze nooit.
def ensure_env():
    lines = read_env()
    present, new = set(), []
    for i, line in enumerate(lines):
        name, sep, value = line.partition("=")
        name = name.strip()
        if sep and name in SECRETS and not line.lstrip().startswith("#"):
            present.add(name)
            if not value.strip():
                lines[i] = f"{name}={secrets.token_hex(32)}"
                new.append(name)
    missing = [name for name in SECRETS if name not in present]
    lines += [f"{name}={secrets.token_hex(32)}" for name in missing]
    write_env(lines)
    return new + missing


# Zet een instelling in .env, of haalt hem weg bij None; regels in commentaar blijven staan.
def set_env(name, value):
    lines = [line for line in read_env() if line.lstrip().startswith("#") or line.partition("=")[0].strip() != name]
    if value is not None:
        lines.append(f"{name}={value}")
    write_env(lines)


# De hackstand voor de hacking week (MC-18), standaard uit. Geeft de instellingen, of None per instelling.
def hackstand():
    print("\n🏫 Hackstand, alleen voor de hacking week, als de hele klas aanvalt vanaf één schooladres:\n"
          "   n  🙂 normaal (standaard): per adres 20 foute inlogpogingen per kwartier en 10 nieuwe accounts per uur\n"
          "   j  🏁 hacking week: per adres 100 foute inlogpogingen per kwartier en 60 nieuwe accounts per uur,\n"
          "         zodat klasgenoten elkaar niet buitensluiten")
    if not yes("Hackstand aan?"):
        return {"THROTTLE_IP_MODE": None, "THROTTLE_PAIR_EXEMPT_USERS": None}
    print("\n🎯 Een gedeeld demo-account dat iedereen mag aanvallen: foute wachtwoorden sluiten het dan niet af voor de rest.")
    # Dezelfde regel als een gebruikersnaam in de app; "-" is geen demo-account.
    demo = ask("Naam van het demo-account (- voor geen)", "hackingweek", r"[A-Za-z0-9_]{3,20}|-")
    return {"THROTTLE_IP_MODE": "hackweek", "THROTTLE_PAIR_EXEMPT_USERS": None if demo == "-" else demo}


def local():
    check_tools("lokaal")
    added = ensure_env()
    print(f"\n🔑 Nieuwe geheimen in .env: {', '.join(added)} (elk 256 willekeurige bits, nooit getoond)" if added
          else "\n🔐 .env: alle geheimen staan er al")
    # Zonder terminal blijft wat er in .env staat; HTTPS_ONLY zet compose.yaml lokaal op 0 (HTTP).
    if INTERACTIVE:
        settings = hackstand()
        # Nog steeds interactief: er is echt geantwoord, dus de keuze mag in .env.
        if INTERACTIVE:
            for name, value in settings.items():
                set_env(name, value)
    print("\n🐳 Containers bouwen en starten... ☕ de eerste keer duurt dit even.\n")
    if subprocess.run([shutil.which("docker"), "compose", "up", "-d", "--build", "--wait"], cwd=REPO).returncode != 0:
        stop("docker compose up lukte niet; de melding van Docker staat hierboven.\n"
             "   💡 Draait Docker (op Windows: Docker Desktop)? Start het en probeer het opnieuw.")
    print("\n🎉 Klaar! De app draait op http://127.0.0.1:5000")
    print("💡 Stoppen kan met: docker compose down\n")


# Git in deze map; None als het niet lukt.
def git(*args):
    result = subprocess.run([shutil.which("git"), *args], cwd=REPO, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


# owner/naam van de GitHub-repo, uit de remote origin; ook voor wie de repo heeft gekopieerd. ghcr.io wil kleine letters.
def github_repo(url):
    match = re.search(r"github\.com[:/]([\w.-]+/[\w.-]+?)(?:\.git)?/?$", url or "")
    return match and match.group(1).lower()


# Staat de image er, en mag iedereen hem ophalen? Dat moet: Container Apps logt niet in bij ghcr.io.
def image_public(repo, tag):
    accept = ("application/vnd.oci.image.index.v1+json, application/vnd.oci.image.manifest.v1+json, "
              "application/vnd.docker.distribution.manifest.v2+json")
    try:
        with urllib.request.urlopen(f"https://ghcr.io/token?scope=repository:{repo}:pull", timeout=15) as response:
            token = json.load(response)["token"]
        request = urllib.request.Request(f"https://ghcr.io/v2/{repo}/manifests/{tag}", method="HEAD",
                                         headers={"Authorization": f"Bearer {token}", "Accept": accept})
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status == 200
    except (urllib.error.URLError, KeyError, ValueError):
        return False


# Terraform in terraform/, met de uitvoer en de vragen gewoon in deze terminal.
def terraform(*args):
    return subprocess.run([shutil.which("terraform"), "-chdir=terraform", *args], cwd=REPO).returncode == 0


# Alles voor Azure in één keer: de state-opslag als die er nog niet is, de image die GitHub bouwde, en Terraform.
def azure():
    check_tools("azure")
    # Zonder login kan er niets; dan eerst uitleggen hoe, ook bij een tenant die MFA eist.
    account = subprocess.run([shutil.which("az"), "account", "show", "--query", "[name, user.name]", "-o", "tsv"],
                             capture_output=True, text=True)
    if account.returncode != 0:
        stop(AZ_LOGIN_HELP, icon="🔐")
    subscription, login = (account.stdout.splitlines() + ["", ""])[:2]
    print(f"\n☁️  Ingelogd bij Azure, subscription: {subscription}")

    # Kip en ei: Terraform moet zijn state ergens kwijt voordat het iets maakt; die opslag zet een script eenmalig neer.
    if (REPO / "backend.conf").exists():
        print("🗄️  Opslag voor de Terraform-state: staat er al (backend.conf)")
    else:
        print("\n🗄️  Nog geen opslag voor de Terraform-state; azuresetup_v2.py zet die nu eenmalig klaar.")
        if subprocess.run([sys.executable, str(REPO / "scripts" / "azuresetup_v2.py")], cwd=REPO).returncode != 0:
            sys.exit(1)

    # De tag is de inhoud van app/ in je laatste commit (zie image.yml): een commit zonder app-wijziging hergebruikt hem.
    repo, tree = github_repo(git("remote", "get-url", "origin")), git("rev-parse", "HEAD:app")
    if not (repo and tree):
        stop("Geen GitHub-repo gevonden (git remote get-url origin); de image komt van GitHub Actions.", icon="🤔")
    tag = f"app-{tree}"
    image = f"ghcr.io/{repo}:{tag}"
    print(f"\n📦 De image van app/ zoals in je laatste commit: {image}")
    if not image_public(repo, tag):
        stop("Die image staat nog niet op ghcr.io, of hij is niet openbaar.\n"
             "   💡 Push je laatste commit en wacht tot de GitHub Action Image groen is, een paar minuten:\n"
             f"      https://github.com/{repo}/actions\n"
             "   Daarna opnieuw: python scripts/setup.py azure", icon="⏳")
    print("   ✅ Staat klaar, en Container Apps mag hem ophalen")

    hack = hackstand() if INTERACTIVE else {"THROTTLE_IP_MODE": None, "THROTTLE_PAIR_EXEMPT_USERS": None}
    # De mail bij een blokkade (alerts.tf): standaard het adres waarmee je bij az bent ingelogd. Niet in de repo, die is openbaar.
    email = login if re.fullmatch(EMAIL, login) else ""
    if INTERACTIVE:
        print("\n📧 Bij een blokkade stuurt Azure binnen een paar minuten een mail.")
        email = ask("Naar welk adres?", email or "-", EMAIL)
    if not re.fullmatch(EMAIL, email):
        stop("Geen e-mailadres voor de alert; draai dit script in een terminal en vul er een in.", icon="📧")
    variables = [f"app_image={image}", f"alert_email={email}"]
    if hack["THROTTLE_IP_MODE"]:
        variables += ["throttle_ip_mode=hackweek", "min_replicas=1"]
    if hack["THROTTLE_PAIR_EXEMPT_USERS"]:
        variables.append(f"throttle_pair_exempt_users={hack['THROTTLE_PAIR_EXEMPT_USERS']}")

    print("\n🏗️  Terraform. Het laat eerst zien wat het gaat doen, en begint pas als jij yes typt.\n")
    # backend.conf is de enige bron: na een nieuwe bootstrap kent .terraform nog de oude opslag, en dan stopt init
    # zonder -reconfigure. Er gaat geen state mee; die hoort bij de opslag.
    if not terraform("init", "-input=false", "-reconfigure", "-backend-config=../backend.conf"):
        stop("terraform init lukte niet; de melding staat hierboven.")
    # De vraag om yes blijft staan: hier gaan resources aan die geld kosten.
    if not terraform("apply", *(f"-var={v}" for v in variables)):
        stop("terraform apply lukte niet, of je typte geen yes; de melding staat hierboven.")
    url = subprocess.run([shutil.which("terraform"), "-chdir=terraform", "output", "-raw", "app_url"],
                         cwd=REPO, capture_output=True, text=True).stdout.strip()
    print(f"\n🎉 Klaar! De app staat op {url}")
    print("⏳ Terraform heeft de schema-job gestart; geeft inloggen de eerste minuut een fout, probeer het dan zo nog eens.")
    print("💡 Bijwerken: push naar main, wacht tot de Action Image groen is, en draai dit script opnieuw.\n")


print("\n🛡️  Notities-app uitrollen")
print("👋 Welkom! Ik loop alles met je door. Enter kiest steeds wat tussen [ ] staat.\n")
if len(sys.argv) > 1:
    choice = sys.argv[1]
elif INTERACTIVE:
    choice = ask("🧭 Waar rol je uit? lokaal of azure", "lokaal", r"lokaal|azure")
else:
    choice = "lokaal"
if choice == "lokaal":
    local()
elif choice == "azure":
    azure()
else:
    stop(f"Onbekende keuze: {choice!r}. Kies lokaal of azure.", icon="🤔")
