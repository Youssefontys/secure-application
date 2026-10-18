# Zet eenmalig de opslag voor de Terraform-state op Azure op, en de ID's van die opslag in GitHub.
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
from pathlib import Path

# Emoji ook als de uitvoer naar een pipe of bestand gaat: Python voor 3.15 schrijft daar op Windows cp1252.
# Een stream zonder reconfigure (IDLE, een test) kan al Unicode.
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")

# backend.conf komt in de hoofdmap van de repo, waar setup.py en terraform init hem zoeken.
BACKEND_CONF = Path(__file__).resolve().parent.parent / "backend.conf"
# West Europe neemt geen nieuwe tenants aan (RequestDisallowedByAzure); dezelfde regio als terraform/variables.tf.
DEFAULT_LOCATION = "germanywestcentral"
# In de vraag doorgestreept; wie daar al resources heeft, mag hem nog wel intypen.
CLOSED_LOCATION = "westeurope"
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


# Stoppen met de melding, met witregels eromheen zodat hij opvalt; zelfde vorm als setup.py.
def stop(message, icon="❌"):
    sys.exit(f"\n{icon} {message}\n\n🛑 Stoppen.\n")


# De fout van az één keer: de regels Code, Message en Target herhalen meestal de eerste regel.
def az_error(stderr):
    lines = [line for line in stderr.strip().splitlines() if not line.startswith("WARNING:")] or [""]
    first = lines[0].removeprefix("ERROR: ")
    return "\n".join([first, *(line for line in lines[1:] if not ((value := line.partition(": ")[2]) and value in first))])


# Voert az uit en geeft de uitvoer; bij een fout stoppen, of None met ignore_error.
def az(*args, ignore_error=False):
    result = subprocess.run(as_args("az", *args), capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    if ignore_error:
        return None
    stop(f"FOUT: {az_error(result.stderr)}")


# Zoals az, maar opnieuw proberen zolang Azure nog bezig is; "bestaat al" telt als gelukt. Alleen een nieuwe poging meldt zich.
def az_retry(*args, tries=10, delay=10):
    for attempt in range(1, tries + 1):
        result = subprocess.run(as_args("az", *args), capture_output=True, text=True)
        err = result.stderr.strip()
        if result.returncode == 0 or any(x in err for x in IGNORABLE):
            return result.stdout.strip()
        if attempt == tries or not any(x in err for x in RETRYABLE):
            stop(f"FOUT: {az_error(err)}")
        print(f"   ⏳ Azure is nog bezig; over {delay}s poging {attempt + 1} van {tries}...")
        time.sleep(delay)
        delay += 5


def assign(role, assignee, scope):
    print(f"   🔑 {role}")
    az_retry("role", "assignment", "create", "--role", role, "--assignee", assignee, "--scope", scope, "-o", "none")


# Een vraag met een standaardwaarde; met pattern alleen een antwoord dat er helemaal aan voldoet.
# shown vervangt wat er tussen de haakjes staat, bijvoorbeeld met een optie die niet kan.
def ask_user(question, default=None, pattern=None, shown=None):
    prompt = f"{question} [{shown or default}]: " if default else f"{question}: "
    while True:
        ans = input(prompt).strip() or default
        if ans is None:
            continue
        if pattern is None or re.fullmatch(pattern, ans):
            return ans
        print("🤔 Dat kan niet: alleen letters, cijfers en - _ . mogen.")


# Is gh er en ingelogd? Anders kunnen de GitHub-secrets niet automatisch.
def gh_ready():
    gh = shutil.which("gh")
    if not gh:
        print("   💡 GitHub CLI (gh) niet gevonden; met https://cli.github.com zet dit script de secrets zelf.")
        return False
    if subprocess.run([gh, "auth", "status"], capture_output=True).returncode != 0:
        print("   💡 gh is niet ingelogd, of het token is verlopen: gh auth login")
        return False
    print("   ✅ gh is ingelogd")
    return True


# De uitrol zelf.
print("\n🛡️  Azure Terraform Bootstrap")
print("👋 Eenmalig: de opslag waarin Terraform onthoudt wat er op Azure staat. Daarna doet Terraform de rest.")
print("   Enter kiest steeds wat tussen [ ] staat.\n")

# 1. Ingelogd en de subscription; de ID's pas daarna lezen, ook de tenant van een andere subscription.
# Zelf az login starten kan hier niet: az() vangt de uitvoer af, en dan wacht de keuze van de subscription onzichtbaar.
name = az("account", "show", "--query", "name", "-o", "tsv", ignore_error=True)
if not name:
    stop("Eerst even inloggen bij Azure: az login\n"
         "   Zegt dat \"Authentication failed against tenant <ID>\" met AADSTS50076? Dan wil die tenant MFA:\n"
         "   az login --tenant <ID>\n   Daarna dit script opnieuw.", icon="🔐")
print(f"☁️  Ingelogd bij Azure, subscription: {name}")
if ask_user("🔀 Andere subscription? (j/n)", "n").lower() == "j":
    az("account", "set", "--subscription", ask_user("Subscription ID", pattern=GUID))
sub_id = az("account", "show", "--query", "id", "-o", "tsv")
tenant_id = az("account", "show", "--query", "tenantId", "-o", "tsv")
me = az("ad", "signed-in-user", "show", "--query", "id", "-o", "tsv")

# 2. Providers
print("\n🧩 Providers registreren, eenmalig per subscription...")
for namespace in ("Microsoft.Storage", "Microsoft.KeyVault", "Microsoft.ManagedIdentity"):
    az_retry("provider", "register", "--namespace", namespace, "--wait", "-o", "none", tries=2)
    print(f"   ✅ {namespace}")

# 3. Invoer; met vier cijfers erachter blijft de naam van de opslag binnen de 3 tot 24 tekens van Azure.
print("\n📝 Een paar keuzes; de standaard is prima:")
rg = ask_user("Resource Group naam", DEFAULT_RG_NAME, pattern=r"[A-Za-z0-9_.-]{0,89}[A-Za-z0-9_-]")
# Doorstrepen met een combinerend streepje per letter: werkt in elke terminal die UTF-8 toont, zonder kleurcodes.
closed = "".join(char + "\u0336" for char in CLOSED_LOCATION)
location = ask_user("Regio", DEFAULT_LOCATION, pattern=r"[a-z0-9]+", shown=f"{DEFAULT_LOCATION} | {closed} neemt geen nieuwe klanten aan")
container = ask_user("Blob container naam", "tfstate", pattern=r"[a-z0-9](?!.*--)[a-z0-9-]{1,61}[a-z0-9]")
prefix = ask_user("Storage prefix (3-10 chars)", "tfstate", pattern=r"[a-z0-9]{3,10}")
sa_name = f"{prefix}{random.randint(1000, 9999)}"
suffix = random.randint(1000, 9999)
mi_name, kv_name, key_name = f"mi-{prefix}-{suffix}", f"kv-{prefix}-{suffix}", "tfstate-cmk-key"
if ask_user("\n🚦 Starten? (j/n)", "j").lower() != "j":
    print("👋 Niets aangemaakt. Tot later!")
    sys.exit(0)

print(f"\n🚀 Daar gaan we, in {location}. Dit duurt een paar minuten.\n")
az("group", "create", "--name", rg, "--location", location, "-o", "none")
print(f"📁 Resource group: {rg}")

# A. De identiteit van de opslag, en wachten tot Azure hem kent.
print(f"🪪 Identiteit voor de opslag: {mi_name}")
az_retry("identity", "create", "--name", mi_name, "--resource-group", rg, "--location", location, "-o", "none")
print("   ⏳ Even wachten tot Azure hem overal kent...")
for _ in range(12):
    mi_principal_id = az("identity", "show", "--name", mi_name, "--resource-group", rg,
                         "--query", "principalId", "-o", "tsv", ignore_error=True)
    if mi_principal_id:
        break
    time.sleep(5)
uami_id = f"/subscriptions/{sub_id}/resourceGroups/{rg}/providers/Microsoft.ManagedIdentity/userAssignedIdentities/{mi_name}"

# B. Key Vault met gescheiden rollen: jij beheert de sleutel, de identiteit mag hem alleen gebruiken.
print(f"🔐 Key Vault: {kv_name}")
az("keyvault", "create", "--name", kv_name, "--resource-group", rg, "--location", location,
   "--enable-rbac-authorization", "true", "--enable-purge-protection", "true", "--retention-days", "90", "-o", "none")
kv_scope = f"/subscriptions/{sub_id}/resourceGroups/{rg}/providers/Microsoft.KeyVault/vaults/{kv_name}"
assign("Key Vault Crypto Officer", me, kv_scope)
assign("Key Vault Crypto Service Encryption User", mi_principal_id, kv_scope)

# C. De eigen sleutel (RSA 4096).
print(f"🗝️  Eigen sleutel (RSA 4096): {key_name}")
time.sleep(15)
az_retry("keyvault", "key", "create", "--vault-name", kv_name, "--name", key_name, "--kty", "RSA", "--size", "4096", "-o", "none")

# D. De opslag, versleuteld met die sleutel, alleen over HTTPS en niet publiek.
print(f"📦 Opslag: {sa_name}, versleuteld met die sleutel, alleen over HTTPS")
kv_uri = az("keyvault", "show", "--name", kv_name, "--query", "properties.vaultUri", "-o", "tsv")
az_retry("storage", "account", "create", "--name", sa_name, "--resource-group", rg, "--location", location,
         "--sku", "Standard_LRS", "--kind", "StorageV2", "--allow-blob-public-access", "false",
         "--min-tls-version", "TLS1_2", "--https-only", "true",
         "--identity-type", "UserAssigned", "--user-identity-id", uami_id,
         "--encryption-key-source", "Microsoft.Keyvault", "--encryption-key-vault", kv_uri,
         "--encryption-key-name", key_name, "--encryption-services", "blob",
         "--key-vault-user-identity-id", uami_id, "-o", "none")
print("♻️  Vorige versies bewaren, en 7 dagen terughalen na verwijderen")
az_retry("storage", "account", "blob-service-properties", "update", "--account-name", sa_name, "--resource-group", rg,
         "--enable-versioning", "true", "--enable-delete-retention", "true", "--delete-retention-days", "7",
         "--enable-container-delete-retention", "true", "--container-delete-retention-days", "7", "-o", "none")
sa_scope = f"/subscriptions/{sub_id}/resourceGroups/{rg}/providers/Microsoft.Storage/storageAccounts/{sa_name}"
assign("Storage Blob Data Owner", me, sa_scope)
assign("Storage Blob Data Contributor", mi_principal_id, sa_scope)
print(f"⏳ {PROPAGATION_WAIT // 60} minuten wachten tot Azure de sleutel en de rechten overal kent... ☕")
time.sleep(PROPAGATION_WAIT)
az_retry("storage", "container", "create", "--name", container, "--account-name", sa_name, "--auth-mode", "login", "-o", "none")
print(f"🗃️  Container: {container}")

# E. GitHub: geen geheimen, alleen ID's en namen voor de backend. AZURE_CLIENT_ID komt bij de CI-stap, van een eigen
# identiteit met een federated credential (OIDC); niet die van de opslag, want die mag de sleutel van de state gebruiken.
print("\n🐙 GitHub, voor de pipeline later; nu nog niet nodig")
values = {"AZURE_SUBSCRIPTION_ID": sub_id, "AZURE_TENANT_ID": tenant_id,
          "BACKEND_RG_NAME": rg, "BACKEND_STORAGE_ACCOUNT": sa_name, "BACKEND_CONTAINER_NAME": container}
if gh_ready() and ask_user("GitHub Secrets automatisch instellen? (j/n)", "j").lower() == "j":
    repo = ask_user("Volledige GitHub repo (bijv. user/repo)", pattern=r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
    print(f"   🔏 Secrets zetten in {repo}...")
    for key, value in values.items():
        # De waarde via stdin, niet als argument: dan staat hij niet in de proceslijst.
        result = subprocess.run(as_args("gh", "secret", "set", key, "--repo", repo), input=value, capture_output=True, text=True)
        print(f"   ✅ {key}" if result.returncode == 0 else f"   ❌ {key} (mislukt: {result.stderr.strip()})")
else:
    print("   📋 Zelf invullen zodra er een pipeline is (Settings > Secrets and variables > Actions):")
    for key, value in values.items():
        print(f"      {key:23} = {value}")

# F. Het backend-bestand voor terraform init; één omgeving, dus één state.
with open(BACKEND_CONF, "w", encoding="utf-8", newline="\n") as f:
    f.write(f'resource_group_name  = "{rg}"\nstorage_account_name = "{sa_name}"\ncontainer_name       = "{container}"\n'
            f'key                  = "terraform.tfstate"\nuse_azuread_auth     = true\n\n'
            f'subscription_id      = "{sub_id}"\ntenant_id            = "{tenant_id}"\n')

print(f"\n📝 backend.conf geschreven: {BACKEND_CONF}")
print("\n🎉 Klaar! De deur voor Terraform staat open.")
print("👉 De rest doet python scripts/setup.py azure; als dat dit script startte, gaat het nu vanzelf verder.\n")
