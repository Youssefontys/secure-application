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

REPO = Path(__file__).resolve().parent.parent
ENV = REPO / ".env"
# Deze geheimen moeten in .env staan; ontbreekt er een of is hij leeg, dan maakt setup hem aan.
SECRETS = ("POSTGRES_PASSWORD", "FLASK_SECRET_KEY", "DATA_ENCRYPTION_KEY")
# Wat er per doel op de machine moet staan, en waarvoor.
NEEDS = {
    "lokaal": [("docker", "Docker met Compose v2, voor de containers")],
    "azure": [("az", "de Azure CLI, om in te loggen en de Terraform-state op te zetten"),
              ("terraform", "Terraform 1.11 of nieuwer, voor de resources"),
              ("docker", "Docker, om de image te bouwen en te pushen")],
}
# Zonder terminal geen vragen: dan gelden de standaardwaarden.
INTERACTIVE = sys.stdin.isatty()


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
        print("Dat antwoord ken ik niet; probeer het opnieuw.")


def yes(question):
    return ask(f"{question} (j/n)", "n", r"[jJnN]").lower() == "j"


# Stopt met een lijst van wat ontbreekt, voordat er iets gebeurt.
def check_tools(target):
    missing = [f"  - {tool}: {why}" for tool, why in NEEDS[target] if not shutil.which(tool)]
    if missing:
        sys.exit("Niet gevonden:\n" + "\n".join(missing))


def read_env():
    return ENV.read_text(encoding="utf-8").splitlines() if ENV.exists() else []


def write_env(lines):
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
    if not yes("Hackstand voor de hacking week (een klas achter één adres)?"):
        return {"THROTTLE_IP_MODE": None, "THROTTLE_PAIR_EXEMPT_USERS": None}
    # Dezelfde regel als een gebruikersnaam in de app; "-" is geen demo-account.
    demo = ask("Demo-account zonder teller per naam (- voor geen)", "hackingweek", r"[A-Za-z0-9_]{3,20}|-")
    return {"THROTTLE_IP_MODE": "hackweek", "THROTTLE_PAIR_EXEMPT_USERS": None if demo == "-" else demo}


def local():
    check_tools("lokaal")
    added = ensure_env()
    if added:
        print("Nieuw in .env:", ", ".join(added))
    # Zonder terminal blijft wat er in .env staat; HTTPS_ONLY zet compose.yaml lokaal op 0 (HTTP).
    if INTERACTIVE:
        settings = hackstand()
        # Nog steeds interactief: er is echt geantwoord, dus de keuze mag in .env.
        if INTERACTIVE:
            for name, value in settings.items():
                set_env(name, value)
    subprocess.run([shutil.which("docker"), "compose", "up", "-d", "--build", "--wait"], cwd=REPO, check=True)
    print("De app draait op http://127.0.0.1:5000")


# Nog niet automatisch: eerst de image en de koppeling met GitHub (OIDC). Wel de juiste stappen, met deze keuzes.
def azure():
    check_tools("azure")
    env = ask("Omgeving", "dev", r"dev|test|prod") if INTERACTIVE else "dev"
    hack = hackstand() if INTERACTIVE else {"THROTTLE_IP_MODE": None, "THROTTLE_PAIR_EXEMPT_USERS": None}
    image = "ghcr.io/youssefontys/secure-application:<tag>"
    variables = [f"environment={env}", f"app_image={image}"]
    if hack["THROTTLE_IP_MODE"]:
        variables += ["throttle_ip_mode=hackweek", "min_replicas=1"]
    if hack["THROTTLE_PAIR_EXEMPT_USERS"]:
        variables.append(f"throttle_pair_exempt_users={hack['THROTTLE_PAIR_EXEMPT_USERS']}")
    print("\nAzure rolt nog niet automatisch uit. De stappen:")
    print("  1. Eenmalig de Terraform-state:  python scripts/azuresetup_v2.py")
    print(f"  2. De image:                     docker build -t {image} app  en  docker push {image}")
    print(f"  3. Terraform:                    terraform -chdir=terraform init -backend-config=../backend.{env}.conf")
    print("                                   terraform -chdir=terraform apply " + " ".join(f"-var {v}" for v in variables))
    print("  4. Het schema, eenmalig:         het commando uit de output schema_job_command")
    sys.exit(1)


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
    sys.exit(f"Onbekende keuze: {choice!r}. Kies lokaal of azure.")
