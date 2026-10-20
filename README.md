# Secure application

Professional application for the Yellow Teaming (Security Engineering) specialisation, Fontys ICT semester 6 (Cyber Security Advanced, 2627nj).

## What this is

A small notes application that started as a **deliberately insecure baseline** and gets security features one at a time. The baseline only did what is needed to be functional: register, log in, change the password, delete the account, and create, edit and delete notes, with plain-text passwords, no CSRF protection, no rate limiting and no ownership check on notes. What has been added since is under Status.

Every feature that is added has an entry in `BoK/`: the use case, the misuse case it answers and the mitigation, written at the moment it is built. We build first and write the analysis alongside, not the other way around. The app, the code, the scripts and the tests are in English; the BoK is in Dutch, and so are the commit messages before 20 October 2026. The first version of this application, with Argon2, 2FA, Vault encryption and rate limiting, was BOK-SECENGINEER, now a private repository; it was the reference for what to add, and the subjects in `BoK/Subjects/` compare the two.

## Structure

- `app/` - the notes application, one file per part: `app.py` creates the app, `db.py` talks to the database, `auth.py` handles logging in (including the second step), `account.py` the profile, `notes.py` the notes, `totp.py` the TOTP calculation, `throttle.py` the login limits, `passwords.py` the rule for a new password and the Argon2id hashing, `encryption.py` the encryption of the TOTP secret and the notes, `csrf.py` the CSRF token of every form, `events.py` the security events in the log. The website (HTML, CSS, JS) is in `app/web/`
- `db/` - the database schema and the password of the app role, run by the database container on first start
- `BoK/Architecture/` - components, data flows, trust boundaries and the authentication and authorization points, with a diagram in `diagram/`
- `BoK/Threat Analysis/` - use cases, misuse cases, mitigations, attack trees, the tests that go with them, and a risk matrix (likelihood × impact, before and after the mitigations), with a use case diagram and misuse case diagrams in `diagrams/`
- `BoK/Subjects/` - per BoK subject (week) what was built, why it is safe and what it does not solve; `Standards.md` maps the app on the OWASP Top 10 Proactive Controls, ASVS 5.0, the CSA Cloud Controls Matrix and EN 40000, and `Laws.md` covers the AVG (with a self-assessment), NIS2 and the CRA
- `compose.yaml` - app and database for local use, and the ZAP baseline (DAST) under the profile `scan`, which the pipeline runs too: `docker compose --profile scan run --rm zap`
- `.github/dependabot.yml` - weekly update proposals for the pinned packages, images, Terraform providers and GitHub Actions
- `.github/workflows/CI-image.yml` - on every pull request to `main`, builds the image, makes its SBoM, scans it with the VEX and runs the security test, without publishing (the job `check`, required by a ruleset on `main`); on every push to `main`, does the same and then publishes the image to ghcr.io, tagged with the commit
- `.github/workflows/CD-azure.yml` - after Image succeeded on a push to `main` that changed `app/`, puts that image on Azure once you approve it, signed in through OIDC without a password or key in GitHub; it only changes the image of the container app
- `zap-rules.tsv` - the decision per rule of the ZAP baseline: fixed ones on FAIL, accepted ones on IGNORE with the reason
- `SECURITY.md` - how to report a vulnerability privately, and what is in scope
- `vex/` - `openvex.json`, which says per vulnerability in the image whether it affects the image and why, and in `README.md` how a finding is triaged
- `scripts/` - `deployment.py` to deploy, locally or to Azure, and to remove it all again. It asks what to do and starts `deploy_local.py`, `deploy_azure.py` or `undo.py`, which take what they share from it: paths, questions, stopping and hackmode. `setup_azure.py` is the one-time Terraform state bootstrap that `deploy_azure.py` starts when it is missing
- `tests/` - the security test against the local stack: `securitytest.py` runs one test per topic (`bruteforcetest.py` and the others), each with the normal flow, the attack and the mitigation it proves. It empties the local accounts, so it only runs with `--wipe`
- `terraform/` - Azure: Container Apps, PostgreSQL B1ms in a private network and Key Vault; secrets stay out of the Terraform state. `deploy.tf` is the identity for the job `deploy`, which may only change the container app; it only exists once you choose to deploy from GitHub. Deployed on 18 October 2026 in France Central, and removed again on 19 October 2026 with `deployment.py undo`

## Requirements

- **Locally:** Docker with Compose v2, and Python 3 for `scripts/deployment.py`.
- **Azure:** an Azure subscription in which you may create resources, role assignments and a custom role (Owner, or Contributor with User Access Administrator), the Azure CLI, Terraform 1.11 or newer, Python 3 and Git. No Docker and no GitHub token: GitHub Actions builds the image on every push to `main`. Optional, to deploy from GitHub after your approval: the GitHub CLI (`gh`) and admin rights on the repo.
- **Signed in to Azure** before `python scripts/deployment.py azure`: run `az login`. If it says `Authentication failed against tenant <ID>` with `AADSTS50076`, that tenant requires MFA and `az login` skipped it; run `az login --tenant <ID>` and approve the second step in your authenticator app. On Windows the sign-in opens in a small Windows window (Web Account Manager) instead of the browser; that is the default since Azure CLI 2.61.0.
- **Signed in to GitHub**, only to deploy from GitHub: run `gh auth login`. `deployment.py azure` then sets up the environment `azure` and reads how GitHub names the repo in the OIDC token of a job, with the IDs of owner and repo if the repo uses immutable subjects. Without `gh` it skips this, and you update by running it again.

`deployment.py` checks these first and names what is missing.

## Run it

```sh
python scripts/deployment.py
```

It asks where to deploy (local or Azure) and whether to turn on hackmode for the hacking week, with a class behind one school address. Locally it creates missing secrets in `.env` and starts the stack. On Azure it sets up the Terraform state storage once, checks that GitHub Actions published the image of your last commit, and runs `terraform init` and `apply`; Terraform shows the plan and waits for `yes`, and starts the schema job itself. With `gh` it then asks whether to deploy from GitHub: it sets up the environment `azure` (only `main`, with you as the required reviewer) and the three IDs the job `deploy` signs in with. Then a merge into `main` builds and scans the image, and the job `deploy` waits until you approve it in the Actions tab. Without `gh`, to update, merge a pull request into `main`, wait for the Image action, and run it again. To remove it all again, `python scripts/deployment.py undo` asks per part, with no as the default: on Azure `terraform destroy` (which still waits for `yes`) and then the state storage, `backend.conf` and `terraform/.terraform`; and with `gh` the environment `azure`, so pushes to `main` no longer wait for an approval; locally the containers, the database volume, the built image and `.env`. A step that fails stops before the next one, so the state storage stays as long as Terraform still needs it. With `python scripts/deployment.py local` and no terminal (as in CI) it asks nothing and keeps what is in `.env`. On Linux or macOS the command is often `python3`; the script works the same on Windows and Linux.

In your own copy (a fork, or a copy under your own account), almost nothing needs to be set in GitHub. In a fork, turn on the workflows in the Actions tab first, because GitHub turns them off in forks. Then push to `main` or start the Image workflow in the Actions tab, and GitHub builds the image under your own name with the token of the run. Then `az login` and `python scripts/deployment.py azure` set up your own state storage and deploy with your own subscription. In a private copy the image package is private too; Container Apps then cannot pull it, and `deployment.py` stops and says so.

Or by hand: copy `.env.example` to `.env`, fill in the four values, and run `docker compose up --build`.

Had the stack running before 20 October 2026? The database is now called `notes`, with the owner `notes_owner` and the app role `notes_app`, and those are only created in an empty volume. Run `python scripts/deployment.py undo` (or `docker compose down -v`) first. That deletes the local data.

Then open http://127.0.0.1:5000.

## Status

The baseline plus the first security features, each with an entry in `BoK/Threat Analysis/entries.md`:

- pinned dependencies (MIT-03) and a length limit on notes (MIT-04)
- mandatory two-step verification with TOTP, a recovery code for a lost phone, login limits per IP address and per account, and a session version that ends old sessions (MIT-05 to MIT-12); see `BoK/Subjects/Week 5 Authentication.md`
- a rule of 12 to 64 characters for a new password (MIT-13), and a forgotten-password route that uses the recovery code and the app code (MIT-14)
- an ownership check on every note (MIT-15), and the current password before changing it or deleting the account (MIT-16)
- the TOTP secret and the notes encrypted with AES-256-GCM, with the key outside the database (MIT-17, MIT-18), and passwords hashed with Argon2id (MIT-19); see `BoK/Subjects/Week 6 Encryption.md`
- hackmode for the hacking week, off by default (MIT-10)
- a CSRF token on every form, strict security headers, input and configuration checks, every route closed by default, safe failure, gunicorn as an unprivileged user, and an own database role that can only read and write the app's tables (MIT-20 to MIT-27); see `BoK/Subjects/Week 7 Application Security.md`
- taken from BOK-SECENGINEER and an audit: no page in the browser cache, sessions of at most 8 hours, a limit on registrations and notes, every security event as a JSON line in the log, an owner-only `.env`, and Dependabot (MIT-28 to MIT-33); see `BoK/Subjects/Week 6 Logging.md`
- the image built, its SBoM made and scanned for known vulnerabilities, and published by GitHub Actions with only the rights it needs and no own token (MIT-34 to MIT-36), the same build, SBoM and scan as a required check on every pull request, so a known vulnerability does not reach `main`, and the security test in that check, so a change that breaks a mitigation does not either (MIT-39), and a mail when a lockout starts on Azure (MIT-37); see `BoK/Subjects/Week 8 CI-CD.md`
- every known HIGH or CRITICAL vulnerability, also one without a fix, stops the check until there is a decision in the VEX (MIT-41), and no program in the image has a setuid or setgid bit (MIT-42); see `vex/README.md`
- DAST with the ZAP baseline on every pull request, with a decision per finding in `zap-rules.tsv`, which found two missing headers (MIT-46)
- code scanning with CodeQL on every pull request, Dependabot alerts and security updates, and private vulnerability reporting (MIT-45); see `SECURITY.md`
- psycopg with the libpq of Debian instead of psycopg-binary and its 15 bundled libraries, so the scan sees what it loads and Debian updates it (MIT-43)
- the Terraform state in its own storage with its own key, reachable only through Entra ID (MIT-38), and TLS on Azure checked against the NCSC guidelines (MIT-40); see `BoK/Subjects/Week 6 Encryption.md`

On Azure the log is kept for 30 days in Log Analytics (MIT-31). Still open: only a lockout sends a mail (MC-28), the database role can still change every row the app can (MC-08), the running app holds the data key, locally from `.env` and on Azure from Key Vault (MC-22), the security test in the pipeline covers the local stack, not Azure, and the scan does not see Python itself or the OpenSSL inside cryptography (MC-11). Deployed to Azure on 18 October 2026 and removed again on 19 October 2026; it goes back up before the hacking week.

## License

MIT, see `LICENSE`. That covers the code and the BoK.
