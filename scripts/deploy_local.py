# Deploying locally with Docker Compose: the secrets in .env, hackmode, and the containers. Start through deployment.py.

import secrets
import shutil
import subprocess

import deployment
from deployment import ENV, REPO, SECRETS, check_tools, hackmode, stop


def read_env():
    return ENV.read_text(encoding="utf-8").splitlines() if ENV.exists() else []


# Only the owner may read .env (0600), already before writing; otherwise every user of the machine reads
# the keys too (MIT-32). On Windows chmod only sets the read-only flag, and that stays off.
def write_env(lines):
    ENV.touch(mode=0o600, exist_ok=True)
    ENV.chmod(0o600)
    ENV.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="")


# Fills in missing or empty secrets in .env with 256 random bits; never shows them.
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


# Sets a setting in .env, or removes it for None; commented lines stay.
def set_env(name, value):
    lines = [line for line in read_env() if line.lstrip().startswith("#") or line.partition("=")[0].strip() != name]
    if value is not None:
        lines.append(f"{name}={value}")
    write_env(lines)


def run():
    check_tools("local")
    added = ensure_env()
    print(f"\n🔑 New secrets in .env: {', '.join(added)} (each 256 random bits, never shown)" if added
          else "\n🔐 .env: all secrets are already there")
    # Without a terminal, what is in .env stays; compose.yaml sets HTTPS_ONLY to 0 locally (HTTP).
    if deployment.INTERACTIVE:
        settings = hackmode()
        # Still interactive: there really was an answer, so the choice may go into .env.
        if deployment.INTERACTIVE:
            for name, value in settings.items():
                set_env(name, value)
    print("\n🐳 Building and starting the containers... ☕ the first time this takes a while.\n")
    if subprocess.run([shutil.which("docker"), "compose", "up", "-d", "--build", "--wait"], cwd=REPO).returncode != 0:
        stop("docker compose up did not work; the message from Docker is above.\n"
             "   💡 Is Docker running (on Windows: Docker Desktop)? Start it and try again.")
    print("\n🎉 Done! The app runs on http://127.0.0.1:5000")
    print("💡 Stop it with: docker compose down; everything gone, the data too: python scripts/deployment.py undo\n")
