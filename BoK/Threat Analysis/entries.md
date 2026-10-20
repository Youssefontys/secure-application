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
- Doel: een nieuw wachtwoord instellen voor het eigen account, met het huidige wachtwoord ter bevestiging
- Onderdelen: C-01, C-02, C-03 (formulier op `/account`, verstuurd naar `/account/password`; AU-04, AZ-06)
- Assets: A-01
- Sinds: 782f0e2

### UC-05 Account verwijderen
- Actor: ingelogde gebruiker
- Doel: het eigen account en alle eigen notities definitief laten verwijderen, na het huidige wachtwoord
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

### UC-09 Wachtwoord vergeten
- Actor: gebruiker die het wachtwoord niet meer weet
- Doel: met de herstelcode en een code uit de authenticator-app een nieuw wachtwoord instellen, en meteen een nieuwe herstelcode krijgen
- Onderdelen: C-01, C-02, C-03 (route `/login/forgot`, AU-08)
- Assets: A-01, A-07, A-08
- Sinds: 428858e

### UC-10 De app uitrollen, bijwerken en weer weghalen
- Actor: beheerder
- Doel: de app op Azure zetten of bijwerken met `python scripts/deployment.py azure`, en alles weer weghalen met `undo`, zonder dat een geheim in de repo, het plan of de state komt
- Onderdelen: C-10, C-09, C-06, C-02, C-03, C-07 (AU-09, AU-13)
- Assets: A-12, A-15, A-16
- Sinds: 75c9967

### UC-11 Een melding krijgen bij een blokkade
- Actor: beheerder
- Doel: binnen ongeveer 10 minuten een mail krijgen als er een blokkade begint, zodat een aanval niet onopgemerkt blijft
- Onderdelen: C-05, C-08 (AZ-13)
- Assets: A-11, A-13
- Sinds: c4ce459

## Misuse cases

### MC-01 Wachtwoorden uit de database lezen
- Aanvallersdoel: toegang tot accounts van anderen, ook op andere sites
- Aanvaller: iemand met leestoegang tot de database of een backup (beheerder, gelekt volume, gecompromitteerde app)
- Assets / onderdelen: A-01, C-03, C-04, F-03
- Gerelateerde use case: UC-01, UC-02
- Stappen:
  - AND 1. De opgeslagen wachtwoorden buitmaken
    - OR  1a. De database rechtstreeks bevragen (`SELECT username, password_hash FROM users`)
    - OR  1b. Het databasevolume of een backup lezen (C-04)
    - OR  1c. De webapplicatie overnemen en ze via F-03 opvragen
  - AND 2. Er het wachtwoord uit halen: sinds MIT-19 staat er alleen een Argon2id-hash, dus offline raden, per account opnieuw door de eigen salt
- Mitigaties: MIT-19 (stap 2: elke gok kost 19 MiB en een Argon2id-berekening, en een hash geldt maar voor één account). MIT-13 (stap 2: minstens 12 tekens maakt raden duurder)
- Restrisico: een zwak of veelgebruikt wachtwoord blijft te raden; er is geen blocklist (geparkeerd). Wie de app overneemt (MC-08, MC-11), ziet het wachtwoord bij het inloggen voorbijkomen. Wie de database kan wijzigen (MC-08), zet er een eigen hash in. Bij een account met tweestapsverificatie is het wachtwoord alleen niet genoeg (MIT-05), en het TOTP-geheim staat versleuteld (MIT-17); wie ook de sleutel heeft (MC-22), kan beide
- Status: gebouwd
- Sinds: baseline; gehasht sinds 9e6e365

### MC-02 Notities van een ander lezen, aanpassen of verwijderen
- Aanvallersdoel: notities van een andere gebruiker lezen of vernietigen
- Aanvaller: elke ingelogde gebruiker met een eigen account
- Assets / onderdelen: A-02, C-02, AZ-03, AZ-04
- Gerelateerde use case: UC-03
- Stappen:
  - AND 1. Een eigen account aanmaken en inloggen (UC-01, UC-02)
  - AND 2. De id van een notitie van een ander invullen in `/notes/<id>/edit` of `/notes/<id>/delete` (de ids zijn opeenvolgende getallen)
- Mitigaties: MIT-15 (stap 2: andermans notitie geeft 404)
- Restrisico: zolang elke nieuwe route op een notitie de eigenaar in de WHERE zet. De ids blijven opeenvolgend, maar raden levert alleen 404 op, net als een id dat niet bestaat
- Status: gebouwd
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
- Mitigaties: MIT-10 (stap 1 en 2: 20 fouten per IP-adres en 5 per account vanaf één adres, daarna een oplopende blokkade). MIT-05 en MIT-12 (stap 1 en 2: tweestapsverificatie is verplicht, dus een geraden wachtwoord geeft alleen een halve login). MIT-13 (stap 3: 12 tot 64 tekens, nog zonder blocklist)
- Restrisico: wie vanaf veel IP-adressen tegelijk raadt (een botnet), wordt per account niet begrensd; dat is bewust, zie MC-18. Een account dat het instellen nog niet heeft afgemaakt, zit nog op één factor (MC-20). En wie raadt, ziet aan de doorverwijzing naar `/login/2fa` dat het wachtwoord klopt. Een veelgebruikt wachtwoord van 12 tekens of meer wordt nog geaccepteerd, want er is geen blocklist
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
  - AND 4. De cookie blijft geldig tot hij verloopt (tot 2f1236e 31 dagen, nu 8 uur). Uitloggen, een nieuw wachtwoord en tweestapsverificatie aanzetten of opnieuw instellen maken hem eerder ongeldig (MIT-09)
- Mitigaties: MIT-09 (stap 4, zodra de gebruiker uitlogt of een van zijn inloggegevens wijzigt). MIT-29 (stap 4: hooguit 8 uur, T-90). Op Azure ook stap 1: MIT-40 (TLS, getoetst aan de richtlijnen van het NCSC; T-113), met de `Secure`-vlag (MIT-23) en HSTS (MIT-21), zodat de browser de cookie alleen over HTTPS stuurt. Lokaal draait de app zonder TLS. De `HttpOnly`-vlag staat standaard aan in Flask; dat houdt JavaScript buiten beeld maar stopt stap 1 tot 3 niet
- Restrisico: een gekopieerde cookie werkt tot de gebruiker uitlogt of zijn wachtwoord of tweestapsverificatie wijzigt, en anders tot 8 uur. Tweestapsverificatie helpt hier niet: de cookie is van na de code
- Status: open
- Sinds: baseline

### MC-05 Handelingen laten uitvoeren via een andere site (CSRF)
- Aanvallersdoel: namens een ingelogde gebruiker notities aanmaken, aanpassen of verwijderen
- Aanvaller: de eigenaar van een andere website die de gebruiker bezoekt
- Assets / onderdelen: A-01, A-02, A-03, C-01, C-02, AZ-02, AZ-04, AZ-06, AZ-07
- Gerelateerde use case: UC-03, UC-04, UC-05
- Stappen:
  - AND 1. De gebruiker is ingelogd en bezoekt de site van de aanvaller
  - AND 2. Die site stuurt een formulier naar `/`, `/notes/<id>/delete`, `/account/password`, `/account/delete` of `/logout`. Tweestapsverificatie opnieuw instellen (`/account/2fa/reset`) of een nieuwe herstelcode maken (`/account/2fa/recovery`) lukt zo niet, want daarvoor is een code nodig die de andere site niet heeft. Sinds MIT-16 geldt hetzelfde voor `/account/password` en `/account/delete`: die vragen het huidige wachtwoord
  - AND 3. De browser stuurt de cookie mee
- Mitigaties: MIT-20 (stap 2: elke POST vraagt het CSRF-token van de sessie, en dat kent de andere site niet). MIT-23 (stap 3: de cookie heeft `SameSite=Lax`, dus de browser stuurt hem niet mee met een formulier van een andere site). MIT-16 voor wachtwoord wijzigen en account verwijderen
- Restrisico: een script dat toch op de eigen pagina draait (MC-07) kan het token lezen; daarom de tweede laag van MIT-21. Een andere poort op hetzelfde adres telt voor de browser als dezelfde site, dus daar helpt `SameSite` niet, het token wel (T-73)
- Status: gebouwd
- Sinds: baseline; dicht sinds 5bd55c5

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
- Mitigaties: MIT-01 (stap 2). MIT-21 (stap 2: de CSP staat geen inline script toe, dus ook een script dat erdoor glipt, voert de browser niet uit). MIT-22 (stap 1: een gebruikersnaam kan geen HTML meer bevatten)
- Restrisico: een script uit een eigen bestand mag wel; wie daar iets in krijgt, heeft de server al. De CSP is een tweede laag, geen vervanging van het escapen
- Status: gebouwd
- Sinds: baseline

### MC-08 Te veel rechten voor de applicatie in de database
- Aanvallersdoel: de hele database overnemen of vernietigen
- Aanvaller: iemand die de webapplicatie overneemt
- Assets / onderdelen: A-01, A-02, A-06, A-10, C-02, C-03, F-03, AU-03, AZ-05
- Gerelateerde use case: UC-01 tot UC-03
- Stappen:
  - AND 1. Een kwetsbaarheid in de app benutten (bijvoorbeeld MC-06 in een toekomstige route, of een afhankelijkheid uit MC-11)
  - AND 2. Met de rechten van de app meer doen dan de app zelf doet:
    - OR  2a. Via de verbinding van de app tabellen weggooien, rollen aanmaken, of als superuser via `COPY` bestanden lezen en commando's uitvoeren op de databaseserver
    - OR  2b. Het wachtwoord van de eigenaar uit de omgeving van de app halen en daarmee inloggen
- Mitigaties: MIT-27 (stap 2a: de app logt in als `notities_app`, die alleen mag lezen en schrijven in de eigen tabellen; stap 2b: het wachtwoord van de eigenaar staat niet meer in de app, en op Azure kan de identiteit van de app de vault met dat wachtwoord niet lezen)
- Restrisico: wat de app mag, mag de aanvaller ook: alle rijen lezen, wijzigen en wissen. Notities en TOTP-geheimen staan versleuteld en wachtwoorden als hash (MIT-17 tot MIT-19), maar hij kan bijvoorbeeld tweestapsverificatie uitzetten of alle notities wissen. Er zijn geen rechten per rij (row-level security); de app filtert zelf op `user_id` (MIT-15). Lokaal staan beide wachtwoorden in `.env` op dezelfde machine. Op Azure is de scheiding gemeten aan de rollen (T-86, 2026-10-18); een leespoging vanuit de container zelf is niet gedaan
- Status: gebouwd
- Sinds: baseline; dicht sinds 1d1b4eb

### MC-09 Bestaande gebruikersnamen opsporen
- Aanvallersdoel: een lijst geldige gebruikersnamen voor gerichte aanvallen (MC-03)
- Aanvaller: iedere bezoeker
- Assets / onderdelen: A-04, C-02, F-01
- Gerelateerde use case: UC-01
- Stappen:
  - AND 1. Veel namen proberen te registreren
  - AND 2. Het antwoord "That username is already taken" onderscheidt bestaande namen
- Mitigaties: MIT-30, deels: sinds 5d0f1d0 telt ook een registratie met een bezette naam mee voor de limiet van 10 per uur per adres, want de teller loopt vóór het opslaan (volgens de code van `register()` in `app/auth.py`; gevonden bij de risicomatrix van 19-10-2026). Bij inloggen rekent de app ook voor een onbekende naam een Argon2id-hash (MIT-19), zodat de responstijd geen tweede manier wordt (T-70)
- Restrisico: vanaf veel adressen blijft opsporen via registreren makkelijk, en in de hackstand mag een adres 60 namen per uur proberen; de melding zelf is bij zelfgekozen namen niet te vermijden
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
- Mitigaties: MIT-22 (stap 1: een verzoek boven 16 KiB krijgt 413 voordat het is ingelezen, en een gebruikersnaam is hoogstens 20 tekens). MIT-04 (titel en notitie). MIT-30 (stap 2: 10 nieuwe accounts per uur per adres; stap 3: 25 notities per account)
- Restrisico: wie veel adressen heeft, maakt per adres 10 accounts per uur, elk met 25 notities. Sinds MIT-19 kost elke registratie, login en wachtwoordwijziging 19 MiB en een Argon2id-berekening. Voor 5d0f1d0 gingen 15 registraties vanaf één adres en 30 notities voor één account allemaal door, en werd `/login` voor anderen trager (15 naar 66 ms met vier scripts tegelijk)
- Status: gebouwd
- Sinds: baseline; begrensd sinds 5d0f1d0

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
  - OR  5. Een kwetsbaarheid in code die buiten dpkg en pip om in de image zit, en die de scan dus niet ziet: de 15 bibliotheken die psycopg-binary zelf meeneemt (uit CentOS 7, met onder andere PCRE 8.32 en een eigen OpenSSL), de OpenSSL die statisch in `cryptography` zit, en Python zelf (T-118 tot T-120)
- Mitigaties: MIT-03 (stap 2, en stap 4 sinds 7bfd435). MIT-33 (stap 1 en 3: Dependabot stelt elke week nieuwe versies voor). MIT-35 (stap 1 en 3: de pipeline publiceert geen image met een bekend lek van HIGH of CRITICAL waarvoor een oplossing is; T-105). MIT-36 (de SBoM: welke pakketten en versies in elke image zitten; T-106). MIT-39 (stap 1 en 3: sinds bc6c669 draait dezelfde scan bij elke pull request, en een ruleset op `main` houdt de merge tegen als hij faalt; T-110, T-111). MIT-41 (stap 1 en 3, ook zonder oplossing: sinds e6a3888 houdt elk lek van HIGH of CRITICAL tegen tot er een beslissing in `vex/openvex.json` staat; T-114 tot T-117). MIT-43 (stap 5, deels: sinds 7790a40 komen libpq en wat hij meetrekt uit Debian, en zijn de 15 bibliotheken van psycopg-binary weg; T-121)
- Restrisico: sinds e6a3888 houdt ook een lek zonder oplossing tegen, tenzij de VEX het voor die versie uitsluit; maar een verklaring kan fout zijn, want de check ziet alleen of er een reden staat (MIT-41). Een lek van MEDIUM of LOW houdt niet tegen. Een lek dat pas na de build bekend wordt, ziet de scan pas bij de volgende pull request of push; een draaiende image wordt niet opnieuw gescand. Dependabot stelt alleen voor; iemand moet de pull request bekijken en samenvoegen. Dat hij pull requests opent, liet T-97 zien; of hij ook de digests van de images bijwerkt, bleek daar nog niet, want die waren al de nieuwste. Minder pakketten helpt wel: sinds 29d201d doet `cryptography` ook Argon2id, en zijn `argon2-cffi` en `argon2-cffi-bindings` weg. Stap 5 is deels dicht. Op c0a21ba laadde de app 70 bestanden, waarvan 52 niet uit een Debian-pakket; Trivy zag geen van de meegeleverde bibliotheken en ook Python zelf niet, en Syft zag ze deels, maar daarop vond Grype niets, omdat hij in de gegevens van Debian zoekt, en Trivy weigerde zo'n SBoM (T-118, T-119). Sinds 7790a40 komen libpq en wat hij meetrekt uit Debian (MIT-43, T-121). Open blijven Python zelf en de OpenSSL die statisch in `cryptography` zit; die werkt alleen een nieuwe base-image of een nieuwe versie van `cryptography` bij. De versie van `libpq5` werkt Dependabot niet bij: een nieuwe versie in Debian laat de build falen tot hij is bijgezet
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
  - AND 2. Een nieuw wachtwoord instellen op `/account/password`; sinds MIT-16 alleen met het huidige wachtwoord, en sinds 72ddaed ook met een code uit de app (AU-04)
- Mitigaties: MIT-16 (stap 2: het huidige wachtwoord en een code uit de app, elk met een limiet per account)
- Restrisico: met alleen de sessie, of de sessie en het wachtwoord, lukt het niet meer (T-98). Wie ook de telefoon of het TOTP-geheim heeft (MC-17), komt er wel door, en dan wordt een tijdelijke sessie een blijvende overname. Wijzigt het slachtoffer zelf het wachtwoord of logt het uit, dan vervalt de sessie van de aanvaller wel (MIT-09). Andersom ook: wijzigt de aanvaller het wachtwoord, dan vervallen alle sessies van het slachtoffer. Omdat tweestapsverificatie verplicht is, blijft de overname beperkt tot deze sessie: de aanvaller kan de tweede factor niet vervangen zonder code (AU-06), dus later opnieuw inloggen vraagt nog steeds de app van het slachtoffer
- Status: gebouwd
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
  - AND 2. `POST /account/delete`; sinds MIT-16 alleen met het huidige wachtwoord, en sinds 72ddaed ook met een code uit de app (AU-04)
- Mitigaties: MIT-16 (stap 2: wachtwoord en code)
- Restrisico: wie het wachtwoord én de telefoon heeft, verwijdert het account wel; dat is onomkeerbaar, er is geen backup en geen herstel
- Status: gebouwd
- Sinds: b03197a

### MC-14 Root en de ontwikkelserver in de container
- Aanvallersdoel: na een overname van de app zo veel mogelijk kunnen in de container, of de dienst onderuit halen
- Aanvaller: wie de app overneemt (bijvoorbeeld via MC-06 in een toekomstige route, of MC-11); voor stap 2 iedere bezoeker
- Assets / onderdelen: C-02, A-05, A-10 (tot 1d1b4eb A-06, zie MC-08)
- Gerelateerde use case: UC-01 tot UC-05
- Stappen:
  - OR  1. Na een overname draait de aanvaller als root in de container: hij kan de code van de app aanpassen en gereedschap installeren, en een uitbraak uit de container begint met rootrechten
  - OR  2. De ontwikkelserver van Flask belasten; Flask waarschuwt bij het starten zelf dat die niet voor productie bedoeld is
  - OR  3. Na een overname alsnog root worden via een programma met een setuid-bit, zoals mount, su of passwd, bijvoorbeeld met een lek in mount (CVE-2026-76642, T-114)
- Mitigaties: MIT-26 (stap 1: de app draait als de gewone gebruiker `app` en mag de code niet aanpassen; stap 2: Gunicorn met twee workers in plaats van de ontwikkelserver). MIT-42 (stap 3: sinds e6a3888 heeft geen programma in de image een setuid- of setgid-bit; T-116)
- Restrisico: wie de app overneemt, kan nog alles wat de app mag, zoals de geheimen in de omgeving lezen (MC-22) en de database gebruiken (MC-08). Het bestandssysteem van de container is niet alleen-lezen
- Status: gebouwd
- Sinds: baseline; dicht sinds 13a2eb4; stap 3 sinds e6a3888

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
  - OR  1. `users.totp_secret` lezen uit de database of het volume
    - AND 1a. De database, het volume of een backup lezen
    - AND 1b. De gegevenssleutel hebben, want sinds MIT-17 staat het geheim versleuteld (MC-22)
  - OR  2. Meekijken of een screenshot maken van de QR-code of de sleutel tijdens het instellen
  - OR  3. De instelpagina of de QR-code uit een cache halen
- Mitigaties: MIT-17 (stap 1: zonder de sleutel is het geheim niet te lezen). MIT-08 (stap 3, en stap 2 voor zover het om later terugkijken gaat)
- Restrisico: wie naast de database ook de sleutel heeft (MC-22), leest het geheim wel. Meekijken tijdens het instellen (stap 2) blijft mogelijk. Het wachtwoord staat nog leesbaar (MC-01), maar zonder het geheim levert een databaselek geen volledige overname meer op. Versleuteling beschermt tegen lezen, niet tegen schrijven: wie de database kan wijzigen (MC-08), zet `totp_enabled` op false, logt in met het leesbare wachtwoord en stelt tweestapsverificatie in met een eigen telefoon
- Status: gebouwd
- Sinds: 18e1424; versleuteld sinds 776931a

### MC-18 Iemand anders buitensluiten met de blokkade
- Aanvallersdoel: een gebruiker niet meer laten inloggen
- Aanvaller: wie een gebruikersnaam kent en hetzelfde IP-adres heeft als het slachtoffer (zelfde netwerk, NAT, of iedereen achter een proxy); voor de codestap: wie het wachtwoord kent
- Assets / onderdelen: C-02, AU-01, AU-05
- Gerelateerde use case: UC-02
- Stappen:
  - OR  1. Vanaf het adres van het slachtoffer 5 foute wachtwoorden voor zijn naam invullen, of 20 voor willekeurige namen
  - OR  2. Met het wachtwoord 5 foute codes invullen: de codestap van het account gaat op slot, oplopend tot 24 uur
  - OR  3. HEAD-verzoeken sturen: tot 7fbc42e telde elke HEAD op een formulierroute als foute poging, zonder formulier in te vullen (T-78)
  - OR  4. Een verkeerde `TRUSTED_PROXIES` (zoals -1 of 2) uitbuiten: dan kiest de aanvaller zelf het adres waarop geteld wordt (T-79)
- Mitigaties: MIT-22 (stap 3: alleen een POST telt). MIT-23 (stap 4: alleen 0 of 1, anders start de app niet). In het ontwerp van MIT-10: de wachtwoordstap blokkeert nooit een account over alle adressen, alleen per adres. Wie een naam kent maar niet op het netwerk van het slachtoffer zit, kan hem niet buitensluiten. Voor de hacking week, met een klas achter één adres van school, de hackstand: `THROTTLE_IP_MODE=hackweek` (100 per adres en een vaste blokkade van 5 minuten) en `THROTTLE_PAIR_EXEMPT_USERS` voor het demoaccount (T-71). Achter een proxy het echte clientadres via `ProxyFix` met `TRUSTED_PROXIES` (3a7c5ae), zonder de poort die Azure kan meesturen (T-72)
- Restrisico: op een gedeeld netwerk delen gebruikers één adres; de hackstand verkleint dat, maar lost het niet op. `TRUSTED_PROXIES` is op Azure gemeten: met 1 staat het adres van de bezoeker in de log, niet dat van de proxy (T-104). Te laag en iedereen deelt het adres van de proxy, te hoog en een aanvaller kiest zelf zijn adres. In de hackstand mag vanaf één adres meer geraden worden en heeft het demoaccount geen teller per naam, dus de stand hoort alleen aan tijdens de hacking week. Stap 2 kan alleen wie het wachtwoord al heeft
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
- Restrisico: wie wachtwoord en bewaarde herstelcode heeft, komt binnen en zet daarmee de tweede factor uit; zo is het bedoeld, en de code is zo veilig als de plek waar hij ligt. De gebruiker krijgt van het gebruik geen bericht buiten de app (er is geen e-mail). Met herstelcode en telefoon kan ook zonder wachtwoord een nieuw wachtwoord worden ingesteld (MC-21)
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

### MC-21 Een nieuw wachtwoord instellen via wachtwoord vergeten
- Aanvallersdoel: het wachtwoord van een ander account vervangen en daarmee binnenkomen
- Aanvaller: iedere bezoeker; de route is bereikbaar zonder wachtwoord
- Assets / onderdelen: A-01, A-04, A-07, A-08, C-02, AU-08
- Gerelateerde use case: UC-09
- Stappen:
  - AND 1. Een bestaande gebruikersnaam kennen
    - OR  1a. Raden of opsporen bij het registreren (MC-09)
    - OR  1b. Uit het antwoord van `/login/forgot` afleiden welke namen bestaan
  - AND 2. De herstelcode hebben
    - OR  2a. Raden: 128 willekeurige bits
    - OR  2b. De code vinden waar de gebruiker hem bewaart (zoals MC-19 stap 2b)
    - OR  2c. Uit de database, een backup of een cache halen (zoals MC-19 stap 2c en 2d)
  - AND 3. Een geldige code uit de app hebben
    - OR  3a. Raden, met de herstelcode al in handen
    - OR  3b. Een onderschepte code gebruiken, meteen of later (zoals MC-16)
    - OR  3c. Het TOTP-geheim buitmaken (MC-17)
- Mitigaties: MIT-14 (1b: één melding en dezelfde tellers voor bestaande en onbekende namen; 2a: 128 bits en een limiet per adres en per naam per adres; 3a: pas na een juiste herstelcode de blokkade van de codestap, MIT-06; 3b: elke code één keer, MIT-07). MIT-11 (2c: alleen de SHA-256, `no-store`). Nog geen (1a, 2b, 3c)
- Restrisico: wie herstelcode en telefoon (of het TOTP-geheim, MC-17) heeft, zet een nieuw wachtwoord; zo is het bedoeld, twee van de drie factoren. De gebruiker merkt het pas bij het volgende inloggen, want er is geen e-mail. Wie met een gestolen herstelcode de code raadt, zet de codestap van het account op slot, ook voor het gewone inloggen (zoals bij MC-15). Vanaf veel adressen tegelijk is het proberen van herstelcodes per account niet begrensd (bewust, zie MC-18), maar 128 bits zijn niet te raden
- Status: open
- Sinds: 428858e

### MC-22 De gegevenssleutel buitmaken
- Aanvallersdoel: met de sleutel (A-09) elk versleuteld TOTP-geheim en elke notitie ontsleutelen, en daarmee samen met de database de tweede factor van elk account
- Aanvaller: iemand met toegang tot de app-container, de ontwikkelmachine of een backup van `.env`
- Assets / onderdelen: A-02, A-07, A-09, C-02
- Gerelateerde use case: UC-07
- Stappen:
  - OR  1. De omgeving van de app-container lezen (`docker compose exec app printenv`); tot 13a2eb4 draaide de app als root (MC-14)
  - OR  2. `.env` op de ontwikkelmachine of in een backup daarvan lezen
  - OR  3. De app overnemen (MC-11), die de sleutel in het geheugen heeft
- Mitigaties: MIT-32 (stap 2, deels: andere gebruikers van de machine lezen `.env` niet meer). Op Azure staat de sleutel sinds 75c9967 in Key Vault (C-07), en alleen de identiteit van de app mag hem lezen (AZ-10, T-86); in Container Apps staat hij alleen als verwijzing. Een tweede sleutel (KEK) die deze sleutel versleutelt, is er niet
- Restrisico: de sleutel staat lokaal leesbaar in `.env` en in de omgeving van de container. Ook met Key Vault heeft de draaiende app hem, dus wie de app overneemt, heeft hem ook
- Status: open
- Sinds: 776931a

### MC-23 Notities uit de database lezen
- Aanvallersdoel: de privénotities van alle gebruikers lezen
- Aanvaller: iemand met leestoegang tot de database of een backup (beheerder, gelekt volume)
- Assets / onderdelen: A-02, C-03, C-04, F-03
- Gerelateerde use case: UC-03
- Stappen:
  - AND 1. De database, het volume of een backup lezen
  - AND 2. De gegevenssleutel hebben, want sinds MIT-18 staan titel en inhoud versleuteld (MC-22)
- Mitigaties: MIT-18 (stap 2)
- Restrisico: wie ook de sleutel heeft (MC-22) of de app overneemt, leest alles. Een waarde is gebonden aan de eigenaar, niet aan de notitie: wie de database kan wijzigen, kan titels en inhoud tussen notities van dezelfde gebruiker verwisselen; tussen gebruikers of tussen titel en inhoud lukt dat niet (T-67). Hoeveel notities iemand heeft en wanneer ze zijn gemaakt, blijft leesbaar
- Status: gebouwd
- Sinds: baseline; versleuteld sinds b2b60e1

### MC-24 De app in een onzichtbaar frame laten klikken (clickjacking)
- Aanvallersdoel: de gebruiker op een knop in de app laten klikken zonder dat hij het ziet, bijvoorbeeld account verwijderen of uitloggen
- Aanvaller: de eigenaar van een andere website die de gebruiker bezoekt
- Assets / onderdelen: A-02, A-03, C-01, C-02, F-02
- Gerelateerde use case: UC-03, UC-05
- Stappen:
  - AND 1. De gebruiker is ingelogd en bezoekt de site van de aanvaller
  - AND 2. Die site laadt de app in een frame, maakt het onzichtbaar en legt er een eigen knop onder
  - AND 3. De gebruiker klikt op wat hij denkt dat de knop van de andere site is
- Mitigaties: MIT-21 (stap 2: `frame-ancestors 'none'` en `X-Frame-Options: DENY`, dus de browser laadt de app niet in een frame)
- Restrisico: een heel oude browser die geen van beide headers kent
- Status: gebouwd
- Sinds: baseline; dicht sinds 2587a60

### MC-25 Een route bereiken die vergeten is af te schermen
- Aanvallersdoel: zonder login bij een functie komen die een ontwikkelaar per ongeluk open liet
- Aanvaller: iedere bezoeker
- Assets / onderdelen: A-02, A-04, C-02, AU-02
- Gerelateerde use case: UC-03 tot UC-06
- Stappen:
  - AND 1. Er komt een nieuwe route bij zonder de controle op de login; tot 6d9f255 moest elke route zelf `@login_required` hebben
  - AND 2. De aanvaller vindt die route en opent hem zonder in te loggen
- Mitigaties: MIT-24 (stap 1: elke route is standaard dicht; alleen een vaste lijst mag zonder login)
- Restrisico: wie een route aan de publieke lijst toevoegt, maakt hem bewust open; de regressietest controleert die lijst (T-80)
- Status: gebouwd
- Sinds: baseline; dicht sinds 6d9f255

### MC-26 Een fout uitlokken om informatie te krijgen of de log te vervalsen
- Aanvallersdoel: interne details zien (code, paden, de database) of valse regels in de log zetten om sporen te wissen
- Aanvaller: iedere bezoeker
- Assets / onderdelen: C-02, C-03, F-02
- Gerelateerde use case: alle
- Stappen:
  - OR  1. Een fout veroorzaken (vreemde invoer, of een moment dat de database weg is) en de foutpagina lezen
  - OR  2. Een regeleinde in de URL zetten, zodat een logregel met dat pad als twee regels in de log komt
- Mitigaties: MIT-25 (stap 1: een korte melding zonder details; de debugmodus staat sinds de baseline uit. Stap 2: het pad gaat als repr de log in, dus een regeleinde wordt `\n`)
- Restrisico: geen; security-events staan sinds 6992001 in de log (MIT-31, MC-28)
- Status: gebouwd
- Sinds: baseline; veilig falen sinds b362061

### MC-27 De notities van de vorige gebruiker zien op een gedeelde computer
- Aanvallersdoel: de notities en het account van wie eerder dezelfde computer gebruikte
- Aanvaller: de volgende gebruiker van een gedeelde computer, zoals in een lokaal op school
- Assets / onderdelen: A-02, A-03, A-04, C-01, F-02, AU-02
- Gerelateerde use case: UC-02, UC-03
- Stappen:
  - OR  1. Na het uitloggen op Terug drukken: de browser toont de bewaarde pagina, zonder hem opnieuw aan de app te vragen (T-89)
  - OR  2. De vorige gebruiker sluit alleen het tabblad en logt niet uit: de sessiecookie werkt nog, tot 31 dagen na het inloggen (T-90)
- Mitigaties: MIT-28 (stap 1: geen pagina in de cache). MIT-29 (stap 2: hooguit 8 uur)
- Restrisico: binnen die 8 uur, en zolang de browser openstaat, werkt een sessie waaruit niet is uitgelogd. Wat de browser zelf onthoudt (geschiedenis, een opgeslagen wachtwoord) valt buiten de app. OWASP waarschuwt dat een cache `no-store` kan negeren
- Status: gebouwd
- Sinds: baseline; dicht sinds dfa6a6f en 2f1236e

### MC-28 Een aanval blijft onopgemerkt
- Aanvallersdoel: aanvallen zonder dat iemand het merkt, en zonder spoor voor achteraf
- Aanvaller: iedereen die een van de andere misuse cases probeert
- Assets / onderdelen: alle assets, A-11, C-02, C-05, F-05
- Gerelateerde use case: UC-11
- Stappen:
  - OR  1. Wachtwoorden, codes of herstelcodes raden (MC-03, MC-15, MC-19): de blokkades werken, maar niemand ziet ze
  - OR  2. Een formulier van een andere site laten versturen (MC-05)
  - OR  3. Rijen in de database wijzigen of verplaatsen (MC-08, MC-23): de notitie ontsleutelt niet meer, maar niemand ziet waarom
  - OR  4. Massaal accounts of notities aanmaken (MC-10)
  - OR  5. Met andermans gegevens het wachtwoord, de tweede factor of het account wijzigen (MC-12, MC-13, MC-20, MC-21)
- Mitigaties: MIT-31 (stap 1 tot 5: elke gebeurtenis een JSON-regel met tijd, soort, adres en account; T-93). MIT-37 (stap 1: een blokkade geeft binnen een paar minuten een mail; T-107)
- Restrisico: alleen een blokkade geeft een mail (MIT-37), en een paar minuten later; andere gebeurtenissen niet, en ook geen verspreide aanval die nergens een teller op slot zet. Lokaal bewaart Docker de log zolang de container bestaat, en wie de host beheert, kan hem wissen. Op Azure staat hij 30 dagen in Log Analytics, waar de app niet bij kan (sinds d547182, uitgerold op 2026-10-18, T-102). Komt er op een dag meer dan 0,1 GB binnen, dan stopt het verzamelen tot de volgende dag: wie dat met een script haalt, valt daarna niet meer op. Gewone verzoeken worden niet gelogd, en een geweigerde poging tijdens een blokkade ook niet apart: je ziet dat er een blokkade was, niet hoe vaak het daarna nog geprobeerd werd. De log bevat persoonsgegevens (A-11): op Azure is de bewaartermijn 30 dagen; het doel hoort bij de AVG-stap
- Status: gebouwd
- Sinds: baseline; gelogd sinds 6992001

### MC-29 De tweede factor vervangen met de sessie en één code
- Aanvallersdoel: het account blijvend overnemen zonder het wachtwoord te kennen
- Aanvaller: wie de sessie van het slachtoffer heeft (MC-04) en één code uit zijn app (MC-16)
- Assets / onderdelen: A-01, A-03, A-07, A-08, C-02, AU-06, AU-08
- Gerelateerde use case: UC-07, UC-09
- Stappen:
  - AND 1. Handelen als het slachtoffer, met zijn sessie (MC-04)
  - AND 2. Eén geldige code uit de app van het slachtoffer, bijvoorbeeld meteen doorgestuurd (MC-16)
  - AND 3. Een eigen wachtwoord zetten
    - OR  3a. De tweede factor opnieuw instellen, de eigen telefoon koppelen, de nieuwe herstelcode krijgen, en daarmee via wachtwoord vergeten (MIT-14) een nieuw wachtwoord zetten
    - OR  3b. Een nieuwe herstelcode vragen, en later met een tweede code via wachtwoord vergeten
- Mitigaties: MIT-16 (stap 3: opnieuw instellen en een nieuwe herstelcode vragen sinds 997e641 ook het huidige wachtwoord; T-99)
- Restrisico: wie het wachtwoord én de telefoon heeft, kan dit wel; dan is het account sowieso over. Gevonden in de audit van 18-10-2026: met alleen de code was dit de zwakste weg, terwijl wachtwoord wijzigen al beide vroeg
- Status: gebouwd
- Sinds: baseline; dicht sinds 997e641

### MC-30 Eigen code laten uitrollen via de pipeline
- Aanvallersdoel: eigen code op Azure laten draaien, met de rechten en geheimen van de app
- Aanvaller: wie de workflow, een action of een token voor ghcr.io kan misbruiken, of wie naar `main` kan pushen
- Assets / onderdelen: A-12, C-06, C-02, F-06, F-07, B-04
- Gerelateerde use case: UC-10
- Stappen:
  - OR  1. Een workflow-stap die meer mag dan nodig, bijvoorbeeld een token met schrijfrechten op de repo of op andere pakketten
  - OR  2. Een action op een tag die de maker, of wie de action overneemt, naar andere code laat wijzen
  - OR  3. Een pull request vanuit een fork die de workflow aanpast en zo een image publiceert
  - OR  4. Een lang geldig token met `write:packages` stelen en daarmee een image onder dezelfde naam publiceren
  - OR  5. Met een overgenomen GitHub-account naar `main` pushen
  - OR  6. Een pull request die de check zelf aanpast, bijvoorbeeld `--exit-code 1` weghaalt, of een verklaring in `vex/openvex.json` zet, zodat die groen wordt en de ruleset de merge toelaat
- Mitigaties: MIT-34 (stap 1 tot 4: het token van de run mag alleen `contents: read` en `packages: write`, checkout staat vast op een commit, een pull request publiceert niets, en er is geen eigen token meer; T-103). MIT-33 (stap 2: Dependabot stelt een nieuwe versie van de action voor). MIT-39 (stap 3: bij een pull request draait alleen de job `check`, met leesrechten; stap 5 deels: rechtstreeks pushen naar `main` houdt de ruleset tegen; T-110, T-112)
- Restrisico: stap 5 blijft: wie het account heeft, kan een pull request mergen of de ruleset uitzetten, en publiceert zo een image die hij kan uitrollen. Stap 6 blijft ook: bij een pull request draait de workflow uit die pull request; alleen wie mergt, ziet een gewijzigde check, of een nieuwe verklaring in de VEX, in de wijzigingen. De stap VEX controleren eist bij elke verklaring een reden, maar ziet niet of die klopt (MIT-41). De image wordt sinds 29e42cc gescand op bekende lekken (MIT-35), en heeft sinds 1d6f21a een SBoM (MIT-36), maar is niet ondertekend; dat is een volgende stap in de pipeline (Week 8). Het pakket is openbaar, maar er staan geen geheimen in en de code is ook openbaar
- Status: open
- Sinds: 19a34dd

### MC-31 De omgeving op Azure overnemen via de beheerder
- Aanvallersdoel: alles op Azure in handen krijgen: de geheimen, de database en wat er draait
- Aanvaller: wie de Azure-login van de beheerder, zijn pc of de Terraform-state te pakken krijgt
- Assets / onderdelen: A-15, A-16, C-09, C-10, F-10, F-11, B-05
- Gerelateerde use case: UC-10
- Stappen:
  - OR  1. De Azure-login van de beheerder stelen, bijvoorbeeld met phishing
  - OR  2. Een geldige `az login`-sessie gebruiken op de pc van de beheerder, zonder zelf in te loggen
  - OR  3. De Terraform-state wijzigen of wissen, zodat de volgende `apply` iets anders doet of resources vergeet
  - OR  4. De Terraform-state lezen met een accountsleutel van de opslag, buiten de rollen om
- Mitigaties: MIT-38 (stap 3 en 4: de state alleen via Entra ID, alleen de beheerder heeft een rol op de blobs, accountsleutels uit, en vorige versies en 7 dagen terughalen na verwijderen). Bij stap 1 vraagt de tenant een tweede stap bij het inloggen (AADSTS50076); dat is een instelling van de tenant, geen eigen maatregel.
- Restrisico: stap 2 blijft: een sessie op de pc geldt zonder nieuwe tweede stap. De beheerder is Owner op de subscription, dus wie zijn login heeft, kan zichzelf elke rol geven en elk geheim lezen; dat geldt ook voor stap 3, want een Owner kan zichzelf een rol op de opslag geven. Een eigen identiteit met minder rechten komt pas met CD, en dan alleen om de image te vervangen.
- Status: open
- Sinds: 75c9967

## Mitigaties

### MIT-01 Automatisch escapen in Jinja
- Houdt tegen: MC-07 stap 2
- Wat: Flask escapet in `.html`-templates alle `{{ ... }}`-waarden standaard. Dit is een standaardinstelling van het framework en geen eigen werk; wij vermijden alleen `|safe` (opmerking in `notes.html`).
- Waar: `app/web/templates/*.html`
- Status: bewezen (T-18; gemeten op 2026-10-15)
- Sinds: baseline

### MIT-02 Parameterized queries
- Houdt tegen: MC-06 stap 1 en 2
- Wat: alle SQL gaat via één helper, `query(sql, (waarden,))`; de waarden worden los van de SQL-tekst naar de database gestuurd en nooit als SQL gelezen.
- Waar: `query()` in `app/db.py`
- Status: bewezen (T-17; gemeten op 2026-10-15)
- Sinds: baseline

### MIT-03 Vastgezette versies van de Python-pakketten en de images
- Houdt tegen: MC-11 stap 2
- Wat: elk pakket staat op een exacte versie in `requirements.txt`, ook de pakketten die Flask en psycopg meetrekken. Een nieuwe versie komt dus alleen binnen als iemand hem bewust kiest. Er staan geen hashes bij, dus pip controleert niet of het bestand hetzelfde is als toen de versie werd gekozen. Sinds 7bfd435 staan ook de base-images vast, op versie en digest (`python:3.15.0-slim-trixie@sha256:…`, `postgres:18.6-trixie@sha256:…`): een tag kan bij een volgende build niet meer naar een andere image wijzen (stap 4). Op 17-10-2026 bleek waarom: `python:3.15-slim` kreeg die dag een nieuwe digest
- Waar: `app/requirements.txt`, `FROM` in `app/Dockerfile`, `image` van `db` in `compose.yaml`
- Status: bewezen (T-22, T-87; gemeten van 2026-10-15 tot 2026-10-17)
- Sinds: db6698e

### MIT-04 Lengtegrens op titel en notitie
- Houdt tegen: MC-10 stap 1, voor zover het om het opslaan van te lange notities gaat
- Wat: de server weigert een titel van meer dan 15 en een notitie van meer dan 250 tekens met een 400, bij aanmaken en bij aanpassen. `maxlength` in de formulieren is alleen gemak in de browser. Het verzoek wordt wel eerst helemaal ingelezen; tegen een groot verzoek zelf helpt dit niet (daarvoor is `MAX_CONTENT_LENGTH` nodig).
- Waar: `read_note_form()` in `app/notes.py`, met `TITLE_MAX` en `BODY_MAX`
- Status: bewezen (T-27; gemeten op 2026-10-15)
- Sinds: 32c2661

### MIT-05 Tweede factor bij inloggen (TOTP)
- Houdt tegen: MC-03 stap 1 en 2, en een gelekt wachtwoord uit MC-01; sinds MIT-12 voor elk account. Maakt MC-12 kleiner
- Wat: na het juiste wachtwoord krijgt de sessie alleen een `pending_user_id`. Daarmee opent geen enkele route, want `require_login` en `load_user` kijken naar `user_id`. Pas na een geldige code op `/login/2fa` wordt de sessie gewist en `user_id` gezet. De halve login vervalt na 5 minuten. TOTP volgens RFC 6238: een geheim van 160 bits (RFC 4226 R6), 6 cijfers, 30 seconden, één stap klokverschil (RFC 6238, 5.2), vergeleken in constante tijd. Alleen de cijfers 0-9 tellen; een code met andere cijfers, zoals Arabisch-Indische, is gewoon fout (T-59). De berekening is zonder dependency geschreven en met de hand tegen alle testvectoren van RFC 6238 en RFC 4226 gecontroleerd (T-35). Aanzetten gebeurt pas na een eerste geldige code. Opnieuw instellen vraagt ook een code (AU-06), zodat wie alleen de sessie heeft de tweede factor niet kan vervangen
- Waar: `login()`, `login_code()` en `check_code()` in `app/auth.py`; `app/totp.py`
- Status: bewezen (T-32, T-35; gemeten op 2026-10-15)
- Sinds: 96626e2; alleen 0-9 sinds ce12d31

### MIT-06 Blokkade na 5 foute codes
- Houdt tegen: MC-15 stap 2
- Wat: foute codes worden per account in de database geteld (`auth_throttle`, via `throttle.py`), niet in de sessie, want een sessie kan de aanvaller gewoon opnieuw beginnen. Elke poging telt vóór de controle, in één SQL-statement, zodat ook verzoeken die tegelijk binnenkomen samen niet meer dan 5 pogingen krijgen; blokkade en verdubbelen gaan dan maar één keer omhoog (T-58). Na 5 fouten in 15 minuten wordt de volgende poging geweigerd en gaat de codestap op slot, in hetzelfde statement; dan wordt ook de juiste code geweigerd. De eerste blokkade duurt 15 minuten, elke volgende twee keer zo lang, tot 24 uur. Een geldige code wist de teller. De controle op de blokkade zit ook in de UPDATE die de code accepteert. Tijdens de blokkade antwoordt de app met 429 en `Retry-After`, de resterende tijd in seconden
- Waar: `check_code()` in `app/auth.py`, `app/throttle.py`
- Status: bewezen (T-30, T-58; gemeten van 2026-10-15 tot 2026-10-16)
- Sinds: 18e1424; verdubbelend sinds 484eca3; 429 sinds 5a82eb5; tellen vóór de controle sinds 49baae5; blokkade in hetzelfde statement sinds 467623d

### MIT-07 Elke code werkt één keer
- Houdt tegen: MC-16 stap 2
- Wat: de tijdstap van de laatst geaccepteerde code staat in `totp_last_step`. Een code van dezelfde of een eerdere stap wordt geweigerd, zoals RFC 6238 5.2 eist ("MUST NOT accept the second attempt"). De controle zit in de WHERE van dezelfde UPDATE die de stap opslaat, zodat van twee gelijktijdige verzoeken met dezelfde code er maar één wint (T-31)
- Waar: `check_code()` in `app/auth.py`
- Status: bewezen (T-31; gemeten op 2026-10-15)
- Sinds: 18e1424

### MIT-08 Het geheim alleen tijdens het instellen, en niet in een cache
- Houdt tegen: MC-17 stap 3, en het later terugkijken uit stap 2
- Wat: de QR-code (`/account/2fa/qr.svg`) en de sleutel zijn alleen op te vragen zolang tweestapsverificatie nog niet aan staat; daarna geeft de QR-route een 404. Beide worden verstuurd met `Cache-Control: no-store`. De QR-code komt van een eigen route en staat niet inline in de pagina
- Waar: `setup_2fa()` en `qr_2fa()` in `app/account.py`; `Cache-Control: no-store` in `security_headers()` in `app/app.py`, sinds MIT-28 op elke pagina
- Status: bewezen (T-36; gemeten op 2026-10-15)
- Sinds: 18e1424

### MIT-09 Sessieversie: oude sessies vervallen
- Houdt tegen: MC-04 stap 4; maakt MC-12 kleiner
- Wat: elke gebruiker heeft een `session_version` in de database, en de sessiecookie krijgt die mee. `load_user` accepteert de sessie alleen als beide gelijk zijn; anders wordt de sessie gewist met de melding "Your session is no longer valid". Uitloggen, een nieuw wachtwoord en tweestapsverificatie aanzetten of opnieuw instellen verhogen de versie. Na een nieuw wachtwoord of een 2FA-wijziging krijgt de huidige sessie de nieuwe versie en blijft ingelogd; alle andere vervallen. Ook een halve login vervalt als de versie verandert voordat de code is ingevuld. Uitloggen logt alle apparaten van het account uit: zonder sessies op de server bij te houden kan het niet preciezer
- Waar: `load_user()`, `start_session()`, `keep_this_session()`, `login_code()` en `logout()` in `app/auth.py`; `change_password()`, `setup_2fa()` en `reset_2fa()` in `app/account.py`
- Status: bewezen (T-14, T-37, T-38; gemeten op 2026-10-15)
- Sinds: 587955a; in dezelfde UPDATE als het nieuwe wachtwoord of de 2FA-wijziging sinds 96b892d, zodat het nooit het een zonder het ander is

### MIT-10 Blokkade op de wachtwoordstap
- Houdt tegen: MC-03 stap 1 en 2
- Wat: foute wachtwoorden worden geteld per IP-adres (20 in 15 minuten) en per account vanaf één adres (5 in 15 minuten). Daarna volgt een blokkade van 15 minuten, die bij herhaling verdubbelt tot een uur; ook het juiste wachtwoord wordt dan geweigerd, met status 429 en `Retry-After`. De tellers hangen aan wat er is ingevuld en niet aan of het account bestaat, dus een blokkade verraadt geen namen. Elke poging telt vóór de controle, zoals bij MIT-06. Een geslaagde login wist de teller van het account; van de teller van het adres gaat alleen die ene poging af, anders zet een aanvaller met een eigen account de adresteller steeds terug. Bewust geen blokkade per account over alle adressen (MC-18). IPv6-adressen tellen per /64; een IPv4-adres dat via een IPv6-socket binnenkomt, telt als dat IPv4-adres (T-60). De sleutels in `auth_throttle` zijn HMAC's, dus de tabel bevat geen leesbare IP-adressen of gebruikersnamen. Bij een nieuwe blokkade gaan de tellers weg waarvan venster en blokkade meer dan een dag voorbij zijn (T-61). Achter een proxy komt het adres uit `X-Forwarded-For` via `ProxyFix` (`TRUSTED_PROXIES`, lokaal 0); een poort erachter valt eraf (T-72). De hackstand voor de hacking week (`THROTTLE_IP_MODE=hackweek`) maakt de limiet per adres 100, met een vaste blokkade van 5 minuten zonder verdubbeling, en `THROTTLE_PAIR_EXEMPT_USERS` haalt het demoaccount uit de teller per naam per adres. Standaard staat beide uit, en een onbekende stand laat de app niet starten (T-71)
- Waar: `login()` in `app/auth.py`, `app/throttle.py`
- Status: bewezen (T-12, T-39, T-58, T-60, T-71, T-72; gemeten van 2026-10-15 tot 2026-10-16)
- Sinds: 484eca3; `Retry-After` sinds 5a82eb5; tellen vóór de controle sinds 49baae5, blokkade in hetzelfde statement sinds 467623d; IPv4 achter IPv6 sinds 87a5006; opruimen sinds db7c907; zonder poort sinds 67a2636; hackstand sinds 8c3fc87

### MIT-11 Herstelcode
- Houdt tegen: MC-19 stap 2a, 2c en 2d; maakt tweestapsverificatie mogelijk zonder dat een kwijtgeraakte telefoon het account onbereikbaar maakt
- Wat: bij het aanzetten van tweestapsverificatie krijgt de gebruiker één keer een herstelcode van 128 willekeurige bits te zien. Alleen de SHA-256 wordt bewaard; een snelle hash is genoeg bij 128 willekeurige bits, anders dan bij een zelfverzonnen wachtwoord. Inloggen met de code kan alleen na het juiste wachtwoord; zonder wachtwoord werkt hij alleen samen met een code uit de app, om een nieuw wachtwoord in te stellen (MIT-14). De code werkt één keer. Bij inloggen zet hij tweestapsverificatie uit en verhoogt de sessieversie, en de app stuurt meteen naar het opnieuw instellen met een nieuwe telefoon (MIT-12). Het verbruik zit in een UPDATE met de hash in de WHERE, dus twee gelijktijdige verzoeken kunnen hem niet allebei gebruiken. 5 fouten in 15 minuten geven een blokkade (via `throttle.py`, met 429 en `Retry-After`). Een nieuwe code maken vraagt het huidige wachtwoord en een code uit de app (AU-06, sinds 997e641; MC-29) en maakt de vorige ongeldig; na wachtwoord vergeten krijgt de gebruiker meteen een nieuwe. De pagina's met de code worden met `Cache-Control: no-store` verstuurd
- Waar: `new_recovery_code()`, `hash_recovery_code()` en `login_recover()` in `app/auth.py`; `setup_2fa()` en `new_recovery()` in `app/account.py`. Sinds 54d4d62 kan de gebruiker de code kopiëren of downloaden, en gaat Verder pas na het vinkje dat hij hem bewaard heeft (`recovery_code.html`, `forms.js`; T-96); zonder JavaScript werkt de pagina als voorheen. Overgenomen uit BOK-SECENGINEER
- Status: bewezen (T-46; gemeten op 2026-10-15)
- Sinds: dc7d258; `Retry-After` sinds 5a82eb5

### MIT-12 Tweestapsverificatie verplicht
- Houdt tegen: MC-03 stap 1 en 2 voor alle accounts, niet alleen voor wie het zelf aanzet; beperkt het venster van MC-20
- Wat: `require_login` laat een ingelogde gebruiker zonder tweestapsverificatie alleen het instellen afmaken (`/account/2fa` en de QR-code); elke andere pagina stuurt daarheen. Dat geldt voor een nieuw account na het eerste wachtwoord, en na het gebruik van een herstelcode. De instelpagina maakt zelf een geheim aan en biedt uitloggen in plaats van annuleren. Uitzetten bestaat niet meer: alleen opnieuw instellen voor een nieuwe telefoon, met een code (AU-06), waarna de app meteen naar het instellen stuurt
- Waar: `require_login()` en `login()` in `app/auth.py`; `setup_2fa()` en `reset_2fa()` in `app/account.py`
- Status: bewezen (T-50; gemeten op 2026-10-15)
- Sinds: 42ab429

### MIT-13 Sterkte-eis voor een nieuw wachtwoord
- Houdt tegen: MC-03 stap 3
- Wat: een nieuw wachtwoord moet 12 tot 64 tekens zijn, bij registreren, wijzigen en wachtwoord vergeten; inloggen controleert alleen. Geen eisen aan cijfers of leestekens: NIST SP 800-63B-4 verbiedt zulke samenstellingsregels. 12 ligt bewust tussen de 8 die NIST minstens eist voor een wachtwoord dat deel is van inloggen met meer factoren, en de 15 voor een wachtwoord als enige factor. 64 is de lengte die NIST minstens wil toestaan. Afwijking van NIST: nog geen vergelijking met een lijst van veelgebruikte en gelekte wachtwoorden (een blocklist, daar een SHALL); die is gepland, met een lijst in de repo in plaats van een externe dienst. De formulieren tonen de grenzen en controleren ze ook in de browser, maar de server beslist
- Waar: `password_problem()` in `app/passwords.py`; `register()` en `forgot_password()` in `app/auth.py`; `change_password()` in `app/account.py`
- Status: bewezen (T-13, T-53; gemeten op 2026-10-16)
- Sinds: 9f690ce

### MIT-14 Wachtwoord vergeten met twee van de drie factoren
- Houdt tegen: MC-21 stap 1b, 2a, 3a en 3b; maakt een vergeten wachtwoord op te lossen zonder het account te verliezen
- Wat: `/login/forgot` vraagt gebruikersnaam, herstelcode, een code uit de app en twee keer het nieuwe wachtwoord. Wachtwoord en telefoon is gewoon inloggen, wachtwoord en herstelcode is telefoon kwijt (MIT-11), herstelcode en telefoon is wachtwoord vergeten; één factor is nooit genoeg. De route is bereikbaar zonder wachtwoord, dus een foute herstelcode telt alleen per IP-adres en per naam per adres, met dezelfde tellers als inloggen (MIT-10), en een juiste herstelcode telt daar als geslaagde poging: een blokkade per account zou iedereen die een naam kent de herstelroutes laten blokkeren (MC-18). Een onbekende naam krijgt dezelfde melding en dezelfde blokkade; het enige verschil in werk is één vergelijking van 64 tekens. Pas als de herstelcode klopt, wordt de code uit de app gecontroleerd met `check_code()`, dus met de blokkade per account en het eenmalige gebruik van de codestap (MIT-06, MIT-07). Nieuw wachtwoord, verbruik van de oude herstelcode, de nieuwe herstelcode en een hogere sessieversie zitten in één UPDATE met de oude hash in de WHERE, dus van twee gelijktijdige verzoeken wint er één. Daarna is de gebruiker niet ingelogd, zoals het OWASP Forgot Password Cheat Sheet aanraadt, maar krijgt meteen een nieuwe herstelcode, met `Cache-Control: no-store`. Het nieuwe wachtwoord valt onder de sterkte-eis (MIT-13)
- Waar: `forgot_password()` en `hash_recovery_code()` in `app/auth.py`; `Cache-Control: no-store` in `security_headers()` in `app/app.py`
- Status: bewezen (T-54, T-57; gemeten op 2026-10-16)
- Sinds: 428858e; nieuwe herstelcode in dezelfde UPDATE sinds 3f7eb20

### MIT-15 Eigenaarscontrole op notities
- Houdt tegen: MC-02 stap 2
- Wat: elke query op één notitie heeft naast de id ook `user_id` uit de sessie in de WHERE: `own_note()` bij openen en aanpassen, de UPDATE zelf, en de DELETE met `RETURNING`. Is de notitie niet van de ingelogde gebruiker, dan volgt 404, precies zoals bij een id dat niet bestaat; zo verraadt het antwoord niet dat de notitie bestaat, wat het OWASP IDOR Prevention Cheat Sheet aanraadt. De lijst op `/` liet al alleen eigen notities zien (AZ-01)
- Waar: `own_note()`, `edit_note()` en `delete_note()` in `app/notes.py`
- Status: bewezen (T-11; gemeten op 2026-10-16)
- Sinds: 668166a

### MIT-16 Herauthenticatie bij wachtwoord wijzigen, account verwijderen en het vervangen van de tweede factor
- Houdt tegen: MC-12 stap 2, MC-13 stap 2 en MC-29 stap 3; ook via een andere site (MC-05) lukken deze twee acties niet meer, want die site kent het wachtwoord niet
- Wat: beide formulieren vragen het huidige wachtwoord én een code uit de app, zodat wie alleen het wachtwoord heeft, hier niets kan (sinds 72ddaed, T-98). Sinds 997e641 geldt hetzelfde voor de tweede factor opnieuw instellen en een nieuwe herstelcode: met alleen de code kon wie de sessie en één code had, zijn eigen telefoon koppelen en via wachtwoord vergeten een eigen wachtwoord zetten (MC-29, T-99). De code loopt via `check_code()`, met dezelfde blokkade en hetzelfde eenmalige gebruik als bij het inloggen (MIT-06, MIT-07). Het wachtwoord controleert `passwords.is_current()`. Dat is de enige plek; sinds MIT-19 met Argon2id. Elke poging telt vóór de controle, per account (`reauth_account`): na 5 fouten in 15 minuten wordt de volgende geweigerd, 15 minuten, verdubbelend tot 24 uur. Per account mag hier, want deze stap is alleen met een sessie te bereiken; zonder limiet kan iemand met een gestolen sessie het wachtwoord raden. Bij wachtwoord wijzigen gaat de sterkte-eis (MIT-13) eerst, zodat een fout in het nieuwe wachtwoord geen poging kost. Het OWASP Authentication Cheat Sheet vraagt de huidige gegevens opnieuw voor het wijzigen van gevoelige accountgegevens, zoals het wachtwoord
- Waar: `refuse_without_both_factors()`, `change_password()`, `delete_account()`, `reset_2fa()` en `new_recovery()` in `app/account.py`; `is_current()` in `app/passwords.py`; `check_code()` in `app/auth.py`
- Status: bewezen (T-23, T-62, T-98, T-99; gemeten van 2026-10-16 tot 2026-10-18)
- Sinds: f40781b; met code sinds 72ddaed; ook bij de tweede factor sinds 997e641

### MIT-17 Versleuteling van het TOTP-geheim
- Houdt tegen: MC-17 stap 1
- Wat: de app versleutelt het TOTP-geheim voordat het de database in gaat, met AES-256-GCM uit de library `cryptography`, zoals het OWASP Cryptographic Storage Cheat Sheet aanraadt: AES met een sleutel van 256 bits in een geauthenticeerde modus. Elke waarde krijgt een nieuwe willekeurige nonce van 96 bits, de lengte die NIST aanraadt. De soort en de `user_id` gaan mee als associated data: een waarde die naar de rij van een ander account wordt gekopieerd, ontsleutelt daar niet (T-63). Vooraan staat de sleutelversie (`v1:`), zodat een nieuwe sleutel later naast de oude kan. De sleutel (A-09) staat in de omgeving van de app en nooit in de database. Wat niet ontsleutelt, telt als geen geheim: dan wordt elke code geweigerd. Een half ingesteld geheim dat niet ontsleutelt, wordt vervangen, want het werkte nog nergens (T-65). Bewust in de app en niet met pgcrypto in de database: dan zou de sleutel bij elke query als parameter mee naar de database gaan, en in de databaselog staan zodra het loggen van statements aanstaat (`log_statement = all`, zoals tijdelijk voor `17_sqli_databaselog`)
- Waar: `app/encryption.py`; `setup_2fa()` en `qr_2fa()` in `app/account.py`; `check_code()` in `app/auth.py`
- Status: bewezen (T-34, T-63; gemeten van 2026-10-16 tot 2026-10-17)
- Sinds: 776931a

### MIT-18 Versleuteling van notities
- Houdt tegen: MC-23 stap 2
- Wat: titel en inhoud gaan met dezelfde helper en sleutel als het TOTP-geheim (MIT-17) de database in: AES-256-GCM, een nieuwe nonce per waarde, de sleutelversie vooraan. De soort (`note_title`, `note_body`) en de `user_id` van de eigenaar gaan mee als associated data, dus een titel als inhoud, of een notitie in de rij van een ander account, ontsleutelt niet (T-67). Wat niet ontsleutelt, staat op de pagina als "(unreadable)". De lengtegrens (MIT-04) geldt voor de tekst zelf, vóór het versleutelen
- Waar: `sealed()` en `readable()` in `app/notes.py`; `app/encryption.py`
- Status: bewezen (T-66, T-67; gemeten van 2026-10-16 tot 2026-10-17)
- Sinds: b2b60e1

### MIT-19 Wachtwoorden als Argon2id-hash
- Houdt tegen: MC-01 stap 2
- Wat: wachtwoorden worden gehasht met Argon2id uit `cryptography` (via OpenSSL; tot 29d201d uit `argon2-cffi`, met hetzelfde formaat), met de minimale instelling uit het OWASP Password Storage Cheat Sheet: 19 MiB geheugen, 2 iteraties, 1 thread. Elke hash krijgt een eigen salt van 16 willekeurige bytes, en algoritme, instelling en salt staan in de hash zelf, in het PHC-formaat (T-68). Hashen en niet versleutelen: de app hoeft het wachtwoord nooit terug te lezen, en OWASP noemt versleutelen alleen voor uitzonderingen waarin dat wel moet. Bij een onbekende naam rekent de app tegen een vaste hash, zodat de responstijd niet verraadt of een naam bestaat (T-70). Is een hash met een oudere instelling gemaakt, dan maakt de app bij de volgende geslaagde login een nieuwe, zoals OWASP aanraadt (T-69). Geen pepper: OWASP noemt dat alleen extra verdediging, en een pepper kan niet meer veranderen zonder de wachtwoorden. Geen omzetting van leesbare wachtwoorden: in de ontwikkelfase begint de database leeg
- Waar: `app/passwords.py`; `register()`, `login()` en `forgot_password()` in `app/auth.py`; `change_password()` in `app/account.py`
- Status: bewezen (T-10, T-68, T-69, T-70; gemeten van 2026-10-16 tot 2026-10-17)
- Sinds: 9e6e365

### MIT-20 CSRF-token per sessie
- Houdt tegen: MC-05 stap 2
- Wat: elke sessie krijgt een willekeurig token van 32 bytes (`secrets.token_urlsafe`), en elk formulier stuurt het mee in een verborgen veld. Een POST zonder het juiste token krijgt 400, met de vergelijking in constante tijd (`hmac.compare_digest`), zoals het OWASP CSRF Prevention Cheat Sheet aanraadt. Een token per sessie, niet per verzoek: OWASP noemt beide, en per verzoek geeft fouten met de terugknop. De controle draait vóór het laden van de gebruiker, zodat een verlopen sessie gewoon naar de inlogpagina gaat. `SameSite=Lax` op de cookie (MIT-23) is volgens OWASP een extra laag, geen vervanging
- Waar: `app/csrf.py`; het veld in alle 14 formulieren in `app/web/templates/`
- Status: bewezen (T-16, T-73; gemeten op 2026-10-17)
- Sinds: 5bd55c5

### MIT-21 Beveiligingsheaders
- Houdt tegen: MC-07 stap 2 (tweede laag), MC-24 stap 2
- Wat: op elk antwoord, ook op foutpagina's: `Content-Security-Policy: default-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'`, `X-Frame-Options: DENY` voor oudere browsers, `X-Content-Type-Options: nosniff` en `Referrer-Policy: same-origin`. De app had al geen inline script of style, dus de CSP kan streng; op de belangrijkste pagina's gaf de browser geen enkele overtreding (T-75). `Strict-Transport-Security` alleen als de app op HTTPS draait, anders zou de browser het lokaal verkeerd onthouden
- Waar: `security_headers()` in `app/app.py`
- Status: bewezen (T-18, T-74, T-75; gemeten van 2026-10-15 tot 2026-10-16)
- Sinds: 2587a60

### MIT-22 Invoercontrole
- Houdt tegen: MC-10 stap 1, MC-07 stap 1 (gebruikersnaam), MC-18 stap 3
- Wat: een gebruikersnaam is 3 tot 20 letters, cijfers of `_`, gecontroleerd met `fullmatch` op een allowlist, zoals het OWASP Input Validation Cheat Sheet aanraadt. Bij registreren een melding; bij inloggen en wachtwoord vergeten telt een andere naam als onbekend, met hetzelfde antwoord. De browser controleert hetzelfde met `pattern` en `maxlength`, maar dat is alleen gemak: de server beslist. Een verzoek boven 16 KiB (`MAX_CONTENT_LENGTH`) krijgt 413 voordat het is ingelezen. Alleen een POST voert een formulieractie uit; HEAD en GET tonen alleen de pagina
- Waar: `USERNAME` en `register()`, `login()`, `forgot_password()` in `app/auth.py`; `MAX_CONTENT_LENGTH` in `app/app.py`
- Status: bewezen (T-21, T-76, T-77, T-78; gemeten van 2026-10-16 tot 2026-10-17)
- Sinds: 7fbc42e (alleen POST); 61221ed (naam en grootte)

### MIT-23 Configuratie controleren en veilige standaarden
- Houdt tegen: MC-18 stap 4; MC-04 en MC-05 (de cookie)
- Wat: configuratie is ook invoer. Bij het starten moeten `TRUSTED_PROXIES` 0 of 1 zijn en `HTTPS_ONLY` 0 of 1, `FLASK_SECRET_KEY` minstens 32 tekens, `DATA_ENCRYPTION_KEY` 256 bits en `THROTTLE_IP_MODE` een bekende stand; anders start de app niet. Standaard veilig: zonder `HTTPS_ONLY` gaat de cookie alleen over HTTPS, en alleen `compose.yaml` zet dat lokaal uit. De cookie heeft altijd `HttpOnly` en `SameSite=Lax`
- Waar: `setting()` en de configuratie in `app/app.py`; `compose.yaml`
- Status: bewezen (T-79; gemeten op 2026-10-16)
- Sinds: 172f43d

### MIT-24 Standaard dicht
- Houdt tegen: MC-25 stap 1
- Wat: één hook vraagt voor elke route een login met tweestapsverificatie; alleen een vaste lijst (`PUBLIC_ENDPOINTS`: inloggen, registreren, de code- en herstelroutes, wachtwoord vergeten, uitloggen en de statische bestanden) mag zonder. Dat vervangt de tien losse `@login_required`. De regressietest haalt alle routes uit de app zelf en controleert dat elke andere route een anonieme bezoeker naar `/login` stuurt (T-80)
- Waar: `require_login()` en `PUBLIC_ENDPOINTS` in `app/auth.py`
- Status: bewezen (T-80; gemeten op 2026-10-16)
- Sinds: 6d9f255

### MIT-25 Veilig falen
- Houdt tegen: MC-26 stap 1 en 2
- Wat: een HTTP-fout (404, 405, 413) krijgt de eigen foutpagina met een korte melding; status en headers, zoals `Allow` bij 405, blijven. Een onverwachte fout geeft 500 met "Something went wrong", en de fout zelf gaat met traceback naar de log (stderr, lokaal en op Azure hetzelfde). Het pad gaat als repr de log in, zodat een regeleinde in de URL `\n` wordt en geen valse regel maakt (log injection, OWASP Logging Cheat Sheet)
- Waar: `http_error()` en `unexpected_error()` in `app/app.py`; `app/web/templates/error.html`
- Status: bewezen (T-81; gemeten op 2026-10-16)
- Sinds: b362061

### MIT-26 Gunicorn als gewone gebruiker
- Houdt tegen: MC-14 stap 1 en 2
- Wat: de image maakt een systeemgebruiker `app` zonder shell en draait daaronder. De code is van root, dus de app kan hem lezen maar niet aanpassen. Gunicorn met twee workers vervangt de ontwikkelserver van Flask, die zelf waarschuwt niet voor productie te zijn. Docker raadt zelf aan: kan een dienst zonder rechten draaien, zet dan met `USER` een gewone gebruiker
- Waar: `app/Dockerfile`; `gunicorn` in `app/requirements.txt`
- Status: bewezen (T-82; gemeten op 2026-10-16)
- Sinds: 13a2eb4

### MIT-27 Eigen databaserol voor de app
- Houdt tegen: MC-08 stap 2a en 2b
- Wat: de app logt in als `notities_app`: geen superuser en nergens eigenaar van. Hij mag `SELECT`, `INSERT`, `UPDATE` en `DELETE` op `users`, `notes` en `auth_throttle`, en `USAGE` op de twee sequences, precies wat de app doet. Tabellen maken, wijzigen of weggooien, rollen aanmaken en `COPY` naar een bestand of programma kunnen niet. Dat laatste mag in PostgreSQL alleen een superuser of een lid van `pg_read_server_files`, `pg_write_server_files` of `pg_execute_server_program`. In een nieuwe database heeft `PUBLIC` sinds PostgreSQL 15 geen `CREATE` meer op het schema `public`, dus ook een eigen tabel maken lukt niet. Lokaal zet `db/app-password.sh` het wachtwoord bij de eerste start, met psql als letterlijke tekst; de app krijgt alleen dat wachtwoord. Op Azure staat het wachtwoord van de eigenaar in een eigen Key Vault die alleen de schema-job leest, met een eigen identiteit; Microsoft raadt een vault per applicatie aan en geen rechten per geheim. De job maakt het schema in een lege database en zet bij elke start het wachtwoord van de app-rol, met `sql.Literal`
- Waar: `db/schema.sql`, `db/app-password.sh`, `DATABASE_URL` in `compose.yaml`; `azurerm_key_vault.admin` in `terraform/keyvault.tf`, `azurerm_container_app_job.schema` in `terraform/app.tf`
- Status: bewezen (T-19, T-83, T-84, T-86; gemeten van 2026-10-17 tot 2026-10-18)
- Sinds: 1d1b4eb; Azure sinds 7535a78

### MIT-28 Geen pagina in de cache
- Houdt tegen: MC-27 stap 1
- Wat: elk antwoord behalve een statisch bestand krijgt `Cache-Control: no-store`, zoals de OWASP Session Management Cheat Sheet aanraadt voor antwoorden met gevoelige sessiedata. De browser bewaart de pagina dan niet, dus na uitloggen toont Terug de inlogpagina in plaats van de notities (T-89). Dit vervangt de lijst van vier pagina's met het TOTP-geheim en de herstelcode (MIT-08, MIT-11). CSS en scripts bevatten niets van een gebruiker en mogen wel in de cache. Gevonden met de audit van 17-10-2026
- Waar: `security_headers()` in `app/app.py`
- Status: bewezen (T-89; gemeten op 2026-10-17)
- Sinds: dfa6a6f

### MIT-29 Sessie van hooguit 8 uur
- Houdt tegen: MC-04 stap 4, MC-27 stap 2
- Wat: `PERMANENT_SESSION_LIFETIME` is 8 uur. Flask controleert bij elk verzoek hoe oud de handtekening van de sessiecookie is, ook bij een cookie die alleen voor de browsersessie geldt (gelezen in de broncode van Flask 3.1.3); een oudere cookie telt als geen sessie (T-90). De app schrijft de cookie bij het inloggen en bij een melding (`flash()`), dus de grens ligt ongeveer 8 uur na de login. Daarvoor gold de standaard van 31 dagen. OWASP noemt een absolute timeout voor elke sessie, met 4 tot 8 uur als voorbeeld voor een werkdag. Overgenomen uit BOK-SECENGINEER
- Waar: `app/app.py`
- Status: bewezen (T-90; gemeten op 2026-10-17)
- Sinds: 2f1236e

### MIT-30 Limiet op registreren en op notities
- Houdt tegen: MC-10 stap 2 en 3; MC-09 deels, want ook een bezette naam telt mee
- Wat: elke registratie telt per adres in `auth_throttle`, ook een gelukte, want ook die kost een Argon2id-berekening van 19 MiB: 10 per uur, daarna een uur op slot, bij herhaling oplopend tot 4 uur; in de hackstand 60 per uur en 5 minuten (T-91). De teller staat vlak voor het hashen, dus een ongeldige naam of een te kort wachtwoord telt niet. Per account hooguit 25 notities, geteld en toegevoegd in één statement (T-92); gelijktijdige verzoeken kunnen er samen een paar overheen, hooguit één per worker, want een slot zou elke notitie trager maken voor een grens die alleen de groei afremt. Overgenomen uit BOK-SECENGINEER (10 per uur en 25 notities; de hackstand daar was 30 per uur)
- Waar: `POLICIES` en `IP_MODES` in `app/throttle.py`; `register()` in `app/auth.py`; `index()` in `app/notes.py`
- Status: bewezen (T-91, T-92; gemeten op 2026-10-17)
- Sinds: 5d0f1d0

### MIT-31 Security-events loggen
- Houdt tegen: MC-28 stap 1 tot 5
- Wat: één functie, `events.event()`, schrijft per gebeurtenis een JSON-regel naar stderr: tijd (UTC), soort, IP-adres, en als dat bekend is het account. Dat is het "when, where, who and what" van de OWASP Logging Cheat Sheet. Lokaal in `docker compose logs`; op Azure zet Container Apps hem in een Log Analytics-workspace, 30 dagen en dan weg, zonder verschil in de code (sinds d547182, T-102 na de uitrol). 21 soorten, op de plekken waar de app al beslist: registreren, inloggen en de blokkades, codes en herstelcodes, wachtwoord vergeten, uitloggen, een verlopen sessie, tweestapsverificatie aan en opnieuw, een nieuw wachtwoord, herauthenticatie, account verwijderen, een geweigerd CSRF-token, de limiet op notities en een notitie die niet ontsleutelt. JSON escapet regeleindes en stuurtekens, dus invoer maakt geen valse regel (log injection). Een gebruikersnaam komt er alleen in als het account bestaat; anders staat er `"known": false` (sinds f977f6d, T-100). Eerst gold de naamregel van MIT-22, maar een wachtwoord als `Zomervakantie2026` voldoet daar ook aan. Een blokkade staat er één keer in, op het moment dat hij begint (`lockout_started`, met de soort teller), en niet bij elke geweigerde poging; anders kon een script de log vullen (sinds f977f6d, T-101). Wachtwoorden, codes, geheimen en de sessiecookie nooit (T-93, T-94). Overgenomen uit BOK-SECENGINEER
- Waar: `app/events.py`; aanroepen in `app/auth.py`, `app/account.py`, `app/csrf.py` en `app/notes.py`; op Azure `terraform/logs.tf`
- Status: bewezen (T-93, T-94, T-100, T-101; gemeten van 2026-10-17 tot 2026-10-18); op Azure uitgerold op 2026-10-18 (T-102)
- Sinds: 6992001; naam en blokkade sinds f977f6d; bewaard op Azure sinds d547182

### MIT-32 .env alleen voor de eigenaar
- Houdt tegen: MC-22 stap 2, deels
- Wat: `deployment.py` zet `.env` op 0600 (alleen de eigenaar mag lezen en schrijven), al vóór het schrijven, en ook een bestaand bestand. Op Linux kreeg het eerst de standaard 0644, leesbaar voor elke gebruiker van de machine (T-95). Op Windows doet `chmod` verder niets; daar gelden de rechten van de map waarin de repo staat. Gevonden met de audit van 17-10-2026
- Waar: `write_env()` in `scripts/deploy_local.py`
- Status: bewezen (T-95; gemeten op 2026-10-17)
- Sinds: 9d3f985

### MIT-33 Dependabot
- Houdt tegen: MC-11 stap 1 en 3
- Wat: `.github/dependabot.yml` laat GitHub elke week een pull request openen als er een nieuwe versie is van een pip-pakket, de base-image in de Dockerfile, de image in `compose.yaml`, een Terraform-provider of een GitHub Action (die sinds 19a34dd). Alles staat vast (MIT-03), dus zonder dit komen ook patches niet vanzelf binnen. Er is geen pipeline voor nodig; in de BoK hoort het bij CI/CD (Week 8). Of Dependabot ook de `@sha256`-digest bijwerkt, staat niet in de documentatie van GitHub (gelezen op 17-10-2026); dat blijkt bij de eerste pull request (T-97)
- Waar: `.github/dependabot.yml`
- Status: bewezen (T-97; gemeten op 2026-10-18)
- Sinds: 19999a9

### MIT-34 De image-pipeline met minimale rechten
- Houdt tegen: MC-30 stap 1 tot 4
- Wat: `.github/workflows/image.yml` bouwt bij elke push naar `main` de image en publiceert hem op ghcr.io. Standaard heeft de workflow geen rechten (`permissions: {}`); de job krijgt alleen `contents: read` en `packages: write`, zoals GitHub aanraadt. Inloggen bij ghcr.io gaat met het token van de run, via stdin; een eigen token (classic) is niet meer nodig. `actions/checkout` staat vast op een volledige commit-hash, en verder gebruikt de workflow gewone `docker`-opdrachten, geen actions van derden. Bij een pull request draait alleen de job `check`, met `contents: read`, en die publiceert niets; de job `image` draait daar niet (sinds bc6c669, MIT-39). De tags zijn de commit en de inhoud van `app/` (de tree-hash van git), nooit `latest`; `deployment.py azure` zoekt de image op die tweede tag en kijkt anoniem of hij openbaar is (T-103)
- Waar: `.github/workflows/image.yml`; het zoeken in `run()` van `scripts/deploy_azure.py`
- Status: bewezen (T-103; gemeten op 2026-10-18)
- Sinds: 19a34dd; tag op de inhoud van `app/` sinds 7d8f7b5; een eigen job bij een pull request sinds bc6c669

### MIT-35 Een scan op bekende lekken vóór het publiceren
- Houdt tegen: MC-11 stap 1 en 3
- Wat: de workflow scant de SBoM van de gebouwde image (MIT-36) met Trivy 0.76.0 (tot bc6c669 0.75.0), vast op versie en digest, vóór het pushen. Een lek van HIGH of CRITICAL stopt de job; dan staat er geen nieuwe image op ghcr.io, en kan `deployment.py azure` hem ook niet uitrollen. Tot e6a3888 alleen een lek waarvoor al een oplossing was (`--ignore-unfixed`); sinds e6a3888 ook een zonder oplossing, tenzij de VEX het voor die versie uitsluit (MIT-41). De eerste scan vond vier keer HIGH, allemaal in de eigen kopieën van urllib3, msgpack en setuptools die pip meeneemt; sinds b31d334 gaat pip na het installeren uit de image, want de app en de schema-job gebruiken hem niet (T-105). Sinds bc6c669 draait dezelfde scan ook bij elke pull request, en houdt hij dan de merge tegen (MIT-39)
- Waar: de stap Scannen op bekende lekken in `.github/workflows/image.yml`; `RUN` in `app/Dockerfile`
- Status: bewezen (T-105; gemeten op 2026-10-18; met Trivy 0.76.0 T-110, gemeten op 2026-10-19)
- Sinds: 29e42cc; pip uit de image sinds b31d334; op de SBoM sinds 1d6f21a; Trivy 0.76.0 sinds bc6c669; ook zonder oplossing sinds e6a3888

### MIT-36 Een SBoM van elke image
- Houdt tegen: MC-11 stap 1 en 3, deels: zonder lijst weet je niet of een nieuw lek in jouw image zit
- Wat: de workflow maakt bij elke build met Trivy 0.76.0 (tot bc6c669 0.75.0) een SBoM in CycloneDX (spec 1.7): alle onderdelen van de image, het besturingssysteem, de Debian-pakketten en de Python-pakketten. Alleen de lijst: volgens Trivy bevat `--format cyclonedx` standaard geen lekken, en VEX komt er niet in. Het hoofdonderdeel heet naar de image en de commit. De SBoM blijft 90 dagen bij de run (een artifact), ook als de scan daarna een lek vindt, en de scan van MIT-35 leest juist die SBoM. Trivy leest de image als tar-bestand, zonder de Docker-socket, dus kan het de image die gepusht wordt niet veranderen (T-106)
- Waar: de stappen SBoM maken en `actions/upload-artifact` in `.github/workflows/image.yml`
- Status: bewezen (T-106; gemeten op 2026-10-18)
- Sinds: 1d6f21a

### MIT-37 Een mail bij een blokkade
- Houdt tegen: MC-28 stap 1, en de andere stappen voor zover ze een teller op slot zetten
- Wat: een log search alert op Azure kijkt elke 5 minuten of er in Log Analytics een `lockout_started` staat, en mailt dan de beheerder via een action group. Na een mail blijft de regel een uur stil, zodat één aanval niet elke 5 minuten een mail geeft. De regel leest met een eigen identiteit, die alleen Log Analytics Reader op de workspace is; zonder eigen identiteit leest een regel volgens Microsoft met de rechten van wie hem het laatst wijzigde. Het adres stelt `deployment.py azure` voor uit `az login` en staat niet in de repo. Vaker kijken kost meer (elke minuut €2,64 per maand in plaats van €1,32) en scheelt weinig, want een regel staat pas na een paar minuten in Log Analytics (T-107)
- Waar: `terraform/alerts.tf`; de vraag naar het adres in `run()` van `scripts/deploy_azure.py`
- Status: bewezen (T-107, T-108; gemeten op 2026-10-18)
- Sinds: c4ce459

### MIT-38 De Terraform-state: eigen sleutel, alleen via Entra ID
- Houdt tegen: MC-31 stap 3 en 4
- Wat: `scripts/azuresetup_v2.py` zet de state in een eigen storage account, versleuteld met een eigen RSA-4096-sleutel in een eigen Key Vault (purge protection, 90 dagen). Terraform logt in via Entra ID (`use_azuread_auth`). De beheerder heeft alleen Storage Blob Data Contributor, wat HashiCorp voor dit backend aanraadt; de identiteit van de opslag heeft alleen de rol om de sleutel te gebruiken. Accountsleutels staan uit, dus ook wie de sleutels mag opvragen, komt er zonder rol niet bij. Vorige versies blijven bewaard, en een verwijderde blob of container is 7 dagen terug te halen.
- Waar: `scripts/azuresetup_v2.py`; `use_azuread_auth = true` in `backend.conf`, die het script schrijft
- Status: bewezen (T-109; gemeten op 2026-10-18)
- Sinds: d51fb9f; minimale rollen en geen accountsleutels sinds e4d9e25

### MIT-39 De check bij elke pull request, verplicht op `main`
- Houdt tegen: MC-11 stap 1 en 3, nu al vóór de merge en niet pas vóór het publiceren; MC-30 stap 3, en stap 5 deels
- Wat: `.github/workflows/image.yml` draait bij elke pull request naar `main` de job `check`: dezelfde stappen als bij het publiceren (bouwen, de SBoM van MIT-36 en de scan van MIT-35), uit één definitie via YAML-ankers, maar alleen met `contents: read` en zonder te publiceren. Vanuit een fork geeft GitHub het token sowieso alleen leesrechten en geen secrets. Een ruleset op `main` maakt de check verplicht: een pull request is nodig, de check `check` moet slagen, en de bypass-lijst is leeg, ook voor de beheerder. Gekozen in deelvraag 1 van het onderzoek (SBoM in CI/CD): Trivy scoorde het hoogst in een labmeting en een benchmark op GitHub-runners; Syft met Grype liet met de standaardinstellingen de vier lekken van T-105 door. Aanleiding: op 19-10-2026 werd een testpull request met pip per ongeluk gemerged (pull request #2). De rem bij het publiceren hield de image tegen (run 39231439170), maar het lek stond wel op `main`, tot de revert 62b2b2e
- Waar: de job `check` in `.github/workflows/image.yml`; de ruleset "Beveiliging Ruleset" op `main` (Settings, Rules, Rulesets), die niet in de repo staat
- Status: bewezen (T-110, T-111, T-112; gemeten op 2026-10-19)
- Sinds: bc6c669; op `main` sinds 7a83161

### MIT-40 TLS op Azure, getoetst aan de richtlijnen van het NCSC
- Houdt tegen: MC-04 stap 1, op Azure; lokaal draait de app zonder TLS
- Wat: de ingress van Container Apps zet TLS voor de app (F-01); `allow_insecure_connections = false` stuurt HTTP met een 301 naar HTTPS, en de `Secure`-vlag (MIT-23) en HSTS (MIT-21) houden de browser daarna op HTTPS. Versies, ciphers en het certificaat kiest het platform; in `terraform/` staat daar niets over. Gemeten en getoetst aan de TLS-richtlijnen van het NCSC (versie 2025-05). Nergens Onvoldoende: alleen TLS 1.3 en 1.2, alleen AEAD-ciphers met ECDHE (forward secrecy), geen CBC en geen RSA-sleuteluitwisseling, geen compressie, geen renegotiation door de client en geen 0-RTT. Drie punten halen het hoogste niveau niet. Het certificaat heeft een RSA-sleutel van 2048 bits, wat de richtlijn sinds 2025 Uit te faseren noemt (3072 bits voor 128 bits sterkte). De sleuteluitwisseling is ECDHE (Voldoende), niet het hybride X25519MLKEM768 (Goed). En de server stuurt geen OCSP-antwoord mee, terwijl de richtlijn OCSP-stapling aanraadt als het kan (T-113)
- Waar: de ingress in `terraform/app.tf`; `HTTPS_ONLY` in de configuratie van de app
- Status: bewezen (T-113; gemeten op 2026-10-19)
- Sinds: 75c9967

### MIT-41 Triage met VEX: elk lek van HIGH of CRITICAL vraagt een beslissing
- Houdt tegen: MC-11 stap 1 en 3 als er nog geen oplossing is: zo'n lek gaat niet meer ongezien door
- Wat: de scan van MIT-35 laat `--ignore-unfixed` los en leest `vex/openvex.json` (OpenVEX 0.2.0). Elke melding van HIGH of CRITICAL stopt de job, tenzij de VEX voor dat pakket en die versie zegt dat de image niet geraakt wordt, met de reden erbij. De triageflow in `vex/README.md` zegt hoe je beslist: bijwerken, weghalen, afschermen, of een verklaring; een lek in CISA KEV, of met een EPSS-score van 0,1 of hoger, gaat voor. Op de image van 368a30d: 44 meldingen van HIGH, 8 lekken, geen in KEV, en een EPSS-score van hooguit 0,005. Bij 5 zit de lekke code niet in de image of draait hij nooit; bij de 3 in mount houdt een maatregel het tegen (MIT-42) (T-114). OpenVEX, geen CycloneDX-VEX: die wijst naar het `serialNumber` van één SBoM, en dat is bij elke build anders (T-114). Trivy filtert ook een `not_affected` zonder reden weg, en een verklaring zonder versie geldt voor elke versie (T-115). Daarom controleert een stap met jq vóór de scan dat elke verklaring een geldige justification en een uitleg heeft, of bij `affected` een actie, en een PURL met versie (T-116). De weggefilterde meldingen staan apart in de log (`--show-suppressed`). Gekozen in deelvraag 2 van het onderzoek (SBoM in CI/CD)
- Waar: `vex/openvex.json` en `vex/README.md`; de stappen VEX controleren en Scannen op bekende lekken in `.github/workflows/image.yml`
- Status: bewezen (T-114 tot T-116 lokaal, T-117 bij pull request #14; gemeten op 2026-10-19)
- Sinds: e6a3888

### MIT-42 Geen setuid- of setgid-bits in de image
- Houdt tegen: MC-14 stap 3
- Wat: de Dockerfile haalt na `useradd` van elk programma de setuid- en setgid-bit weg (`find / -xdev -type f -perm /6000 -exec chmod a-s {} +`). Ervoor waren het er 11, waaronder mount, su en passwd (T-114); erna 0, de app draait als `app`, en de regressietest slaagt (T-116). Zo draait mount met de rechten van `app`, niet als root, en dat dekt de drie lekken in mount af die de scan vond (MIT-41). Aanleiding: de triage van deelvraag 2
- Waar: de `RUN` met `useradd` in `app/Dockerfile`
- Status: bewezen (T-116; gemeten op 2026-10-19)
- Sinds: e6a3888

### MIT-43 psycopg met de libpq van Debian, zonder meegeleverde bibliotheken
- Houdt tegen: MC-11 stap 5, deels: de bibliotheken die psycopg-binary zelf meenam
- Wat: psycopg 3.3.6 zonder binary, in pure Python, met `libpq5` 17.11 uit Debian, vast op versie. Daarvoor nam psycopg-binary 15 eigen bibliotheken mee, gebouwd op manylinux2014 (CentOS 7, sinds 30-06-2024 end-of-life), onder andere PCRE 8.32 van 2012 en een eigen OpenSSL 3.5.8; de app laadde ze allemaal, en de scan zag ze niet (T-118). Nu laadt de app 62 bestanden in plaats van 70: 27 uit 20 Debian-pakketten (eerst 11), 32 van Python zelf en 3 uit de Python-pakketten, met 2 in plaats van 3 kopieën van OpenSSL. De image is 155,0 MB in plaats van 171,5. De scan vindt 83 lekken in plaats van 71, maar geen nieuwe van HIGH, en de rem slaagt met de VEX zoals hij is; de securitytest slaagt met beide, 182 controles (T-121). De prijs: psycopg in pure Python is trager, vooral bij veel rijen (200 keer 1000 rijen: 1228 ms tegen 211 ms), terwijl een pagina van de app maar een paar rijen ophaalt (T-122). Gekozen na deelvraag 3 van het onderzoek
- Waar: `app/requirements.txt`; de `RUN` met `apt-get install` in `app/Dockerfile`
- Status: bewezen (T-121, T-122; gemeten op 2026-10-19; in de pipeline T-124, gemeten op 2026-10-20). TLS naar de database op Azure (`verify-full`, `sslrootcert=system`) met de libpq van Debian is nog niet gemeten; dat gebeurt bij de volgende uitrol
- Sinds: 7790a40
