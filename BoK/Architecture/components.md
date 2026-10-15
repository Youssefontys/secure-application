# Componenten en assets

## Componenten

| ID | Naam | Type | Doet | Sinds |
|----|------|------|------|-------|
| C-01 | Browser | Client (buiten ons beheer) | Toont de pagina's, voert de decoratieve JS uit (`cyber.js`, `account-menu.js`), bewaart de sessiecookie. | baseline |
| C-02 | Webapplicatie | Python 3.15 en Flask, Docker-container `app`, draait als root op de ontwikkelserver | Registreren, inloggen, notities aanmaken, tonen, aanpassen en verwijderen. Rendert de HTML (Jinja) en levert de statische bestanden. | baseline |
| C-03 | Database | PostgreSQL 18, Docker-container `db` | Bewaart gebruikers en notities. Draait `db/schema.sql` bij de eerste start. | baseline |
| C-04 | Databasevolume | Docker-volume `dbdata` | Bewaart de databasebestanden op de host. | baseline |

## Assets (wat beschermd moet worden)

| ID | Asset | Waar | Waarom gevoelig | Sinds |
|----|-------|------|-----------------|-------|
| A-01 | Wachtwoord | `users.password` (C-03), tijdelijk in het verzoek (C-02) | Geeft toegang tot het account; mensen hergebruiken het elders. Staat nu leesbaar. | baseline |
| A-02 | Notities (titel en inhoud) | `notes` (C-03) | Het doel van de applicatie; privé per gebruiker. Staat nu leesbaar. | baseline |
| A-03 | Sessiecookie | Browser (C-01) | Wie hem heeft, is die gebruiker. Een ondertekende Flask-cookie met `user_id`. | baseline |
| A-04 | Gebruikersnaam | `users.username` (C-03) | Identiteit; maakt gericht aanvallen mogelijk. | baseline |
| A-05 | Sessiesleutel (`FLASK_SECRET_KEY`) | Omgevingsvariabele van C-02 | Wie hem heeft, kan sessiecookies namaken. | baseline |
| A-06 | Databasewachtwoord (`POSTGRES_PASSWORD`) | Omgevingsvariabele van C-02 en C-03, `.env` | Geeft volledige toegang tot de database. | baseline |
