# Rolt de app uit: lokaal met Docker Compose, of op Azure met Terraform (terraform/), en maakt dat weer ongedaan.
# Gebruik: python scripts/deployment.py          vraagt alles
#          python scripts/deployment.py lokaal   lokaal; zonder terminal (zoals in CI) zonder vragen
#          python scripts/deployment.py azure    de state-opslag (eenmalig), de image van GitHub, en Terraform
#          python scripts/deployment.py undo     alles weer weg, op Azure en lokaal; vraagt per stap
# Elk doel staat in een eigen bestand (deploy_local.py, deploy_azure.py, undo.py); wat ze delen in common.py.
# Werkt op Windows en Linux: geen shell, alleen lijsten van argumenten.

import sys

import common
import deploy_azure
import deploy_local
import undo
from common import ask, stop

TARGETS = {"lokaal": deploy_local, "azure": deploy_azure, "undo": undo}

print("\n🛡️  Notities-app uitrollen")
print("👋 Welkom! Ik loop alles met je door. Enter kiest steeds wat tussen [ ] staat.\n")
if len(sys.argv) > 1:
    choice = sys.argv[1]
elif common.INTERACTIVE:
    choice = ask("🧭 Waar rol je uit? lokaal of azure (of undo)", "lokaal", r"lokaal|azure|undo")
else:
    choice = "lokaal"
if choice not in TARGETS:
    stop(f"Onbekende keuze: {choice!r}. Kies lokaal, azure of undo.", icon="🤔")
TARGETS[choice].run()
