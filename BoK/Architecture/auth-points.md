# Authenticatie- en autorisatiepunten

Authenticatie: vaststellen wie je bent. Autorisatie: vaststellen wat je mag.
Elk punt staat hier, ook als er (nog) geen controle zit. Een rij met
"ontbreekt" is een open risico en hoort bij een misuse case.

## Authenticatie

| ID | Punt | Onderdeel | Op datastroom | Wat wordt vastgesteld | Mechanisme | Status | Misuse case |
|----|------|-----------|---------------|-----------------------|------------|--------|-------------|
| AU-01 | Inloggen | C-02, route `/login` | F-01 | Dat de gebruiker de eigenaar van het account is | Gebruikersnaam en wachtwoord worden in SQL vergeleken met de leesbaar opgeslagen waarde; één factor; geen limiet op pogingen | gebouwd, zwak | MC-01, MC-03 |
| AU-02 | Sessie bij elk verzoek | C-02, alle routes behalve `/login` en `/register` | F-01 | Dat het verzoek bij een eerder ingelogde gebruiker hoort | `login_required` op elke route. `load_user` haalt bij elk verzoek de gebruiker bij `session["user_id"]` uit de database, dus een sessie van een verwijderd account telt niet meer. Geen eigen vervaltijd (de standaard van Flask is 31 dagen); geen server-side intrekking: uitloggen of een wachtwoordwijziging maakt een gekopieerde cookie niet ongeldig | gebouwd, zwak | MC-04 |
| AU-03 | Applicatie naar database | C-02 naar C-03 | F-03 | Dat de app de app is | Databasewachtwoord (A-06) in een omgevingsvariabele, rol is de eigenaar; geen TLS | gebouwd, zwak | MC-08 |
| AU-04 | Herauthenticatie bij gevoelige acties | C-02, routes `/account/password` en `/account/delete` | F-01 | Dat wie het wachtwoord wijzigt of het account verwijdert de eigenaar is, en niet alleen iemand met zijn sessie | Geen: alleen de sessie (AU-02) telt, het huidige wachtwoord wordt niet gevraagd. De bevestiging bij verwijderen (`confirm.js`) is gebruiksgemak in de browser, geen controle | **ontbreekt** | MC-12, MC-13 |

## Autorisatie

| ID | Punt | Onderdeel | Op datastroom | Wat wordt toegestaan | Mechanisme | Status | Misuse case |
|----|------|-----------|---------------|----------------------|------------|--------|-------------|
| AZ-01 | Notities tonen | C-02, route `/` (GET) | F-03 | Alleen de notities van de ingelogde gebruiker | `WHERE user_id = %s` met de id uit de sessie | gebouwd | |
| AZ-02 | Notitie aanmaken | C-02, route `/` (POST) | F-03 | Alleen ingelogde gebruikers; de notitie krijgt de id uit de sessie | `user_id` uit de sessie, niet uit het formulier | gebouwd | MC-05 (CSRF) |
| AZ-03 | Notitie tonen en aanpassen | C-02, route `/notes/<id>/edit` | F-03 | Alleen de eigenaar van de notitie | Alleen "ingelogd?" wordt gecontroleerd, de eigenaar niet | **ontbreekt** | MC-02 |
| AZ-04 | Notitie verwijderen | C-02, route `/notes/<id>/delete` | F-03 | Alleen de eigenaar van de notitie | Alleen "ingelogd?" wordt gecontroleerd, de eigenaar niet | **ontbreekt** | MC-02 |
| AZ-05 | Databaserechten | C-03 | F-03 | Alleen wat de app echt nodig heeft | De app gebruikt de eigenaarrol: alle rechten, ook DDL en andere databases | **ontbreekt** | MC-08 |
| AZ-06 | Wachtwoord wijzigen | C-02, route `/account/password` (POST) | F-03 | Alleen het eigen wachtwoord | `UPDATE ... WHERE id = %s` met de id uit de sessie, niet uit het formulier | gebouwd | MC-05 (CSRF), MC-12 |
| AZ-07 | Account verwijderen | C-02, route `/account/delete` (POST) | F-03 | Alleen het eigen account | `DELETE ... WHERE id = %s` met de id van de ingelogde gebruiker; de notities gaan mee via `ON DELETE CASCADE` | gebouwd | MC-05 (CSRF), MC-13 |
