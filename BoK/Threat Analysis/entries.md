# Entries

Nieuwste onderaan. Sjabloon en regels: zie `README.md` in deze map.
Status van een mitigatie: `open`, `gebouwd`, `bewezen`.

De baseline bevat bewust geen beveiligingsmaatregelen, behalve twee die het
framework en de databasebibliotheek al meebrengen (MIT-01 en MIT-02). Wat
daarna is toegevoegd, staat met de commit bij "Sinds".

## Use cases

### UC-01 Account aanmaken
- Actor: bezoeker
- Doel: een eigen account krijgen met gebruikersnaam en wachtwoord
- Onderdelen: C-01, C-02, C-03 (route `/register`, F-01, F-03)
- Assets: A-01, A-04
- Sinds: baseline

### UC-02 Inloggen en uitloggen
- Actor: gebruiker
- Doel: bewijzen wie je bent, met een wachtwoord en een code uit de authenticator-app (verplicht), een sessie krijgen, en die weer beeindigen
- Onderdelen: C-01, C-02, C-03 (routes `/login`, `/login/2fa`, `/logout`, AU-01, AU-02, AU-05)
- Assets: A-01, A-03, A-07
- Sinds: baseline

### UC-03 Eigen notities beheren
- Actor: ingelogde gebruiker
- Doel: notities aanmaken, lezen, aanpassen en verwijderen, en alleen die van jezelf zien
- Onderdelen: C-01, C-02, C-03 (routes `/`, `/notes/<id>/edit`, `/notes/<id>/delete`, AZ-01 tot AZ-04)
- Assets: A-02
- Sinds: baseline

### UC-04 Wachtwoord wijzigen
- Actor: ingelogde gebruiker
- Doel: een nieuw wachtwoord instellen voor het eigen account
- Onderdelen: C-01, C-02, C-03 (formulier op `/account`, verstuurd naar `/account/password`; AU-04, AZ-06)
- Assets: A-01
- Sinds: 782f0e2

### UC-05 Account verwijderen
- Actor: ingelogde gebruiker
- Doel: het eigen account en alle eigen notities definitief laten verwijderen
- Onderdelen: C-01, C-02, C-03 (knop op `/account`, verstuurd naar `/account/delete`; AU-04, AZ-07)
- Assets: A-01, A-02, A-04
- Sinds: b03197a

### UC-06 Eigen profiel bekijken
- Actor: ingelogde gebruiker
- Doel: zien met welk account je bent ingelogd, sinds wanneer het bestaat en hoeveel notities erin staan
- Onderdelen: C-01, C-02, C-03 (route `/account`, AZ-08)
- Assets: A-04
- Sinds: 23e2ed3

### UC-07 Tweestapsverificatie instellen en opnieuw instellen
- Actor: ingelogde gebruiker
- Doel: een authenticator-app koppelen, zodat inloggen naast het wachtwoord een code vraagt; een herstelcode krijgen of vervangen; en opnieuw instellen voor een nieuwe telefoon. Verplicht: zonder kan een gebruiker alleen het instellen afmaken
- Onderdelen: C-01, C-02, C-03 (`/account/2fa`, `/account/2fa/qr.svg`, `/account/2fa/recovery`, `/account/2fa/reset`; AU-06, AZ-09)
- Assets: A-07, A-08
- Sinds: 18e1424

### UC-08 Inloggen met de herstelcode
- Actor: gebruiker die zijn telefoon kwijt is
- Doel: met het wachtwoord en de herstelcode toch inloggen, en daarna tweestapsverificatie opnieuw instellen
- Onderdelen: C-01, C-02, C-03 (route `/login/recover`, AU-07)
- Assets: A-01, A-08
- Sinds: dc7d258

## Misuse cases

### MC-01 Wachtwoorden uit de database lezen
- Aanvallersdoel: toegang tot accounts van anderen, ook op andere sites
- Aanvaller: iemand met leestoegang tot de database of een backup (beheerder, gelekt volume, gecompromitteerde app)
- Assets / onderdelen: A-01, C-03, C-04, F-03
- Gerelateerde use case: UC-01, UC-02
- Stappen:
  - OR  1. De database rechtstreeks bevragen (`SELECT username, password FROM users`)
  - OR  2. Het databasevolume of een backup lezen (C-04)
  - OR  3. De webapplicatie overnemen en de wachtwoorden via F-03 opvragen
- Mitigaties: geen (het wachtwoord staat leesbaar)
- Restrisico: elk gelezen wachtwoord is direct bruikbaar. Bij een account met tweestapsverificatie is het wachtwoord alleen niet genoeg (MIT-05), maar wie de database leest, leest ook het TOTP-geheim (MC-17)
- Status: open
- Sinds: baseline

### MC-02 Notities van een ander lezen, aanpassen of verwijderen
- Aanvallersdoel: notities van een andere gebruiker lezen of vernietigen
- Aanvaller: elke ingelogde gebruiker met een eigen account
- Assets / onderdelen: A-02, C-02, AZ-03, AZ-04
- Gerelateerde use case: UC-03
- Stappen:
  - AND 1. Een eigen account aanmaken en inloggen (UC-01, UC-02)
  - AND 2. De id van een notitie van een ander invullen in `/notes/<id>/edit` of `/notes/<id>/delete` (de ids zijn opeenvolgende getallen)
- Mitigaties: geen (alleen "ingelogd?" wordt gecontroleerd, niet de eigenaar)
- Restrisico: alle notities zijn leesbaar en wijzigbaar voor elke gebruiker
- Status: open
- Sinds: baseline

### MC-03 Wachtwoord raden
- Aanvallersdoel: inloggen als een bekende gebruiker
- Aanvaller: iedereen die de gebruikersnaam kent of kan raden
- Assets / onderdelen: A-01, A-04, C-02, AU-01
- Gerelateerde use case: UC-02, UC-04
- Stappen:
  - OR  1. Veelgebruikte wachtwoorden proberen tegen een account (brute force)
  - OR  2. Een lijst gelekte wachtwoorden proberen tegen veel accounts (credential stuffing)
  - AND 3. Zwakke wachtwoorden worden bij registratie en bij wijzigen niet geweigerd
- Mitigaties: MIT-10 (stap 1 en 2: 20 fouten per IP-adres en 5 per account vanaf één adres, daarna een oplopende blokkade). MIT-05 en MIT-12 (stap 1 en 2: tweestapsverificatie is verplicht, dus een geraden wachtwoord geeft alleen een halve login). Nog geen sterkte-eis (stap 3)
- Restrisico: wie vanaf veel IP-adressen tegelijk raadt (een botnet), wordt per account niet begrensd; dat is bewust, zie MC-18. Een account dat het instellen nog niet heeft afgemaakt, zit nog op één factor (MC-20). En wie raadt, ziet aan de doorverwijzing naar `/login/2fa` dat het wachtwoord klopt
- Status: open
- Sinds: baseline

### MC-04 Sessiecookie stelen of blijven gebruiken
- Aanvallersdoel: als een andere gebruiker handelen
- Aanvaller: iemand die de cookie onderschept of kopieert (netwerk, gedeelde computer)
- Assets / onderdelen: A-03, A-05, C-01, F-01, F-02, AU-02
- Gerelateerde use case: UC-02
- Stappen:
  - OR  1. De cookie meelezen op het netwerk (HTTP, geen TLS, geen `Secure`-vlag)
  - OR  2. De cookie kopieren van een gedeelde of onbeheerde browser
  - OR  3. De sessiesleutel (A-05) bemachtigen en zelf een cookie ondertekenen
  - AND 4. De cookie blijft geldig tot hij verloopt (standaard 31 dagen). Uitloggen, een nieuw wachtwoord en tweestapsverificatie aanzetten of opnieuw instellen maken hem ongeldig (MIT-09)
- Mitigaties: MIT-09 (stap 4, zodra de gebruiker uitlogt of een van zijn inloggegevens wijzigt). Verder geen: de `HttpOnly`-vlag staat standaard aan in Flask; dat houdt JavaScript buiten beeld maar stopt stap 1 tot 3 niet
- Restrisico: een gekopieerde cookie werkt tot de gebruiker uitlogt of zijn wachtwoord of tweestapsverificatie wijzigt, en anders tot 31 dagen. Tweestapsverificatie helpt hier niet: de cookie is van na de code
- Status: open
- Sinds: baseline

### MC-05 Handelingen laten uitvoeren via een andere site (CSRF)
- Aanvallersdoel: namens een ingelogde gebruiker notities aanmaken, aanpassen of verwijderen
- Aanvaller: de eigenaar van een andere website die de gebruiker bezoekt
- Assets / onderdelen: A-01, A-02, A-03, C-01, C-02, AZ-02, AZ-04, AZ-06, AZ-07
- Gerelateerde use case: UC-03, UC-04, UC-05
- Stappen:
  - AND 1. De gebruiker is ingelogd en bezoekt de site van de aanvaller
  - AND 2. Die site stuurt een formulier naar `/`, `/notes/<id>/delete`, `/account/password`, `/account/delete` of `/logout`. Tweestapsverificatie opnieuw instellen (`/account/2fa/reset`) of een nieuwe herstelcode maken (`/account/2fa/recovery`) lukt zo niet, want daarvoor is een code nodig die de andere site niet heeft
  - AND 3. De browser stuurt de cookie mee
- Mitigaties: geen (geen CSRF-token; `SameSite` is niet ingesteld, dus het gedrag hangt van de browser af)
- Restrisico: elke POST-route is aanroepbaar vanaf een andere site
- Status: open
- Sinds: baseline

### MC-06 SQL-injectie
- Aanvallersdoel: de database lezen of wijzigen via invoer
- Aanvaller: iedere bezoeker
- Assets / onderdelen: A-01, A-02, C-02, C-03, F-03
- Gerelateerde use case: UC-02, UC-03
- Stappen:
  - OR  1. SQL in het gebruikersnaam- of wachtwoordveld van `/login`
  - OR  2. SQL in titel, inhoud of de gebruikersnaam bij registratie
- Mitigaties: MIT-02 (stappen 1 en 2)
- Restrisico: gering zolang elke query parameters gebruikt; een nieuwe route kan dit weer openen
- Status: gebouwd
- Sinds: baseline

### MC-07 Script in een notitie laten uitvoeren (opgeslagen XSS)
- Aanvallersdoel: JavaScript uitvoeren in de browser van een andere gebruiker, of de cookie lezen
- Aanvaller: iedere ingelogde gebruiker (zie ook MC-02 om andermans notitie te bereiken)
- Assets / onderdelen: A-02, A-03, C-01, C-02, F-02
- Gerelateerde use case: UC-03
- Stappen:
  - AND 1. Een script-tag opslaan in een notitie, of in de gebruikersnaam (die ziet alleen de gebruiker zelf, in de begroeting en op de profielpagina)
  - AND 2. Een slachtoffer laat die notitie renderen
- Mitigaties: MIT-01 (stap 2)
- Restrisico: geen tweede laag. Zonder Content-Security-Policy voert de browser een script uit zodra iemand `|safe` of een andere uitzondering toevoegt
- Status: gebouwd
- Sinds: baseline

### MC-08 Te veel rechten voor de applicatie in de database
- Aanvallersdoel: de hele database overnemen of vernietigen
- Aanvaller: iemand die de webapplicatie overneemt
- Assets / onderdelen: A-01, A-02, A-06, C-02, C-03, F-03, AU-03, AZ-05
- Gerelateerde use case: UC-01 tot UC-03
- Stappen:
  - AND 1. Een kwetsbaarheid in de app benutten (bijvoorbeeld MC-06 in een toekomstige route, of een afhankelijkheid uit MC-11)
  - AND 2. Via de verbinding van de app (eigenaarrol) tabellen weggooien of alle data lezen
- Mitigaties: geen (de app is eigenaar van de database)
- Restrisico: een app-compromittering is een databasecompromittering
- Status: open
- Sinds: baseline

### MC-09 Bestaande gebruikersnamen opsporen
- Aanvallersdoel: een lijst geldige gebruikersnamen voor gerichte aanvallen (MC-03)
- Aanvaller: iedere bezoeker
- Assets / onderdelen: A-04, C-02, F-01
- Gerelateerde use case: UC-01
- Stappen:
  - AND 1. Veel namen proberen te registreren
  - AND 2. Het antwoord "Die gebruikersnaam is al in gebruik" onderscheidt bestaande namen
- Mitigaties: geen (geen limiet op registreren)
- Restrisico: onbeperkt opsporen; de melding zelf is bij zelfgekozen namen niet te vermijden
- Status: open
- Sinds: baseline

### MC-10 De applicatie overbelasten met invoer
- Aanvallersdoel: de dienst onbruikbaar maken
- Aanvaller: iedere bezoeker, of een ingelogde gebruiker
- Assets / onderdelen: C-02, C-03
- Gerelateerde use case: UC-01, UC-03
- Stappen:
  - OR  1. Zeer grote formulieren sturen. Titel en notitie hebben een lengtegrens (MIT-04), maar het verzoek wordt eerst helemaal ingelezen: er is geen `MAX_CONTENT_LENGTH`, en de standaard `MAX_FORM_MEMORY_SIZE` van Flask (500 kB) hield een gewoon formulier van 5 MB niet tegen (T-21). Gebruikersnaam en wachtwoord hebben geen lengtegrens
  - OR  2. Onbeperkt veel accounts aanmaken
  - OR  3. Onbeperkt veel notities aanmaken en tonen
- Mitigaties: MIT-04 (stap 1, alleen voor titel en notitie), nog geen (stap 2 en 3, en de grootte van het verzoek zelf)
- Restrisico: elk verzoek wordt helemaal ingelezen, het aantal accounts en notities is onbeperkt, en een gebruikersnaam kan elke lengte hebben
- Status: open
- Sinds: baseline

### MC-11 Een kwetsbare of kwaadaardige afhankelijkheid
- Aanvallersdoel: code uitvoeren in de app of de database zonder zelf een fout in onze code te vinden
- Aanvaller: wie een bekende kwetsbaarheid in een pakket of image misbruikt, of wie een pakket of image zelf overneemt (supply chain)
- Assets / onderdelen: alle assets, C-02, C-03
- Gerelateerde use case: UC-01 tot UC-03
- Stappen:
  - OR  1. Een bekende kwetsbaarheid in een Python-pakket (Flask, Werkzeug, Jinja2 en de rest in `requirements.txt`) blijft staan omdat niemand bijwerkt
  - OR  2. Een kwaadaardige nieuwe versie van een pakket komt bij de volgende build vanzelf mee
  - OR  3. Een kwetsbaarheid in de base images (`python:3.15-slim`, `postgres:18`), bijvoorbeeld in de Debian-systeembibliotheken
  - OR  4. Een image-tag wijst bij een volgende build naar een andere image dan eerder (tags zijn niet vast)
- Mitigaties: MIT-03 (stap 2), nog geen (stappen 1, 3 en 4)
- Restrisico: vastzetten maakt stap 1 erger: zonder iets dat waarschuwt (zoals Dependabot) komen ook patches niet meer vanzelf binnen
- Status: open
- Sinds: baseline

### MC-12 Wachtwoord wijzigen met andermans sessie
- Aanvallersdoel: een account blijvend overnemen en de eigenaar buitensluiten
- Aanvaller: wie een sessie van het slachtoffer heeft (MC-04), of de browser van het slachtoffer het formulier laat versturen (MC-05)
- Assets / onderdelen: A-01, A-03, C-02, AU-04, AZ-06
- Gerelateerde use case: UC-04
- Stappen:
  - AND 1. Handelen als het slachtoffer
    - OR  1a. Met een gestolen of gekopieerde sessiecookie (MC-04)
    - OR  1b. Via een formulier op een andere site (MC-05)
  - AND 2. Een nieuw wachtwoord instellen op `/account/password`; het huidige wachtwoord wordt niet gevraagd (AU-04 ontbreekt)
- Mitigaties: geen
- Restrisico: een tijdelijke sessie wordt een blijvende overname. Wijzigt het slachtoffer zelf het wachtwoord of logt het uit, dan vervalt de sessie van de aanvaller wel (MIT-09). Andersom ook: wijzigt de aanvaller het wachtwoord, dan vervallen alle sessies van het slachtoffer. Omdat tweestapsverificatie verplicht is, blijft de overname beperkt tot deze sessie: de aanvaller kan de tweede factor niet vervangen zonder code (AU-06), dus later opnieuw inloggen vraagt nog steeds de app van het slachtoffer
- Status: open
- Sinds: 782f0e2

### MC-13 Account van een ander verwijderen
- Aanvallersdoel: het account en alle notities van het slachtoffer vernietigen
- Aanvaller: wie een sessie van het slachtoffer heeft (MC-04), of de browser van het slachtoffer het formulier laat versturen (MC-05)
- Assets / onderdelen: A-01, A-02, A-04, C-02, C-03, AU-04, AZ-07
- Gerelateerde use case: UC-05
- Stappen:
  - AND 1. Handelen als het slachtoffer
    - OR  1a. Met een gestolen of gekopieerde sessiecookie (MC-04)
    - OR  1b. Via een formulier op een andere site (MC-05); de bevestiging uit `forms.js` komt dan niet in beeld
  - AND 2. `POST /account/delete`; het wachtwoord wordt niet opnieuw gevraagd (AU-04 ontbreekt)
- Mitigaties: geen
- Restrisico: onomkeerbaar; er is geen backup en geen herstel
- Status: open
- Sinds: b03197a

### MC-14 Root en de ontwikkelserver in de container
- Aanvallersdoel: na een overname van de app zo veel mogelijk kunnen in de container, of de dienst onderuit halen
- Aanvaller: wie de app overneemt (bijvoorbeeld via MC-06 in een toekomstige route, of MC-11); voor stap 2 iedere bezoeker
- Assets / onderdelen: C-02, A-05, A-06
- Gerelateerde use case: UC-01 tot UC-05
- Stappen:
  - OR  1. Na een overname draait de aanvaller als root in de container: hij kan de code van de app aanpassen en gereedschap installeren, en een uitbraak uit de container begint met rootrechten
  - OR  2. De ontwikkelserver van Flask belasten; Flask waarschuwt bij het starten zelf dat die niet voor productie bedoeld is
- Mitigaties: geen
- Restrisico: een overname van de app is meteen een overname van de hele container
- Status: open
- Sinds: baseline

### MC-15 De code van de tweede stap raden
- Aanvallersdoel: inloggen als een gebruiker met tweestapsverificatie
- Aanvaller: wie het wachtwoord al heeft (MC-01, MC-03, of hergebruik van een elders gelekt wachtwoord)
- Assets / onderdelen: A-03, A-07, C-02, AU-05
- Gerelateerde use case: UC-02
- Stappen:
  - AND 1. Het wachtwoord kennen, zodat `/login/2fa` bereikbaar is
  - AND 2. Codes proberen. Per poging is de kans hoogstens 3 op 1.000.000: de code van nu en die van één stap ervoor en erna tellen
- Mitigaties: MIT-06 (stap 2)
- Restrisico: zonder blokkade zou het bij 100 pogingen per seconde gemiddeld ongeveer een uur duren. Met een vaste blokkade van 15 minuten was de kans ongeveer 41% als iemand een jaar volhoudt. Met de verdubbelende blokkade (15 minuten tot 24 uur) zijn dat ongeveer 1.855 pogingen per jaar: 0,56% (berekend als 1 - (1 - 3/10^6)^n). Wie het wachtwoord kent, kan met de blokkade ook de echte gebruiker buitensluiten (MC-18)
- Status: gebouwd
- Sinds: 96626e2

### MC-16 Een code onderscheppen en gebruiken
- Aanvallersdoel: inloggen als een gebruiker met tweestapsverificatie
- Aanvaller: een nepsite die wachtwoord en code meteen doorgeeft aan de echte app (phishing in real time), of iemand die meekijkt of het verkeer meeleest (geen TLS, MC-04)
- Assets / onderdelen: A-01, A-03, C-01, C-02, F-01, AU-05
- Gerelateerde use case: UC-02
- Stappen:
  - OR  1. De code meteen gebruiken, binnen de stap waarin hij geldt (30 seconden, plus één stap klokverschil)
  - OR  2. De code later nog eens gebruiken (replay)
- Mitigaties: MIT-07 (stap 2), nog geen (stap 1)
- Restrisico: TOTP is niet bestand tegen phishing: een nepsite die direct doorgeeft, komt binnen. Daartegen helpt alleen een factor die aan het domein gebonden is, zoals WebAuthn of passkeys
- Status: open
- Sinds: 96626e2

### MC-17 Het TOTP-geheim buitmaken
- Aanvallersdoel: zelf geldige codes maken, zodat de tweede factor wegvalt
- Aanvaller: iemand met leestoegang tot de database of een backup; iemand die meekijkt tijdens het instellen; of iemand met toegang tot een gedeelde browser- of proxycache
- Assets / onderdelen: A-07, C-01, C-03, C-04, F-02
- Gerelateerde use case: UC-07
- Stappen:
  - OR  1. `users.totp_secret` lezen uit de database of het volume; het geheim staat leesbaar, net als het wachtwoord (MC-01)
  - OR  2. Meekijken of een screenshot maken van de QR-code of de sleutel tijdens het instellen
  - OR  3. De instelpagina of de QR-code uit een cache halen
- Mitigaties: MIT-08 (stap 3, en stap 2 voor zover het om later terugkijken gaat), nog geen (stap 1)
- Restrisico: een databaselek levert wachtwoord en geheim samen, en dan helpt tweestapsverificatie niet meer
- Status: open
- Sinds: 18e1424

### MC-18 Iemand anders buitensluiten met de blokkade
- Aanvallersdoel: een gebruiker niet meer laten inloggen
- Aanvaller: wie een gebruikersnaam kent en hetzelfde IP-adres heeft als het slachtoffer (zelfde netwerk, NAT, of iedereen achter een proxy); voor de codestap: wie het wachtwoord kent
- Assets / onderdelen: C-02, AU-01, AU-05
- Gerelateerde use case: UC-02
- Stappen:
  - OR  1. Vanaf het adres van het slachtoffer 5 foute wachtwoorden voor zijn naam invullen, of 20 voor willekeurige namen
  - OR  2. Met het wachtwoord 5 foute codes invullen: de codestap van het account gaat op slot, oplopend tot 24 uur
- Mitigaties: in het ontwerp van MIT-10: de wachtwoordstap blokkeert nooit een account over alle adressen, alleen per adres. Wie een naam kent maar niet op het netwerk van het slachtoffer zit, kan hem niet buitensluiten
- Restrisico: op een gedeeld netwerk of achter een proxy delen gebruikers één adres. Achter een proxy moet de app het echte clientadres krijgen (bijvoorbeeld met `ProxyFix` en het juiste aantal proxies), anders telt iedereen als één adres. Stap 2 kan alleen wie het wachtwoord al heeft
- Status: open
- Sinds: 484eca3

### MC-19 De herstelcode raden of buitmaken
- Aanvallersdoel: inloggen als een gebruiker met tweestapsverificatie, zonder zijn telefoon
- Aanvaller: wie het wachtwoord al heeft (MC-01, MC-03)
- Assets / onderdelen: A-01, A-08, C-01, C-03, AU-07
- Gerelateerde use case: UC-08
- Stappen:
  - AND 1. Het wachtwoord kennen, zodat `/login/recover` bereikbaar is
  - AND 2. De herstelcode hebben
    - OR  2a. Raden: 128 willekeurige bits
    - OR  2b. De code vinden waar de gebruiker hem bewaart (papier, wachtwoordmanager, screenshot)
    - OR  2c. Uit de database of een backup halen
    - OR  2d. Uit een browser- of proxycache halen
- Mitigaties: MIT-11 (2a: 128 bits en een blokkade; 2c: alleen de SHA-256 staat in de database; 2d: `no-store`), nog geen (2b)
- Restrisico: wie wachtwoord en bewaarde herstelcode heeft, komt binnen en zet daarmee de tweede factor uit; zo is het bedoeld, en de code is zo veilig als de plek waar hij ligt. De gebruiker krijgt van het gebruik geen bericht buiten de app (er is geen e-mail)
- Status: open
- Sinds: dc7d258

### MC-20 De eerste instelling kapen
- Aanvallersdoel: zijn eigen authenticator aan een account koppelen, zodat de echte gebruiker er niet meer in komt
- Aanvaller: wie het wachtwoord heeft van een account dat tweestapsverificatie (nog) niet heeft ingesteld
- Assets / onderdelen: A-01, A-07, A-08, C-02, AU-01, AZ-09
- Gerelateerde use case: UC-07
- Stappen:
  - AND 1. Het wachtwoord kennen (MC-01, MC-03)
  - AND 2. Het account heeft op dat moment geen tweestapsverificatie: net geregistreerd en nog niet ingesteld, of net een herstelcode gebruikt en het opnieuw instellen niet afgemaakt
  - AND 3. Inloggen en het instellen afmaken met een eigen app; de aanvaller krijgt dan ook de herstelcode
- Mitigaties: MIT-12 beperkt het venster: zonder tweestapsverificatie opent alleen het instellen, en een nieuw account of een gebruikte herstelcode gaat er direct naartoe. Nog geen mitigatie voor het venster zelf
- Restrisico: dit is het bekende "trust on first use"-probleem: wie als eerste instelt, wordt vertrouwd. Daartegen helpt een tweede kanaal bij het aanmaken (zoals een bevestigde e-mail), en dat heeft deze app niet
- Status: open
- Sinds: 42ab429

## Mitigaties

### MIT-01 Automatisch escapen in Jinja
- Houdt tegen: MC-07 stap 2
- Wat: Flask escapet in `.html`-templates alle `{{ ... }}`-waarden standaard. Dit is een standaardinstelling van het framework en geen eigen werk; wij vermijden alleen `|safe` (opmerking in `notes.html`).
- Waar: `app/web/templates/*.html`
- Status: gebouwd
- Sinds: baseline

### MIT-02 Parameterized queries
- Houdt tegen: MC-06 stap 1 en 2
- Wat: alle SQL gaat via één helper, `query(sql, (waarden,))`; de waarden worden los van de SQL-tekst naar de database gestuurd en nooit als SQL gelezen.
- Waar: `query()` in `app/db.py`
- Status: gebouwd
- Sinds: baseline

### MIT-03 Vastgezette versies van de Python-pakketten
- Houdt tegen: MC-11 stap 2
- Wat: elk pakket staat op een exacte versie in `requirements.txt`, ook de pakketten die Flask en psycopg meetrekken. Een nieuwe versie komt dus alleen binnen als iemand hem bewust kiest. Er staan geen hashes bij, dus pip controleert niet of het bestand hetzelfde is als toen de versie werd gekozen. De images staan op een tag en niet op een digest, dus voor stap 4 doet dit niets.
- Waar: `app/requirements.txt`
- Status: gebouwd
- Sinds: db6698e

### MIT-04 Lengtegrens op titel en notitie
- Houdt tegen: MC-10 stap 1, voor zover het om het opslaan van te lange notities gaat
- Wat: de server weigert een titel van meer dan 15 en een notitie van meer dan 250 tekens met een 400, bij aanmaken en bij aanpassen. `maxlength` in de formulieren is alleen gemak in de browser. Het verzoek wordt wel eerst helemaal ingelezen; tegen een groot verzoek zelf helpt dit niet (daarvoor is `MAX_CONTENT_LENGTH` nodig).
- Waar: `read_note_form()` in `app/notes.py`, met `TITLE_MAX` en `BODY_MAX`
- Status: gebouwd
- Sinds: 32c2661

### MIT-05 Tweede factor bij inloggen (TOTP)
- Houdt tegen: MC-03 stap 1 en 2, en een gelekt wachtwoord uit MC-01; sinds MIT-12 voor elk account. Maakt MC-12 kleiner
- Wat: na het juiste wachtwoord krijgt de sessie alleen een `pending_user_id`. Daarmee opent geen enkele route, want `login_required` en `load_user` kijken naar `user_id`. Pas na een geldige code op `/login/2fa` wordt de sessie gewist en `user_id` gezet. De halve login vervalt na 5 minuten. TOTP volgens RFC 6238: een geheim van 160 bits (RFC 4226 R6), 6 cijfers, 30 seconden, één stap klokverschil (RFC 6238, 5.2), vergeleken in constante tijd. De berekening is zonder dependency geschreven en met de hand tegen alle testvectoren van RFC 6238 en RFC 4226 gecontroleerd (T-35). Aanzetten gebeurt pas na een eerste geldige code. Opnieuw instellen vraagt ook een code (AU-06), zodat wie alleen de sessie heeft de tweede factor niet kan vervangen
- Waar: `login()`, `login_code()` en `check_code()` in `app/auth.py`; `app/totp.py`
- Status: gebouwd
- Sinds: 96626e2

### MIT-06 Blokkade na 5 foute codes
- Houdt tegen: MC-15 stap 2
- Wat: foute codes worden per account in de database geteld (`auth_throttle`, via `throttle.py`), niet in de sessie, want een sessie kan de aanvaller gewoon opnieuw beginnen. Na 5 fouten in 15 minuten zit de codestap op slot, en dan wordt ook de juiste code geweigerd. De eerste blokkade duurt 15 minuten, elke volgende twee keer zo lang, tot 24 uur. Een geldige code wist de teller. De controle op de blokkade zit ook in de UPDATE die de code accepteert
- Waar: `check_code()` in `app/auth.py`, `app/throttle.py`
- Status: gebouwd
- Sinds: 18e1424; verdubbelend sinds 484eca3

### MIT-07 Elke code werkt één keer
- Houdt tegen: MC-16 stap 2
- Wat: de tijdstap van de laatst geaccepteerde code staat in `totp_last_step`. Een code van dezelfde of een eerdere stap wordt geweigerd, zoals RFC 6238 5.2 eist ("MUST NOT accept the second attempt"). De controle zit in de WHERE van dezelfde UPDATE die de stap opslaat, zodat van twee gelijktijdige verzoeken met dezelfde code er maar één wint (T-31)
- Waar: `check_code()` in `app/auth.py`
- Status: gebouwd
- Sinds: 18e1424

### MIT-08 Het geheim alleen tijdens het instellen, en niet in een cache
- Houdt tegen: MC-17 stap 3, en het later terugkijken uit stap 2
- Wat: de QR-code (`/account/2fa/qr.svg`) en de sleutel zijn alleen op te vragen zolang tweestapsverificatie nog niet aan staat; daarna geeft de QR-route een 404. Beide worden verstuurd met `Cache-Control: no-store`. De QR-code komt van een eigen route en staat niet inline in de pagina
- Waar: `setup_2fa()`, `qr_2fa()` en `no_store()` in `app/account.py`
- Status: gebouwd
- Sinds: 18e1424

### MIT-09 Sessieversie: oude sessies vervallen
- Houdt tegen: MC-04 stap 4; maakt MC-12 kleiner
- Wat: elke gebruiker heeft een `session_version` in de database, en de sessiecookie krijgt die mee. `load_user` accepteert de sessie alleen als beide gelijk zijn; anders wordt de sessie gewist met de melding "Je sessie is niet meer geldig". Uitloggen, een nieuw wachtwoord en tweestapsverificatie aanzetten of opnieuw instellen verhogen de versie. Na een nieuw wachtwoord of een 2FA-wijziging krijgt de huidige sessie de nieuwe versie en blijft ingelogd; alle andere vervallen. Ook een halve login vervalt als de versie verandert voordat de code is ingevuld. Uitloggen logt alle apparaten van het account uit: zonder sessies op de server bij te houden kan het niet preciezer
- Waar: `load_user()`, `start_session()`, `end_other_sessions()`, `login_code()` en `logout()` in `app/auth.py`; `change_password()`, `setup_2fa()` en `reset_2fa()` in `app/account.py`
- Status: gebouwd
- Sinds: 587955a

### MIT-10 Blokkade op de wachtwoordstap
- Houdt tegen: MC-03 stap 1 en 2
- Wat: foute wachtwoorden worden geteld per IP-adres (20 in 15 minuten) en per account vanaf één adres (5 in 15 minuten). Daarna volgt een blokkade van 15 minuten, die bij herhaling verdubbelt tot een uur; ook het juiste wachtwoord wordt dan geweigerd, met status 429. De tellers hangen aan wat er is ingevuld en niet aan of het account bestaat, dus een blokkade verraadt geen namen. Een geslaagde login wist alleen de teller van het account, nooit die van het adres: anders zet een aanvaller met een eigen account zijn adresteller steeds terug. Bewust geen blokkade per account over alle adressen (MC-18). IPv6-adressen tellen per /64. De sleutels in `auth_throttle` zijn HMAC's, dus de tabel bevat geen leesbare IP-adressen of gebruikersnamen
- Waar: `login()` in `app/auth.py`, `app/throttle.py`
- Status: gebouwd
- Sinds: 484eca3

### MIT-11 Herstelcode
- Houdt tegen: MC-19 stap 2a, 2c en 2d; maakt tweestapsverificatie mogelijk zonder dat een kwijtgeraakte telefoon het account onbereikbaar maakt
- Wat: bij het aanzetten van tweestapsverificatie krijgt de gebruiker één keer een herstelcode van 128 willekeurige bits te zien. Alleen de SHA-256 wordt bewaard; een snelle hash is genoeg bij 128 willekeurige bits, anders dan bij een zelfverzonnen wachtwoord. Inloggen met de code kan alleen na het juiste wachtwoord. De code werkt één keer: hij zet tweestapsverificatie uit en verhoogt de sessieversie, en de app stuurt meteen naar het opnieuw instellen met een nieuwe telefoon (MIT-12). Het verbruik zit in een UPDATE met de hash in de WHERE, dus twee gelijktijdige verzoeken kunnen hem niet allebei gebruiken. 5 fouten in 15 minuten geven een blokkade (via `throttle.py`). Een nieuwe code maken vraagt een code uit de app (AU-06) en maakt de vorige ongeldig. De pagina's met de code worden met `Cache-Control: no-store` verstuurd
- Waar: `new_recovery_code()` en `login_recover()` in `app/auth.py`; `setup_2fa()` en `new_recovery()` in `app/account.py`
- Status: gebouwd
- Sinds: dc7d258

### MIT-12 Tweestapsverificatie verplicht
- Houdt tegen: MC-03 stap 1 en 2 voor alle accounts, niet alleen voor wie het zelf aanzet; beperkt het venster van MC-20
- Wat: `login_required` laat een ingelogde gebruiker zonder tweestapsverificatie alleen het instellen afmaken (`/account/2fa` en de QR-code); elke andere pagina stuurt daarheen. Dat geldt voor een nieuw account na het eerste wachtwoord, en na het gebruik van een herstelcode. De instelpagina maakt zelf een geheim aan en biedt uitloggen in plaats van annuleren. Uitzetten bestaat niet meer: alleen opnieuw instellen voor een nieuwe telefoon, met een code (AU-06), waarna de app meteen naar het instellen stuurt
- Waar: `login_required()` en `login()` in `app/auth.py`; `setup_2fa()` en `reset_2fa()` in `app/account.py`
- Status: gebouwd
- Sinds: 42ab429
