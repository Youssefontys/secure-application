# Secure application

Professional application for the Yellow Teaming (Security Engineering) specialisation, Fontys ICT semester 6 (Cyber Security Advanced, 2627nj).

## What this is

A small notes application that started as a **deliberately insecure baseline** and gets security features one at a time. The baseline only did what is needed to be functional: register, log in, change the password, delete the account, and create, edit and delete notes, with plain-text passwords, no CSRF protection, no rate limiting and no ownership check on notes. What has been added since is under Status.

Every feature that is added has an entry in `BoK/`: the use case, the misuse case it answers and the mitigation, written at the moment it is built. We build first and write the analysis alongside, not the other way around. The first version of this application (more complete, with Argon2, 2FA, Vault encryption and rate limiting) is in [BOK-SECENGINEER](https://github.com/Youssefontys/BOK-SECENGINEER) and is used as a reference for what to add next.

## Structure

- `app/` - the notes application, one file per part: `app.py` creates the app, `db.py` talks to the database, `auth.py` handles logging in (including the second step), `account.py` the profile, `notes.py` the notes, `totp.py` the TOTP calculation, `throttle.py` the login limits, `passwords.py` the rule for a new password. The website (HTML, CSS, JS) is in `app/web/`
- `db/` - the database schema, run by the database container on first start
- `BoK/Architecture/` - components, data flows, trust boundaries and the authentication and authorization points
- `BoK/Threat Analysis/` - use cases, misuse cases, mitigations, attack trees and the tests that go with them
- `BoK/Subjects/` - per BoK subject (week) what was built, why it is safe and what it does not solve
- `compose.yaml` - app and database for local use

## Run it

```sh
cp .env.example .env     # fill in two values
docker compose up --build
```

Then open http://127.0.0.1:5000.

## Status

The baseline plus the first security features, each with an entry in `BoK/Threat Analysis/entries.md`:

- pinned dependencies (MIT-03) and a length limit on notes (MIT-04)
- mandatory two-step verification with TOTP, a recovery code for a lost phone, login limits per IP address and per account, and a session version that ends old sessions (MIT-05 to MIT-12); see `BoK/Subjects/Week 5 Authentication.md`
- a rule of 12 to 64 characters for a new password (MIT-13), and a forgotten-password route that uses the recovery code and the app code (MIT-14)

Still open: passwords are stored in plain text, there is no CSRF protection and no ownership check on notes. Not safe to expose to the internet.
