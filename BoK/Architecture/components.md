# Componenten en assets

## Componenten

| ID | Naam | Type | Doet | Sinds |
|----|------|------|------|-------|
| C-01 | Browser | Client (buiten ons beheer) | Toont de pagina's, voert de JS uit (`cyber.js` decoratief, `account-menu.js` voor het menu, `forms.js` voor de bevestiging bij verwijderen en de grijze opslaanknop), bewaart de sessiecookie. | baseline |
| C-02 | Webapplicatie | Python 3.15 en Flask, Docker-container `app`, draait als root op de ontwikkelserver | Registreren, inloggen met wachtwoord en een code uit een authenticator-app (verplicht), tweestapsverificatie instellen en opnieuw instellen, inloggen met een herstelcode, een vergeten wachtwoord opnieuw instellen met herstelcode en code uit de app, een profielpagina tonen, wachtwoord wijzigen, account verwijderen, notities aanmaken, tonen, aanpassen en verwijderen. Begroet de gebruiker met naam. Rendert de HTML (Jinja) en levert de statische bestanden. | baseline |
| C-03 | Database | PostgreSQL 18, Docker-container `db` | Bewaart gebruikers, notities en de tellers van de poginglimieten (`auth_throttle`, met HMAC's als sleutel; tellers waarvan venster en blokkade een dag voorbij zijn, gaan bij een nieuwe blokkade weg). Draait `db/schema.sql` bij de eerste start. | baseline |
| C-04 | Databasevolume | Docker-volume `dbdata` | Bewaart de databasebestanden op de host. | baseline |

## Assets (wat beschermd moet worden)

| ID | Asset | Waar | Waarom gevoelig | Sinds |
|----|-------|------|-----------------|-------|
| A-01 | Wachtwoord | `users.password` (C-03), tijdelijk in het verzoek (C-02) | Geeft toegang tot het account; mensen hergebruiken het elders. Staat nu leesbaar. Een nieuw wachtwoord moet 12 tot 64 tekens zijn (MIT-13). | baseline |
| A-02 | Notities (titel en inhoud) | `notes` (C-03) | Het doel van de applicatie; privé per gebruiker. Staat nu leesbaar. | baseline |
| A-03 | Sessiecookie | Browser (C-01) | Wie hem heeft, is die gebruiker. Een ondertekende (niet versleutelde) Flask-cookie met `user_id` en de sessieversie (`session_version`); tijdens een halve login `pending_user_id`, `pending_version` en `pending_since`; en, tot ze getoond zijn, de meldingen van `flash()`. | baseline |
| A-04 | Gebruikersnaam | `users.username` (C-03), de begroeting en de profielpagina (F-02) | Identiteit; maakt gericht aanvallen mogelijk. | baseline |
| A-05 | Sessiesleutel (`FLASK_SECRET_KEY`) | Omgevingsvariabele van C-02 | Wie hem heeft, kan sessiecookies namaken. Hij is ook de sleutel van de HMAC's in `auth_throttle`: wie hem heeft, kan door te proberen achterhalen bij welk IP-adres of welke naam een teller hoort. Een nieuwe sleutel maakt alle sessies en alle tellers ongeldig. | baseline |
| A-06 | Databasewachtwoord (`POSTGRES_PASSWORD`) | Omgevingsvariabele van C-02 en C-03, `.env` | Geeft volledige toegang tot de database. | baseline |
| A-07 | TOTP-geheim | `users.totp_secret` (C-03), en tijdens het instellen als tekst en QR-code in de browser (F-02) | Wie het heeft, kan zelf geldige codes maken; dan valt de tweede factor weg. Staat leesbaar in de database. | 18e1424 |
| A-08 | Herstelcode | `users.recovery_hash` (C-03): alleen de SHA-256; de code zelf één keer in de browser, na het aanzetten, na het vervangen en na een nieuw wachtwoord via wachtwoord vergeten (F-02) | Samen met het wachtwoord kan iemand er zonder de telefoon mee inloggen, en daarmee gaat de tweede factor uit. Samen met een code uit de app stelt iemand er een nieuw wachtwoord mee in (AU-08). | dc7d258 |
