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
| T-02 | UC-02 | Inloggen met juist en fout wachtwoord; uitloggen en daarna `/` openen | 302 naar `/`; 401; 302 naar `/login` |
| T-03 | UC-02 | Als ingelogde gebruiker `/login` en `/register` openen | 302 naar `/` |
| T-04 | UC-03 | Notitie aanmaken, tonen, aanpassen, verwijderen | Na aanpassen staat "bewerkt" met tijd erbij; na verwijderen is hij weg |
| T-05 | UC-03 | Lege titel of inhoud bij aanmaken en bij aanpassen | Beide 400 met dezelfde foutmelding |
| T-06 | UC-03 | Tijd van een nieuwe notitie | Nederlandse tijd, niet UTC |
| T-07 | UC-02 | Begroeting om 05:59, 06:00, 11:59, 12:00, 17:59 en 18:00 | Goedenacht, Goedemorgen, Goedemorgen, Goedemiddag, Goedemiddag, Goedenavond, gevolgd door de gebruikersnaam |
| T-08 | UC-04 | Wachtwoord wijzigen: leeg, twee verschillende, geldig | 400; 400; daarna werkt het oude niet (401) en het nieuwe wel |
| T-09 | UC-05 | Account verwijderen | Inloggen geeft 401, de notities zijn weg, een tweede sessie van hetzelfde account geldt als uitgelogd |
| T-26 | UC-06 | `/account` openen als ingelogde gebruiker, en zonder in te loggen | Eigen gebruikersnaam, aanmaakdatum en aantal notities; zonder login 302 naar `/login` |

## Aanval

| ID | Dekt | Test | Nu | Na de mitigatie |
|----|------|------|----|-----------------|
| T-10 | MC-01 | Na registreren `users.password` uitlezen | Het wachtwoord staat er leesbaar | Een hash, niet terug te rekenen |
| T-11 | MC-02 | Gebruiker B opent, wijzigt en verwijdert een notitie van A via `/notes/<id>/edit` en `/delete` | Lukt | 404, notitie van A ongewijzigd |
| T-12 | MC-03 | 50 foute inlogpogingen achter elkaar op één account | Allemaal 401, geen vertraging of blokkade | Na een paar pogingen vertraagd of geblokkeerd |
| T-13 | MC-03 | Registreren of wijzigen naar wachtwoord `a` | Geaccepteerd | Geweigerd met uitleg |
| T-14 | MC-04 | Cookie kopiëren, uitloggen, gekopieerde cookie gebruiken | Werkt nog | 302 naar `/login` |
| T-15 | MC-04, MC-12 | Twee sessies; in de ene het wachtwoord wijzigen; de andere gebruiken | Werkt nog | De andere sessie is uitgelogd |
| T-16 | MC-05 | POST naar `/`, `/account/password` en `/account/delete` zonder token en met `Origin` van een andere site | Geaccepteerd (gemeten voor `/`) | Geweigerd (400 of 403) |
| T-17 | MC-06 | Inloggen met `' OR '1'='1` als gebruikersnaam en wachtwoord | 401 | 401 (blijft zo; dit is het bewijs voor MIT-02) |
| T-18 | MC-07 | Notitie met `<script>` opslaan en de pagina ophalen | Staat er als `&lt;script&gt;` | Idem, plus een CSP-header (bewijs voor MIT-01 en de tweede laag) |
| T-19 | MC-08 | Met de verbinding van de app `CREATE TABLE` en `DROP TABLE` uitvoeren | Lukt | Geweigerd: de app-rol mag alleen lezen en schrijven in zijn eigen tabellen |
| T-20 | MC-09 | Een bestaande en een nieuwe naam registreren, antwoorden vergelijken | Verschillend antwoord (409 en 302) | Vertraagd of beperkt na een aantal pogingen |
| T-21 | MC-10 | Een notitie van 5 MB sturen | 400, maar pas nadat de 5 MB is ingelezen (lokaal ongeveer 2,4 s) | 413, voordat het verzoek wordt ingelezen |
| T-22 | MC-11 | `pip freeze` in de image vergelijken met `requirements.txt`; image scannen | `pip freeze` gelijk; een scan is nog niet gedaan | Gelijk; de scan draait in CI en meldt bekende kwetsbaarheden |
| T-23 | MC-12 | Wachtwoord wijzigen zonder het huidige te kennen | Lukt | Geweigerd zonder het juiste huidige wachtwoord |
| T-24 | MC-13 | Account verwijderen met een `POST` zonder bevestiging en zonder wachtwoord | Lukt | Geweigerd zonder het juiste wachtwoord |
| T-25 | MC-14 | `whoami` in de app-container; de logs bij het starten | `root`; "WARNING: This is a development server" | Een gewone gebruiker; een productieserver zonder die waarschuwing |
| T-27 | MC-10 | Titel van 15 en 16 tekens, notitie van 250 en 251 tekens, bij aanmaken en aanpassen | 302, 400, 302, 400 | Idem; dit is het bewijs voor MIT-04 |
