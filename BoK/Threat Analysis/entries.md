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
- Doel: bewijzen wie je bent, een sessie krijgen, en die weer beeindigen
- Onderdelen: C-01, C-02, C-03 (routes `/login`, `/logout`, AU-01, AU-02)
- Assets: A-01, A-03
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
- Onderdelen: C-01, C-02, C-03 (route `/account/password`, AU-04, AZ-06)
- Assets: A-01
- Sinds: 782f0e2

### UC-05 Account verwijderen
- Actor: ingelogde gebruiker
- Doel: het eigen account en alle eigen notities definitief laten verwijderen
- Onderdelen: C-01, C-02, C-03 (route `/account/delete`, AU-04, AZ-07)
- Assets: A-01, A-02, A-04
- Sinds: b03197a

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
- Restrisico: elk gelezen wachtwoord is direct bruikbaar
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
- Mitigaties: geen (geen limiet op pogingen, geen sterkte-eis, een factor)
- Restrisico: onbeperkt aantal pogingen
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
  - AND 4. De cookie blijft geldig na uitloggen en na een wachtwoordwijziging, tot hij verloopt (standaard 31 dagen)
- Mitigaties: geen (de `HttpOnly`-vlag staat standaard aan in Flask; dat houdt JavaScript buiten beeld maar stopt de stappen hierboven niet)
- Restrisico: een gekopieerde cookie werkt weken
- Status: open
- Sinds: baseline

### MC-05 Handelingen laten uitvoeren via een andere site (CSRF)
- Aanvallersdoel: namens een ingelogde gebruiker notities aanmaken, aanpassen of verwijderen
- Aanvaller: de eigenaar van een andere website die de gebruiker bezoekt
- Assets / onderdelen: A-01, A-02, A-03, C-01, C-02, AZ-02, AZ-04, AZ-06, AZ-07
- Gerelateerde use case: UC-03, UC-04, UC-05
- Stappen:
  - AND 1. De gebruiker is ingelogd en bezoekt de site van de aanvaller
  - AND 2. Die site stuurt een formulier naar `/`, `/notes/<id>/delete`, `/account/password`, `/account/delete` of `/logout`
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
  - AND 1. Een script-tag opslaan in een notitie, of in de gebruikersnaam (die ziet alleen de gebruiker zelf, in de begroeting)
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
  - OR  1. Zeer grote formulieren sturen (geen `MAX_CONTENT_LENGTH`, geen lengtegrens op velden; de standaard `MAX_FORM_MEMORY_SIZE` van Flask, 500 kB, hield een gewoon formulier van 5 MB niet tegen, zie T-21)
  - OR  2. Onbeperkt veel accounts aanmaken
  - OR  3. Onbeperkt veel notities aanmaken en tonen
- Mitigaties: geen
- Restrisico: een enkel account kan opslag en geheugen vullen
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
- Restrisico: een tijdelijke sessie wordt een blijvende overname. Wijzigt het slachtoffer zelf het wachtwoord, dan werkt de sessie van de aanvaller gewoon door (MC-04 stap 4)
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
    - OR  1b. Via een formulier op een andere site (MC-05); de bevestiging uit `confirm.js` komt dan niet in beeld
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

## Mitigaties

### MIT-01 Automatisch escapen in Jinja
- Houdt tegen: MC-07 stap 2
- Wat: Flask escapet in `.html`-templates alle `{{ ... }}`-waarden standaard. Dit is een standaardinstelling van het framework en geen eigen werk; wij vermijden alleen `|safe` (opmerking in `notes.html`).
- Waar: `app/web/templates/*.html`
- Status: gebouwd
- Sinds: baseline

### MIT-02 Parameterized queries
- Houdt tegen: MC-06 stap 1 en 2
- Wat: alle SQL gaat via `cur.execute(sql, (waarden,))`; de waarden worden los van de SQL-tekst naar de database gestuurd en nooit als SQL gelezen.
- Waar: `app/app.py`
- Status: gebouwd
- Sinds: baseline

### MIT-03 Vastgezette versies van de Python-pakketten
- Houdt tegen: MC-11 stap 2
- Wat: elk pakket staat op een exacte versie in `requirements.txt`, ook de pakketten die Flask en psycopg meetrekken. Een nieuwe versie komt dus alleen binnen als iemand hem bewust kiest. Er staan geen hashes bij, dus pip controleert niet of het bestand hetzelfde is als toen de versie werd gekozen. De images staan op een tag en niet op een digest, dus voor stap 4 doet dit niets.
- Waar: `app/requirements.txt`
- Status: gebouwd
- Sinds: db6698e
