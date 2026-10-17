-- Draait automatisch bij de eerste start van een leeg databasevolume
-- (zie compose.yaml).

CREATE TABLE users (
    id         SERIAL PRIMARY KEY,
    username   TEXT UNIQUE NOT NULL,
    -- Argon2id-hash met eigen salt en de instellingen erin (MIT-19); het wachtwoord zelf staat nergens.
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Staat ook in de sessiecookie. Bij uitloggen, een nieuw wachtwoord of een
    -- wijziging aan de tweestapsverificatie gaat hij omhoog; een cookie met een
    -- oudere versie telt dan niet meer (MIT-09).
    session_version INTEGER NOT NULL DEFAULT 0,

    -- Tweestapsverificatie met TOTP (RFC 6238). Het geheim wordt bij het
    -- instellen gezet, maar telt pas mee als totp_enabled true is: dat gebeurt
    -- na een eerste geldige code. Het geheim staat versleuteld opgeslagen (MIT-17).
    totp_secret       TEXT,
    totp_enabled      BOOLEAN NOT NULL DEFAULT false,
    -- De tijdstap van de laatst geaccepteerde code. Een code van dezelfde of
    -- een eerdere stap wordt geweigerd, dus elke code werkt maar één keer (MIT-07).
    totp_last_step    BIGINT,
    -- SHA-256 van de herstelcode (MIT-11); de code zelf wordt nergens bewaard.
    recovery_hash     TEXT
);

-- Poginglimieten bij inloggen (MIT-06, MIT-10), zie app/throttle.py. De sleutel
-- is een HMAC van wat er geteld wordt (IP-adres, account), dus hier staan geen
-- leesbare IP-adressen of gebruikersnamen.
CREATE TABLE auth_throttle (
    key          TEXT PRIMARY KEY,
    failures     INTEGER NOT NULL DEFAULT 0,
    window_start TIMESTAMPTZ NOT NULL DEFAULT now(),
    locked_until TIMESTAMPTZ,
    -- Hoe vaak deze sleutel al op slot ging: elke volgende blokkade duurt twee keer zo lang.
    lock_count   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE notes (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    -- Titel en inhoud versleuteld met AES-256-GCM, gebonden aan de eigenaar (MIT-18).
    title      TEXT NOT NULL,
    body       TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Leeg tot de notitie voor het eerst wordt aangepast.
    updated_at TIMESTAMPTZ
);
