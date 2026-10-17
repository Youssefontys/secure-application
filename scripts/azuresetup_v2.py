# Zet eenmalig de opslag voor de Terraform-state op Azure op, plus de koppeling met GitHub Actions (OIDC).
# - De opslag is versleuteld met een eigen sleutel (RSA 4096) in Key Vault, met purge protection.
# - Gescheiden rollen: wie dit draait beheert de sleutel; de identiteit van de opslag mag hem alleen gebruiken.
# - Geen shell: elk commando is een lijst van argumenten. Op Windows is az een .cmd-bestand en leest cmd.exe
#   de argumenten toch opnieuw, dus de echte bescherming is de allowlist op alle invoer (letters, cijfers, - _ .).
# Uit BOK-SECENGINEER, daarna aangepast; de wijzigingen staan in de git-geschiedenis. Werkt op Windows en Linux.

import random
import re
import shutil
import subprocess
import sys
import time

DEFAULT_LOCATION = "westeurope"
DEFAULT_RG_NAME = "rg-tfstate-mgmt"
PROPAGATION_WAIT = 120
# Allowlist voor een subscription ID: een GUID, verder niets.
GUID = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
# Fouten die bij het doorvoeren in Azure horen en vanzelf overgaan, en fouten die betekenen dat het er al is.
RETRYABLE = ("ResourceNotFound", "ConnectionAbortedError", "PrincipalNotFound", "AuthorizationFailed")
IGNORABLE = ("RoleAssignmentExists", "already exists", "Subscription is not registered")


# Het commando als lijst van argumenten, zonder shell; het programma via PATH (op Windows az.cmd).
def as_args(*args):
    return [shutil.which(args[0]) or args[0], *args[1:]]


# Voert az uit en geeft de uitvoer; bij een fout stoppen, of None met ignore_error.
def az(*args, ignore_error=False):
    result = subprocess.run(as_args("az", *args), capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    if ignore_error:
        return None
    sys.exit(f"\n❌ FOUT: {result.stderr.strip()}\n🛑 Stoppen.")


# Zoals az, maar opnieuw proberen zolang Azure nog bezig is; "bestaat al" telt als gelukt.
def az_retry(*args, tries=10, delay=10):
    for attempt in range(1, tries + 1):
        print(f"   ⏳ az {' '.join(args[:2])}... (poging {attempt})")
        result = subprocess.run(as_args("az", *args), capture_output=True, text=True)
        err = result.stderr.strip()
        if result.returncode == 0 or any(x in err for x in IGNORABLE):
            return result.stdout.strip()
        if attempt == tries or not any(x in err for x in RETRYABLE):
            sys.exit(f"❌ FATAL: {err}\n🛑 Stoppen.")
        print(f"    ⚠️ Tijdelijke Azure-fout. Wachten {delay}s...")
        time.sleep(delay)
        delay += 5


def assign(role, assignee, scope):
    az_retry("role", "assignment", "create", "--role", role, "--assignee", assignee, "--scope", scope, "-o", "none")


# Een vraag met een standaardwaarde; met pattern alleen een antwoord dat er helemaal aan voldoet.
def ask_user(question, default=None, pattern=None):
    prompt = f"{question} [{default}]: " if default else f"{question}: "
    while True:
        ans = input(prompt).strip() or default
        if ans is None:
            continue
        if pattern is None or re.fullmatch(pattern, ans):
            return ans
        print("❌ Ongeldige invoer: alleen letters, cijfers en - _ . zijn toegestaan.")


# Is gh er en ingelogd? Anders kunnen de GitHub-secrets niet automatisch.
def gh_ready():
    gh = shutil.which("gh")
    if not gh:
        print("\n⚠️ GitHub CLI (gh) niet gevonden; installeer via https://cli.github.com om de secrets automatisch te zetten.")
        return False
    if subprocess.run([gh, "auth", "status"], capture_output=True).returncode != 0:
        print("❌ gh is niet ingelogd of het token is verlopen: gh auth login")
        return False
    print("✅ gh is ingelogd.")
    return True


# De uitrol zelf.
print("\n🛡️  Azure Terraform Bootstrap\n")

# 1. Inloggen en de subscription; de ID's pas daarna lezen, ook de tenant van een andere subscription.
name = az("account", "show", "--query", "name", "-o", "tsv", ignore_error=True)
if not name:
    print("⚠️ Inloggen...")
    az("login", "-o", "none")
    name = az("account", "show", "--query", "name", "-o", "tsv")
print(f"✅ Context: {name}")
if ask_user("Andere subscription? (j/n)", "n").lower() == "j":
    az("account", "set", "--subscription", ask_user("Subscription ID", pattern=GUID))
sub_id = az("account", "show", "--query", "id", "-o", "tsv")
tenant_id = az("account", "show", "--query", "tenantId", "-o", "tsv")
me = az("ad", "signed-in-user", "show", "--query", "id", "-o", "tsv")

# 2. Providers
print("\n⚙️  Providers check...")
for namespace in ("Microsoft.Storage", "Microsoft.KeyVault", "Microsoft.ManagedIdentity"):
    az_retry("provider", "register", "--namespace", namespace, "--wait", "-o", "none", tries=2)

# 3. Invoer; met vier cijfers erachter blijft de naam van de opslag binnen de 3 tot 24 tekens van Azure.
rg = ask_user("Resource Group naam", DEFAULT_RG_NAME, pattern=r"[A-Za-z0-9_.-]{0,89}[A-Za-z0-9_-]")
location = ask_user("Regio", DEFAULT_LOCATION, pattern=r"[a-z0-9]+")
container = ask_user("Blob container naam", "tfstate", pattern=r"[a-z0-9](?!.*--)[a-z0-9-]{1,61}[a-z0-9]")
prefix = ask_user("Storage prefix (3-10 chars)", "tfstate", pattern=r"[a-z0-9]{3,10}")
sa_name = f"{prefix}{random.randint(1000, 9999)}"
suffix = random.randint(1000, 9999)
mi_name, kv_name, key_name = f"mi-{prefix}-{suffix}", f"kv-{prefix}-{suffix}", "tfstate-cmk-key"
if ask_user("\nStarten? (j/n)", "j").lower() != "j":
    sys.exit(0)

print(f"\n🚀 Start setup in {location}...")
az("group", "create", "--name", rg, "--location", location, "-o", "none")

# A. De identiteit van de opslag, en wachten tot Azure hem kent.
print(f"→ UAMI '{mi_name}' aanmaken...")
az_retry("identity", "create", "--name", mi_name, "--resource-group", rg, "--location", location, "-o", "none")
print("   ⏳ ID propagation...")
for _ in range(12):
    mi_principal_id = az("identity", "show", "--name", mi_name, "--resource-group", rg,
                         "--query", "principalId", "-o", "tsv", ignore_error=True)
    if mi_principal_id:
        break
    time.sleep(5)
mi_client_id = az("identity", "show", "--name", mi_name, "--resource-group", rg, "--query", "clientId", "-o", "tsv")
uami_id = f"/subscriptions/{sub_id}/resourceGroups/{rg}/providers/Microsoft.ManagedIdentity/userAssignedIdentities/{mi_name}"

# B. Key Vault met gescheiden rollen: jij beheert de sleutel, de identiteit mag hem alleen gebruiken.
print(f"→ Key Vault '{kv_name}'...")
az("keyvault", "create", "--name", kv_name, "--resource-group", rg, "--location", location,
   "--enable-rbac-authorization", "true", "--enable-purge-protection", "true", "--retention-days", "90", "-o", "none")
kv_scope = f"/subscriptions/{sub_id}/resourceGroups/{rg}/providers/Microsoft.KeyVault/vaults/{kv_name}"
assign("Key Vault Crypto Officer", me, kv_scope)
assign("Key Vault Crypto Service Encryption User", mi_principal_id, kv_scope)

# C. De eigen sleutel (RSA 4096).
print(f"→ CMK '{key_name}' (RSA 4096)...")
time.sleep(15)
az_retry("keyvault", "key", "create", "--vault-name", kv_name, "--name", key_name, "--kty", "RSA", "--size", "4096", "-o", "none")

# D. De opslag, versleuteld met die sleutel, alleen over HTTPS en niet publiek.
print(f"→ Storage '{sa_name}' met CMK...")
kv_uri = az("keyvault", "show", "--name", kv_name, "--query", "properties.vaultUri", "-o", "tsv")
az_retry("storage", "account", "create", "--name", sa_name, "--resource-group", rg, "--location", location,
         "--sku", "Standard_LRS", "--kind", "StorageV2", "--allow-blob-public-access", "false",
         "--min-tls-version", "TLS1_2", "--https-only", "true",
         "--identity-type", "UserAssigned", "--user-identity-id", uami_id,
         "--encryption-key-source", "Microsoft.Keyvault", "--encryption-key-vault", kv_uri,
         "--encryption-key-name", key_name, "--encryption-services", "blob",
         "--key-vault-user-identity-id", uami_id, "-o", "none")
print("→ Storage settings...")
az_retry("storage", "account", "blob-service-properties", "update", "--account-name", sa_name, "--resource-group", rg,
         "--enable-versioning", "true", "--enable-delete-retention", "true", "--delete-retention-days", "7",
         "--enable-container-delete-retention", "true", "--container-delete-retention-days", "7", "-o", "none")
sa_scope = f"/subscriptions/{sub_id}/resourceGroups/{rg}/providers/Microsoft.Storage/storageAccounts/{sa_name}"
assign("Storage Blob Data Owner", me, sa_scope)
assign("Storage Blob Data Contributor", mi_principal_id, sa_scope)
print(f"⏳ {PROPAGATION_WAIT}s wachten op CMK & RBAC propagatie...")
time.sleep(PROPAGATION_WAIT)
az_retry("storage", "container", "create", "--name", container, "--account-name", sa_name, "--auth-mode", "login", "-o", "none")

# E. GitHub: geen geheimen, alleen ID's en namen voor OIDC en de backend.
print("\n--- GitHub Integratie ---")
values = {"AZURE_CLIENT_ID": mi_client_id, "AZURE_SUBSCRIPTION_ID": sub_id, "AZURE_TENANT_ID": tenant_id,
          "BACKEND_RG_NAME": rg, "BACKEND_STORAGE_ACCOUNT": sa_name, "BACKEND_CONTAINER_NAME": container}
if gh_ready() and ask_user("GitHub Secrets automatisch instellen? (j/n)", "j").lower() == "j":
    repo = ask_user("Volledige GitHub repo (bijv. user/repo)", pattern=r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
    print(f"Secrets aan het zetten in {repo}...")
    for key, value in values.items():
        # De waarde via stdin, niet als argument: dan staat hij niet in de proceslijst.
        result = subprocess.run(as_args("gh", "secret", "set", key, "--repo", repo), input=value, capture_output=True, text=True)
        print(f"   ✅ {key}" if result.returncode == 0 else f"   ❌ {key} (mislukt: {result.stderr.strip()})")
else:
    print("\nHandmatig kopiëren:")
    for key, value in values.items():
        print(f"   {key:23} = {value}")

# F. Een backend-bestand per omgeving voor terraform init.
print("\n📝 Backend Configs genereren...")
for env in ("dev", "test", "prod"):
    with open(f"backend.{env}.conf", "w", encoding="utf-8", newline="\n") as f:
        f.write(f'resource_group_name  = "{rg}"\nstorage_account_name = "{sa_name}"\ncontainer_name       = "{container}"\n'
                f'key                  = "{env}/terraform.tfstate"\nuse_azuread_auth     = true\n\n'
                f'subscription_id      = "{sub_id}"\ntenant_id            = "{tenant_id}"\n')

print("\n🎉 GEREED! Setup voltooid. Gebruik nu de backend.conf in Terraform.")
