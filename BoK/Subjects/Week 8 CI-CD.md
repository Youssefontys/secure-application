# Week 8: CI/CD security checks

Zeven stappen van de pipeline staan. Bij elke push naar `main` bouwt GitHub Actions de image en zet hem op ghcr.io (MIT-34): het token van de run mag alleen dat, `actions/checkout` staat vast op een commit, en een eigen token is niet meer nodig. Trivy maakt van elke image een SBoM (MIT-36), en scant die: een bekend lek van HIGH of CRITICAL houdt de image tegen (MIT-35), sinds deelvraag 2 van het onderzoek ook als er nog geen oplossing is, tot er een beslissing in de VEX staat (MIT-41). De eerste scan vond vier lekken, allemaal in pip, dat nu uit de image gaat. Sinds deelvraag 1 van het onderzoek draaien dezelfde stappen ook bij elke pull request, zonder te publiceren, en maakt een ruleset op `main` die check verplicht (MIT-39): een bekend lek komt dan niet eens meer op `main`. En sinds de securitytest in de repo staat, draait de check die ook: een wijziging die een maatregel breekt, komt niet op `main` (MIT-39, T-125). En sinds MIT-44 zet `CD-azure.yml` een nieuwe image op Azure zodra de beheerder het goedkeurt, met OIDC en zonder sleutel in GitHub. En sinds MIT-46 draait bij elke pull request ook de ZAP baseline, met een beslissing per melding.

De details staan in de entries (MC-30, MC-11, MC-14, MIT-34 tot MIT-36, MIT-39 en MIT-41 tot MIT-47; C-06, C-11, A-12, A-14, A-18, A-19, F-06, F-07, F-12, F-13, B-04, B-06, AU-14, AZ-16 en AZ-17 in de architectuur) en de tests T-103, T-105, T-106, T-110 tot T-112 en T-114 tot T-138. De triageflow staat in `vex/README.md`.

## De dreiging

- **Wat op Azure draait, komt uit de pipeline.** Wie de image kan vervangen, draait eigen code met de rechten en geheimen van de app (MC-30).
- **Een workflow die meer mag dan nodig,** een action op een tag die verschuift, of een lang geldig token met `write:packages`: elk is een weg naar een andere image.
- **Bekende lekken in de pakketten en de base-image** blijven ongemerkt staan zolang niemand scant (MC-11).
- **Een pull request kan alles aanpassen,** ook de Dockerfile en de workflow zelf. Wat er bij een pull request draait, is dus code van wie hem opent (B-06).

## Wat er beter wordt

| Onderdeel | Voor | Na |
|---|---|---|
| Wie bouwt de image | Jij, op je eigen pc, met `docker build` en `docker push` | GitHub Actions, bij elke push naar `main` |
| Inloggen bij ghcr.io | Een eigen token (classic) met `write:packages`, dat weken geldig blijft | Het token van de run: alleen `contents: read` en `packages: write`, en weg na de run |
| De image openbaar maken | Met de hand, eenmalig, in de instellingen van het pakket | Vanzelf: een pakket dat de workflow maakt, krijgt de zichtbaarheid van de repo |
| De tag | Zelf kiezen | De commit, en de inhoud van `app/` (de tree-hash van git), nooit `latest` |
| Weten wat er in de image zit | Nergens vastgelegd | Een CycloneDX-SBoM van elke image, 90 dagen bij de run |
| Bekende lekken in de image | Niemand keek; er zaten vier keer HIGH in, in pip | Trivy vóór het publiceren; 0, want pip gaat na het installeren uit de image |
| Een pull request | Er draaide niets; een pull request met pip werd gewoon gemerged (pull request #2, 19-10-2026) | De job `check` bouwt, maakt de SBoM en scant; faalt hij, dan houdt de ruleset de merge tegen |
| Tests | Alleen lokaal, met de hand | De securitytest in de check van elke pull request: 182 controles |
| Uitrollen | Vijf stappen van de routekaart in `setup.py` (nu `deployment.py`) | `python scripts/deployment.py azure`: het zoekt de image bij je laatste commit en draait Terraform. Daarna na elke merge vanuit GitHub, na één klik op Approve |

## Hoe het werkt

- **De workflow:** `.github/workflows/CI-image.yml`, met twee jobs. Bij een pull request naar `main` draait `check`; bij een push naar `main`, en met de hand (`workflow_dispatch`), draait `image`. Beide doen dezelfde stappen. Die staan één keer in het bestand, met YAML-ankers (`&` en `*`), zodat de check precies scant wat er gepubliceerd wordt; alleen `image` pusht daarna.
- **Rechten:** standaard geen (`permissions: {}`); `check` krijgt alleen `contents: read`, `image` alleen `contents: read` en `packages: write`. Bij een pull request vanuit een fork krijgt het token volgens GitHub sowieso alleen leesrechten, en geen secrets.
- **Bouwen en pushen** met de gewone `docker`-opdrachten, zonder actions van derden. Het token gaat via stdin naar `docker login`.
- **De SBoM:** Trivy 0.76.0, vast op versie en digest, leest de image als tar-bestand en maakt er een CycloneDX-SBoM van: alleen de lijst, zonder lekken of VEX. jq zet de naam en tag van de image als hoofdonderdeel. De SBoM gaat als artifact bij de run, ook als de scan daarna een lek vindt.
- **De VEX:** `vex/openvex.json`, OpenVEX 0.2.0, per lek welke pakketten met welke versie de image niet raken, en waarom. Vóór de scan controleert een stap met jq dat elke verklaring een geldige reden heeft en een PURL met versie; Trivy zelf controleert dat niet (T-115).
- **De scan:** tussen de SBoM en het pushen. Trivy scant de SBoM, niet de image zelf, met de VEX erbij. Een lek van HIGH of CRITICAL stopt de job, ook zonder oplossing, tenzij de VEX het voor die versie uitsluit; wat de VEX wegfiltert, staat apart in de log. Stopt de job, dan komt er geen nieuwe image op ghcr.io, en kan `deployment.py azure` hem ook niet uitrollen. Bij een pull request faalt de check.
- **De securitytest:** alleen in `check`, na de scan. `deployment.py local` start de stack van `compose.yaml` zonder vragen, met wegwerpgeheimen in `.env` op de runner; daarna draait `tests/securitytest.py --wipe`, met een test per onderwerp. Een controle die faalt, laat de check falen. `--wipe` moet erbij, omdat de test de accounts van de database leegmaakt; op de runner is dat de bedoeling.
- **DAST (`CI-dast.yml`):** bij elke pull request, naast `check`, met een eigen stack, in een eigen workflow. Daar draait de ZAP baseline, passief, en `zap-rules.tsv` legt per regel de beslissing vast: opgelost op FAIL, geaccepteerd op IGNORE met de reden. Een melding zonder beslissing laat de job falen.
- **Uitrollen (`CD-azure.yml`):** na een geslaagde Image op `main` die `app/` veranderde, in de environment `azure`, die alleen `main` toestaat en op goedkeuring wacht. De job logt met OIDC in als `id-notes-deploy`, leest de template van de app uit Azure, zet alleen de image, en controleert de nieuwe revisie en `/login`. Terraform blijft de bron van al het andere. Een aparte workflow, zodat CI (`CI-image.yml`) en CD elk hun eigen rechten hebben.
- **De ruleset op `main`:** een pull request is verplicht, de check `check` moet slagen, en de bypass-lijst is leeg, ook voor de beheerder. Goedkeuren door een tweede persoon is niet nodig: er is maar één beheerder.
- **Twee tags:** de commit-hash, en `app-` met de tree-hash van `app/`. `deployment.py azure` rekent die tweede zelf uit met `git rev-parse HEAD:app`, en kijkt anoniem bij ghcr.io of de image er is en openbaar is, zoals Container Apps hem ophaalt. Een commit die alleen Terraform of de BoK verandert, heeft zo geen nieuwe build nodig.
- **Dependabot** houdt `actions/checkout` bij, net als de pakketten en de images (MIT-33).

## Waarom het veilig is

| Wat | Hoe | Gemeten |
|---|---|---|
| Het token mag niet meer dan nodig | `permissions: {}`, en per job alleen `contents: read` en `packages: write` | T-103: de log van de run toont `Contents: read`, `Metadata: read` en `Packages: write` |
| Een action kan niet verschuiven | `actions/checkout` op een volledige commit-hash, niet op een tag; GitHub raadt dat zelf aan | T-103: opgehaald op `3d3c42e5` |
| Een pull request publiceert niets | Bij een pull request draait alleen `check`, met `contents: read`; `image` draait daar niet | T-110: alleen `check` draaide, met `Contents: read` en `Metadata: read` |
| De lijst klopt | De SBoM bevat het besturingssysteem, de Debian-pakketten en precies de 14 Python-pakketten uit `requirements.txt` | T-106: 103 onderdelen; een scan op de SBoM vindt hetzelfde als een scan op de image |
| Een bekend lek gaat niet live | Trivy vóór het pushen; met een lek stopt de job | T-105: met pip 4 keer HIGH (exit 1), zonder pip 0 (exit 0) |
| Een bekend lek komt niet op `main` | Dezelfde scan bij elke pull request, en de ruleset maakt die verplicht | T-110: een image zonder lek gaat door (Trivy 0.76.0). T-111: een pull request met pip faalt met 4 keer HIGH, en GitHub houdt de merge tegen |
| Niemand komt om de check heen | De ruleset, met een lege bypass-lijst | T-112: een push rechtstreeks naar `main` geweigerd (`GH013`) |
| Een lek zonder oplossing gaat niet ongezien door | Geen `--ignore-unfixed` meer; alleen een verklaring in de VEX laat het door | T-114: 44 meldingen van HIGH, 8 lekken, alle zonder oplossing en eerder ongezien. T-116: met de VEX 0 over, de 44 apart in de log |
| Wat een bezoeker ziet, heeft geen open melding | De ZAP baseline bij elke pull request, met een beslissing per melding | T-135: zes meldingen, twee van Low; T-136: opgelost of geaccepteerd, 0 open |
| Een slechtere instelling in Terraform valt op | `trivy config` op `terraform/` in `CI-iac.yml`, met een beslissing per melding in `.trivyignore.yaml` (MIT-47) | T-137: negen meldingen zonder beslissingen, exit 1. T-138: met beslissingen exit 0 |
| Een bekend patroon in de eigen code valt op | CodeQL bij elke pull request en push, voor Python, JavaScript en de workflows | T-131: een TOTP-geheim in de log van de check gevonden; T-132: weg na de fix; T-134: een melding van high houdt de merge tegen |
| Een verklaring zonder reden telt niet | De stap Check VEX, vóór de scan | T-116: vijf kapotte varianten geweigerd, de echte VEX door |
| Een wijziging die een maatregel breekt, komt niet op `main` | De securitytest in de check, die de ruleset verplicht maakt | T-125: 182 controles, alles goed, in 212 s |
| mount draait niet als root | Geen programma met een setuid- of setgid-bit (MIT-42) | T-116: 0, eerst 11; de regressietest slaagt |
| Geen sleutel voor Azure in GitHub | OIDC: Entra ID accepteert alleen het token van een job in de environment `azure` van deze repo, met de vaste ID's | T-127: een token met een ander subject geweigerd (`AADSTS700213`) |
| Uitrollen gaat niet ongezien | De environment `azure` wacht op goedkeuring van de beheerder | T-128: de job begon pas na Approve, en zette de image in 76 s |
| De pipeline kan op Azure alleen de app wijzigen | Eén eigen rol, alleen op de container app | T-129: één toekenning, drie acties, alleen op `ca-notes` |
| Geen token dat kan uitlekken | Geen eigen token meer; dat van de run vervalt na de run | De stap met een token (classic) is weg uit `setup.py` (nu `deployment.py`) |

## Wat het niet oplost

- **Wie een pull request kan mergen, bepaalt de image,** en kan hem uitrollen: met `deployment.py azure`, of door de uitrol vanuit GitHub goed te keuren. Die goedkeuring komt van hetzelfde account als de merge: ze houdt een uitrol tegen die je niet wilde, niet een overgenomen account. Als beheerder kan hij ook de ruleset uitzetten. Je GitHub-account, met tweestapsverificatie, is dus de sleutel.
- **De check draait uit de pull request zelf.** Een pull request die de workflow aanpast, kan de check groen maken (MC-30, stap 6); alleen wie mergt, ziet dat in de wijzigingen.
- **De securitytest test de lokale stack, niet Azure.** Key Vault, TLS naar de database en de alerts ziet hij niet. En een pull request die de test aanpast, kan hem groen maken, net als de scan (MC-30, stap 6).
- **ZAP ziet alleen de buitenkant, en blokkeert niet.** Hij scant zonder account en valt niet actief aan, dus de pagina's achter de login en een echte aanval ziet hij niet. De job `dast` is niet verplicht in de ruleset (MIT-46).
- **CodeQL houdt alleen high en hoger tegen.** Sinds 2026-10-20 eist de ruleset de uitkomst van CodeQL; een melding van medium of low ziet alleen wie in het Security-tabblad of op de pull request kijkt (MIT-45, T-134).
- **Elke pull request wacht langer:** de check duurt zo'n 4 minuten, vooral door de securitytest.
- **De scan ziet niet alles.** Een lek dat pas later bekend wordt, ziet de scan pas bij de volgende pull request of push, een draaiende image wordt niet opnieuw gescand, en MEDIUM en LOW houden niet tegen. En hij ziet niets van wat buiten dpkg en pip om in de image zit: Python zelf en de OpenSSL in `cryptography` (T-118, deelvraag 3 van het onderzoek). De 15 bibliotheken die psycopg-binary meenam, zijn sinds MIT-43 weg; libpq komt nu uit Debian (T-121).
- **Een verklaring in de VEX kan fout zijn.** De check ziet of er een reden staat, niet of die klopt; dat ziet alleen wie mergt.
- **Elk nieuw lek van HIGH of CRITICAL houdt elke pull request tegen,** ook een die alleen de BoK verandert, tot er een beslissing is. Dat is de bedoeling, maar het kost werk.
- **Niet ondertekend.** Of een image echt uit deze workflow komt, is niet na te gaan.
- **De SBoM blijft 90 dagen.** Daarna is hij weg bij GitHub; hij hangt nog niet aan de image zelf. Opnieuw scannen, als er later een lek bekend wordt, gebeurt nog niet.
- **Het pakket is openbaar.** Iedereen kan de image ophalen; er staan geen geheimen in, en de code is ook openbaar.
- **Uitrollen gebeurt nog op je eigen pc.** Valt die tijdens een `apply` weg, dan kan er een resource buiten de state blijven (zie de eerste uitrol hieronder).

## Keuzes

- **Gewone `docker`-opdrachten, geen actions van derden.** Elke action is code van iemand anders, met het token van de run; met alleen `actions/checkout` is er één om vast te zetten en bij te houden.
- **Een tag op de inhoud van `app/`.** Hetzelfde idee als een digest: dezelfde inhoud geeft dezelfde tag. Zo hoeft er niet na elke commit gebouwd te worden voordat je kunt uitrollen.
- **Een openbaar pakket, geen inloggegevens voor Container Apps.** Dan staat er nergens een token voor de registry; de prijs is dat iedereen de image kan ophalen.
- **Elk lek houdt tegen, ook zonder oplossing.** Tot deelvraag 2 alleen een lek met een oplossing (`--ignore-unfixed`); volgens Trivy laat die optie alleen lekken zien waarvoor een oplossing is. Dat was ook een beslissing: alle andere accepteren zonder te kijken. Nu vraagt elk lek een beslissing (MIT-41).
- **Scannen op de SBoM, niet op de image.** Dezelfde uitkomst (T-106), en zo wordt de SBoM echt gebruikt in plaats van alleen bewaard. Dezelfde SBoM kan later opnieuw gescand worden, zonder de image.
- **OpenVEX, niet CycloneDX-VEX.** Een CycloneDX-VEX wijst via het `serialNumber` naar één SBoM, en Trivy geeft elke SBoM een nieuw nummer (T-114); een OpenVEX wijst naar het pakket, met een PURL. De SBoM blijft alleen de lijst.
- **Een maatregel boven een verklaring.** Voor de lekken in mount was een verklaring alleen mogelijk geweest, met de lege `/etc/fstab`; zonder setuid-bit (MIT-42) hangt het niet meer af van een bestand dat iemand later vult.
- **pip uit de image, geen nieuwe versies kiezen.** De vier lekken zaten in de eigen kopieën van pip; weghalen wat niet nodig is, was de kleinste oplossing.
- **Trivy als image in een opdracht, niet als action.** Om dezelfde reden: geen actions van derden. De prijs: Dependabot houdt de versie van Trivy niet bij.
- **Trivy, niet Syft met Grype.** Uit deelvraag 1 van het onderzoek: in een labmeting en een benchmark op GitHub-runners vond Trivy precies de vier lekken van pip, in één tool, en was het per run ruim een minuut sneller. Syft met Grype liet met de standaardinstellingen diezelfde lekken door.
- **Eén workflow met twee jobs, en YAML-ankers.** Twee workflows met dezelfde stappen kunnen uit elkaar lopen; één job voor beide zou bij een pull request ook `packages: write` krijgen. Dependabot leest de ankers ook (`aliases: true` in zijn parser).
- **Een lege bypass-lijst.** Anders is de rem met één klik te omzeilen, ook door jezelf, per ongeluk, zoals bij pull request #2.
- **Uitrollen vanuit GitHub, maar pas na goedkeuring (20-10-2026).** Automatisch na elke merge is sneller, maar dan rolt wie mergt meteen uit. Met een rol alleen op de container app, niet op de resource group: dan kon de pipeline ook de database, de job of het netwerk wijzigen.

## De eerste uitrol (18-10-2026)

- **Regio: France Central.** West Europe neemt geen nieuwe tenants aan (`RequestDisallowedByAzure`), en in Germany West Central mag deze subscription geen PostgreSQL maken (`restricted`). Terraform controleert dat nu al bij het plan, via de capabilities-API van PostgreSQL (`database.tf`); `az postgres flexible-server list-skus` liet het niet zien.
- **Providers:** Container Apps, PostgreSQL en Log Analytics stonden niet aan op de nieuwe subscription; Terraform registreert ze zelf.
- **Wat misging:** azurerm 5.8.0 kon het verwijderen van de Container Apps-omgeving in Germany West Central niet volgen (`polling support for the Content-Type "" was not implemented`); Azure verwijderde hem wel. Een onderbroken `apply` liet daarna een private DNS-zone buiten de state; `terraform import` nam hem op, zonder iets in Azure te veranderen.
- **Gemeten na de uitrol:** HTTPS met een geldig certificaat, HTTP met een 301 naar HTTPS, HSTS, CSP, `no-store` en een sessiecookie met `Secure`. De schema-job draaide en slaagde. De log komt in Log Analytics, met het adres van de bezoeker (T-102, T-104), en de identiteit van de app heeft geen rol op de vault van de eigenaar (T-86).
- **Opnieuw opgebouwd (18-10-2026, 's avonds):** alles op Azure weggehaald, ook de state-opslag, en met `python scripts/deployment.py azure` vanaf nul opnieuw neergezet: eerst de nieuwe bootstrap met minimale rollen en zonder accountsleutels (MIT-38, T-109), daarna Terraform met de Engelse image. De app draaide daarna de image van de laatste commit, met HSTS, CSP, `no-store` en een 301 van HTTP naar HTTPS.
- **Weer weggehaald (19-10-2026):** met `python scripts/deployment.py undo`, na de TLS-meting (T-113). Alleen `NetworkWatcherRG` bleef staan; die maakt Azure zelf bij een netwerk, en hij kost niets. Vóór de hacking week rol ik opnieuw uit.

### De regio, vergeleken (18-10-2026)

Gemeten en opgezocht na de eerste uitrol, om te zien of een andere regio sneller of goedkoper is. De ping is één meting met azurespeed.com vanuit de browser, in Nederland. De prijzen komen uit de Azure Retail Prices API: PostgreSQL B1ms 730 uur plus 32 GB opslag per maand, in euro; Container Apps per vCPU-seconde in dollar, omdat de API dat bedrag in euro op 0 afrondt.

| Regio | Ping | PostgreSQL per maand | Container Apps per vCPU-s | Kan het? |
|---|---|---|---|---|
| West Europe | 14 ms | €16,63 | $0,000034 | Nee: neemt geen nieuwe tenants aan (`RequestDisallowedByAzure`) |
| Germany West Central | 18 ms | €16,63 | $0,000024 | Nee: PostgreSQL is `restricted` voor deze subscription |
| UK South | 20 ms | €15,94 | $0,000034 | Ja, maar buiten de EU |
| Belgium Central | 21 ms | €16,63 | $0,000031 | Nee: geen log search alert (`scheduledQueryRules`) in deze regio |
| France Central | 23 ms | €15,94 | $0,000024 | Ja, en uitgerold |

- **Beschikbaarheid gecontroleerd met Azure zelf.** De capabilities-API van PostgreSQL per regio (B1ms en versie 18 zijn er in alle vijf), en de regio's per soort resource (`az provider show`): in Belgium Central bestaat alles wat Terraform maakt, behalve de log search alert van MIT-37. De action group is wereldwijd. Of die alert in een andere regio mag staan dan de workspace, is nergens bevestigd te vinden.
- **Ping maakt niet uit.** 9 ms tussen de snelste en France Central, terwijl inloggen alleen al zo'n 130 ms rekent aan Argon2id (gemeten in de regressietest).
- **Prijs maakt weinig uit.** De database scheelt hooguit €0,69 per maand. Container Apps blijft binnen het gratis tegoed van 180.000 vCPU-seconden en 360.000 GiB-seconden per subscription per maand, ook een week hackmode met 1 replica (0,25 vCPU en 0,5 GiB: 151.200 vCPU-seconden en 302.400 GiB-seconden); daarboven is France Central per vCPU-seconde het goedkoopst.
- **UK South ligt buiten de EU.** Dan staan gebruikersnamen, IP-adressen in de log en het e-mailadres van de beheerder in het Verenigd Koninkrijk; dat moet Laws & Compliance dan verantwoorden.
- **Besluit: France Central blijft.** Het goedkoopst, in de EU, en al uitgerold en gemeten.

## Volgende stappen, één per keer

1. Gedaan: een scan van de image op bekende lekken, met een rem vóór het publiceren (MIT-35).
2. Gedaan: de SBoM van elke image, als bewijs bij de build, en de scan daarop (MIT-36).
3. Gedaan: deelvraag 1 van het onderzoek: welk formaat en welke tool, waar de SBoM gemaakt wordt, wie hem leest, en hoe een merge wordt tegengehouden. Het antwoord: CycloneDX 1.7 van het gebouwde image, gemaakt en gescand met Trivy, op de SBoM, met een ruleset.
4. Gedaan (19-10-2026): daaruit een check bij elke pull request die de image bouwt, de SBoM maakt en scant, en niets publiceert, verplicht via een ruleset (MIT-39).
5. Gedaan (19-10-2026): deelvraag 2 van het onderzoek: elk lek van HIGH of CRITICAL vraagt een beslissing, vastgelegd in de VEX (MIT-41), en geen setuid-bits meer in de image (MIT-42).
6. De SBoM van de image op `main` elke dag opnieuw scannen, zodat een lek dat na de build bekend wordt niet op de volgende pull request wacht (MC-11).
7. Gedaan (20-10-2026): de securitytest in de check van stap 4, zodat een wijziging die een maatregel breekt niet op `main` komt (MIT-39, T-125).
8. Gedaan (20-10-2026): SAST met CodeQL, voor Python, JavaScript en de workflows, met Dependabot alerts en private vulnerability reporting (MIT-45). Als default setup in de instellingen, niet als workflow-bestand: minder om bij te houden, maar een kopie van de repo krijgt het dus niet vanzelf.
9. Gedaan (20-10-2026): uitrollen vanuit GitHub (CD), alleen de image, met OIDC en zonder sleutel, pas na goedkeuring, en alleen als er voor Azure is gekozen (MIT-44). `deployment.py azure` zet de environment `azure` en de drie ID's als environment secrets, niet als repository-variabelen: dan staan ze niet in de openbare log. In een fork of kopie zonder Azure doet de job niets. `deployment.py undo` haalt de environment weer weg.

## Screenshots

Voor het verslag, lokaal in `screenshots/Week 8 CI-CD/` (niet in de repo).

| Onderdeel | Voor | Na | Code |
|---|---|---|---|
| De image bouwen | `week8_voor_image_1_met_de_hand` | `week8_na_image_1_door_github` | `week8_code_image_1_workflow` |
| De scan | `week8_voor_scan_1_vier_lekken` | `week8_na_scan_1_schoon` | `week8_code_image_1_workflow` |
| De SBoM | `week8_voor_sbom_1_geen_lijst` | `week8_na_sbom_1_bij_de_run` | `week8_code_image_1_workflow` |
| De scan met de VEX | `week8_voor_vex_1_ignore_unfixed` | `week8_na_vex_1_weggefilterd_in_de_log` | `week8_code_vex_1_openvex` |
| De check bij een pull request | `week8_voor_check_1_gemerged` | `week8_na_check_1_tegengehouden` | `week8_code_check_1_workflow` |
| De log van de mislukte check | geen | `week8_na_check_2_log_vier_lekken` | `week8_code_check_1_workflow` |
| Een pull request zonder lek | geen | `week8_na_check_3_schoon_door` | `week8_code_check_1_workflow` |
| De ruleset op `main` | `week8_voor_ruleset_1_geen_regels` | `week8_na_ruleset_1_main` | geen: staat in de instellingen |

## Bronnen

Opgehaald en gecontroleerd op 18-10-2026.

- GitHub, secure use of GitHub Actions ("Pin references to actions to a commit SHA"; het token "the minimum required permissions"): https://docs.github.com/en/actions/reference/security/secure-use
- GitHub, publiceren met `GITHUB_TOKEN` (het pakket krijgt de zichtbaarheid van de repo): https://docs.github.com/en/packages/managing-github-packages-using-github-actions-workflows/publishing-and-installing-a-package-with-github-actions
- GitHub, zichtbaarheid van een pakket ("Once you make a package public, you cannot make it private again"): https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility
- Trivy, SBoM maken ("By default, `--format cyclonedx` represents SBOM and doesn't include vulnerabilities"): https://trivy.dev/latest/docs/supply-chain/sbom/
- Trivy, een SBoM scannen ("Trivy can take the following SBOM formats as an input and scan for vulnerabilities"): https://trivy.dev/latest/docs/target/sbom/
- Trivy, filtering (`--ignore-unfixed`: "To skip all unfixed vulnerabilities"): https://trivy.dev/latest/docs/configuration/filtering/
- Trivy, VEX als bestand (OpenVEX via PURL, CycloneDX via BOM-Link met `serialNumber`), opgehaald op 19-10-2026: https://trivy.dev/latest/docs/supply-chain/vex/file/
- OpenVEX, specificatie v0.2.0, opgehaald op 19-10-2026: https://github.com/openvex/spec/blob/main/OPENVEX-SPEC.md
- GitHub, events die een workflow starten (bij `pull_request`: "The `GITHUB_TOKEN` has read-only permissions in pull requests from forked repositories"), opgehaald op 19-10-2026: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
- GitHub, regels voor rulesets ("The pull request doesn't necessarily have to be approved, but it must be opened"), opgehaald op 19-10-2026: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets
- GitHub changelog, YAML-ankers in workflows (18-09-2025), opgehaald op 19-10-2026: https://github.blog/changelog/2025-09-18-actions-yaml-anchors-and-non-public-workflow-templates/
- Dependabot, de parser van workflows (`YAML.safe_load(content, aliases: true, ...)`), gelezen op 19-10-2026: https://github.com/dependabot/dependabot-core/blob/main/github_actions/lib/dependabot/github_actions/workflow_file.rb
- Microsoft, regio's die geen nieuwe klanten aannemen: https://learn.microsoft.com/azure/azure-resource-manager/troubleshooting/error-region-access-policy
- Azure Retail Prices API (PostgreSQL B1ms en opslag, Container Apps, Log Analytics per regio): https://prices.azure.com/api/retail/prices
- Azure Speed Test (ping per regio vanuit de browser): https://www.azurespeed.com/Azure/Latency
- Microsoft, prijzen van Container Apps ("The first 180,000 vCPU-seconds, 360,000 GiB-seconds, and 2 million requests per subscription per month are free"): https://azure.microsoft.com/pricing/details/container-apps/
