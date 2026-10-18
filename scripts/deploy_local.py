# Lokaal uitrollen met Docker Compose: de geheimen in .env, de hackstand, en de containers. Start via deployment.py.

import secrets
import shutil
import subprocess

import common
from common import ENV, REPO, SECRETS, check_tools, hackstand, stop


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


def run():
    check_tools("lokaal")
    added = ensure_env()
    print(f"\n🔑 Nieuwe geheimen in .env: {', '.join(added)} (elk 256 willekeurige bits, nooit getoond)" if added
          else "\n🔐 .env: alle geheimen staan er al")
    # Zonder terminal blijft wat er in .env staat; HTTPS_ONLY zet compose.yaml lokaal op 0 (HTTP).
    if common.INTERACTIVE:
        settings = hackstand()
        # Nog steeds interactief: er is echt geantwoord, dus de keuze mag in .env.
        if common.INTERACTIVE:
            for name, value in settings.items():
                set_env(name, value)
    print("\n🐳 Containers bouwen en starten... ☕ de eerste keer duurt dit even.\n")
    if subprocess.run([shutil.which("docker"), "compose", "up", "-d", "--build", "--wait"], cwd=REPO).returncode != 0:
        stop("docker compose up lukte niet; de melding van Docker staat hierboven.\n"
             "   💡 Draait Docker (op Windows: Docker Desktop)? Start het en probeer het opnieuw.")
    print("\n🎉 Klaar! De app draait op http://127.0.0.1:5000")
    print("💡 Stoppen kan met: docker compose down; alles weg, ook de data: python scripts/deployment.py undo\n")
