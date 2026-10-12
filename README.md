# Secure application

Professional application for the Yellow Teaming (Security Engineering) specialisation, Fontys ICT semester 6 (Cyber Security Advanced, 2627nj).

## What this is

A small notes application that starts as a **deliberately insecure baseline** and gets security features one at a time. The baseline only does what is needed to be functional: register, log in, and create, edit and delete notes. Passwords are stored in plain text, there is no CSRF protection, no rate limiting and no ownership check on notes.

Every feature that is added has an entry in `BoK/`: the use case, the misuse case it answers and the mitigation, written at the moment it is built. We build first and write the analysis alongside, not the other way around. The first version of this application (more complete, with Argon2, 2FA, Vault encryption and rate limiting) is in [BOK-SECENGINEER](https://github.com/Youssefontys/BOK-SECENGINEER) and is used as a reference for what to add next.

## Structure

- `app/` - the notes application: Python code in `app/`, the website (HTML, CSS, JS) in `app/web/`
- `BoK/Architecture/` - components, data flows, trust boundaries and the authentication and authorization points
- `BoK/Threat Analysis/` - use cases, misuse cases, mitigations and attack trees
- `compose.yaml` - app and database for local use

## Run it

```sh
cp .env.example .env     # fill in two values
docker compose up --build
```

Then open http://127.0.0.1:5000.

## Status

Baseline only. Not safe to expose to the internet.
