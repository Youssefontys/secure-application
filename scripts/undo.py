# Everything gone again, on Azure and locally. Start through deployment.py undo.
# Every step asks first, no by default; so without a terminal nothing happens.

import os
import re
import shutil
import subprocess

from deployment import ENV, REPO, SECRETS, check_tools, stop, terraform, yes


def run():
    conf = REPO / "backend.conf"
    # Azure first, and the state storage last: without state Terraform no longer knows what must go.
    if not conf.exists():
        print("☁️  No backend.conf, so no deployment on Azure that Terraform knows.")
    elif yes("☁️  Remove everything on Azure: the app, the database with all notes, and the storage of the state?"):
        check_tools("azure")
        # For removing the values do not matter, but Terraform wants them, and checks the address.
        if not (terraform("init", "-input=false", "-reconfigure", "-backend-config=../backend.conf")
                and terraform("destroy", "-var=app_image=gone", "-var=alert_email=nobody@example.com")):
            stop("terraform destroy did not work, or you did not type yes; the state storage and backend.conf stay.\n"
                 "   💡 Is the state storage itself already gone? Then only remove backend.conf.")
        rg = re.search(r'^resource_group_name\s*=\s*"([A-Za-z0-9_.-]+)"', conf.read_text(encoding="utf-8"), re.M)
        if not rg:
            stop("No resource group in backend.conf; remove the state storage yourself in the portal.")
        print(f"\n🗄️  Removing the state storage: {rg.group(1)}. ☕ This takes a few minutes.")
        if subprocess.run([shutil.which("az"), "group", "delete", "--name", rg.group(1), "--yes"]).returncode != 0:
            stop("az group delete did not work; backend.conf stays, so you can try again.")
        conf.unlink()
        # Only a cache: the providers and where the state was; init fetches it again.
        shutil.rmtree(REPO / "terraform" / ".terraform", ignore_errors=True)
        print("   ✅ Gone, with backend.conf and terraform/.terraform. Through purge protection the Key Vaults stay\n"
              "      deleted for 90 days; that costs nothing, and a new deployment picks new names.\n"
              "   💡 Azure makes NetworkWatcherRG itself for a virtual network; it costs nothing and comes back\n"
              "      by itself on a new deployment, so it stays.")
    if yes("🐳 Remove locally: the containers, the database with all notes, the built image and .env?"):
        check_tools("local")
        # The database first: without .env but with the old database in the volume the app no longer starts.
        # compose.yaml requires the secrets on down too (${...:?}), so without .env placeholder values; down does not use them.
        env = {**os.environ, **dict.fromkeys(SECRETS, "undo")}
        if subprocess.run([shutil.which("docker"), "compose", "down", "--volumes", "--rmi", "local"], cwd=REPO, env=env).returncode != 0:
            stop("docker compose down did not work; .env stays, otherwise it no longer matches the database.\n"
                 "   💡 Is Docker running (on Windows: Docker Desktop)? Start it and try again.")
        ENV.unlink(missing_ok=True)
        print("   ✅ Gone. Start again: python scripts/deployment.py local")
    print("\n👋 Done.\n")
