# Week 5: Authentication

Inloggen vraagt nu twee factoren: het wachtwoord en een code van 6 cijfers uit een authenticator-app (TOTP, RFC 6238). Dat is verplicht voor elk account. Daaromheen staan vier maatregelen die de tweede factor pas echt sterk maken: oude sessies vervallen (sessieversie), raden wordt begrensd (poginglimieten), een kwijtgeraakte telefoon sluit niemand buiten (herstelcode), en wie nog geen tweede factor heeft, kan alleen het instellen afmaken. Daarbij komen twee basisonderdelen die er vanaf het begin in hadden moeten zitten: wie het wachtwoord vergeet, stelt een nieuw in met de herstelcode en een code uit de app, en een nieuw wachtwoord moet 12 tot 64 tekens zijn.

De details staan in de entries (UC-02, UC-07 tot UC-09; MC-03, MC-04, MC-12, MC-15 tot MC-21; MIT-05 tot MIT-14) en de tests (T-12 tot T-15, T-28 tot T-61). Dit bestand vat ze samen.

Systeemauthenticatie is in deze stap niet veranderd: de app logt bij de database in met een wachtwoord uit de omgeving en zonder TLS (AU-03). Certificaten of mTLS tussen app en database zijn een mogelijke volgende stap.

## Wat er beter wordt

| Onderdeel | Voor | Na |
|---|---|---|
| Tweede factor (MIT-05, MIT-12) | Een wachtwoord was genoeg; raden, hergebruik of het leesbare wachtwoord uit de database gaf toegang | Een juist wachtwoord geeft alleen een halve login (`pending_user_id`), en daarmee opent geen enkele route. Pas met een geldige code ben je binnen. Elk account moet het instellen |
| Sessieversie (MIT-09) | Een gekopieerde cookie werkte na uitloggen of een wachtwoordwijziging gewoon door, tot 31 dagen | Uitloggen, een nieuw wachtwoord en het (opnieuw) instellen van de tweede factor maken elke oudere cookie ongeldig, ook een kopie |
| Poginglimieten (MIT-06, MIT-10) | Onbeperkt wachtwoorden raden; foute codes 15 minuten vast op slot | Wachtwoord: 20 fouten per IP-adres of 5 per account vanaf één adres, dan een blokkade die verdubbelt. Code: 5 fouten, dan 15 minuten, verdubbelend tot 24 uur |
| Wachtwoord vergeten (MIT-14) | Wachtwoord vergeten betekende: account kwijt | Met de herstelcode en een code uit de app een nieuw wachtwoord, en meteen een nieuwe herstelcode; het oude wachtwoord is daarvoor niet nodig |
| Sterkte-eis (MIT-13) | Elk wachtwoord werd geaccepteerd, ook `a` | Een nieuw wachtwoord moet 12 tot 64 tekens zijn |
| Herstelcode (MIT-11) | Telefoon kwijt betekende: account kwijt | Een eenmalige herstelcode van 128 bits vervangt één keer de code; daarna stel je de tweede factor opnieuw in |

## Waarom het veilig is

| Wat | Hoe | Gemeten |
|---|---|---|
| Correct algoritme | TOTP volgens RFC 6238 zonder dependency: geheim van 160 bits (RFC 4226 R6), 6 cijfers, 30 seconden, hoogstens één stap klokverschil (RFC 6238 5.2), vergelijken in constante tijd | Alle 16 testvectoren van RFC 6238 en RFC 4226 (T-35) |
| Halve login opent niets | De sessie krijgt na het wachtwoord alleen `pending_user_id`; die vervalt na 5 minuten, en ook als de sessieversie intussen verandert | T-32, T-33, T-38 |
| Elke code één keer | De laatst geaccepteerde tijdstap staat in de database. RFC 6238 5.2: de verifier MUST NOT accept the second attempt. De controle zit in dezelfde UPDATE die de stap opslaat | Twee gelijktijdige verzoeken met dezelfde code: één binnen (T-31) |
| Raden begrensd | Tellers per sleutel in de database (`throttle.py`), niet in de sessie. Elke poging telt vóór de controle, dus ook gelijktijdige verzoeken blijven binnen de limiet. De sleutels zijn HMAC's, dus geen leesbare namen of IP-adressen. Een geslaagde login wist de accountteller; van die van het adres gaat alleen die ene poging af | T-12, T-30, T-39 tot T-43, T-58, T-60, T-61 |
| Oude sessies vervallen | Een `session_version` in de database en in de cookie; die moeten gelijk zijn | T-14, T-15, T-37 |
| Herstelcode | 128 willekeurige bits; alleen de SHA-256 staat in de database. Werkt één keer, met de hash in de WHERE van de UPDATE; eigen blokkade; nieuwe code alleen met een code uit de app | T-44 tot T-49 |
| Wachtwoord vergeten | Twee van de drie factoren: herstelcode en telefoon. Een foute herstelcode telt per adres en per naam per adres, en een onbekende naam krijgt hetzelfde antwoord. Pas na een juiste herstelcode geldt de blokkade van de codestap. Nieuw wachtwoord en verbruik van de code in één UPDATE; daarna niet automatisch ingelogd | T-52, T-54 tot T-57 |
| Sterkte-eis | 12 tot 64 tekens bij registreren, wijzigen en wachtwoord vergeten, zonder samenstellingsregels (NIST SP 800-63B-4) | T-13, T-53 |
| Verplicht | `login_required` laat een gebruiker zonder tweede factor alleen het instellen afmaken | T-50 |
| Geheim beschermd | QR-code en sleutel alleen tijdens het instellen, daarna 404; `Cache-Control: no-store` op alle pagina's met het geheim of de herstelcode | T-36, T-49 |
| Niet buitensluiten, niet weghalen | Aanzetten pas na een eerste geldige code. Opnieuw instellen en een nieuwe herstelcode vragen een code (AU-06), dus wie alleen de sessie heeft, kan de tweede factor niet vervangen | T-28, T-45 |

## Wat het niet oplost

- **Raden met het wachtwoord in handen (MC-15).** Met de verdubbelende blokkade zijn dat ongeveer 1.855 pogingen per jaar: 0,56% kans om een code te raden. Met de vaste blokkade van eerst was dat ongeveer 41%.
- **Phishing in real time (MC-16).** Een nepsite die de code direct doorgeeft, komt binnen. Daartegen helpt alleen een factor die aan het domein gebonden is, zoals WebAuthn of passkeys.
- **Het TOTP-geheim staat leesbaar in de database (MC-17).** Een databaselek levert wachtwoord en geheim samen. Versleuteling hoort bij database security.
- **Een gestolen sessiecookie (MC-04)** werkt tot de gebruiker uitlogt of zijn gegevens wijzigt, en anders tot 31 dagen. De tweede factor helpt daar niet: de cookie is van na de code.
- **Uitloggen logt alle apparaten uit.** Zonder sessies op de server bij te houden kan het niet preciezer.
- **Buitensluiten (MC-18).** Op een gedeeld netwerk of achter een proxy delen gebruikers één IP-adres. Achter een proxy moet de app het echte clientadres krijgen, anders telt iedereen als één adres.
- **Verspreid raden (MC-03).** Wie vanaf heel veel adressen raadt, wordt per account niet begrensd; dat is bewust, anders kan iedereen met een gebruikersnaam een account blokkeren. De tweede factor vangt dit op.
- **De bewaarde herstelcode (MC-19, MC-21)** is zo veilig als de plek waar hij ligt; met het wachtwoord of met de telefoon erbij is het account over. De gebruiker merkt het pas bij het volgende inloggen, want er is geen e-mail.
- **De eerste instelling (MC-20).** Wie het wachtwoord heeft van een account dat de tweede factor nog niet heeft ingesteld, kan zijn eigen app koppelen ("trust on first use"). Daartegen helpt een tweede kanaal, zoals een bevestigde e-mail.
- **Wachtwoorden staan nog leesbaar opgeslagen (MC-01).** Dat hoort bij secure password storage (Argon2id).
- **Geen blocklist (MC-03).** Een veelgebruikt wachtwoord van 12 tekens of meer wordt nog geaccepteerd. NIST eist een vergelijking met veelgebruikte en gelekte wachtwoorden; die is gepland, met een lijst in de repo in plaats van een externe dienst.

## Keuzes

- **TOTP zelf geschreven in plaats van `pyotp`.** Het algoritme is een HMAC over een teller (ongeveer 20 regels). Zonder library is er een dependency minder om bij te houden (MC-11), en de berekening is met de testvectoren uit de RFC te bewijzen. De QR-code komt wel uit een library, `segno`: pure Python zonder eigen dependencies, vastgezet op 1.6.6.
- **Tellers in de database, niet in de sessie.** Een sessie is een cookie van de aanvaller zelf; hij kan een nieuwe beginnen. Een teller in de database kan hij niet terugzetten.
- **Tellen vóór de controle.** Wie eerst controleert en pas daarna telt, laat verzoeken die tegelijk binnenkomen allemaal door. Van 40 gelijktijdige foute wachtwoorden werden er eerst minstens 14 gecontroleerd, terwijl de limiet 5 is, en de verdubbelteller sprong naar 17. Nu telt één SQL-statement de poging en weigert boven de limiet. BOK-SECENGINEER telde alleen bij herstel vooraf; bij inloggen en de code telde het pas na de controle, met hetzelfde gat.
- **Geen blokkade per account over alle adressen in de wachtwoordstap.** Anders kan iedereen die een gebruikersnaam kent dat account buitensluiten. In de codestap mag het wel: die bereik je alleen met het juiste wachtwoord.
- **SHA-256 voor de herstelcode, geen Argon2.** Bij 128 willekeurige bits valt er niets te raden of op te zoeken. Trage hashes zijn er voor wachtwoorden die mensen zelf verzinnen.
- **De herstelcode zet de tweede factor uit.** De telefoon is kwijt, dus het oude geheim is niet meer te vertrouwen. Omdat de tweede factor verplicht is, stuurt de app meteen naar het opnieuw instellen.
- **Aanzetten pas na een geldige code.** Zo sluit niemand zichzelf buiten met een verkeerd ingestelde app.
- **Wachtwoord vergeten met herstelcode en telefoon, niet met e-mail.** Twee van de drie factoren, zoals in BOK-SECENGINEER, maar hier naast de route voor een kwijtgeraakte telefoon. Een reset per e-mail vraagt een e-mailadres (een persoonsgegeven) en een maildienst, en maakt de mailbox de sleutel tot het account.
- **Geen blokkade per account voor foute herstelcodes bij wachtwoord vergeten.** Die route is bereikbaar zonder wachtwoord; een blokkade per account zou iedereen die een naam kent de herstelroutes laten blokkeren. Pas na een juiste herstelcode telt een foute code per account, zoals na een juist wachtwoord.
- **Na de reset niet ingelogd, wel meteen een nieuwe herstelcode.** Het OWASP Forgot Password Cheat Sheet raadt automatisch inloggen af. Zonder nieuwe herstelcode zou de volgende kwijtgeraakte telefoon het account kosten.
- **12 tot 64 tekens, geen samenstellingsregels.** NIST SP 800-63B-4 eist minstens 8 tekens voor een wachtwoord dat één van meer factoren is, en 15 als het de enige factor is; 12 ligt ertussen, net als in BOK-SECENGINEER. 64 is de lengte die NIST minstens wil toestaan. Verplichte cijfers of leestekens verbiedt NIST.
- **400 bij een fout, 429 bij een blokkade, geen 401.** Een 401 moet volgens RFC 9110 een `WWW-Authenticate`-header hebben, en die hoort bij HTTP-authenticatie, niet bij een inlogformulier. 429 is de code voor rate limiting (RFC 6585); `Retry-After` geeft in seconden hoe lang de blokkade nog duurt. Dat verraadt niets nieuws: de melding op de pagina noemt dezelfde tijd.

## Vergelijking met BOK-SECENGINEER

De oplossingen lijken nu veel meer op elkaar. Het grootste verschil dat overblijft, is dat de oude het TOTP-geheim versleutelt.

| | BOK-SECENGINEER | Deze repo |
|---|---|---|
| TOTP | `pyotp` | Eigen code, met RFC-testvectoren gecontroleerd |
| QR-code | `qrcode`, als data-URI in de pagina | `segno`, via een eigen route (past bij een strikte CSP) |
| Versies vastgezet | Nee | Ja |
| Verplicht | Ja, bij registratie | Ja, na het eerste wachtwoord |
| Bevestigen met een eerste code | Nee | Ja |
| Opnieuw instellen (nieuwe telefoon) | Niet mogelijk | Kan, met een code |
| Geheim in de database | Versleuteld (pgcrypto) | Leesbaar (MC-17) |
| Poginglimieten | Per account en per IP, oplopend; bij herstel telt een poging vóór de controle, bij inloggen en de code pas erna | Per account en per IP, oplopend; elke poging telt vóór de controle |
| Gelijktijdige verzoeken | Rijslot (`FOR UPDATE`) en een tweede controle | Voorwaarden in één UPDATE |
| Halve login vervalt na | 10 minuten | 5 minuten, en bij een nieuwe sessieversie |
| Oude sessies ongeldig | Sessieversie (`auth_version`) | Sessieversie (`session_version`) |
| Herstel | Wachtwoord herstellen met herstelcode én 2FA-code; voor een kwijtgeraakte telefoon geen route | Allebei: telefoon kwijt (wachtwoord en herstelcode) en wachtwoord vergeten (herstelcode en 2FA-code) |
| Wachtwoordeisen | 12 tot 1024 tekens | 12 tot 64 tekens |
| Hash van de herstelcode | Argon2id | SHA-256 (128 willekeurige bits) |
| CSRF-tokens | In elk geval op de authenticatieformulieren | Nee (MC-05) |
| Logging van pogingen | Ja | Nee |

Wat de oude meer heeft, hoort bij andere BoK-onderwerpen: versleuteling bij database security, CSRF bij secure coding, logging bij logging en monitoring.

## Screenshots

Voor het verslag, lokaal in `screenshots/Week 5 Authentication/` (niet in de repo). Elke "voor" en "na" heeft een balk met de echte URL.

| Onderdeel | Voor | Na | Code |
|---|---|---|---|
| Tweede factor | `week5_voor_1` tot `_3` | `week5_na_1` tot `_9` | `week5_code_1_inloggen`, `week5_code_2_controle` |
| Sessieversie | `week5_voor_sessie_1`, `_2` | `week5_na_sessie_1`, `_2` | `week5_code_3_sessieversie` |
| Poginglimieten | `week5_voor_blokkade_1` | `week5_na_blokkade_1` tot `_3` | `week5_code_4_blokkade` |
| Herstelcode | `week5_voor_herstel_1` | `week5_na_2_herstelcode_getoond`, `week5_na_herstel_1` tot `_4` | `week5_code_5_herstelcode` |
| Verplicht | `week5_voor_verplicht_1`, `_2` | `week5_na_verplicht_1`, `_2` | `week5_code_6_verplicht` |
| Wachtwoord vergeten en sterkte-eis | geen (basisonderdeel) | `week5_na_sterkte_1`, `week5_na_vergeten_1` tot `_4` | `week5_code_7_wachtwoord_vergeten` |

## Bronnen

Opgehaald en gecontroleerd op 15-10-2026; NIST en OWASP op 16-10-2026.

- RFC 6238, TOTP: https://www.rfc-editor.org/rfc/rfc6238 (paragraaf 5.2 en bijlage B)
- RFC 4226, HOTP: https://www.rfc-editor.org/rfc/rfc4226 (eis R6 en bijlage D)
- RFC 9110, HTTP Semantics: https://www.rfc-editor.org/rfc/rfc9110 (paragraaf 10.2.3 en 15.5.2)
- RFC 6585, Additional HTTP Status Codes: https://www.rfc-editor.org/rfc/rfc6585 (paragraaf 4)
- NIST SP 800-63B-4, Password Verifiers: https://pages.nist.gov/800-63-4/sp800-63b.html#passwordver
- OWASP Forgot Password Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html
- Key Uri Format (`otpauth://`): https://github.com/google/google-authenticator/wiki/Key-Uri-Format
