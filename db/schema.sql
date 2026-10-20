-- Runs automatically at the first start of an empty database volume
-- (see compose.yaml).

CREATE TABLE users (
    id         SERIAL PRIMARY KEY,
    username   TEXT UNIQUE NOT NULL,
    -- Argon2id hash with its own salt and the settings in it (MIT-19); the password itself is stored nowhere.
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Also in the session cookie. On logout, a new password or a
    -- change to the two-step verification it goes up; a cookie with an
    -- older version then no longer counts (MIT-09).
    session_version INTEGER NOT NULL DEFAULT 0,

    -- Two-step verification with TOTP (RFC 6238). The secret is set during the
    -- setup, but only counts once totp_enabled is true: that happens
    -- after a first valid code. The secret is stored encrypted (MIT-17).
    totp_secret       TEXT,
    totp_enabled      BOOLEAN NOT NULL DEFAULT false,
    -- The time step of the last accepted code. A code from the same or
    -- an earlier step is refused, so every code works only once (MIT-07).
    totp_last_step    BIGINT,
    -- SHA-256 of the recovery code (MIT-11); the code itself is stored nowhere.
    recovery_hash     TEXT
);

-- Attempt limits at login (MIT-06, MIT-10), see app/throttle.py. The key
-- is an HMAC of what is counted (IP address, account), so there are no
-- readable IP addresses or usernames here.
CREATE TABLE auth_throttle (
    key          TEXT PRIMARY KEY,
    failures     INTEGER NOT NULL DEFAULT 0,
    window_start TIMESTAMPTZ NOT NULL DEFAULT now(),
    locked_until TIMESTAMPTZ,
    -- How often this key has been locked: every next lockout lasts twice as long.
    lock_count   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE notes (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    -- Title and body encrypted with AES-256-GCM, bound to the owner (MIT-18).
    title      TEXT NOT NULL,
    body       TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Empty until the note is edited for the first time.
    updated_at TIMESTAMPTZ
);

-- The app logs in as this role, not as the owner (MIT-27): reading and writing in its
-- own tables, and nothing else. No creating or dropping tables, no roles, no
-- files or programs through COPY. db/app-password.sh (locally) or the schema job (Azure)
-- sets the password, so it is not in this file.
CREATE ROLE notes_app LOGIN;
GRANT SELECT, INSERT, UPDATE, DELETE ON users, notes, auth_throttle TO notes_app;
GRANT USAGE ON SEQUENCE users_id_seq, notes_id_seq TO notes_app;
