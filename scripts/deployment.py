# Deploys the app: locally with Docker Compose, or on Azure with Terraform (terraform/), and undoes that again.
# Usage: python scripts/deployment.py          asks everything
#        python scripts/deployment.py local    locally; without a terminal (as in CI) without questions
#        python scripts/deployment.py azure    the state storage (once), the image from GitHub, and Terraform
#        python scripts/deployment.py undo     everything gone again, on Azure and locally; asks per step
# Each target is in a file of its own (deploy_local.py, deploy_azure.py, undo.py); what they share is here: paths,
# questions, stopping and hackmode.
# Works on Windows and Linux: no shell, only lists of arguments.

import re
import shutil
import subprocess
import sys
from pathlib import Path

# The targets import what they share from this file. As a script it is called __main__; this way it is the same module
# under both names, with the same INTERACTIVE.
sys.modules.setdefault("deployment", sys.modules[__name__])

# Emoji also when the output goes to a pipe or file: Python before 3.15 writes cp1252 there on Windows.
# A stream without reconfigure (IDLE, a test) can already do Unicode.
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent.parent
ENV = REPO / ".env"
# These secrets must be in .env; if one is missing or empty, deploy_local.py creates it.
SECRETS = ("POSTGRES_PASSWORD", "APP_DB_PASSWORD", "FLASK_SECRET_KEY", "DATA_ENCRYPTION_KEY")
# What must be on the machine per target, and what for.
NEEDS = {
    "local": [("docker", "Docker with Compose v2, for the containers")],
    "azure": [("az", "the Azure CLI, to sign in and set up the Terraform state"),
              ("terraform", "Terraform 1.11 or newer, for the resources"),
              ("git", "Git, to find the image GitHub built from your app/")],
}
# Without a terminal no questions: then the defaults apply. ask() turns it off on EOF, so read it in the targets as
# deployment.INTERACTIVE, not through a from-import that keeps the old value.
INTERACTIVE = sys.stdin.isatty()


# Stop with the message, with blank lines around it so it stands out; same form as setup_azure.py.
def stop(message, icon="❌"):
    sys.exit(f"\n{icon} {message}\n\n🛑 Stopping.\n")


# A question with a default; only an answer that fully matches pattern (allowlist, MIT-22).
# No input (EOF) counts as no terminal: on Windows NUL also looks like one.
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
        print("🤔 I do not know that answer; please try again.")


def yes(question):
    return ask(f"{question} (y/n)", "n", r"[yYnN]").lower() == "y"


# Stops with a list of what is missing, before anything happens.
def check_tools(target):
    print("🔍 Checking that everything is there...")
    missing = [f"   ❓ {tool}: {why}" for tool, why in NEEDS[target] if not shutil.which(tool)]
    if missing:
        stop("Not found yet:\n" + "\n".join(missing) + "\n   💡 Install what is missing and then start this script again.")
    for tool, why in NEEDS[target]:
        print(f"   ✅ {tool}: {why}")


# Hackmode for the hacking week (MC-18), off by default. Returns the settings, or None per setting.
def hackmode():
    print("\n🏫 Hackmode, only for the hacking week, when the whole class attacks from one school address:\n"
          "   n  🙂 normal (default): per address 20 failed login attempts per quarter of an hour and 10 new accounts per hour\n"
          "   y  🏁 hacking week: per address 100 failed login attempts per quarter of an hour and 60 new accounts per hour,\n"
          "         so classmates do not lock each other out")
    if not yes("Hackmode on?"):
        return {"THROTTLE_IP_MODE": None, "THROTTLE_PAIR_EXEMPT_USERS": None}
    print("\n🎯 A shared demo account that everyone may attack: wrong passwords then do not lock it for the rest.")
    # The same rule as a username in the app; "-" is no demo account.
    demo = ask("Name of the demo account (- for none)", "hackingweek", r"[A-Za-z0-9_]{3,20}|-")
    return {"THROTTLE_IP_MODE": "hackweek", "THROTTLE_PAIR_EXEMPT_USERS": None if demo == "-" else demo}


# Terraform in terraform/, with the output and the questions simply in this terminal.
def terraform(*args):
    return subprocess.run([shutil.which("terraform"), "-chdir=terraform", *args], cwd=REPO).returncode == 0


# Git in this folder; None if it does not work.
def git(*args):
    result = subprocess.run([shutil.which("git"), *args], cwd=REPO, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


# owner/name of the GitHub repo, from the remote origin; also for whoever copied the repo. An allowlist (MIT-22).
def github_repo():
    match = re.search(r"github\.com[:/]([\w.-]+/[\w.-]+?)(?:\.git)?/?$", git("remote", "get-url", "origin") or "")
    return match and match.group(1)


# The GitHub CLI, signed in; None if it is not there. Only for deploying from GitHub (MIT-44), so not in NEEDS.
def gh(*args, stdin=None):
    if not shutil.which("gh"):
        return None
    result = subprocess.run([shutil.which("gh"), *args], input=stdin, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


if __name__ == "__main__":
    # Only here: the targets import what is above, so that must exist already.
    import deploy_azure
    import deploy_local
    import undo

    TARGETS = {"local": deploy_local, "azure": deploy_azure, "undo": undo}
    print("\n🛡️  Deploying the notes app")
    print("👋 Welcome! I will walk you through everything. Enter always picks what is between [ ].\n")
    if len(sys.argv) > 1:
        choice = sys.argv[1]
    elif INTERACTIVE:
        choice = ask("🧭 Where do you deploy? local or azure (or undo)", "local", r"local|azure|undo")
    else:
        choice = "local"
    if choice not in TARGETS:
        stop(f"Unknown choice: {choice!r}. Choose local, azure or undo.", icon="🤔")
    TARGETS[choice].run()
