# Week 8: CI/CD security checks

Drie stappen van de pipeline staan. Bij elke push naar `main` bouwt GitHub Actions de image en zet hem op ghcr.io (MIT-34): het token van de run mag alleen dat, `actions/checkout` staat vast op een commit, en een eigen token is niet meer nodig. Trivy maakt van elke image een SBoM (MIT-36), en scant die: een bekend lek waarvoor een oplossing is, houdt de image tegen (MIT-35). De eerste scan vond vier lekken, allemaal in pip, dat nu uit de image gaat. Tests draaien nog niet; die komen er stap voor stap bij.

De details staan in de entries (MC-30, MC-11, MIT-34 tot MIT-36; C-06, A-12, A-14, F-06, F-07 en B-04 in de architectuur) en de tests T-103, T-105 en T-106.

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
| Weten wat er in de image zit | Nergens vastgelegd | Een CycloneDX-SBoM van elke image, 90 dagen bij de run |
| Bekende lekken in de image | Niemand keek; er zaten vier keer HIGH in, in pip | Trivy vóór het publiceren; 0, want pip gaat na het installeren uit de image |
| Uitrollen | Vijf stappen van de routekaart in `setup.py` (nu `deployment.py`) | `python scripts/deployment.py azure`: het zoekt de image bij je laatste commit en draait Terraform |

## Hoe het werkt

- **De workflow:** `.github/workflows/image.yml`. Hij draait bij een push naar `main`, en met de hand (`workflow_dispatch`); niet bij een pull request.
- **Rechten:** standaard geen (`permissions: {}`); de job krijgt alleen `contents: read` en `packages: write`.
- **Bouwen en pushen** met de gewone `docker`-opdrachten, zonder actions van derden. Het token gaat via stdin naar `docker login`.
- **De SBoM:** Trivy 0.75.0, vast op versie en digest, leest de image als tar-bestand en maakt er een CycloneDX-SBoM van: alleen de lijst, zonder lekken of VEX. jq zet de naam en tag van de image als hoofdonderdeel. De SBoM gaat als artifact bij de run, ook als de scan daarna een lek vindt.
- **De scan:** tussen de SBoM en het pushen. Trivy scant de SBoM, niet de image zelf. Een lek van HIGH of CRITICAL waarvoor een oplossing is, stopt de job: dan komt er geen nieuwe image op ghcr.io, en kan `deployment.py azure` hem ook niet uitrollen.
- **Twee tags:** de commit-hash, en `app-` met de tree-hash van `app/`. `deployment.py azure` rekent die tweede zelf uit met `git rev-parse HEAD:app`, en kijkt anoniem bij ghcr.io of de image er is en openbaar is, zoals Container Apps hem ophaalt. Een commit die alleen Terraform of de BoK verandert, heeft zo geen nieuwe build nodig.
- **Dependabot** houdt `actions/checkout` bij, net als de pakketten en de images (MIT-33).

## Waarom het veilig is

| Wat | Hoe | Gemeten |
|---|---|---|
| Het token mag niet meer dan nodig | `permissions: {}`, en per job alleen `contents: read` en `packages: write` | T-103: de log van de run toont `Contents: read`, `Metadata: read` en `Packages: write` |
| Een action kan niet verschuiven | `actions/checkout` op een volledige commit-hash, niet op een tag; GitHub raadt dat zelf aan | T-103: opgehaald op `3d3c42e5` |
| Een pull request publiceert niets | Geen trigger op `pull_request` | In de workflow |
| De lijst klopt | De SBoM bevat het besturingssysteem, de Debian-pakketten en precies de 14 Python-pakketten uit `requirements.txt` | T-106: 103 onderdelen; een scan op de SBoM vindt hetzelfde als een scan op de image |
| Een bekend lek gaat niet live | Trivy vóór het pushen; met een lek stopt de job | T-105: met pip 4 keer HIGH (exit 1), zonder pip 0 (exit 0) |
| Geen token dat kan uitlekken | Geen eigen token meer; dat van de run vervalt na de run | De stap met een token (classic) is weg uit `setup.py` (nu `deployment.py`) |

## Wat het niet oplost

- **Wie naar `main` kan pushen, bepaalt de image,** en kan hem met `deployment.py azure` uitrollen. Je GitHub-account, met tweestapsverificatie, is dus de sleutel.
- **Nog geen tests.** Een image die stuk is, wordt gewoon gepubliceerd.
- **De scan ziet niet alles.** Een lek zonder oplossing houdt de image niet tegen, een lek dat pas later bekend wordt, ziet de scan pas bij de volgende push, en een draaiende image wordt niet opnieuw gescand.
- **Niet ondertekend.** Of een image echt uit deze workflow komt, is niet na te gaan.
- **De SBoM blijft 90 dagen.** Daarna is hij weg bij GitHub; hij hangt nog niet aan de image zelf. Opnieuw scannen, als er later een lek bekend wordt, gebeurt nog niet.
- **Het pakket is openbaar.** Iedereen kan de image ophalen; er staan geen geheimen in, en de code is ook openbaar.
- **Uitrollen gebeurt nog op je eigen pc.** Valt die tijdens een `apply` weg, dan kan er een resource buiten de state blijven (zie de eerste uitrol hieronder).

## Keuzes

- **Gewone `docker`-opdrachten, geen actions van derden.** Elke action is code van iemand anders, met het token van de run; met alleen `actions/checkout` is er één om vast te zetten en bij te houden.
- **Een tag op de inhoud van `app/`.** Hetzelfde idee als een digest: dezelfde inhoud geeft dezelfde tag. Zo hoeft er niet na elke commit gebouwd te worden voordat je kunt uitrollen.
- **Een openbaar pakket, geen inloggegevens voor Container Apps.** Dan staat er nergens een token voor de registry; de prijs is dat iedereen de image kan ophalen.
- **Alleen een lek met een oplossing houdt tegen (`--ignore-unfixed`).** Dan stopt de job alleen als er iets te doen is. Volgens Trivy laat deze optie alleen lekken zien waarvoor een oplossing is.
- **Scannen op de SBoM, niet op de image.** Dezelfde uitkomst (T-106), en zo wordt de SBoM echt gebruikt in plaats van alleen bewaard. Dezelfde SBoM kan later opnieuw gescand worden, zonder de image.
- **Geen VEX.** De SBoM is alleen de lijst; wat een lek voor deze app betekent, is de tweede deelvraag van het onderzoek.
- **pip uit de image, geen nieuwe versies kiezen.** De vier lekken zaten in de eigen kopieën van pip; weghalen wat niet nodig is, was de kleinste oplossing.
- **Trivy als image in een opdracht, niet als action.** Om dezelfde reden: geen actions van derden. De prijs: Dependabot houdt de versie van Trivy niet bij.
- **Nog geen uitrol vanuit GitHub (CD).** Dat vraagt een identiteit in Azure die de pipeline mag gebruiken, met rechten op de resource group. Eerst de checks.

## De eerste uitrol (18-10-2026)

- **Regio: France Central.** West Europe neemt geen nieuwe tenants aan (`RequestDisallowedByAzure`), en in Germany West Central mag deze subscription geen PostgreSQL maken (`restricted`). Terraform controleert dat nu al bij het plan, via de capabilities-API van PostgreSQL (`database.tf`); `az postgres flexible-server list-skus` liet het niet zien.
- **Providers:** Container Apps, PostgreSQL en Log Analytics stonden niet aan op de nieuwe subscription; Terraform registreert ze zelf.
- **Wat misging:** azurerm 5.8.0 kon het verwijderen van de Container Apps-omgeving in Germany West Central niet volgen (`polling support for the Content-Type "" was not implemented`); Azure verwijderde hem wel. Een onderbroken `apply` liet daarna een private DNS-zone buiten de state; `terraform import` nam hem op, zonder iets in Azure te veranderen.
- **Gemeten na de uitrol:** HTTPS met een geldig certificaat, HTTP met een 301 naar HTTPS, HSTS, CSP, `no-store` en een sessiecookie met `Secure`. De schema-job draaide en slaagde. De log komt in Log Analytics, met het adres van de bezoeker (T-102, T-104), en de identiteit van de app heeft geen rol op de vault van de eigenaar (T-86).

## Volgende stappen, één per keer

1. Gedaan: een scan van de image op bekende lekken, met een rem vóór het publiceren (MIT-35).
2. Gedaan: de SBoM van elke image, als bewijs bij de build, en de scan daarop (MIT-36).
3. De tests in de pipeline, tegen een wegwerp-stack.
4. SAST (statische code-analyse).
5. Uitrollen vanuit GitHub, met een akkoord per uitrol.

## Screenshots

Voor het verslag, lokaal in `screenshots/Week 8 CI-CD/` (niet in de repo).

| Onderdeel | Voor | Na | Code |
|---|---|---|---|
| De image bouwen | `week8_voor_image_1_met_de_hand` | `week8_na_image_1_door_github` | `week8_code_image_1_workflow` |
| De scan | `week8_voor_scan_1_vier_lekken` | `week8_na_scan_1_schoon` | `week8_code_image_1_workflow` |
| De SBoM | `week8_voor_sbom_1_geen_lijst` | `week8_na_sbom_1_bij_de_run` | `week8_code_image_1_workflow` |

## Bronnen

Opgehaald en gecontroleerd op 18-10-2026.

- GitHub, secure use of GitHub Actions ("Pin references to actions to a commit SHA"; het token "the minimum required permissions"): https://docs.github.com/en/actions/reference/security/secure-use
- GitHub, publiceren met `GITHUB_TOKEN` (het pakket krijgt de zichtbaarheid van de repo): https://docs.github.com/en/packages/managing-github-packages-using-github-actions-workflows/publishing-and-installing-a-package-with-github-actions
- GitHub, zichtbaarheid van een pakket ("Once you make a package public, you cannot make it private again"): https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility
- Trivy, SBoM maken ("By default, `--format cyclonedx` represents SBOM and doesn't include vulnerabilities"): https://trivy.dev/latest/docs/supply-chain/sbom/
- Trivy, een SBoM scannen ("Trivy can take the following SBOM formats as an input and scan for vulnerabilities"): https://trivy.dev/latest/docs/target/sbom/
- Trivy, filtering (`--ignore-unfixed`: "To skip all unfixed vulnerabilities"): https://trivy.dev/latest/docs/configuration/filtering/
- Microsoft, regio's die geen nieuwe klanten aannemen: https://learn.microsoft.com/azure/azure-resource-manager/troubleshooting/error-region-access-policy
