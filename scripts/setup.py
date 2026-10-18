# Rolt de app uit: lokaal met Docker Compose, of op Azure (Terraform in terraform/, nog niet automatisch).
# Gebruik: python scripts/setup.py          vraagt alles
#          python scripts/setup.py lokaal   lokaal; zonder terminal (zoals in CI) zonder vragen
# Werkt op Windows en Linux: geen shell, alleen lijsten van argumenten.

import re
import secrets
import shutil
import subprocess
import sys
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
              ("docker", "Docker, om de image te bouwen en te pushen")],
}
# Zonder terminal geen vragen: dan gelden de standaardwaarden.
INTERACTIVE = sys.stdin.isatty()
# Eist een tenant MFA, dan slaat az login hem over (AADSTS50076) en is er geen subscription; --tenant vraagt er wel om.
AZ_LOGIN_HELP = """Niet ingelogd bij Azure, of geen subscription gevonden. Eerst inloggen:
   az login
   Zegt az login "Authentication failed against tenant <ID>" met AADSTS50076, dan eist die tenant MFA.
   Log dan in bij die tenant, en keur de tweede stap goed in je authenticator-app:
   az login --tenant <ID>
   Daarna opnieuw: python scripts/setup.py azure"""
IMAGE = "ghcr.io/youssefontys/secure-application:<tag>"


# Stoppen met de melding, met witregels eromheen zodat hij opvalt; zelfde vorm als azuresetup_v2.py.
def stop(message):
    sys.exit(f"\n❌ {message}\n\n🛑 Stoppen.\n")


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
        print("❌ Dat antwoord ken ik niet; probeer het opnieuw.")


def yes(question):
    return ask(f"{question} (j/n)", "n", r"[jJnN]").lower() == "j"


# Stopt met een lijst van wat ontbreekt, voordat er iets gebeurt.
def check_tools(target):
    missing = [f"   - {tool}: {why}" for tool, why in NEEDS[target] if not shutil.which(tool)]
    if missing:
        stop("Niet gevonden:\n" + "\n".join(missing))
    print("✅ Gevonden:", ", ".join(tool for tool, _ in NEEDS[target]))


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
    print("\n⚙️  Hackstand, alleen voor de hacking week, als de hele klas aanvalt vanaf één schooladres:\n"
          "   n  normaal (standaard): per adres 20 foute inlogpogingen per kwartier en 10 nieuwe accounts per uur\n"
          "   j  hacking week: per adres 100 foute inlogpogingen per kwartier en 60 nieuwe accounts per uur,\n"
          "      zodat klasgenoten elkaar niet buitensluiten")
    if not yes("Hackstand aan?"):
        return {"THROTTLE_IP_MODE": None, "THROTTLE_PAIR_EXEMPT_USERS": None}
    print("\n🎯 Een gedeeld demo-account dat iedereen mag aanvallen: foute wachtwoorden sluiten het dan niet af voor de rest.")
    # Dezelfde regel als een gebruikersnaam in de app; "-" is geen demo-account.
    demo = ask("Naam van het demo-account (- voor geen)", "hackingweek", r"[A-Za-z0-9_]{3,20}|-")
    return {"THROTTLE_IP_MODE": "hackweek", "THROTTLE_PAIR_EXEMPT_USERS": None if demo == "-" else demo}


def local():
    check_tools("lokaal")
    added = ensure_env()
    print(f"🔑 Nieuw in .env: {', '.join(added)} (256 willekeurige bits, niet getoond)" if added
          else "✅ .env: alle geheimen staan erin")
    # Zonder terminal blijft wat er in .env staat; HTTPS_ONLY zet compose.yaml lokaal op 0 (HTTP).
    if INTERACTIVE:
        settings = hackstand()
        # Nog steeds interactief: er is echt geantwoord, dus de keuze mag in .env.
        if INTERACTIVE:
            for name, value in settings.items():
                set_env(name, value)
    print("\n🐳 Containers bouwen en starten...\n")
    if subprocess.run([shutil.which("docker"), "compose", "up", "-d", "--build", "--wait"], cwd=REPO).returncode != 0:
        stop("docker compose up lukte niet; de melding van Docker staat hierboven.")
    print("\n🎉 De app draait op http://127.0.0.1:5000\n")


# Nog niet automatisch: eerst de image en de koppeling met GitHub (OIDC). Wel de juiste stappen, met deze keuzes.
def azure():
    check_tools("azure")
    # Stap 1 kan niets zonder login; dan eerst uitleggen hoe, ook bij een tenant die MFA eist.
    account = subprocess.run([shutil.which("az"), "account", "show", "--query", "name", "-o", "tsv"], capture_output=True, text=True)
    if account.returncode != 0:
        stop(AZ_LOGIN_HELP)
    print(f"✅ Ingelogd bij Azure, subscription: {account.stdout.strip()}")
    hack = hackstand() if INTERACTIVE else {"THROTTLE_IP_MODE": None, "THROTTLE_PAIR_EXEMPT_USERS": None}
    variables = [f"app_image={IMAGE}"]
    if hack["THROTTLE_IP_MODE"]:
        variables += ["throttle_ip_mode=hackweek", "min_replicas=1"]
    if hack["THROTTLE_PAIR_EXEMPT_USERS"]:
        variables.append(f"throttle_pair_exempt_users={hack['THROTTLE_PAIR_EXEMPT_USERS']}")
    print("\n📋 Azure rolt nog niet automatisch uit. De stappen, één commando per regel:\n")
    print("   1. De Terraform-state, eenmalig")
    print("      python scripts/azuresetup_v2.py\n")
    # GitHub Packages accepteert alleen een token (classic); docker vraagt erom, dus het komt niet in de shellgeschiedenis.
    print("   2. De image")
    print("      docker login ghcr.io -u youssefontys     (wachtwoord: een token (classic) met write:packages)")
    print(f"      docker build -t {IMAGE} app")
    print(f"      docker push {IMAGE}")
    # Een nieuw pakket is privé, en Terraform geeft Container Apps geen inlog voor ghcr.io: dan start de app niet.
    print("      Eenmalig na de eerste push: het pakket openbaar maken (Package settings > Change visibility > Public).")
    print("      Daarna kan het niet meer privé; de repo is al openbaar en de image heeft geen geheimen.\n")
    print("   3. Terraform")
    print("      terraform -chdir=terraform init -backend-config=../backend.conf")
    print("      terraform -chdir=terraform apply " + " ".join(f"-var {v}" for v in variables) + "\n")
    print("   4. Het schema, eenmalig")
    print("      het commando uit de output schema_job_command\n")
    sys.exit(1)


print("\n🛡️  Notities-app uitrollen\n")
if len(sys.argv) > 1:
    choice = sys.argv[1]
elif INTERACTIVE:
    choice = ask("Waar rol je uit? lokaal of azure", "lokaal", r"lokaal|azure")
else:
    choice = "lokaal"
if choice == "lokaal":
    local()
elif choice == "azure":
    azure()
else:
    stop(f"Onbekende keuze: {choice!r}. Kies lokaal of azure.")
