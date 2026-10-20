# Rolt de app uit: lokaal met Docker Compose, of op Azure met Terraform (terraform/), en maakt dat weer ongedaan.
# Gebruik: python scripts/deployment.py          vraagt alles
#          python scripts/deployment.py lokaal   lokaal; zonder terminal (zoals in CI) zonder vragen
#          python scripts/deployment.py azure    de state-opslag (eenmalig), de image van GitHub, en Terraform
#          python scripts/deployment.py undo     alles weer weg, op Azure en lokaal; vraagt per stap
# Elk doel staat in een eigen bestand (deploy_local.py, deploy_azure.py, undo.py); wat ze delen staat hier: paden,
# vragen, stoppen en de hackstand.
# Werkt op Windows en Linux: geen shell, alleen lijsten van argumenten.

import re
import shutil
import subprocess
import sys
from pathlib import Path

# De doelen importeren wat ze delen uit dit bestand. Als script heet het __main__; zo is het onder beide namen dezelfde
# module, met dezelfde INTERACTIVE.
sys.modules.setdefault("deployment", sys.modules[__name__])

# Emoji ook als de uitvoer naar een pipe of bestand gaat: Python voor 3.15 schrijft daar op Windows cp1252.
# Een stream zonder reconfigure (IDLE, een test) kan al Unicode.
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent.parent
ENV = REPO / ".env"
# Deze geheimen moeten in .env staan; ontbreekt er een of is hij leeg, dan maakt deploy_local.py hem aan.
SECRETS = ("POSTGRES_PASSWORD", "APP_DB_PASSWORD", "FLASK_SECRET_KEY", "DATA_ENCRYPTION_KEY")
# Wat er per doel op de machine moet staan, en waarvoor.
NEEDS = {
    "lokaal": [("docker", "Docker met Compose v2, voor de containers")],
    "azure": [("az", "de Azure CLI, om in te loggen en de Terraform-state op te zetten"),
              ("terraform", "Terraform 1.11 of nieuwer, voor de resources"),
              ("git", "Git, om de image te vinden die GitHub van je app/ bouwde")],
}
# Zonder terminal geen vragen: dan gelden de standaardwaarden. ask() zet hem uit bij EOF, dus lees hem in de doelen als
# deployment.INTERACTIVE, niet via een from-import die de oude waarde houdt.
INTERACTIVE = sys.stdin.isatty()


# Stoppen met de melding, met witregels eromheen zodat hij opvalt; zelfde vorm als setup_azure.py.
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


# Terraform in terraform/, met de uitvoer en de vragen gewoon in deze terminal.
def terraform(*args):
    return subprocess.run([shutil.which("terraform"), "-chdir=terraform", *args], cwd=REPO).returncode == 0


if __name__ == "__main__":
    # Pas hier: de doelen importeren wat hierboven staat, dus dat moet er al zijn.
    import deploy_azure
    import deploy_local
    import undo

    TARGETS = {"lokaal": deploy_local, "azure": deploy_azure, "undo": undo}
    print("\n🛡️  Notities-app uitrollen")
    print("👋 Welkom! Ik loop alles met je door. Enter kiest steeds wat tussen [ ] staat.\n")
    if len(sys.argv) > 1:
        choice = sys.argv[1]
    elif INTERACTIVE:
        choice = ask("🧭 Waar rol je uit? lokaal of azure (of undo)", "lokaal", r"lokaal|azure|undo")
    else:
        choice = "lokaal"
    if choice not in TARGETS:
        stop(f"Onbekende keuze: {choice!r}. Kies lokaal, azure of undo.", icon="🤔")
    TARGETS[choice].run()
