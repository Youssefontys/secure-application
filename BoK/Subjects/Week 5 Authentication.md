# Week 5: Authentication

Gebruikers kunnen tweestapsverificatie aanzetten: naast het wachtwoord een code van 6 cijfers uit een authenticator-app (TOTP, RFC 6238). Met alleen het wachtwoord kom je dan niet meer binnen. De details staan in de entries (UC-07, MC-15 tot MC-17, MIT-05 tot MIT-08) en de tests (T-28 tot T-36); dit bestand vat ze samen.

Systeemauthenticatie is in deze stap niet veranderd: de app logt bij de database in met een wachtwoord uit de omgeving en zonder TLS (AU-03). Certificaten of mTLS tussen app en database zijn een mogelijke volgende stap.

## Wat er beter wordt

**Voor:** een wachtwoord was genoeg. Raden, een elders gelekt wachtwoord hergebruiken of het leesbare wachtwoord uit de database halen gaf direct toegang (MC-01, MC-03).

**Na:** wie tweestapsverificatie aanzet, heeft twee factoren nodig: iets wat je weet (het wachtwoord) en iets wat je hebt (de app met het geheim). Een juist wachtwoord geeft alleen een halve login: de sessie krijgt `pending_user_id` en geen `user_id`, en daarmee opent geen enkele route. Gemeten: `/`, `/account` en een notitie aanmaken sturen allemaal terug naar `/login` (T-32).

## Waarom het veilig is

| Wat | Hoe | Gemeten |
|---|---|---|
| Correct algoritme | TOTP volgens RFC 6238, zonder dependency: geheim van 160 bits (RFC 4226 R6), 6 cijfers, 30 seconden, hoogstens één stap klokverschil (RFC 6238 5.2), vergelijken in constante tijd | Alle 16 testvectoren van RFC 6238 en RFC 4226 (T-35) |
| Raden is begrensd (MIT-06) | Na 5 foute codes op rij zit de codestap 15 minuten op slot, ook voor de juiste code. Per account in de database, niet in de sessie | Bij de 5e fout op slot, ook vanuit een nieuwe sessie (T-30) |
| Elke code één keer (MIT-07) | De laatst geaccepteerde tijdstap staat in de database. RFC 6238 5.2: de verifier MUST NOT accept the second attempt. De controle zit in dezelfde UPDATE die de stap opslaat | Twee gelijktijdige verzoeken met dezelfde code: één binnen (T-31) |
| Halve login vervalt | Na 5 minuten weggegooid | T-33 |
| Geheim beschermd (MIT-08) | QR-code en sleutel alleen tijdens het instellen, daarna 404; `Cache-Control: no-store`; QR-code via een eigen route, niet inline | T-36 |
| Niet buitensluiten, niet weghalen | Aanzetten pas na een eerste geldige code. Uitzetten vraagt een code (AU-06), dus wie alleen de sessie heeft, kan de tweede factor niet weghalen | T-28 |

## Wat het niet oplost

- **Doorzetten bij raden (MC-15).** Met het wachtwoord in handen en 5 pogingen per 15 minuten is de kans 0,14% per dag, maar ongeveer 41% na een jaar. Een blokkade die oploopt bij herhaling zou dat drukken.
- **Phishing in real time (MC-16).** Een nepsite die de code direct doorgeeft, komt binnen. Daartegen helpt alleen een factor die aan het domein gebonden is, zoals WebAuthn of passkeys.
- **Het geheim staat leesbaar in de database (MC-17).** Een databaselek levert wachtwoord en geheim samen.
- **Het is een keuze van de gebruiker.** Accounts zonder tweestapsverificatie blijven op één factor (MC-03).
- **Een gestolen sessiecookie** werkt nog steeds, want die is van na de code (MC-04).

## Keuzes

- **TOTP zelf geschreven in plaats van `pyotp`.** Het algoritme is een HMAC over een teller (ongeveer 20 regels). Zonder library is er een dependency minder om bij te houden (MC-11), en de berekening is met de testvectoren uit de RFC te bewijzen. De QR-code komt wel uit een library, `segno`: pure Python zonder eigen dependencies, vastgezet op 1.6.6.
- **Teller in de database, niet in de sessie.** Een sessie is een cookie van de aanvaller zelf; hij kan een nieuwe beginnen. Een teller in de database kan hij niet terugzetten.
- **Aanzetten pas na een geldige code.** Zo sluit niemand zichzelf buiten met een verkeerd ingestelde app.
- **Optioneel.** Verplicht maken kan later. Dan is er ook een herstelroute nodig voor wie zijn telefoon kwijt is, en die is er nu niet.

## Vergelijking met BOK-SECENGINEER

Niet dezelfde oplossing. De oude is op meer punten gehard, de nieuwe is kleiner en op een paar punten beter.

| | BOK-SECENGINEER | Deze repo |
|---|---|---|
| TOTP | `pyotp` | Eigen code, met RFC-testvectoren gecontroleerd |
| QR-code | `qrcode`, als data-URI in de pagina | `segno`, via een eigen route (past bij een strikte CSP) |
| Versies vastgezet | Nee (`requirements.txt` zonder versies) | Ja |
| Verplicht | Ja, bij registratie | Nee, aan te zetten op het profiel |
| Bevestigen met een eerste code | Nee | Ja |
| Uitzetten | Niet mogelijk | Kan, met een code |
| Geheim in de database | Versleuteld (pgcrypto) | Leesbaar (MC-17) |
| Blokkade foute codes | Per account én per IP, oplopend tot 24 uur | Per account, vast 15 minuten |
| Gelijktijdige verzoeken | Rijslot (`FOR UPDATE`) en een tweede controle | Voorwaarden in één UPDATE |
| Halve login vervalt na | 10 minuten | 5 minuten |
| Sessies ongeldig maken | Sessieversie (`auth_version`) | Nee (MC-04) |
| Herstel zonder telefoon | Herstelcode | Nee |
| CSRF-tokens | In elk geval op de authenticatieformulieren | Nee (MC-05) |
| Logging van pogingen | Ja | Nee |

Wat de oude heeft en deze nog niet, staat in deze repo als open misuse case. Het meeste hoort bij andere BoK-onderwerpen: versleuteling bij database security, CSRF bij secure coding, logging bij logging en monitoring.

## Bronnen

Opgehaald en gecontroleerd op 15-10-2026.

- RFC 6238, TOTP: https://www.rfc-editor.org/rfc/rfc6238 (paragraaf 5.2 en bijlage B)
- RFC 4226, HOTP: https://www.rfc-editor.org/rfc/rfc4226 (eis R6 en bijlage D)
- Key Uri Format (`otpauth://`): https://github.com/google/google-authenticator/wiki/Key-Uri-Format
