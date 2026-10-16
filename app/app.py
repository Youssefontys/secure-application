# Maakt de Flask-app en hangt auth, account en notes eraan; de modules staan in de README.
# Zwakke plekken staan als misuse case in de BoK; in de code staat het MC-nummer erbij.

import os
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

import account
import auth
import notes
import passwords
from db import TIMEZONE, close_connection

# De website (HTML-templates en statische bestanden) staat in web/, los van de code.
app = Flask(__name__, template_folder="web/templates", static_folder="web/static")
# Flask ondertekent de sessiecookie met deze sleutel.
app.secret_key = os.environ["FLASK_SECRET_KEY"]
# Op Azure: het echte clientadres achter zoveel proxies, anders telt iedereen als één adres (MC-18). Lokaal 0.
proxies = int(os.environ.get("TRUSTED_PROXIES", "0"))
if proxies:
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=proxies, x_proto=proxies)
# Op Azure (HTTPS): de sessiecookie nooit over gewoon HTTP (MC-04). Lokaal draait de app op HTTP.
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("HTTPS_ONLY") == "1"

for blueprint in (auth.bp, account.bp, notes.bp):
    app.register_blueprint(blueprint)
app.teardown_appcontext(close_connection)
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
