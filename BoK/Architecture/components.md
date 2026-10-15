# Componenten en assets

## Componenten

| ID | Naam | Type | Doet | Sinds |
|----|------|------|------|-------|
| C-01 | Browser | Client (buiten ons beheer) | Toont de pagina's, voert de JS uit (`cyber.js` decoratief, `account-menu.js` voor het menu, `forms.js` voor de bevestiging bij verwijderen en de grijze opslaanknop), bewaart de sessiecookie. | baseline |
| C-02 | Webapplicatie | Python 3.15 en Flask, Docker-container `app`, draait als root op de ontwikkelserver | Registreren, inloggen, een profielpagina tonen, wachtwoord wijzigen, account verwijderen, notities aanmaken, tonen, aanpassen en verwijderen. Begroet de gebruiker met naam. Rendert de HTML (Jinja) en levert de statische bestanden. | baseline |
| C-03 | Database | PostgreSQL 18, Docker-container `db` | Bewaart gebruikers en notities. Draait `db/schema.sql` bij de eerste start. | baseline |
| C-04 | Databasevolume | Docker-volume `dbdata` | Bewaart de databasebestanden op de host. | baseline |

## Assets (wat beschermd moet worden)

| ID | Asset | Waar | Waarom gevoelig | Sinds |
|----|-------|------|-----------------|-------|
| A-01 | Wachtwoord | `users.password` (C-03), tijdelijk in het verzoek (C-02) | Geeft toegang tot het account; mensen hergebruiken het elders. Staat nu leesbaar. | baseline |
| A-02 | Notities (titel en inhoud) | `notes` (C-03) | Het doel van de applicatie; privé per gebruiker. Staat nu leesbaar. | baseline |
| A-03 | Sessiecookie | Browser (C-01) | Wie hem heeft, is die gebruiker. Een ondertekende (niet versleutelde) Flask-cookie met `user_id` en, tot ze getoond zijn, de meldingen van `flash()`. | baseline |
| A-04 | Gebruikersnaam | `users.username` (C-03), de begroeting en de profielpagina (F-02) | Identiteit; maakt gericht aanvallen mogelijk. | baseline |
| A-05 | Sessiesleutel (`FLASK_SECRET_KEY`) | Omgevingsvariabele van C-02 | Wie hem heeft, kan sessiecookies namaken. | baseline |
| A-06 | Databasewachtwoord (`POSTGRES_PASSWORD`) | Omgevingsvariabele van C-02 en C-03, `.env` | Geeft volledige toegang tot de database. | baseline |
