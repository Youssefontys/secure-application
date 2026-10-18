# Alles weer weg, op Azure en lokaal. Start via setup.py opruimen.
# Elke stap vraagt eerst, standaard nee; zonder terminal gebeurt er dus niets.

import os
import re
import shutil
import subprocess

from common import ENV, REPO, SECRETS, check_tools, stop, terraform, yes


def run():
    conf = REPO / "backend.conf"
    # Azure eerst, en de state-opslag als laatste: zonder state weet Terraform niet meer wat er weg moet.
    if not conf.exists():
        print("☁️  Geen backend.conf, dus geen uitrol op Azure die Terraform kent.")
    elif yes("☁️  Alles op Azure weghalen: de app, de database met alle notities, en de opslag van de state?"):
        check_tools("azure")
        # Voor weghalen maakt de waarde niet uit, maar Terraform wil ze hebben, en controleert het adres.
        if not (terraform("init", "-input=false", "-reconfigure", "-backend-config=../backend.conf")
                and terraform("destroy", "-var=app_image=weg", "-var=alert_email=niemand@example.com")):
            stop("terraform destroy lukte niet, of je typte geen yes; de state-opslag en backend.conf blijven staan.\n"
                 "   💡 Is de state-opslag zelf al weg? Haal dan alleen backend.conf weg.")
        rg = re.search(r'^resource_group_name\s*=\s*"([A-Za-z0-9_.-]+)"', conf.read_text(encoding="utf-8"), re.M)
        if not rg:
            stop("Geen resource group in backend.conf; haal de state-opslag zelf weg in de portal.")
        print(f"\n🗄️  De state-opslag weghalen: {rg.group(1)}. ☕ Dit duurt een paar minuten.")
        if subprocess.run([shutil.which("az"), "group", "delete", "--name", rg.group(1), "--yes"]).returncode != 0:
            stop("az group delete lukte niet; backend.conf blijft staan, zodat je het opnieuw kunt proberen.")
        conf.unlink()
        # Alleen een cache: de providers en waar de state stond; init haalt hem opnieuw op.
        shutil.rmtree(REPO / "terraform" / ".terraform", ignore_errors=True)
        print("   ✅ Weg, met backend.conf en terraform/.terraform. De Key Vaults blijven door purge protection\n"
              "      90 dagen als verwijderd staan; dat kost niets, en een nieuwe uitrol kiest nieuwe namen.\n"
              "   💡 NetworkWatcherRG maakt Azure zelf bij een virtueel netwerk; die kost niets en komt bij een\n"
              "      nieuwe uitrol vanzelf terug, dus die blijft staan.")
    if yes("🐳 Lokaal weghalen: de containers, de database met alle notities, de gebouwde image en .env?"):
        check_tools("lokaal")
        # Eerst de database: zonder .env maar met de oude database in het volume start de app niet meer.
        # compose.yaml eist de geheimen ook bij down (${...:?}), dus zonder .env vulwaarden; down gebruikt ze niet.
        env = {**os.environ, **dict.fromkeys(SECRETS, "opruimen")}
        if subprocess.run([shutil.which("docker"), "compose", "down", "--volumes", "--rmi", "local"], cwd=REPO, env=env).returncode != 0:
            stop("docker compose down lukte niet; .env blijft staan, anders past hij niet meer bij de database.\n"
                 "   💡 Draait Docker (op Windows: Docker Desktop)? Start het en probeer het opnieuw.")
        ENV.unlink(missing_ok=True)
        print("   ✅ Weg. Opnieuw beginnen: python scripts/setup.py lokaal")
    print("\n👋 Klaar.\n")
