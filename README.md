# Secure application

Professional application for the Yellow Teaming (Security Engineering) specialisation, Fontys ICT semester 6 (Cyber Security Advanced, 2627nj).

## What this is

A small notes application that started as a **deliberately insecure baseline** and gets security features one at a time. The baseline only did what is needed to be functional: register, log in, change the password, delete the account, and create, edit and delete notes, with plain-text passwords, no CSRF protection, no rate limiting and no ownership check on notes. What has been added since is under Status.

Every feature that is added has an entry in `BoK/`: the use case, the misuse case it answers and the mitigation, written at the moment it is built. We build first and write the analysis alongside, not the other way around. The first version of this application (more complete, with Argon2, 2FA, Vault encryption and rate limiting) is in [BOK-SECENGINEER](https://github.com/Youssefontys/BOK-SECENGINEER) and is used as a reference for what to add next.

## Structure

- `app/` - the notes application, one file per part: `app.py` creates the app, `db.py` talks to the database, `auth.py` handles logging in (including the second step), `account.py` the profile, `notes.py` the notes, `totp.py` the TOTP calculation, `throttle.py` the login limits, `passwords.py` the rule for a new password and the Argon2id hashing, `encryption.py` the encryption of the TOTP secret and the notes, `csrf.py` the CSRF token of every form. The website (HTML, CSS, JS) is in `app/web/`
- `db/` - the database schema, run by the database container on first start
- `BoK/Architecture/` - components, data flows, trust boundaries and the authentication and authorization points
- `BoK/Threat Analysis/` - use cases, misuse cases, mitigations, attack trees and the tests that go with them
- `BoK/Subjects/` - per BoK subject (week) what was built, why it is safe and what it does not solve
- `compose.yaml` - app and database for local use, with scanner profiles in comments
- `scripts/` - `setup.py` to deploy (locally now, Azure follows), and the Terraform state bootstrap scripts imported from BOK-SECENGINEER
- `terraform/` - Azure: Container Apps, PostgreSQL B1ms in a private network and Key Vault; secrets stay out of the Terraform state. Not deployed yet

## Requirements

- **Locally:** Docker with Compose v2, and Python 3 for `scripts/setup.py`.
- **Azure:** an Azure subscription in which you may create resources and role assignments, the Azure CLI, Terraform 1.11 or newer, Python 3, and Docker to build the image. The GitHub CLI (`gh`) is optional, for the pipeline secrets.

`setup.py` checks these first and names what is missing.

## Run it

```sh
python scripts/setup.py
```

It asks where to deploy (local or Azure) and whether to turn on the hackstand for the hacking week, with a class behind one school address. Locally it creates missing secrets in `.env` and starts the stack; Azure does not deploy automatically yet, so it prints the exact steps. With `python scripts/setup.py lokaal` and no terminal (as in CI) it asks nothing and keeps what is in `.env`. On Linux or macOS the command is often `python3`; the script works the same on Windows and Linux.

Or by hand: copy `.env.example` to `.env`, fill in the four values, and run `docker compose up --build`.

Had the stack running before the app got its own database role? The role is only created in an empty volume, so run `docker compose down -v` first. That deletes the local data.

Then open http://127.0.0.1:5000.

## Status

The baseline plus the first security features, each with an entry in `BoK/Threat Analysis/entries.md`:

- pinned dependencies (MIT-03) and a length limit on notes (MIT-04)
- mandatory two-step verification with TOTP, a recovery code for a lost phone, login limits per IP address and per account, and a session version that ends old sessions (MIT-05 to MIT-12); see `BoK/Subjects/Week 5 Authentication.md`
- a rule of 12 to 64 characters for a new password (MIT-13), and a forgotten-password route that uses the recovery code and the app code (MIT-14)
- an ownership check on every note (MIT-15), and the current password before changing it or deleting the account (MIT-16)
- the TOTP secret and the notes encrypted with AES-256-GCM, with the key outside the database (MIT-17, MIT-18), and passwords hashed with Argon2id (MIT-19); see `BoK/Subjects/Week 6 Encryption.md`
- a hackstand for the hacking week, off by default (MIT-10)
- a CSRF token on every form, strict security headers, input and configuration checks, every route closed by default, safe failure, gunicorn as an unprivileged user, and an own database role that can only read and write the app's tables (MIT-20 to MIT-27); see `BoK/Subjects/Week 7 Application Security.md`

Still open: security events are not logged yet, the database role can still change every row the app can (MC-08), and the data key is read from `.env` until Key Vault on Azure (MC-22). Not deployed yet.
