# Op Azure uitrollen: de state-opslag als die er nog niet is (azuresetup_v2.py), de image die GitHub bouwde,
# en Terraform. Start via setup.py.

import json
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

import common
from common import REPO, ask, check_tools, hackstand, stop, terraform

# Eist een tenant MFA, dan slaat az login hem over (AADSTS50076) en is er geen subscription; --tenant vraagt er wel om.
AZ_LOGIN_HELP = """Eerst even inloggen bij Azure: je bent nog niet ingelogd, of er is geen subscription gevonden.
   az login
   Zegt az login "Authentication failed against tenant <ID>" met AADSTS50076? Dan wil die tenant een
   tweede stap (MFA). Log dan in bij die tenant, en keur het goed in je authenticator-app:
   az login --tenant <ID>
   Daarna opnieuw: python scripts/setup.py azure"""
# Een e-mailadres, als allowlist (MIT-22); dezelfde regel als de validatie van alert_email in terraform/variables.tf.
EMAIL = r"[^@\s]+@[^@\s]+\.[A-Za-z]{2,}"


# Git in deze map; None als het niet lukt.
def git(*args):
    result = subprocess.run([shutil.which("git"), *args], cwd=REPO, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


# owner/naam van de GitHub-repo, uit de remote origin; ook voor wie de repo heeft gekopieerd. ghcr.io wil kleine letters.
def github_repo(url):
    match = re.search(r"github\.com[:/]([\w.-]+/[\w.-]+?)(?:\.git)?/?$", url or "")
    return match and match.group(1).lower()


# Staat de image er, en mag iedereen hem ophalen? Dat moet: Container Apps logt niet in bij ghcr.io.
def image_public(repo, tag):
    accept = ("application/vnd.oci.image.index.v1+json, application/vnd.oci.image.manifest.v1+json, "
              "application/vnd.docker.distribution.manifest.v2+json")
    try:
        with urllib.request.urlopen(f"https://ghcr.io/token?scope=repository:{repo}:pull", timeout=15) as response:
            token = json.load(response)["token"]
        request = urllib.request.Request(f"https://ghcr.io/v2/{repo}/manifests/{tag}", method="HEAD",
                                         headers={"Authorization": f"Bearer {token}", "Accept": accept})
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status == 200
    except (urllib.error.URLError, KeyError, ValueError):
        return False


# Alles voor Azure in één keer: de state-opslag als die er nog niet is, de image die GitHub bouwde, en Terraform.
def run():
    check_tools("azure")
    # Zonder login kan er niets; dan eerst uitleggen hoe, ook bij een tenant die MFA eist.
    account = subprocess.run([shutil.which("az"), "account", "show", "--query", "[name, user.name]", "-o", "tsv"],
                             capture_output=True, text=True)
    if account.returncode != 0:
        stop(AZ_LOGIN_HELP, icon="🔐")
    subscription, login = (account.stdout.splitlines() + ["", ""])[:2]
    print(f"\n☁️  Ingelogd bij Azure, subscription: {subscription}")

    # Kip en ei: Terraform moet zijn state ergens kwijt voordat het iets maakt; die opslag zet een script eenmalig neer.
    if (REPO / "backend.conf").exists():
        print("🗄️  Opslag voor de Terraform-state: staat er al (backend.conf)")
    else:
        print("\n🗄️  Nog geen opslag voor de Terraform-state; azuresetup_v2.py zet die nu eenmalig klaar.")
        if subprocess.run([sys.executable, str(REPO / "scripts" / "azuresetup_v2.py")], cwd=REPO).returncode != 0:
            sys.exit(1)

    # De tag is de inhoud van app/ in je laatste commit (zie image.yml): een commit zonder app-wijziging hergebruikt hem.
    repo, tree = github_repo(git("remote", "get-url", "origin")), git("rev-parse", "HEAD:app")
    if not (repo and tree):
        stop("Geen GitHub-repo gevonden (git remote get-url origin); de image komt van GitHub Actions.", icon="🤔")
    tag = f"app-{tree}"
    image = f"ghcr.io/{repo}:{tag}"
    print(f"\n📦 De image van app/ zoals in je laatste commit: {image}")
    if not image_public(repo, tag):
        stop("Die image staat nog niet op ghcr.io, of hij is niet openbaar.\n"
             "   💡 Push je laatste commit en wacht tot de GitHub Action Image groen is, een paar minuten:\n"
             f"      https://github.com/{repo}/actions\n"
             "   Daarna opnieuw: python scripts/setup.py azure", icon="⏳")
    print("   ✅ Staat klaar, en Container Apps mag hem ophalen")

    hack = hackstand() if common.INTERACTIVE else {"THROTTLE_IP_MODE": None, "THROTTLE_PAIR_EXEMPT_USERS": None}
    # De mail bij een blokkade (alerts.tf): standaard het adres waarmee je bij az bent ingelogd. Niet in de repo, die is openbaar.
    email = login if re.fullmatch(EMAIL, login) else ""
    if common.INTERACTIVE:
        print("\n📧 Bij een blokkade stuurt Azure binnen een paar minuten een mail.")
        email = ask("Naar welk adres?", email or "-", EMAIL)
    if not re.fullmatch(EMAIL, email):
        stop("Geen e-mailadres voor de alert; draai dit script in een terminal en vul er een in.", icon="📧")
    variables = [f"app_image={image}", f"alert_email={email}"]
    if hack["THROTTLE_IP_MODE"]:
        variables += ["throttle_ip_mode=hackweek", "min_replicas=1"]
    if hack["THROTTLE_PAIR_EXEMPT_USERS"]:
        variables.append(f"throttle_pair_exempt_users={hack['THROTTLE_PAIR_EXEMPT_USERS']}")

    print("\n🏗️  Terraform. Het laat eerst zien wat het gaat doen, en begint pas als jij yes typt.\n")
    # backend.conf is de enige bron: na een nieuwe bootstrap kent .terraform nog de oude opslag, en dan stopt init
    # zonder -reconfigure. Er gaat geen state mee; die hoort bij de opslag.
    if not terraform("init", "-input=false", "-reconfigure", "-backend-config=../backend.conf"):
        stop("terraform init lukte niet; de melding staat hierboven.")
    # De vraag om yes blijft staan: hier gaan resources aan die geld kosten.
    if not terraform("apply", *(f"-var={v}" for v in variables)):
        stop("terraform apply lukte niet, of je typte geen yes; de melding staat hierboven.")
    url = subprocess.run([shutil.which("terraform"), "-chdir=terraform", "output", "-raw", "app_url"],
                         cwd=REPO, capture_output=True, text=True).stdout.strip()
    print(f"\n🎉 Klaar! De app staat op {url}")
    print("⏳ Terraform heeft de schema-job gestart; geeft inloggen de eerste minuut een fout, probeer het dan zo nog eens.")
    print("💡 Bijwerken: push naar main, wacht tot de Action Image groen is, en draai dit script opnieuw.")
    print("💡 Alles weer weg, zodat het niets meer kost: python scripts/setup.py opruimen\n")
