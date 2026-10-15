-- Draait automatisch bij de eerste start van een leeg databasevolume
-- (zie compose.yaml).

CREATE TABLE users (
    id         SERIAL PRIMARY KEY,
    username   TEXT UNIQUE NOT NULL,
    -- Het wachtwoord staat leesbaar opgeslagen (MC-01).
    password   TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Staat ook in de sessiecookie. Bij uitloggen, een nieuw wachtwoord of een
    -- wijziging aan de tweestapsverificatie gaat hij omhoog; een cookie met een
    -- oudere versie telt dan niet meer (MIT-09).
    session_version INTEGER NOT NULL DEFAULT 0,

    -- Tweestapsverificatie met TOTP (RFC 6238). Het geheim wordt bij het
    -- instellen gezet, maar telt pas mee als totp_enabled true is: dat gebeurt
    -- na een eerste geldige code. Het geheim staat leesbaar opgeslagen (MC-17).
    totp_secret       TEXT,
    totp_enabled      BOOLEAN NOT NULL DEFAULT false,
    -- De tijdstap van de laatst geaccepteerde code. Een code van dezelfde of
    -- een eerdere stap wordt geweigerd, dus elke code werkt maar één keer (MIT-07).
    totp_last_step    BIGINT,
    -- Foute codes op rij, en tot wanneer de codestap op slot zit (MIT-06).
    totp_failures     INTEGER NOT NULL DEFAULT 0,
    totp_locked_until TIMESTAMPTZ
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
