"""Notitie-app: registreren, inloggen (met tweestapsverificatie als die aan staat),
wachtwoord wijzigen, account verwijderen en notities beheren.

Dit bestand maakt de app en hangt de onderdelen eraan:
- db.py: de databaseverbinding (query)
- auth.py: registreren, inloggen, de tweede stap, uitloggen, wie wat mag openen
- account.py: profiel, tweestapsverificatie, wachtwoord, account verwijderen
- notes.py: notities
- totp.py: de TOTP-berekening (RFC 6238)

De bekende zwakke plekken staan als misuse case in BoK/Threat Analysis/entries.md.
Waar zo'n zwakke plek in de code zit, staat het MC-nummer erbij.
"""

import os
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Flask

import account
import auth
import notes
from db import TIMEZONE

# De website (HTML-templates en statische bestanden) staat in web/, los van de code.
app = Flask(__name__, template_folder="web/templates", static_folder="web/static")
# Flask heeft een sleutel nodig om de sessiecookie te ondertekenen.
app.secret_key = os.environ["FLASK_SECRET_KEY"]

for blueprint in (auth.bp, account.bp, notes.bp):
    app.register_blueprint(blueprint)
app.jinja_env.globals.update(TITLE_MAX=notes.TITLE_MAX, BODY_MAX=notes.BODY_MAX)


@app.template_filter("date")
def format_date(value, with_time=True):
    return value.strftime("%d-%m-%Y %H:%M" if with_time else "%d-%m-%Y")


@app.template_global()
def greeting():
    """Goedemorgen, -middag, -avond of -nacht, naar de Nederlandse tijd."""
    hour = datetime.now(ZoneInfo(TIMEZONE)).hour
    if hour < 6:
        return "Goedenacht"
    if hour < 12:
        return "Goedemorgen"
    if hour < 18:
        return "Goedemiddag"
    return "Goedenavond"
