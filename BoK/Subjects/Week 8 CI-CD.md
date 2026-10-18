# Week 8: CI/CD security checks

De eerste stap van de pipeline staat: bij elke push naar `main` bouwt GitHub Actions de image en zet hem op ghcr.io (MIT-34). Het token van de run mag alleen dat, `actions/checkout` staat vast op een commit, en een eigen token is niet meer nodig. Tests en scans draaien nog niet; die komen er stap voor stap bij.

De details staan in de entries (MC-30, MIT-34; C-06, A-12, F-06, F-07 en B-04 in de architectuur) en de test T-103.

## De dreiging

- **Wat op Azure draait, komt uit de pipeline.** Wie de image kan vervangen, draait eigen code met de rechten en geheimen van de app (MC-30).
- **Een workflow die meer mag dan nodig,** een action op een tag die verschuift, of een lang geldig token met `write:packages`: elk is een weg naar een andere image.
- **Bekende lekken in de pakketten en de base-image** blijven ongemerkt staan zolang niemand scant (MC-11).

## Wat er beter wordt

| Onderdeel | Voor | Na |
|---|---|---|
| Wie bouwt de image | Jij, op je eigen pc, met `docker build` en `docker push` | GitHub Actions, bij elke push naar `main` |
| Inloggen bij ghcr.io | Een eigen token (classic) met `write:packages`, dat weken geldig blijft | Het token van de run: alleen `contents: read` en `packages: write`, en weg na de run |
| De image openbaar maken | Met de hand, eenmalig, in de instellingen van het pakket | Vanzelf: een pakket dat de workflow maakt, krijgt de zichtbaarheid van de repo |
| De tag | Zelf kiezen | De commit, en de inhoud van `app/` (de tree-hash van git), nooit `latest` |
| Uitrollen | Vijf stappen van de routekaart in `setup.py` | `python scripts/setup.py azure`: het zoekt de image bij je laatste commit en draait Terraform |

## Hoe het werkt

- **De workflow:** `.github/workflows/image.yml`. Hij draait bij een push naar `main`, en met de hand (`workflow_dispatch`); niet bij een pull request.
- **Rechten:** standaard geen (`permissions: {}`); de job krijgt alleen `contents: read` en `packages: write`.
- **Bouwen en pushen** met de gewone `docker`-opdrachten, zonder actions van derden. Het token gaat via stdin naar `docker login`.
- **Twee tags:** de commit-hash, en `app-` met de tree-hash van `app/`. `setup.py azure` rekent die tweede zelf uit met `git rev-parse HEAD:app`, en kijkt anoniem bij ghcr.io of de image er is en openbaar is, zoals Container Apps hem ophaalt. Een commit die alleen Terraform of de BoK verandert, heeft zo geen nieuwe build nodig.
- **Dependabot** houdt `actions/checkout` bij, net als de pakketten en de images (MIT-33).

## Waarom het veilig is

| Wat | Hoe | Gemeten |
|---|---|---|
| Het token mag niet meer dan nodig | `permissions: {}`, en per job alleen `contents: read` en `packages: write` | T-103: de log van de run toont `Contents: read`, `Metadata: read` en `Packages: write` |
| Een action kan niet verschuiven | `actions/checkout` op een volledige commit-hash, niet op een tag; GitHub raadt dat zelf aan | T-103: opgehaald op `3d3c42e5` |
| Een pull request publiceert niets | Geen trigger op `pull_request` | In de workflow |
| Geen token dat kan uitlekken | Geen eigen token meer; dat van de run vervalt na de run | De stap met een token (classic) is weg uit `setup.py` |

## Wat het niet oplost

- **Wie naar `main` kan pushen, bepaalt de image,** en kan hem met `setup.py azure` uitrollen. Je GitHub-account, met tweestapsverificatie, is dus de sleutel.
- **Nog geen tests en geen scans.** Een image met een bekend lek wordt gewoon gepubliceerd. Dat is de volgende stap.
- **Niet ondertekend, geen SBoM.** Of een image echt uit deze workflow komt, is niet na te gaan. De SBoM is ook het onderzoeksonderwerp.
- **Het pakket is openbaar.** Iedereen kan de image ophalen; er staan geen geheimen in, en de code is ook openbaar.
- **Uitrollen gebeurt nog op je eigen pc.** Valt die tijdens een `apply` weg, dan kan er een resource buiten de state blijven (zie de eerste uitrol hieronder).

## Keuzes

- **Gewone `docker`-opdrachten, geen actions van derden.** Elke action is code van iemand anders, met het token van de run; met alleen `actions/checkout` is er één om vast te zetten en bij te houden.
- **Een tag op de inhoud van `app/`.** Hetzelfde idee als een digest: dezelfde inhoud geeft dezelfde tag. Zo hoeft er niet na elke commit gebouwd te worden voordat je kunt uitrollen.
- **Een openbaar pakket, geen inloggegevens voor Container Apps.** Dan staat er nergens een token voor de registry; de prijs is dat iedereen de image kan ophalen.
- **Nog geen uitrol vanuit GitHub (CD).** Dat vraagt een identiteit in Azure die de pipeline mag gebruiken, met rechten op de resource group. Eerst de checks.

## De eerste uitrol (18-10-2026)

- **Regio: France Central.** West Europe neemt geen nieuwe tenants aan (`RequestDisallowedByAzure`), en in Germany West Central mag deze subscription geen PostgreSQL maken (`restricted`). Terraform controleert dat nu al bij het plan, via de capabilities-API van PostgreSQL (`database.tf`); `az postgres flexible-server list-skus` liet het niet zien.
- **Providers:** Container Apps, PostgreSQL en Log Analytics stonden niet aan op de nieuwe subscription; Terraform registreert ze zelf.
- **Wat misging:** azurerm 5.8.0 kon het verwijderen van de Container Apps-omgeving in Germany West Central niet volgen (`polling support for the Content-Type "" was not implemented`); Azure verwijderde hem wel. Een onderbroken `apply` liet daarna een private DNS-zone buiten de state; `terraform import` nam hem op, zonder iets in Azure te veranderen.
- **Gemeten na de uitrol:** HTTPS met een geldig certificaat, HTTP met een 301 naar HTTPS, HSTS, CSP, `no-store` en een sessiecookie met `Secure`. De schema-job draaide en slaagde. De log komt in Log Analytics, met het adres van de bezoeker (T-102, T-104), en de identiteit van de app heeft geen rol op de vault van de eigenaar (T-86).

## Volgende stappen, één per keer

1. Een scan van de image op bekende lekken, met een rem vóór het publiceren.
2. De SBoM van elke image, als bewijs bij de build.
3. De tests in de pipeline, tegen een wegwerp-stack.
4. SAST (statische code-analyse).
5. Uitrollen vanuit GitHub, met een akkoord per uitrol.

## Screenshots

Voor het verslag, lokaal in `screenshots/Week 8 CI-CD/` (niet in de repo).

| Onderdeel | Voor | Na | Code |
|---|---|---|---|
| De image bouwen | `week8_voor_image_1_met_de_hand` | `week8_na_image_1_door_github` | `week8_code_image_1_workflow` |

## Bronnen

Opgehaald en gecontroleerd op 18-10-2026.

- GitHub, secure use of GitHub Actions ("Pin references to actions to a commit SHA"; het token "the minimum required permissions"): https://docs.github.com/en/actions/reference/security/secure-use
- GitHub, publiceren met `GITHUB_TOKEN` (het pakket krijgt de zichtbaarheid van de repo): https://docs.github.com/en/packages/managing-github-packages-using-github-actions-workflows/publishing-and-installing-a-package-with-github-actions
- GitHub, zichtbaarheid van een pakket ("Once you make a package public, you cannot make it private again"): https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility
- Microsoft, regio's die geen nieuwe klanten aannemen: https://learn.microsoft.com/azure/azure-resource-manager/troubleshooting/error-region-access-policy
