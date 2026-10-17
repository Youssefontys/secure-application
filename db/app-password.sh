#!/bin/sh
# Zet het wachtwoord van de app-rol uit schema.sql (MIT-27), bij de eerste start van een leeg volume.
# psql vult :'password' in als letterlijke tekst, dus het wachtwoord kan nooit als SQL worden gelezen.
psql -v ON_ERROR_STOP=1 -v password="$APP_DB_PASSWORD" --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
ALTER ROLE notities_app PASSWORD :'password';
SQL
