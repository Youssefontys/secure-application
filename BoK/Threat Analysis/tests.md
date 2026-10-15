# Tests

Mogelijke tests per use case en misuse case. Nog niet gebouwd; dit is de
lijst om ze uit te bouwen.

Twee soorten:

- **Functioneel (UC):** de normale werking. Moet altijd slagen, ook na elke
  security-feature. Zo zie je wanneer een maatregel iets breekt.
- **Aanval (MC):** laat zien dat de aanval nu werkt. Komt er een mitigatie,
  dan draait de verwachting om. Slaagt de test met de nieuwe verwachting, dan
  mag de mitigatie op `bewezen`.

ID's: `T-`, nooit hergebruiken. Kolom "Nu" is met de hand gemeten op
2026-10-15 met curl tegen de lokale stack, behalve waar iets anders staat.

## Functioneel

| ID | Dekt | Test | Verwacht |
|----|------|------|----------|
| T-01 | UC-01 | Registreren met een nieuwe naam; dezelfde naam nog een keer | 302 naar `/login` met melding; daarna 409 |
| T-02 | UC-02 | Inloggen met juist en fout wachtwoord; uitloggen en daarna `/` openen | Na de code 302 naar `/` (T-29); 400; 302 naar `/login` |
| T-03 | UC-02 | Als ingelogde gebruiker `/login` en `/register` openen | 302 naar `/` |
| T-04 | UC-03 | Notitie aanmaken, tonen, aanpassen, verwijderen | Na aanpassen staat "bewerkt" met tijd erbij; na verwijderen is hij weg |
| T-05 | UC-03 | Lege titel of inhoud bij aanmaken en bij aanpassen | Beide 400 met dezelfde foutmelding |
| T-06 | UC-03 | Tijd van een nieuwe notitie | Nederlandse tijd, niet UTC |
| T-07 | UC-02 | Begroeting om 05:59, 06:00, 11:59, 12:00, 17:59 en 18:00 | Goedenacht, Goedemorgen, Goedemorgen, Goedemiddag, Goedemiddag, Goedenavond, gevolgd door de gebruikersnaam |
| T-08 | UC-04 | Wachtwoord wijzigen: leeg, twee verschillende, geldig | 400; 400; daarna werkt het oude niet (400) en het nieuwe wel |
| T-09 | UC-05 | Account verwijderen | Inloggen geeft 400, de notities zijn weg, een tweede sessie van hetzelfde account geldt als uitgelogd |
| T-26 | UC-06 | `/account` openen als ingelogde gebruiker, en zonder in te loggen | Eigen gebruikersnaam, aanmaakdatum en aantal notities; zonder login 302 naar `/login` |
| T-28 | UC-07 | Tweestapsverificatie instellen: foute code, juiste code, daarna de QR-code opvragen; opnieuw instellen met foute en juiste code | 400; aan, met herstelcode; QR-code 404; 400; naar het instellen |
| T-29 | UC-02 | Inloggen met een account met tweestapsverificatie, en met een account zonder | Met: na het wachtwoord naar `/login/2fa`, na de code naar `/`. Zonder: na het wachtwoord naar `/account/2fa` (MIT-12) |
| T-44 | UC-08 | Met wachtwoord en herstelcode inloggen (ook met hoofdletters, spaties en streepjes) | Naar `/account/2fa` met de melding dat de herstelcode is gebruikt; tweestapsverificatie moet opnieuw worden ingesteld |
| T-45 | UC-07 | Een nieuwe herstelcode maken met een foute en met een juiste code uit de app | 400; daarna een nieuwe code, en de vorige werkt niet meer |

## Aanval

| ID | Dekt | Test | Nu | Na de mitigatie |
|----|------|------|----|-----------------|
| T-10 | MC-01 | Na registreren `users.password` uitlezen | Het wachtwoord staat er leesbaar | Een hash, niet terug te rekenen |
| T-11 | MC-02 | Gebruiker B opent, wijzigt en verwijdert een notitie van A via `/notes/<id>/edit` en `/notes/<id>/delete` | Lukt | 404, notitie van A ongewijzigd |
| T-12 | MC-03 | Foute wachtwoorden achter elkaar op één account | De 5e geeft 429 met `Retry-After: 900`: een blokkade van 15 minuten; ook het juiste wachtwoord wordt dan geweigerd (sinds MIT-10) | Idem; dit is het bewijs voor MIT-10 |
| T-13 | MC-03 | Registreren of wijzigen naar wachtwoord `a` | Geaccepteerd | Geweigerd met uitleg |
| T-14 | MC-04 | Cookie kopiëren, uitloggen, gekopieerde cookie gebruiken | 302 naar `/login` met de melding "Je sessie is niet meer geldig" (sinds MIT-09) | Idem; dit is het bewijs voor MIT-09 |
| T-15 | MC-04, MC-12 | Twee sessies; in de ene het wachtwoord wijzigen; de andere gebruiken | De andere sessie is uitgelogd, de eigen blijft ingelogd (sinds MIT-09) | Idem |
| T-16 | MC-05 | POST naar `/`, `/account/password` en `/account/delete` zonder token en met `Origin` van een andere site | Geaccepteerd (gemeten voor `/`) | Geweigerd (400 of 403) |
| T-17 | MC-06 | Inloggen met `' OR '1'='1` als gebruikersnaam en wachtwoord | 400 | 400 (blijft zo; dit is het bewijs voor MIT-02) |
| T-18 | MC-07 | Notitie met `<script>` opslaan en de pagina ophalen | Staat er als `&lt;script&gt;` | Idem, plus een CSP-header (bewijs voor MIT-01 en de tweede laag) |
| T-19 | MC-08 | Met de verbinding van de app `CREATE TABLE` en `DROP TABLE` uitvoeren | Lukt | Geweigerd: de app-rol mag alleen lezen en schrijven in zijn eigen tabellen |
| T-20 | MC-09 | Een bestaande en een nieuwe naam registreren, antwoorden vergelijken | Verschillend antwoord (409 en 302) | Vertraagd of beperkt na een aantal pogingen |
| T-21 | MC-10 | Een notitie van 5 MB sturen | 400, maar pas nadat de 5 MB is ingelezen (lokaal ongeveer 2,4 s) | 413, voordat het verzoek wordt ingelezen |
| T-22 | MC-11 | `pip freeze` in de image vergelijken met `requirements.txt`; image scannen | `pip freeze` gelijk; een scan is nog niet gedaan | Gelijk; de scan draait in CI en meldt bekende kwetsbaarheden |
| T-23 | MC-12 | Wachtwoord wijzigen zonder het huidige te kennen | Lukt | Geweigerd zonder het juiste huidige wachtwoord |
| T-24 | MC-13 | Account verwijderen met een `POST` zonder bevestiging en zonder wachtwoord | Lukt | Geweigerd zonder het juiste wachtwoord |
| T-25 | MC-14 | `whoami` in de app-container; de logs bij het starten | `root`; "WARNING: This is a development server" | Een gewone gebruiker; een productieserver zonder die waarschuwing |
| T-27 | MC-10 | Titel van 15 en 16 tekens, notitie van 250 en 251 tekens, bij aanmaken en aanpassen | 302, 400, 302, 400 | Idem; dit is het bewijs voor MIT-04 |
| T-30 | MC-15 | Na het wachtwoord 5 foute codes, daarna de juiste code, ook vanuit een nieuwe sessie; daarna nog twee keer 5 fouten na het verlopen van de blokkade | 5e fout: 429 met `Retry-After: 900`, 15 minuten op slot, de juiste code geweigerd, ook in de nieuwe sessie; daarna 30 en 60 minuten | Idem; dit is het bewijs voor MIT-06 |
| T-31 | MC-16 | Een geaccepteerde code nog eens gebruiken, en twee gelijktijdige verzoeken met dezelfde nieuwe code | Geweigerd; van de twee komt er precies één binnen | Idem; dit is het bewijs voor MIT-07 |
| T-32 | MC-03 | Met alleen het juiste wachtwoord van een account met tweestapsverificatie naar `/`, `/account` en een notitie aanmaken | Alle drie 302 naar `/login` | Idem; dit is het bewijs voor MIT-05 |
| T-33 | MC-15 | Een halve login die ouder is dan 5 minuten | Weggegooid, naar `/login` met de melding "Dat duurde te lang" (gemeten met de testclient van Flask) | Idem |
| T-34 | MC-17 | `users.totp_secret` uitlezen | Het geheim staat leesbaar | Versleuteld |
| T-35 | MIT-05 | `totp.code_at` tegen de testvectoren van RFC 6238 bijlage B (SHA1, 8 cijfers) en RFC 4226 bijlage D | Alle 16 goed | Idem |
| T-36 | MC-17 | Headers van `/account/2fa` en `/account/2fa/qr.svg`; de QR-code opvragen nadat het instellen klaar is | `Cache-Control: no-store`; 404 | Idem; dit is het bewijs voor MIT-08 |
| T-37 | MC-04 | Een sessie van vóór het aanzetten van tweestapsverificatie gebruiken, nadat het in een andere sessie is aangezet | 302 naar `/login` | Idem; bewijs voor MIT-09 |
| T-38 | MC-12 | Halve login (alleen wachtwoord), dan in een andere sessie het wachtwoord wijzigen, dan de juiste code invullen | 302 naar `/login`: de halve login is vervallen | Idem; bewijs voor MIT-09 |
| T-39 | MC-03 | 20 foute wachtwoorden vanaf één adres, telkens voor een andere naam; daarna een bestaand account met het juiste wachtwoord | De 20e geeft 429 met `Retry-After: 900`; het bestaande account wordt vanaf dat adres ook geweigerd | Idem; bewijs voor MIT-10 |
| T-40 | MC-03 | Na een verlopen blokkade opnieuw 5 foute wachtwoorden, een paar keer achter elkaar | 15, 30, 60, 60 minuten | Idem |
| T-41 | MC-03 | Een paar foute wachtwoorden, dan een geslaagde login; daarna `auth_throttle` bekijken | De teller van het account is weg, die van het adres staat er nog | Idem |
| T-42 | MC-03 | De inhoud van `auth_throttle` doorzoeken op gebruikersnamen en IP-adressen | Alleen HMAC's, geen leesbare namen of adressen | Idem |
| T-43 | MC-18 | Een ander account vanaf hetzelfde adres terwijl één account geblokkeerd is; een onbekende naam fout invullen | Het andere account komt binnen; de onbekende naam krijgt dezelfde melding als een bestaande | Idem |
| T-46 | MC-19 | Een al gebruikte herstelcode nog eens; twee gelijktijdige verzoeken met dezelfde code | 400; van de twee komt er één binnen, de ander krijgt 400 | Idem; bewijs voor MIT-11 |
| T-47 | MC-19 | `users.recovery_hash` bekijken na het aanzetten | 64 tekens (SHA-256), niet gelijk aan de code | Idem |
| T-48 | MC-19 | 5 foute herstelcodes | De 5e geeft 429 met `Retry-After: 900`: een blokkade van 15 minuten | Idem |
| T-49 | MC-19 | Headers van de pagina's die de herstelcode tonen | `Cache-Control: no-store` | Idem |
| T-50 | MC-03 | Een account zonder tweestapsverificatie: na het wachtwoord naar `/`, `/account` en een notitie aanmaken | Alle drie 302 naar `/account/2fa` | Idem; bewijs voor MIT-12 |
| T-51 | MC-20 | Met alleen het wachtwoord van een account zonder tweestapsverificatie het instellen afmaken met een eigen app | Lukt | Geweigerd zonder een tweede kanaal (bijvoorbeeld een bevestigde e-mail) |
