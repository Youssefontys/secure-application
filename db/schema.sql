-- Draait automatisch bij de eerste start van een leeg databasevolume
-- (zie compose.yaml).

CREATE TABLE users (
    id         SERIAL PRIMARY KEY,
    username   TEXT UNIQUE NOT NULL,
    -- Het wachtwoord staat leesbaar opgeslagen (MC-01).
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
