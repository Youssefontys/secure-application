# Week 6: Encryption

Het TOTP-geheim staat nu versleuteld in de database. De app versleutelt het met AES-256-GCM voordat het de database in gaat, en de sleutel staat buiten de database. De gekozen focus is daarmee **databaseversleuteling op kolomniveau, in de app**. Key management met Azure Key Vault is de volgende laag en komt bij de Azure-aanvulling (zie "Later").

De details staan in de entries (MC-17, MC-22; MIT-17) en de tests (T-34, T-63, T-64). Dit bestand vat ze samen.

## Versleutelen, hashen en ondertekenen

Drie verschillende dingen, die in deze app allemaal voorkomen:

- **Versleutelen** is tweerichtingsverkeer: wie de sleutel heeft, krijgt de oorspronkelijke waarde terug. Dat is nodig voor gegevens die de app zelf moet lezen. Het TOTP-geheim is zo'n gegeven: de app rekent er elke code mee uit.
- **Hashen** is eenrichtingsverkeer: de app kan alleen controleren of iets klopt. Dat is genoeg voor de herstelcode (SHA-256, MIT-11), en later voor wachtwoorden (Argon2id, bij Secure password storage). Die worden dus niet versleuteld.
- **Ondertekenen** bewijst dat niemand iets heeft veranderd, maar verbergt niets. De sessiecookie is ondertekend met `FLASK_SECRET_KEY`, niet versleuteld.

## De dreiging

- **Wie:** iemand die de database leest zonder via de app te gaan, via een gelekte backup of het volume (C-04), het databasewachtwoord (A-06), of de eigenaarrol (MC-08).
- **Wat die eerst kreeg:** het TOTP-geheim van elk account, leesbaar (MC-17), samen met het leesbare wachtwoord (MC-01). Daarmee is elk account over, ondanks de verplichte tweede factor.
- **Wat die nu krijgt:** het wachtwoord nog wel, maar het geheim alleen als `v1:` en onleesbare tekens. Zonder de sleutel (A-09) is daar geen code mee te maken.

## Wat er beter wordt

| Onderdeel | Voor | Na |
|---|---|---|
| TOTP-geheim in de database (MIT-17) | Leesbaar: wie de database leest, maakt zelf geldige codes | Versleuteld met AES-256-GCM; de sleutel staat niet in de database |
| Gegevens verplaatsen (MIT-17) | n.v.t. | Een versleuteld geheim dat naar de rij van een ander account wordt gekopieerd, ontsleutelt daar niet |

## Hoe het werkt

- **Algoritme:** AES-256-GCM uit de library `cryptography`. Het OWASP Cryptographic Storage Cheat Sheet raadt AES aan, bij voorkeur met 256 bits, in een geauthenticeerde modus zoals GCM. Die modus versleutelt en merkt ook op als iemand de versleutelde waarde wijzigt.
- **Nonce:** per waarde een nieuwe, willekeurige van 96 bits, de lengte die NIST aanraadt. Met dezelfde sleutel mag een nonce nooit twee keer worden gebruikt; daarom is hij per waarde nieuw.
- **Associated data:** de soort (`totp_secret`) en de `user_id` gaan mee. Ze worden gecontroleerd maar niet versleuteld. Dezelfde waarde in een andere rij ontsleutelt dus niet.
- **Sleutelversie:** elke waarde begint met `v1:`. Een nieuwe sleutel kan later als `v2` naast de oude.
- **De sleutel (A-09):** `DATA_ENCRYPTION_KEY`, 256 bits, uit de omgeving van de app. Lokaal staat hij in `.env`, op Azure komt hij uit Key Vault zonder dat de code verandert. Hij staat los van `FLASK_SECRET_KEY`, zodat elke sleutel één doel heeft.
- **Ontsleutelen mislukt:** dan telt het als geen geheim, en wordt elke code geweigerd. Bij twijfel gaat de deur dus dicht. Alleen een half ingesteld geheim wordt dan vervangen, want dat werkte nog nergens (T-65).
- **In de code:** `encrypt()` en `decrypt()` in `app/encryption.py`. Versleuteld wordt in `setup_2fa()`, ontsleuteld in `setup_2fa()`, `qr_2fa()` en `check_code()`.

## Waarom het veilig is

| Wat | Hoe | Gemeten |
|---|---|---|
| Het geheim staat niet leesbaar in de database | `users.totp_secret` bevat `v1:` gevolgd door nonce, versleuteld geheim en tag | T-34 |
| Een waarde werkt alleen op haar eigen plek | De `user_id` gaat mee als associated data | T-63 |
| Een onleesbaar half ingesteld geheim zet niemand vast | Het wordt vervangen; het werkte nog nergens | T-65 |
| De sleutel staat niet bij de data | Alleen in de omgeving van de app; niet in de database | T-64 |
| Geen zelfgeschreven cryptografie | AES-GCM uit `cryptography`, vastgezet op 50.0.2 met `cffi` en `pycparser` (MIT-03) | `pip freeze` gelijk aan `requirements.txt` |

## Wat nog leesbaar is

Alleen het TOTP-geheim is versleuteld. Per gegeven waar het staat en waar het hoort:

| Gegeven | Hoe het nu staat | Waar het hoort |
|---|---|---|
| Wachtwoorden (A-01) | Leesbaar in `users.password` (MC-01) | Hashen met Argon2id, bij Secure password storage. Niet versleutelen: de app hoeft ze nooit terug te lezen |
| Notities (A-02) | Leesbaar in `notes` | Kan met dezelfde helper; bewust niet in deze stap |
| Gebruikersnamen (A-04) | Leesbaar | Nodig om op te zoeken bij het inloggen |
| Herstelcode (A-08) | Alleen de SHA-256 | Klaar: gehasht |
| Tellers van de poginglimieten | HMAC's als sleutel | Klaar |
| Sessiecookie (A-03) | Ondertekend, niet versleuteld: de inhoud (`user_id`, sessieversie) is leesbaar voor wie de cookie heeft | Bewust: er staat niets geheims in |
| Verkeer tussen browser en app (F-01, F-02) | HTTP zonder TLS, lokaal | TLS bij Azure (App Service, `HTTPS_ONLY`) |
| Verbinding tussen app en database (F-03) | Zonder TLS, lokaal | `sslmode=require` op Azure |
| Databasebestanden en volume (C-04, F-04) | Geen schijfversleuteling lokaal | Op Azure versleutelt de dienst de opslag; te controleren bij de Azure-stap |
| Geheimen in `.env` (A-05, A-06, A-09) | Leesbaar op de ontwikkelmachine en in de omgeving van de container | Key Vault, bij de Azure-aanvulling |

## Wat het niet oplost

- **Wie de sleutel heeft, leest het geheim (MC-22).** Lokaal staat de sleutel in `.env` en in de omgeving van de container, en de container draait als root (MC-14). Ook met Key Vault heeft de draaiende app de sleutel; wie de app overneemt, heeft hem dus ook.
- **Sleutel kwijt is geheimen kwijt.** Zonder de sleutel moet elke gebruiker tweestapsverificatie opnieuw instellen, via de herstelcode. Die werkt nog, want hij is gehasht en niet versleuteld. Lokaal is dat geen probleem; op Azure bewaakt Key Vault de sleutel.
- **Een nieuwe sleutel is voorbereid, niet gebouwd.** De versie `v1:` staat erin, maar ontsleutelen met een oude naast een nieuwe sleutel moet nog worden geschreven.
- **Versleuteling beschermt tegen lezen, niet tegen schrijven.** Een eigen geheim in de kolom zetten lukt niet zonder de sleutel. Maar wie de database kan wijzigen (MC-08), zet `totp_enabled` op false, logt in met het leesbare wachtwoord (MC-01) en stelt tweestapsverificatie in met een eigen telefoon. Dat hoort bij databasebeveiliging (eigen rollen voor de app) en bij Argon2 voor de wachtwoorden.

## Keuzes

- **In de app versleutelen, niet in de database met pgcrypto.** Met pgcrypto gaat de sleutel bij elke query als parameter mee naar de database, dus juist naar de plek van de data. Staat het loggen van statements aan (`log_statement = all`), dan staat hij ook in de databaselog: `17_sqli_databaselog`, gemaakt met die instelling tijdelijk aan, laat zien dat parameters daar leesbaar staan. OWASP raadt aan om sleutels waar mogelijk op een andere plek te bewaren dan de versleutelde data.
- **`cryptography`, geen eigen AES.** De TOTP-berekening is zelf geschreven, omdat het een HMAC is van een paar regels en met testvectoren te bewijzen. AES zelf schrijven is daarmee niet te vergelijken.
- **De waarde binden aan haar plek** met associated data. Zonder die binding zou een aanvaller met schrijfrechten het geheim van zijn eigen account in de rij van een slachtoffer kunnen zetten.
- **Een aparte sleutel**, niet `FLASK_SECRET_KEY` hergebruiken. OWASP raadt aan om verschillende sleutels volledig onafhankelijk te houden.
- **Bij twijfel weigeren:** wat niet ontsleutelt, telt als geen geheim.
- **Geen migratie van bestaande geheimen.** We zitten in de ontwikkelfase; lokaal staan alleen testaccounts, en de eerste uitrol op Azure begint met een lege database.
- **Alleen het TOTP-geheim in deze stap.** Daar zit het grootste risico. Notities kunnen later met dezelfde helper.

## Later: key management op Azure

Dit onderdeel wordt verder uitgewerkt bij de Azure-aanvulling:

- **De sleutel uit Key Vault**, met alleen de managed identity van de app als lezer. App Service kan de omgevingsvariabele daaruit vullen, dus de code blijft gelijk.
- **Eventueel envelope-versleuteling:** een tweede sleutel (KEK) in Key Vault die `DATA_ENCRYPTION_KEY` (de DEK) versleutelt. Volgens OWASP werkt dat alleen als de KEK apart van de DEK staat; de versleutelde DEK mag dan bij de data.
- **Een nieuwe sleutel** via `v2:`, naast `v1:`.
- **De opslag van de Terraform-state** wordt al versleuteld met een eigen sleutel (RSA 4096) in Key Vault, door `scripts/azuresetup_v2.py`. Dat is key management voor de infrastructuur.

## Vergelijking met BOK-SECENGINEER

| | BOK-SECENGINEER | Deze repo |
|---|---|---|
| TOTP-geheim | Versleuteld met pgcrypto (`pgp_sym_encrypt`) in de database; de sleutel gaat bij elke query mee | Versleuteld met AES-256-GCM in de app; de sleutel komt nooit in de database |
| Notities | Versleuteld via HashiCorp Vault Transit | Leesbaar (bewust nog niet) |
| Waarde gebonden aan haar plek | Nee | Ja, met associated data |

## Screenshots

Voor het verslag, lokaal in `screenshots/Week 6 Encryption/` (niet in de repo).

| Onderdeel | Voor | Na | Code |
|---|---|---|---|
| TOTP-geheim in de database | `week6_voor_1_totp_geheim_leesbaar` | `week6_na_1_totp_geheim_versleuteld` | `week6_code_1_versleuteling` |

## Bronnen

Opgehaald en gecontroleerd op 16-10-2026 en 17-10-2026.

- OWASP Cryptographic Storage Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html
- `cryptography`, AEAD (AESGCM): https://cryptography.io/en/latest/hazmat/primitives/aead/
