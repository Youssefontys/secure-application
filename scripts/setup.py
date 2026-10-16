# Rolt de app uit: lokaal met Docker Compose, of op Azure (de Terraform-code volgt).
# Gebruik: python scripts/setup.py [lokaal|azure]

import secrets
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ENV = REPO / ".env"
# Deze geheimen moeten in .env staan; ontbreekt er een of is hij leeg, dan maakt setup hem aan.
SECRETS = ("POSTGRES_PASSWORD", "FLASK_SECRET_KEY", "DATA_ENCRYPTION_KEY")


# Vult ontbrekende of lege geheimen in .env aan met 256 willekeurige bits; toont ze nooit.
def ensure_env():
    lines = ENV.read_text(encoding="utf-8").splitlines() if ENV.exists() else []
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
    ENV.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="")
    return new + missing


def local():
    added = ensure_env()
    if added:
        print("Nieuw in .env:", ", ".join(added))
    # Argumenten als lijst, zonder shell: niets uit de invoer kan als commando worden gelezen.
    subprocess.run(["docker", "compose", "up", "-d", "--build", "--wait"], cwd=REPO, check=True)
    print("De app draait op http://127.0.0.1:5000")


def azure():
    print("Azure is nog niet klaar: de Terraform-code voor de database, Key Vault en de app volgt.")
    print("Het script voor de Terraform-state staat al in scripts/azuresetup_v2.py.")
    sys.exit(1)


choice = sys.argv[1] if len(sys.argv) > 1 else input("Waar rol je uit? [1] lokaal (Docker Compose)  [2] Azure: ").strip()
if choice in ("1", "lokaal"):
    local()
elif choice in ("2", "azure"):
    azure()
else:
    sys.exit(f"Onbekende keuze: {choice!r}. Kies 1 (lokaal) of 2 (Azure).")
