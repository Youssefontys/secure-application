# Rolt de app uit: lokaal met Docker Compose, of op Azure met Terraform (terraform/), en ruimt hem weer op.
# Gebruik: python scripts/setup.py          vraagt alles
#          python scripts/setup.py lokaal   lokaal; zonder terminal (zoals in CI) zonder vragen
#          python scripts/setup.py azure    de state-opslag (eenmalig), de image van GitHub, en Terraform
#          python scripts/setup.py opruimen alles weer weg, op Azure en lokaal; vraagt per stap
# Elk doel staat in een eigen bestand (deploy_local.py, deploy_azure.py, cleanup.py); wat ze delen in common.py.
# Werkt op Windows en Linux: geen shell, alleen lijsten van argumenten.

import sys

import cleanup
import common
import deploy_azure
import deploy_local
from common import ask, stop

TARGETS = {"lokaal": deploy_local, "azure": deploy_azure, "opruimen": cleanup}

print("\n🛡️  Notities-app uitrollen")
print("👋 Welkom! Ik loop alles met je door. Enter kiest steeds wat tussen [ ] staat.\n")
if len(sys.argv) > 1:
    choice = sys.argv[1]
elif common.INTERACTIVE:
    choice = ask("🧭 Waar rol je uit? lokaal of azure (of opruimen)", "lokaal", r"lokaal|azure|opruimen")
else:
    choice = "lokaal"
if choice not in TARGETS:
    stop(f"Onbekende keuze: {choice!r}. Kies lokaal, azure of opruimen.", icon="🤔")
TARGETS[choice].run()
