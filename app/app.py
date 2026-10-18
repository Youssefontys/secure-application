# Maakt de Flask-app en hangt auth, account en notes eraan; de modules staan in de README.
# Zwakke plekken staan als misuse case in de BoK; in de code staat het MC-nummer erbij.

import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from flask import Flask, render_template, request
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

import account
import auth
import csrf
import notes
import passwords
from db import TIMEZONE, close_connection


# Configuratie is ook invoer: alleen een bekende waarde, anders start de app niet (MIT-23).
def setting(name, default, allowed):
    value = os.environ.get(name, default)
    if value not in allowed:
        raise RuntimeError(f"{name} moet {' of '.join(allowed)} zijn, niet {value!r}.")
    return value


# De website (HTML-templates en statische bestanden) staat in web/, los van de code.
app = Flask(__name__, template_folder="web/templates", static_folder="web/static")
# Flask ondertekent de sessiecookie met deze sleutel; setup.py maakt er een van 64 tekens.
app.secret_key = os.environ["FLASK_SECRET_KEY"]
if len(app.secret_key) < 32:
    raise RuntimeError("FLASK_SECRET_KEY moet minstens 32 tekens zijn.")
# Op Azure: het echte clientadres achter de ene proxy van Container Apps (MC-18). Lokaal 0.
# Alleen 0 of 1: met -1 of 2 kiest een aanvaller zelf zijn adres en omzeilt hij de limieten.
if setting("TRUSTED_PROXIES", "0", ("0", "1")) == "1":
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
# Standaard veilig: de sessiecookie alleen over HTTPS (MC-04). Lokaal, op HTTP, zet compose.yaml dit uit.
app.config["SESSION_COOKIE_SECURE"] = setting("HTTPS_ONLY", "1", ("0", "1")) == "1"
# Niet meesturen met een formulier van een andere site (MC-05); het CSRF-token is de tweede laag.
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
# Flask weigert een cookie waarvan de handtekening ouder is; zonder deze regel 31 dagen (MIT-29, MC-04).
# De app schrijft de cookie vooral bij het inloggen, dus dit is ongeveer 8 uur na de login.
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)
# Het grootste formulier is een notitie van 250 tekens; meer wordt geweigerd voordat het is ingelezen (MC-10).
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024

# Vóór het laden van de gebruiker, zodat een verlopen sessie gewoon naar de inlogpagina gaat (MIT-20).
app.before_request(csrf.check)
for blueprint in (auth.bp, account.bp, notes.bp):
    app.register_blueprint(blueprint)
app.teardown_appcontext(close_connection)
app.jinja_env.globals.update(
    TITLE_MAX=notes.TITLE_MAX, BODY_MAX=notes.BODY_MAX, NOTES_MAX=notes.NOTES_MAX,
    PASSWORD_MIN=passwords.PASSWORD_MIN, PASSWORD_MAX=passwords.PASSWORD_MAX, csrf_token=csrf.token,
)


# Alleen eigen bestanden en geen inline script: een tweede laag tegen XSS (MC-07); geen frame op een andere site (MC-24).
CSP = "default-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"


# Op elk antwoord, ook op foutpagina's (MIT-21). HSTS alleen over HTTPS, anders onthoudt de browser het verkeerd.
@app.after_request
def security_headers(response):
    response.headers["Content-Security-Policy"] = CSP
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    # Geen pagina in een browser- of proxycache: na uitloggen toont Terug niets meer (MIT-28), en geheim en
    # herstelcode blijven nergens staan (MIT-08, MIT-11). Statische bestanden mogen wel in de cache.
    if request.endpoint != "static":
        response.headers["Cache-Control"] = "no-store"
    if app.config["SESSION_COOKIE_SECURE"]:
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
    return response


# Korte meldingen voor de fouten die een bezoeker kan veroorzaken; 413 komt voordat het verzoek is ingelezen (MIT-22).
HTTP_MESSAGES = {404: "This page does not exist.", 405: "That is not possible here.", 413: "This request is too large."}


# Status en headers (zoals Allow bij 405) blijven; alleen de pagina wordt de eigen foutpagina.
@app.errorhandler(HTTPException)
def http_error(error):
    response = error.get_response()
    response.set_data(render_template("error.html", code=error.code, message=HTTP_MESSAGES.get(error.code, "That did not work.")))
    return response


# Veilig falen (MIT-25): de bezoeker ziet geen details, de log wel. %r, zodat een regeleinde
# in de URL geen valse logregel maakt (log injection).
@app.errorhandler(Exception)
def unexpected_error(error):
    app.logger.exception("Onverwachte fout bij %s %r", request.method, request.path)
    return render_template("error.html", code=500, message="Something went wrong. Please try again later."), 500


@app.template_filter("date")
def format_date(value, with_time=True):
    return value.strftime("%d-%m-%Y %H:%M" if with_time else "%d-%m-%Y")


# Per blok van zes uur, naar de Nederlandse tijd; 's nachts Hello, want good night is een afscheid.
@app.template_global()
def greeting():
    return ("Hello", "Good morning", "Good afternoon", "Good evening")[datetime.now(ZoneInfo(TIMEZONE)).hour // 6]
