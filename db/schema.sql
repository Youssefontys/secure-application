-- Baseline: alleen wat nodig is om te werken. Draait automatisch bij de
-- eerste start van een leeg databasevolume.

CREATE TABLE users (
    id         SERIAL PRIMARY KEY,
    username   TEXT UNIQUE NOT NULL,
    -- BASELINE: het wachtwoord staat leesbaar in de database. Dit is bewust
    -- het beginpunt, zie BoK/Threat Analysis (MC-01).
    password   TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE notes (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title      TEXT NOT NULL,
    body       TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Leeg tot de notitie voor het eerst wordt aangepast.
    updated_at TIMESTAMPTZ
);
