# Week 6: Encryption

Wie de database leest, vindt geen bruikbaar geheim meer:
- Het TOTP-geheim en de notities zijn versleuteld met AES-256-GCM (MIT-17, MIT-18).
- De wachtwoorden zijn gehasht met Argon2id (MIT-19).

De versleutelde gegevens kan de app terug ontsleutelen met een sleutel die buiten de database staat. Van een wachtwoord bestaat alleen een hash die niet terug te rekenen is.

De gekozen focus is **databaseversleuteling op kolomniveau, in de app**. Ook key management en secrets horen bij deze week: hoe dat nu geregeld is, staat onder "Key management en secrets". Key Vault is de volgende laag en komt bij de Azure-aanvulling (zie "Later").

De details staan in de entries (MC-01, MC-17, MC-22, MC-23; MIT-17 tot MIT-19) en de tests (T-10, T-34, T-63 tot T-70). Dit bestand vat ze samen.

## Versleutelen, hashen en ondertekenen

Drie verschillende dingen, die in deze app allemaal voorkomen:

- **Versleutelen** is tweerichtingsverkeer: wie de sleutel heeft, krijgt de oorspronkelijke waarde terug. Dat is nodig voor gegevens die de app zelf moet lezen: het TOTP-geheim, waarmee de app elke code uitrekent, en de notities, die de gebruiker wil teruglezen.
- **Hashen** is eenrichtingsverkeer: de app kan alleen controleren of iets klopt. Dat is genoeg voor wachtwoorden (Argon2id, MIT-19) en de herstelcode (SHA-256, MIT-11). Die worden dus niet versleuteld. OWASP noemt versleutelen van wachtwoorden alleen voor uitzonderingen waarin het origineel echt terug moet.
- **Ondertekenen** bewijst dat niemand iets heeft veranderd, maar verbergt niets. De sessiecookie is ondertekend met `FLASK_SECRET_KEY`, niet versleuteld.

## De dreiging

- **Wie:** iemand die de database leest zonder via de app te gaan. Dat kan via:
  - een gelekte backup of het volume (C-04);
  - het databasewachtwoord (A-06);
  - de verbinding van de app (MC-08); sinds MIT-27 een eigen rol, die nog wel alle rijen mag lezen.
- **Wat die eerst kreeg:** van elk account het wachtwoord (MC-01), het TOTP-geheim (MC-17) en alle notities (MC-23), allemaal leesbaar. Daarmee was elk account over, ondanks de verplichte tweede factor.
- **Wat die nu krijgt:**
  - Van elk wachtwoord alleen een Argon2id-hash. Raden kan nog, maar elke gok kost 19 MiB en een berekening, per account opnieuw.
  - Het geheim en de notities als `v1:` en onleesbare tekens. Zonder de sleutel (A-09) is daar niets mee te doen.

## Wat er beter wordt

| Onderdeel | Voor | Na |
|---|---|---|
| Wachtwoord in de database (MIT-19) | Leesbaar: wie de database leest, logt direct in, ook op andere sites waar het wachtwoord hergebruikt is | Een Argon2id-hash met eigen salt; terugrekenen kan niet, alleen raden |
| TOTP-geheim in de database (MIT-17) | Leesbaar: wie de database leest, maakt zelf geldige codes | Versleuteld met AES-256-GCM; de sleutel staat niet in de database |
| Notities in de database (MIT-18) | Leesbaar: wie de database leest, leest alle notities van iedereen | Versleuteld met AES-256-GCM; alleen de eigenaar leest ze, op de pagina |
| Gegevens verplaatsen (MIT-17, MIT-18) | n.v.t. | Een geheim of notitie die naar de rij van een ander account wordt gekopieerd, ontsleutelt daar niet |
| Een onbekende naam bij inloggen (MIT-19) | n.v.t. | Even snel geweigerd als een fout wachtwoord: ook dan rekent de app een hash |

## Hoe het werkt

### Versleutelen: het TOTP-geheim en de notities (MIT-17, MIT-18)

- **Algoritme:** AES-256-GCM uit de library `cryptography`. Het OWASP Cryptographic Storage Cheat Sheet raadt AES aan, bij voorkeur met 256 bits, in een geauthenticeerde modus zoals GCM. Die modus versleutelt en merkt ook op als iemand de versleutelde waarde wijzigt.
- **Nonce:** per waarde een nieuwe, willekeurige van 96 bits, de lengte die NIST aanraadt. Met dezelfde sleutel mag een nonce nooit twee keer worden gebruikt; daarom is hij per waarde nieuw.
- **Associated data:** de soort (`totp_secret`, `note_title`, `note_body`) en de `user_id` gaan mee. Ze worden gecontroleerd maar niet versleuteld. Dezelfde waarde in een andere rij, of een titel als inhoud, ontsleutelt dus niet.
- **Sleutelversie:** elke waarde begint met `v1:`. Een nieuwe sleutel kan later als `v2` naast de oude.
- **De sleutel (A-09):** `DATA_ENCRYPTION_KEY`, 256 bits, uit de omgeving van de app.
  - Lokaal staat hij in `.env`; op Azure komt hij uit Key Vault, zonder dat de code verandert.
  - Hij staat los van `FLASK_SECRET_KEY`, zodat elke sleutel één doel heeft.
  - Eén sleutel voor het geheim en de notities; de soort in de associated data houdt ze uit elkaar.
- **Ontsleutelen mislukt:**
  - Bij het TOTP-geheim telt dat als geen geheim, en wordt elke code geweigerd; bij twijfel gaat de deur dus dicht. Alleen een half ingesteld geheim wordt dan vervangen, want dat werkte nog nergens (T-65).
  - Bij een notitie staat er "(unreadable)".
- **In de code:** `encrypt()` en `decrypt()` in `app/encryption.py`.
  - Het geheim wordt versleuteld in `setup_2fa()`, en ontsleuteld in `setup_2fa()`, `qr_2fa()` en `check_code()`.
  - De notities lopen via `sealed()` en `readable()` in `app/notes.py`.

### Hashen: de wachtwoorden (MIT-19)

- **Algoritme:** Argon2id uit `cryptography`, dat de app al had voor AES; het rekenwerk doet OpenSSL. De minimale instelling uit het OWASP Password Storage Cheat Sheet: 19 MiB geheugen, 2 iteraties, 1 thread. Tot 29d201d kwam Argon2id uit `argon2-cffi`; het formaat is hetzelfde, dus oude hashes werken nog (T-88).
- **Salt:** per hash 16 willekeurige bytes. Hetzelfde wachtwoord geeft bij twee accounts dus twee verschillende hashes (T-68).
- **Wat er staat:** `$argon2id$v=19$m=19456,t=2,p=1$` met daarachter de salt en de hash. De instelling staat in de hash zelf, zodat de app weet waarmee hij moet controleren.
- **Onbekende naam:** dan rekent de app tegen een vaste hash. Een fout wachtwoord en een naam die niet bestaat, duren daardoor even lang (T-70: 101 en 100 ms).
- **Nieuwe instelling:** is een hash met een oudere instelling gemaakt, dan maakt de app bij de volgende geslaagde login een nieuwe (T-69). Zo raadt OWASP het aan. De app ziet het aan het begin van de hash, waar de instelling in staat.
- **In de code:** alles in `app/passwords.py`: `hash_password()`, `matches()`, `rehash_if_needed()` en `is_current()`. Registreren, inloggen, wachtwoord vergeten en wachtwoord wijzigen gebruiken alleen die functies.

## Waarom het veilig is

| Wat | Hoe | Gemeten |
|---|---|---|
| Het wachtwoord staat nergens | `users.password_hash` bevat alleen algoritme, instelling, salt en hash | T-10 |
| Elke hash geldt voor één account | Een eigen salt per hash | T-68 |
| Een oudere instelling verdwijnt vanzelf | Bij de volgende login een nieuwe hash | T-69 |
| Inloggen verraadt geen namen | Ook bij een onbekende naam één Argon2id-berekening | T-70 |
| Het geheim staat niet leesbaar in de database | `users.totp_secret` bevat `v1:` gevolgd door nonce, versleuteld geheim en tag | T-34 |
| De notities staan niet leesbaar in de database | `notes.title` en `notes.body` idem | T-66 |
| Een waarde werkt alleen op haar eigen plek | De soort en de `user_id` gaan mee als associated data | T-63, T-67 |
| Een onleesbaar half ingesteld geheim zet niemand vast | Het wordt vervangen; het werkte nog nergens | T-65 |
| De sleutel staat niet bij de data | Alleen in de omgeving van de app; niet in de database | T-64 |
| Geen zelfgeschreven cryptografie | AES-GCM en Argon2id uit `cryptography`, met de afhankelijkheden vastgezet (MIT-03) | `pip freeze` gelijk aan `requirements.txt` |

## Wat nog leesbaar is

Per gegeven waar het staat en waar het hoort:

| Gegeven | Hoe het nu staat | Waar het hoort |
|---|---|---|
| Wachtwoorden (A-01) | Een Argon2id-hash (MIT-19) | Klaar |
| TOTP-geheim (A-07) | Versleuteld (MIT-17) | Klaar |
| Notities (A-02) | Versleuteld (MIT-18) | Klaar |
| Herstelcode (A-08) | Alleen de SHA-256 | Klaar: gehasht |
| Tellers van de poginglimieten | HMAC's als sleutel | Klaar |
| Gebruikersnamen (A-04) | Leesbaar | Nodig om op te zoeken bij het inloggen |
| Aantal notities en hun tijden | Leesbaar | Nodig om te sorteren; geen inhoud |
| Sessiecookie (A-03) | Ondertekend, niet versleuteld: de inhoud (`user_id`, sessieversie) is leesbaar voor wie de cookie heeft | Bewust: er staat niets geheims in |
| Verkeer tussen browser en app (F-01, F-02) | HTTP zonder TLS, lokaal | Op Azure zet Container Apps TLS 1.2 of 1.3 ervoor en stuurt HTTP door naar HTTPS; daarbij `HTTPS_ONLY` (`terraform/app.tf`). Getoetst aan de richtlijnen van het NCSC: zie TLS op Azure hieronder |
| Verbinding tussen app en database (F-03) | Zonder TLS, lokaal | Op Azure TLS 1.3 met `sslmode=verify-full`, en de database alleen in een privé-netwerk (`terraform/database.tf`) |
| Databasebestanden en volume (C-04, F-04) | Geen schijfversleuteling lokaal | Op Azure versleutelt de dienst alle data, logs en backups op schijf, met een sleutel van Azure. Een eigen sleutel (CMK) kan alleen bij het aanmaken van de server |
| Geheimen in `.env` (A-05, A-06, A-09, A-10) | Leesbaar op de ontwikkelmachine en in de omgeving van de container | Key Vault (`terraform/keyvault.tf`) |

## Wat het niet oplost

- **Wie de sleutel heeft, leest het geheim en de notities (MC-22).** Lokaal staat de sleutel in `.env` en in de omgeving van de container. Ook met Key Vault heeft de draaiende app de sleutel. Wie de app overneemt, heeft hem dus ook, en ziet bovendien elk wachtwoord bij het inloggen voorbijkomen.
- **Een zwak wachtwoord blijft te raden.** Argon2id maakt elke gok duur, niet onmogelijk. De lengte-eis (MIT-13) helpt; een blocklist van veelgebruikte wachtwoorden is geparkeerd.
- **Versleuteling en hashen beschermen tegen lezen, niet tegen schrijven.** Wie de database kan wijzigen (MC-08), kan:
  - een eigen hash als wachtwoord zetten;
  - `totp_enabled` op false zetten en tweestapsverificatie met een eigen telefoon instellen;
  - notities verwijderen.

  Een eigen geheim of een eigen notitie erin zetten lukt niet, want daarvoor is de sleutel nodig. De eigen rol voor de app (MIT-27, Week 7) helpt hier maar half: die mag deze rijen nog steeds wijzigen, want de app doet dat zelf ook. Het schema aanpassen of weggooien kan hij niet meer.
- **Een notitie is gebonden aan de eigenaar, niet aan de notitie.** Wie de database kan wijzigen, kan titels en inhoud tussen notities van dezelfde gebruiker verwisselen. Tussen gebruikers of tussen titel en inhoud lukt dat niet (T-67).
- **Sleutel kwijt is geheimen en notities kwijt.** Tweestapsverificatie is opnieuw in te stellen via de herstelcode, want die is gehasht en niet versleuteld, en werkt dus nog. De notities zijn dan echt weg. Lokaal is dat geen probleem; op Azure bewaakt Key Vault de sleutel.
- **Een nieuwe sleutel is voorbereid, niet gebouwd.** De versie `v1:` staat erin, maar ontsleutelen met een oude sleutel naast een nieuwe moet nog worden geschreven.
- **Elke registratie kost 19 MiB en een berekening (MC-10).** Inloggen is begrensd (MIT-10), registreren nog niet.

## Keuzes

- **In de app versleutelen, niet in de database met pgcrypto.**
  - Met pgcrypto gaat de sleutel bij elke query als parameter mee naar de database, dus juist naar de plek van de data.
  - Staat het loggen van statements aan (`log_statement = all`), dan staat hij ook in de databaselog. `17_sqli_databaselog`, gemaakt met die instelling tijdelijk aan, laat zien dat parameters daar leesbaar staan.
  - OWASP raadt aan om sleutels waar mogelijk op een andere plek te bewaren dan de versleutelde data.
- **`cryptography`, geen eigen AES of Argon2.** De TOTP-berekening is wel zelf geschreven: dat is een HMAC van een paar regels, met testvectoren te bewijzen. AES en Argon2 zelf schrijven is daarmee niet te vergelijken.
- **Argon2id uit `cryptography`, niet uit `argon2-cffi`.** `cryptography` kan het sinds versie 44.0.0, en het PHC-formaat sinds 45.0.0. Hetzelfde algoritme en formaat, en twee pakketten minder in de image (MC-11).
- **Wachtwoorden hashen, niet versleutelen.** De app hoeft een wachtwoord nooit terug te lezen. Een versleuteld wachtwoord is met de sleutel in één keer leesbaar; een hash niet.
- **Argon2id met het minimum van OWASP, niet met de standaard van `argon2-cffi`, die BOK-SECENGINEER gebruikte.**
  - De standaard is het tweede aanbevolen profiel uit RFC 9106: 64 MiB, 3 iteraties, 4 threads. Dat is zwaarder; BOK-SECENGINEER gebruikte het.
  - Hier het minimum, omdat elke login op een kleine Azure-machine anders 64 MiB vraagt.
  - Verhogen kan later: de rehash bij de login zet bestaande hashes dan vanzelf om.
- **Ook rekenen bij een onbekende naam.** Anders is een onbekende naam sneller geweigerd dan een fout wachtwoord, en verraadt de responstijd welke namen bestaan (MC-09).
- **Geen pepper.** OWASP noemt dat alleen extra verdediging. Een pepper kan bovendien niet meer veranderen zonder de wachtwoorden van iedereen.
- **De waarde binden aan haar plek** met associated data. Zonder die binding kan een aanvaller met schrijfrechten zijn eigen geheim of notitie in de rij van een slachtoffer zetten.
- **Notities binden aan de eigenaar, niet aan de notitie.** Binden aan de notitie kan pas als het id bekend is, dus na de INSERT. Dat kost een extra query, voor alleen het verwisselen binnen één account.
- **Een aparte sleutel voor de data**, niet `FLASK_SECRET_KEY` hergebruiken. OWASP raadt aan om verschillende sleutels volledig onafhankelijk te houden.
- **Geen omzetting van bestaande gegevens.** We zitten in de ontwikkelfase. De lokale database is voor deze stap leeg opnieuw aangemaakt, en de eerste uitrol op Azure begint ook leeg.

## Key management en secrets

Waar de geheimen nu staan, wie ze kan lezen en hoe ze gemaakt worden:

| Geheim | Doel | Waar | Gemaakt |
|---|---|---|---|
| `DATA_ENCRYPTION_KEY` (A-09) | Versleutelt het TOTP-geheim en de notities | `.env`, omgeving van de app | 256 willekeurige bits |
| `FLASK_SECRET_KEY` (A-05) | Ondertekent de sessiecookie, en is de HMAC-sleutel van de tellers | `.env`, omgeving van de app | 256 willekeurige bits |
| `POSTGRES_PASSWORD` (A-06) | Wachtwoord waarmee de app inlogt op de database | `.env`, omgeving van app en database | 256 willekeurige bits |

- **Nooit in git.** `.env` en `backend.conf` staan in `.gitignore` (tot 31d93f9 `backend.*.conf`, één per omgeving); in de repo zit alleen `.env.example`, zonder waarden. Op 17-10-2026 is de hele geschiedenis doorzocht: geen sleutelwaarde, en nooit een `.env` of backend-bestand gecommit.
- **Zelf gemaakt, nooit getoond.** `python scripts/deployment.py lokaal` vult een ontbrekende of lege sleutel aan met 256 bits uit de module `secrets` van Python, en noemt alleen de naam. Een bestaande sleutel blijft staan.
- **Niet leeg starten.** Compose start niet als een van de vier leeg is (`${...:?}`). De app start niet met een `DATA_ENCRYPTION_KEY` die geen 256 bits is.
- **Eén doel per sleutel, op één na.** De gegevenssleutel staat los van de rest. `FLASK_SECRET_KEY` heeft twee taken. Een nieuwe sessiesleutel maakt daardoor ook alle tellers van de poginglimieten ongeldig (A-05).
- **De Azure-scripts zetten niets in GitHub.** Tot a9b2a23 kon `azuresetup_v2.py` ID's als GitHub-secret zetten, via stdin aan `gh`; geen workflow las ze, dus dat stuk is weg. Uitrollen vanuit GitHub krijgt later een eigen identiteit met een federated credential (OIDC), niet die van de opslag; tot b733d12 zette het script juist die in GitHub.
- **De sleutel van de Terraform-state.** Een eigen RSA-4096-sleutel in Key Vault, met purge protection en 90 dagen bewaartijd na verwijderen. De rollen zijn gescheiden: wie het script draait, beheert de sleutel (Key Vault Crypto Officer); de managed identity mag hem alleen gebruiken (Key Vault Crypto Service Encryption User).

Wat nog mist:
- Lokaal staan de sleutels leesbaar in `.env` en in de omgeving van de container (T-64, MC-22).
- Er is nog geen rotatie: `v2:` is voorbereid, niet gebouwd.
- De pipeline scant nog niet op geheimen.

## Key management op Azure

Uitgerold op 18-10-2026, in France Central (zie Week 8 voor de uitrol). In Container Apps staan de drie geheimen van de app alleen als verwijzing naar Key Vault, zonder waarde (gemeten met `az containerapp secret list`). Voor key management:

- **De geheimen komen nergens in Terraform terecht.** Terraform maakt ze als ephemeral waarde: de gegevenssleutel en de sessiesleutel elk 32 willekeurige bytes, de twee databasewachtwoorden elk 40 tekens. Die stuurt Terraform write-only naar Key Vault, dus ze staan niet in het plan en niet in de state. Het databasewachtwoord leest Terraform terug uit Key Vault, zodat vault en database altijd hetzelfde hebben, ook als een eerste uitrol halverwege stopt.
- **Alleen de app leest ze**, met een eigen managed identity die de rol Key Vault Secrets User heeft. Het wachtwoord van de eigenaar staat sinds MIT-27 in een eigen vault, die alleen de schema-job leest. Container Apps zet de waarden als omgevingsvariabele, dus de code blijft gelijk. Wie Terraform draait, mag geheimen schrijven (Key Vault Secrets Officer), niet de vault beheren.
- **Kwijtraken kan niet zomaar.** Purge protection en 90 dagen bewaartijd na verwijderen. Belangrijk, want sleutel kwijt is notities kwijt.
- **Een nieuwe sleutel.** De databasewachtwoorden en de sessiesleutel veranderen als `secret_version` omhoog gaat; Terraform start dan zelf de schema-job, die het nieuwe wachtwoord van de app-rol zet. De gegevenssleutel staat vast op versie 1, tot `v2:` gebouwd is.
- **Eventueel envelope-versleuteling:** een tweede sleutel (KEK) in Key Vault die `DATA_ENCRYPTION_KEY` (de DEK) versleutelt. Volgens OWASP werkt dat alleen als de KEK apart van de DEK staat; de versleutelde DEK mag dan bij de data.
- **De opslag van de Terraform-state** wordt al versleuteld met een eigen sleutel (RSA 4096) in Key Vault, door `scripts/azuresetup_v2.py`. Dat is key management voor de infrastructuur.

Trivy 0.75.0 vond op 17-10-2026 zeven punten in `terraform/`, met per punt een besluit:

| Punt | Ernst | Besluit |
|---|---|---|
| AZU-0013: Key Vault blokkeert het netwerk niet standaard (2 keer, sinds MIT-27 twee vaults) | CRITICAL | Bewust nog open. Lezen kan alleen met een Entra-token en een rol. Een firewall vraagt een vast adres voor wie Terraform draait, en eerst een test of Container Apps de geheimen dan nog ophaalt. Bij de eerste uitrol |
| AZU-0017: geheimen zonder vervaldatum (4 keer) | LOW | Bewust. Zonder automatische rotatie zet een vervaldatum de app op een dag stil, en de gegevenssleutel mag niet vervallen |
| AZU-0019, AZU-0024: verbindingen en checkpoints niet gelogd | MEDIUM | Bij Logging en monitoring, samen met waar de logs naartoe gaan |
| AZU-0021: verbindingen niet begrensd | MEDIUM | Bij Logging en monitoring; de app heeft zelf poginglimieten (MIT-10) |

## TLS op Azure, gemeten (19-10-2026)

Op Azure zet de ingress van Container Apps TLS voor de app. Terraform zegt alleen dat HTTP naar HTTPS gaat (`allow_insecure_connections = false`); versies, ciphers en het certificaat kiest het platform. Gemeten met openssl 3.5.9 vanaf de pc van de beheerder, en getoetst aan de TLS-richtlijnen van het NCSC (versie 2025-05). Die kennen vier niveaus: Goed, Voldoende, Uit te faseren en Onvoldoende (T-113, MIT-40).

| Onderdeel | Gemeten | Volgens het NCSC |
|---|---|---|
| Versies | TLS 1.3 en 1.2; 1.0 en 1.1 geweigerd | Gebruik TLS 1.3, en 1.2 voor oudere clients; 1.0 en 1.1 zijn sinds 2025 Onvoldoende |
| Ciphers | AES-256-GCM, ChaCha20-Poly1305 en AES-128-GCM, bij TLS 1.2 alleen met ECDHE-RSA; geen CBC, geen RSA-sleuteluitwisseling, geen DHE | De voorkeur gaat naar AES-256-GCM en ChaCha20-Poly1305; AES-128-GCM is Voldoende; CBC is Uit te faseren en RSA-sleuteluitwisseling Onvoldoende, maar die biedt de server niet aan |
| Sleuteluitwisseling | X25519 of P-256; niet X25519MLKEM768 | ECDHE is sinds 2025 Voldoende, met het oog op quantumcomputers; X25519MLKEM768 is Goed, en het NCSC raadt aan het nu al te overwegen |
| Certificaat | Van Microsoft, voor het standaarddomein van de omgeving: RSA-2048, SHA-384, geldig tot 25-01-2027, keten geldig | RSA van 2048 tot 3071 bits is sinds 2025 Uit te faseren; 3072 bits geeft de nagestreefde 128 bits sterkte |
| Intrekking | Rechtstreeks gevraagd: OCSP `good`; de server stuurt het antwoord niet mee | Gebruik OCSP-stapling als het kan; dat is privacyvriendelijker voor de bezoeker |
| Opties | Geen compressie; renegotiation door de client geweigerd; bij TLS 1.3 geen sessieticket, dus geen 0-RTT | Geen compressie, renegotiation bij voorkeur uit, 0-RTT uit: alle drie zo |

- **Nergens Onvoldoende, niet overal Goed.** Wat het verkeer nu beschermt, is volgens het NCSC voldoende.
- **De drie punten liggen bij het platform.** RSA-2048, geen hybride sleuteluitwisseling en geen OCSP-stapling zijn keuzes van Azure voor het standaarddomein; in `terraform/` is daar niets aan te zetten. Met een eigen domein kan Container Apps een eigen certificaat gebruiken, met een langere sleutel; de sleuteluitwisseling en de stapling blijven bij de ingress.
- **Zonder stapling vraagt de browser zelf.** Een browser die OCSP gebruikt, vraagt de status dan bij Microsoft op, en Microsoft ziet zo welke site er bezocht wordt.
- **De TLS stopt bij de ingress.** Van de ingress naar de container gaat het verkeer als HTTP, binnen het eigen netwerk van de omgeving (F-01).

## Vergelijking met BOK-SECENGINEER

| | BOK-SECENGINEER | Deze repo |
|---|---|---|
| Wachtwoorden | Argon2id met de standaard van `argon2-cffi` (64 MiB, 3 iteraties, 4 threads) | Argon2id met het minimum van OWASP (19 MiB, 2 iteraties, 1 thread), rehash bij de login en een vaste hash voor onbekende namen |
| TOTP-geheim | Versleuteld met pgcrypto (`pgp_sym_encrypt`) in de database; de sleutel gaat bij elke query mee | Versleuteld met AES-256-GCM in de app; de sleutel komt nooit in de database |
| Notities | Versleuteld via HashiCorp Vault Transit: de sleutel blijft in Vault, de app vraagt Vault om te versleutelen | Versleuteld met AES-256-GCM in de app, met dezelfde helper als het geheim |
| Waarde gebonden aan haar plek | Nee | Ja, met associated data |

## Screenshots

Voor het verslag, lokaal in `screenshots/Week 6 Encryption/` (niet in de repo).

| Onderdeel | Voor | Na | Code |
|---|---|---|---|
| TOTP-geheim in de database | `week6_voor_1_totp_geheim_leesbaar` | `week6_na_1_totp_geheim_versleuteld` | `week6_code_1_versleuteling` |
| Wachtwoord in de database | `week6_voor_2_wachtwoord_leesbaar` | `week6_na_2_wachtwoord_gehasht` | `week6_code_3_argon2` |
| Notities in de database | `week6_voor_3_notities_leesbaar` | `week6_na_3_notities_versleuteld` | `week6_code_2_notities` |

## Bronnen

Opgehaald en gecontroleerd op 16-10-2026 en 17-10-2026.

- OWASP Cryptographic Storage Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html
- OWASP Password Storage Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
- `cryptography`, AEAD (AESGCM): https://cryptography.io/en/latest/hazmat/primitives/aead/
- `cryptography`, Argon2id (sinds 44.0.0, PHC-formaat sinds 45.0.0): https://cryptography.io/en/latest/hazmat/primitives/key-derivation-functions/
- NCSC, Transport Layer Security (TLS): beveiligingsrichtlijnen, versie 2025-05 (de vier niveaus, hoofdstuk 3 en Bijlage A met de wijzigingen sinds 2021), gelezen op 19-10-2026: https://www.ncsc.nl/api/media/sites/default/files/TLS-Richtlijnen-2025-05.pdf
