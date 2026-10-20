#!/bin/sh
# Sets the password of the app role from schema.sql (MIT-27), at the first start of an empty volume.
# psql fills in :'password' as literal text, so the password can never be read as SQL.
psql -v ON_ERROR_STOP=1 -v password="$APP_DB_PASSWORD" --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
ALTER ROLE notes_app PASSWORD :'password';
SQL
