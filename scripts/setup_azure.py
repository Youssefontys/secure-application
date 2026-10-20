# Sets up the storage for the Terraform state on Azure once; after that Terraform does the rest (deployment.py azure).
# - The storage is encrypted with its own key (RSA 4096) in Key Vault, with purge protection.
# - Separated roles: whoever runs this manages the key; the identity of the storage may only use it.
# - No shell: every command is a list of arguments. On Windows az is a .cmd file and cmd.exe still reads
#   the arguments again, so the real protection is the allowlist on all input (letters, digits, - _ .).
# Taken from BOK-SECENGINEER, then adapted; the changes are in the git history. Works on Windows and Linux.

import random
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Emoji also when the output goes to a pipe or file: Python before 3.15 writes cp1252 there on Windows.
# A stream without reconfigure (IDLE, a test) can already do Unicode.
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")

# backend.conf goes into the root folder of the repo, where deployment.py and terraform init look for it.
BACKEND_CONF = Path(__file__).resolve().parent.parent / "backend.conf"
# West Europe takes no new tenants (RequestDisallowedByAzure); the same region as terraform/variables.tf.
DEFAULT_LOCATION = "francecentral"
# Struck through in the question; whoever already has resources there may still type it in.
CLOSED_LOCATION = "westeurope"
DEFAULT_RG_NAME = "rg-tfstate-mgmt"
PROPAGATION_WAIT = 120
# Allowlist for a subscription ID: a GUID, nothing else.
GUID = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
# Errors that belong to propagation in Azure and pass by themselves, and errors that mean it is already there.
RETRYABLE = ("ResourceNotFound", "ConnectionAbortedError", "PrincipalNotFound", "AuthorizationFailed")
IGNORABLE = ("RoleAssignmentExists", "already exists")


# The command as a list of arguments, without a shell; the program through PATH (on Windows az.cmd).
def as_args(*args):
    return [shutil.which(args[0]) or args[0], *args[1:]]


# Stop with the message, with blank lines around it so it stands out; same form as deployment.py.
def stop(message, icon="❌"):
    sys.exit(f"\n{icon} {message}\n\n🛑 Stopping.\n")


# The error of az once: the lines Code, Message and Target usually repeat the first line.
def az_error(stderr):
    lines = [line for line in stderr.strip().splitlines() if not line.startswith("WARNING:")] or [""]
    first = lines[0].removeprefix("ERROR: ")
    return "\n".join([first, *(line for line in lines[1:] if not ((value := line.partition(": ")[2]) and value in first))])


# Runs az and returns the output; on an error stop, or None with ignore_error.
def az(*args, ignore_error=False):
    result = subprocess.run(as_args("az", *args), capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    if ignore_error:
        return None
    stop(f"ERROR: {az_error(result.stderr)}")


# Like az, but try again while Azure is still busy; "already exists" counts as success. Only a new attempt reports itself.
def az_retry(*args, tries=10, delay=10):
    for attempt in range(1, tries + 1):
        result = subprocess.run(as_args("az", *args), capture_output=True, text=True)
        err = result.stderr.strip()
        if result.returncode == 0 or any(x in err for x in IGNORABLE):
            return result.stdout.strip()
        if attempt == tries or not any(x in err for x in RETRYABLE):
            stop(f"ERROR: {az_error(err)}")
        print(f"   ⏳ Azure is still busy; in {delay}s attempt {attempt + 1} of {tries}...")
        time.sleep(delay)
        delay += 5


def assign(role, assignee, scope):
    print(f"   🔑 {role}")
    az_retry("role", "assignment", "create", "--role", role, "--assignee", assignee, "--scope", scope, "-o", "none")


# A question with a default; with pattern only an answer that fully meets it.
# shown replaces what is between the brackets, for example with an option that is not possible.
def ask_user(question, default=None, pattern=None, shown=None):
    prompt = f"{question} [{shown or default}]: " if default else f"{question}: "
    while True:
        ans = input(prompt).strip() or default
        if ans is None:
            continue
        if pattern is None or re.fullmatch(pattern, ans):
            return ans
        print("🤔 That is not possible: only letters, digits and - _ . are allowed.")


# The deployment itself.
print("\n🛡️  Azure Terraform Bootstrap")
print("👋 Once: the storage in which Terraform remembers what is on Azure. After that Terraform does the rest.")
print("   Enter always picks what is between [ ].\n")

# 1. Signed in and the subscription; read the IDs only after that, also the tenant of another subscription.
# Starting az login here is not possible: az() captures the output, and then the subscription choice waits invisibly.
name = az("account", "show", "--query", "name", "-o", "tsv", ignore_error=True)
if not name:
    stop("First sign in to Azure: az login\n"
         "   Does it say \"Authentication failed against tenant <ID>\" with AADSTS50076? Then that tenant wants MFA:\n"
         "   az login --tenant <ID>\n   Then run this script again.", icon="🔐")
print(f"☁️  Signed in to Azure, subscription: {name}")
if ask_user("🔀 Another subscription? (y/n)", "n").lower() == "y":
    az("account", "set", "--subscription", ask_user("Subscription ID", pattern=GUID))
sub_id = az("account", "show", "--query", "id", "-o", "tsv")
tenant_id = az("account", "show", "--query", "tenantId", "-o", "tsv")
me = az("ad", "signed-in-user", "show", "--query", "id", "-o", "tsv")

# 2. Providers
print("\n🧩 Registering providers, once per subscription...")
for namespace in ("Microsoft.Storage", "Microsoft.KeyVault", "Microsoft.ManagedIdentity"):
    az_retry("provider", "register", "--namespace", namespace, "--wait", "-o", "none", tries=2)
    print(f"   ✅ {namespace}")

# 3. Input; with four digits after it the name of the storage stays within the 3 to 24 characters of Azure.
print("\n📝 A few choices; the default is fine:")
rg = ask_user("Resource Group name", DEFAULT_RG_NAME, pattern=r"[A-Za-z0-9_.-]{0,89}[A-Za-z0-9_-]")
# Strike through with a combining stroke per letter: works in every terminal that shows UTF-8, without colour codes.
closed = "".join(char + "̶" for char in CLOSED_LOCATION)
location = ask_user("Region", DEFAULT_LOCATION, pattern=r"[a-z0-9]+", shown=f"{DEFAULT_LOCATION} | {closed} takes no new customers")
container = ask_user("Blob container name", "tfstate", pattern=r"[a-z0-9](?!.*--)[a-z0-9-]{1,61}[a-z0-9]")
prefix = ask_user("Storage prefix (3-10 chars)", "tfstate", pattern=r"[a-z0-9]{3,10}")
sa_name = f"{prefix}{random.randint(1000, 9999)}"
suffix = random.randint(1000, 9999)
mi_name, kv_name, key_name = f"mi-{prefix}-{suffix}", f"kv-{prefix}-{suffix}", "tfstate-cmk-key"
if ask_user("\n🚦 Start? (y/n)", "y").lower() != "y":
    print("👋 Nothing created. See you later!")
    sys.exit(0)

print(f"\n🚀 Here we go, in {location}. This takes a few minutes.\n")
az("group", "create", "--name", rg, "--location", location, "-o", "none")
print(f"📁 Resource group: {rg}")

# A. The identity of the storage, and wait until Azure knows it.
print(f"🪪 Identity for the storage: {mi_name}")
az_retry("identity", "create", "--name", mi_name, "--resource-group", rg, "--location", location, "-o", "none")
print("   ⏳ Waiting a moment until Azure knows it everywhere...")
for _ in range(12):
    mi_principal_id = az("identity", "show", "--name", mi_name, "--resource-group", rg,
                         "--query", "principalId", "-o", "tsv", ignore_error=True)
    if mi_principal_id:
        break
    time.sleep(5)
uami_id = f"/subscriptions/{sub_id}/resourceGroups/{rg}/providers/Microsoft.ManagedIdentity/userAssignedIdentities/{mi_name}"

# B. Key Vault with separated roles: you manage the key, the identity may only use it.
print(f"🔐 Key Vault: {kv_name}")
az("keyvault", "create", "--name", kv_name, "--resource-group", rg, "--location", location,
   "--enable-rbac-authorization", "true", "--enable-purge-protection", "true", "--retention-days", "90", "-o", "none")
kv_scope = f"/subscriptions/{sub_id}/resourceGroups/{rg}/providers/Microsoft.KeyVault/vaults/{kv_name}"
assign("Key Vault Crypto Officer", me, kv_scope)
assign("Key Vault Crypto Service Encryption User", mi_principal_id, kv_scope)

# C. The own key (RSA 4096).
print(f"🗝️  Own key (RSA 4096): {key_name}")
time.sleep(15)
az_retry("keyvault", "key", "create", "--vault-name", kv_name, "--name", key_name, "--kty", "RSA", "--size", "4096", "-o", "none")

# D. The storage, encrypted with that key, only over HTTPS and not public.
# Without account keys: otherwise whoever may request the keys reads the state outside the roles; Terraform signs in through Entra.
print(f"📦 Storage: {sa_name}, encrypted with that key, only over HTTPS and without account keys")
kv_uri = az("keyvault", "show", "--name", kv_name, "--query", "properties.vaultUri", "-o", "tsv")
az_retry("storage", "account", "create", "--name", sa_name, "--resource-group", rg, "--location", location,
         "--sku", "Standard_LRS", "--kind", "StorageV2", "--allow-blob-public-access", "false",
         "--min-tls-version", "TLS1_2", "--https-only", "true", "--allow-shared-key-access", "false",
         "--identity-type", "UserAssigned", "--user-identity-id", uami_id,
         "--encryption-key-source", "Microsoft.Keyvault", "--encryption-key-vault", kv_uri,
         "--encryption-key-name", key_name, "--encryption-services", "blob",
         "--key-vault-user-identity-id", uami_id, "-o", "none")
print("♻️  Keeping previous versions, and 7 days to restore after deleting")
az_retry("storage", "account", "blob-service-properties", "update", "--account-name", sa_name, "--resource-group", rg,
         "--enable-versioning", "true", "--enable-delete-retention", "true", "--delete-retention-days", "7",
         "--enable-container-delete-retention", "true", "--container-delete-retention-days", "7", "-o", "none")
sa_scope = f"/subscriptions/{sub_id}/resourceGroups/{rg}/providers/Microsoft.Storage/storageAccounts/{sa_name}"
# What HashiCorp recommends for the backend. The identity gets nothing here: Storage only uses it for the key.
assign("Storage Blob Data Contributor", me, sa_scope)
print(f"⏳ Waiting {PROPAGATION_WAIT // 60} minutes until Azure knows the key and the rights everywhere... ☕")
time.sleep(PROPAGATION_WAIT)
az_retry("storage", "container", "create", "--name", container, "--account-name", sa_name, "--auth-mode", "login", "-o", "none")
print(f"🗃️  Container: {container}")

# E. The backend file for terraform init; one environment, so one state.
with open(BACKEND_CONF, "w", encoding="utf-8", newline="\n") as f:
    f.write(f'resource_group_name  = "{rg}"\nstorage_account_name = "{sa_name}"\ncontainer_name       = "{container}"\n'
            f'key                  = "terraform.tfstate"\nuse_azuread_auth     = true\n\n'
            f'subscription_id      = "{sub_id}"\ntenant_id            = "{tenant_id}"\n')

print(f"\n📝 backend.conf written: {BACKEND_CONF}")
print("\n🎉 Done! The door for Terraform is open.")
print("👉 python scripts/deployment.py azure does the rest; if that started this script, it now continues by itself.\n")
