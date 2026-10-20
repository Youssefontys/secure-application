# Security policy

This is a student project for the Yellow Teaming specialisation at Fontys ICT: a notes application that started deliberately insecure and gets its security features one at a time. Every weak spot that is known is written down as a misuse case in `BoK/Threat Analysis/entries.md`, with what is done about it and what remains.

## Reporting a vulnerability

Report it privately through **Security → Report a vulnerability** on this repository (GitHub private vulnerability reporting). Please do not open a public issue for it.

Useful to include: what you did, what happened, what you expected, and the commit or the version of the image (the tag `app-...`) it applies to.

There is no bug bounty and no fixed response time: reports are read during the semester. A confirmed finding gets a misuse case or a step in an existing one, a mitigation, and a test in the BoK, and you are credited if you want to be.

## Scope

- The code on `main`: the app (`app/`), the database files (`db/`), the scripts (`scripts/`), the tests (`tests/`), Terraform (`terraform/`) and the workflows (`.github/workflows/`).
- The image on ghcr.io that is built from it.

Attack only your own copy, locally (`python scripts/deployment.py local`) or in your own Azure subscription. The deployment on Azure of this repository is only a target when the owner says so, for example in the hacking week of the course.

## Known and accepted

Read `BoK/Threat Analysis/risk-matrix.md` and the residual risk (Restrisico) of each misuse case first: what is there is known, and most of it is a conscious choice.
