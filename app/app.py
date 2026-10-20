# Creates the Flask app and attaches auth, account and notes to it; the modules are listed in the README.
# Weak spots are misuse cases in the BoK; the code names the MC number next to them.

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


# Configuration is input too: only a known value, otherwise the app does not start (MIT-23).
def setting(name, default, allowed):
    value = os.environ.get(name, default)
    if value not in allowed:
        raise RuntimeError(f"{name} must be {' or '.join(allowed)}, not {value!r}.")
    return value


# The website (HTML templates and static files) is in web/, apart from the code.
app = Flask(__name__, template_folder="web/templates", static_folder="web/static")
# Flask signs the session cookie with this key; deployment.py makes one of 64 characters.
app.secret_key = os.environ["FLASK_SECRET_KEY"]
if len(app.secret_key) < 32:
    raise RuntimeError("FLASK_SECRET_KEY must be at least 32 characters.")
# On Azure: the real client address behind the one proxy of Container Apps (MC-18). Locally 0.
# Only 0 or 1: with -1 or 2 an attacker picks their own address and gets around the limits.
if setting("TRUSTED_PROXIES", "0", ("0", "1")) == "1":
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
# Safe by default: the session cookie only over HTTPS (MC-04). Locally, on HTTP, compose.yaml turns this off.
app.config["SESSION_COOKIE_SECURE"] = setting("HTTPS_ONLY", "1", ("0", "1")) == "1"
# Not sent with a form from another site (MC-05); the CSRF token is the second layer.
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
# Flask refuses a cookie whose signature is older; without this line 31 days (MIT-29, MC-04).
# The app writes the cookie mainly at login, so this is about 8 hours after the login.
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)
# The largest form is a note of 250 characters; more is refused before it is read (MC-10).
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024

# Before the user is loaded, so an expired session simply goes to the login page (MIT-20).
app.before_request(csrf.check)
for blueprint in (auth.bp, account.bp, notes.bp):
    app.register_blueprint(blueprint)
app.teardown_appcontext(close_connection)
app.jinja_env.globals.update(
    TITLE_MAX=notes.TITLE_MAX, BODY_MAX=notes.BODY_MAX, NOTES_MAX=notes.NOTES_MAX,
    PASSWORD_MIN=passwords.PASSWORD_MIN, PASSWORD_MAX=passwords.PASSWORD_MAX, csrf_token=csrf.token,
)


# Only own files and no inline script: a second layer against XSS (MC-07); no frame on another site (MC-24).
CSP = "default-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"


# On every response, error pages too (MIT-21). HSTS only over HTTPS, otherwise the browser remembers it wrongly.
@app.after_request
def security_headers(response):
    response.headers["Content-Security-Policy"] = CSP
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    # No page in a browser or proxy cache: after logging out, Back shows nothing (MIT-28), and the secret and
    # recovery code are kept nowhere (MIT-08, MIT-11). Static files may be cached.
    if request.endpoint != "static":
        response.headers["Cache-Control"] = "no-store"
    if app.config["SESSION_COOKIE_SECURE"]:
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
    return response


# Short messages for the errors a visitor can cause; 413 comes before the request is read (MIT-22).
HTTP_MESSAGES = {404: "This page does not exist.", 405: "That is not possible here.", 413: "This request is too large."}


# Status and headers (such as Allow on 405) stay; only the page becomes the own error page.
@app.errorhandler(HTTPException)
def http_error(error):
    response = error.get_response()
    response.set_data(render_template("error.html", code=error.code, message=HTTP_MESSAGES.get(error.code, "That did not work.")))
    return response


# Fail safely (MIT-25): the visitor sees no details, the log does. %r, so a line break
# in the URL does not make a false log line (log injection).
@app.errorhandler(Exception)
def unexpected_error(error):
    app.logger.exception("Unexpected error at %s %r", request.method, request.path)
    return render_template("error.html", code=500, message="Something went wrong. Please try again later."), 500


@app.template_filter("date")
def format_date(value, with_time=True):
    return value.strftime("%d-%m-%Y %H:%M" if with_time else "%d-%m-%Y")


# Per block of six hours, in Dutch time; at night Hello, because good night is a goodbye.
@app.template_global()
def greeting():
    return ("Hello", "Good morning", "Good afternoon", "Good evening")[datetime.now(ZoneInfo(TIMEZONE)).hour // 6]
