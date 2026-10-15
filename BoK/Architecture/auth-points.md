# Authenticatie- en autorisatiepunten

Authenticatie: vaststellen wie je bent. Autorisatie: vaststellen wat je mag.
Elk punt staat hier, ook als er (nog) geen controle zit. Een rij met
"ontbreekt" is een open risico en hoort bij een misuse case.

## Authenticatie

| ID | Punt | Onderdeel | Op datastroom | Wat wordt vastgesteld | Mechanisme | Status | Misuse case |
|----|------|-----------|---------------|-----------------------|------------|--------|-------------|
| AU-01 | Inloggen | C-02, route `/login` | F-01 | Dat de gebruiker de eigenaar van het account is | Gebruikersnaam en wachtwoord worden in SQL vergeleken met de leesbaar opgeslagen waarde. Poginglimiet (MIT-10): 20 fouten per IP-adres of 5 per account vanaf één adres in 15 minuten, daarna een blokkade van 15 minuten die verdubbelt tot een uur. Het IP-adres is `request.remote_addr`; achter een proxy is dat het adres van de proxy. Staat tweestapsverificatie aan, dan is dit alleen de eerste factor en geeft een juist wachtwoord een halve login (AU-05) | gebouwd, zwak | MC-01, MC-03 |
| AU-02 | Sessie bij elk verzoek | C-02, alle routes behalve `/login`, `/login/2fa`, `/login/recover` en `/register` | F-01 | Dat het verzoek bij een eerder ingelogde gebruiker hoort | `login_required` op elke route. `load_user` haalt bij elk verzoek de gebruiker bij `session["user_id"]` uit de database, dus een sessie van een verwijderd account telt niet meer. De sessieversie in de cookie moet gelijk zijn aan `users.session_version`; uitloggen, een nieuw wachtwoord en tweestapsverificatie aan- of uitzetten verhogen die, zodat oudere cookies (ook kopieën) niet meer werken. Een halve login (`pending_user_id`, na alleen het wachtwoord) telt niet als ingelogd. Geen eigen vervaltijd: zonder een van die gebeurtenissen werkt een cookie tot 31 dagen (de standaard van Flask) | gebouwd | MC-04 |
| AU-03 | Applicatie naar database | C-02 naar C-03 | F-03 | Dat de app de app is | Databasewachtwoord (A-06) in een omgevingsvariabele, rol is de eigenaar; geen TLS | gebouwd, zwak | MC-08 |
| AU-04 | Herauthenticatie bij gevoelige acties | C-02, routes `/account/password` en `/account/delete` | F-01 | Dat wie het wachtwoord wijzigt of het account verwijdert de eigenaar is, en niet alleen iemand met zijn sessie | Geen: alleen de sessie (AU-02) telt, het huidige wachtwoord wordt niet gevraagd. De bevestiging bij verwijderen (`forms.js`) is gebruiksgemak in de browser, geen controle | **ontbreekt** | MC-12, MC-13 |
| AU-05 | Tweede factor bij inloggen | C-02, route `/login/2fa` | F-01 | Dat de gebruiker naast het wachtwoord ook het TOTP-geheim bezit | TOTP (RFC 6238): 6 cijfers, stappen van 30 seconden, één stap klokverschil. Elke code werkt één keer. Na 5 foute codes in 15 minuten zit deze stap voor het account op slot: 15 minuten, verdubbelend tot 24 uur (MIT-06). De halve login vervalt na 5 minuten. Alleen voor accounts die het hebben aangezet | gebouwd | MC-15, MC-16, MC-17 |
| AU-06 | Code bij uitzetten van tweestapsverificatie en bij een nieuwe herstelcode | C-02, routes `/account/2fa/disable` en `/account/2fa/recovery` | F-01 | Dat wie de tweede factor weghaalt of een nieuwe herstelcode maakt, de tweede factor ook bezit | Een geldige TOTP-code, met dezelfde controles als AU-05 | gebouwd | MC-12 |
| AU-07 | Herstelcode bij inloggen | C-02, route `/login/recover` | F-01 | Dat de gebruiker de herstelcode bezit, in plaats van de tweede factor | Alleen na het juiste wachtwoord (halve login). De SHA-256 van de ingevulde code wordt in constante tijd vergeleken met de opgeslagen hash. Werkt één keer: zet daarna tweestapsverificatie uit en verhoogt de sessieversie. 5 fouten in 15 minuten: blokkade van 15 minuten, verdubbelend tot 24 uur | gebouwd | MC-19 |

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
| AZ-08 | Profiel tonen | C-02, route `/account` | F-03 | Alleen het eigen profiel | `WHERE id = %s` met de id van de ingelogde gebruiker; er staat geen id in de URL om te veranderen | gebouwd | |
| AZ-09 | Tweestapsverificatie instellen en uitzetten | C-02, routes `/account/2fa/*` | F-03 | Alleen voor het eigen account | `WHERE id = %s` met de id van de ingelogde gebruiker; de QR-code alleen zolang het instellen loopt | gebouwd | |
