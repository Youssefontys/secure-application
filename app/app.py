# Maakt de Flask-app en hangt auth, account en notes eraan; de modules staan in de README.
# Zwakke plekken staan als misuse case in de BoK; in de code staat het MC-nummer erbij.

import os
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Flask

import account
import auth
import notes
import passwords
from db import TIMEZONE

# De website (HTML-templates en statische bestanden) staat in web/, los van de code.
app = Flask(__name__, template_folder="web/templates", static_folder="web/static")
# Flask ondertekent de sessiecookie met deze sleutel.
app.secret_key = os.environ["FLASK_SECRET_KEY"]

for blueprint in (auth.bp, account.bp, notes.bp):
    app.register_blueprint(blueprint)
app.jinja_env.globals.update(
    TITLE_MAX=notes.TITLE_MAX, BODY_MAX=notes.BODY_MAX,
    PASSWORD_MIN=passwords.PASSWORD_MIN, PASSWORD_MAX=passwords.PASSWORD_MAX,
)


@app.template_filter("date")
def format_date(value, with_time=True):
    return value.strftime("%d-%m-%Y %H:%M" if with_time else "%d-%m-%Y")


# Goedemorgen, -middag, -avond of -nacht, naar de Nederlandse tijd.
@app.template_global()
def greeting():
    hour = datetime.now(ZoneInfo(TIMEZONE)).hour
    if hour < 6:
        return "Goedenacht"
    if hour < 12:
        return "Goedemorgen"
    if hour < 18:
        return "Goedemiddag"
    return "Goedenavond"
