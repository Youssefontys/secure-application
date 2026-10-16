# Registreren, inloggen met wachtwoord en code, uitloggen, en wie welke route mag openen.

import hashlib
import hmac
import re
import secrets
import time
from collections import namedtuple
from functools import wraps

import psycopg
from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

import passwords
import throttle
import totp
from db import query

bp = Blueprint("auth", __name__)

# Zo lang heb je na het wachtwoord om de code in te vullen.
PENDING_MAX_SECONDS = 300
# Een geweigerde code: de melding, en hoeveel minuten de blokkade duurt (0 als er geen is).
CodeError = namedtuple("CodeError", "message minutes")
# Zonder tweestapsverificatie kom je alleen hier (MIT-12).
SETUP_ENDPOINTS = {"account.setup_2fa", "account.qr_2fa"}


# Zet de ingelogde gebruiker in g.user, maar alleen als de sessieversie klopt (MIT-09).
@bp.before_app_request
def load_user():
    g.user = None
    user_id = session.get("user_id")
    if user_id is None or request.endpoint == "static":
        return
    user = query("SELECT id, username, session_version, totp_enabled FROM users WHERE id = %s", (user_id,), one=True)
    # Versie lager dan in de database: een oude cookie of een kopie, dus niet meer geldig.
    if user is None or user.session_version != session.get("session_version"):
        session.clear()
        flash("Je sessie is niet meer geldig. Log opnieuw in.")
        return
    g.user = user


# Een verse sessie voor deze gebruiker, met de huidige sessieversie.
def start_session(user_id, version):
    session.clear()
    session["user_id"] = user_id
    session["session_version"] = version


# Hoogt de sessieversie op: andere sessies vervallen, de huidige krijgt de nieuwe versie.
def end_other_sessions(user_id):
    row = query(
        "UPDATE users SET session_version = session_version + 1 WHERE id = %s RETURNING session_version",
        (user_id,), one=True,
    )
    session["session_version"] = row.session_version


# Alleen ingelogd (AU-02) en met tweestapsverificatie; anders alleen het instellen (MIT-12).
def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))
        if not g.user.totp_enabled and request.endpoint not in SETUP_ENDPOINTS:
            return redirect(url_for("account.setup_2fa"))
        return view(*args, **kwargs)
    return wrapper


# Wie al is ingelogd, hoeft niet opnieuw in te loggen of te registreren.
def logged_out_only(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if g.user is not None:
            return redirect(url_for("notes.index"))
        return view(*args, **kwargs)
    return wrapper


@bp.route("/register", methods=["GET", "POST"])
@logged_out_only
def register():
    if request.method == "GET":
        return render_template("auth.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    if not username or not password:
        return render_template("auth.html", error="Vul een gebruikersnaam en wachtwoord in."), 400
    error = passwords.password_problem(password)
    if error:
        return render_template("auth.html", error=error), 400

    try:
        query("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
    except psycopg.errors.UniqueViolation:
        return render_template("auth.html", error="Die gebruikersnaam is al in gebruik."), 409
    flash("Je account is aangemaakt. Je kunt nu inloggen.")
    return redirect(url_for("auth.login"))


@bp.route("/login", methods=["GET", "POST"])
@logged_out_only
def login():
    if request.method == "GET":
        return render_template("auth.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    # Tellen per adres en per naam per adres (MIT-10), ook voor onbekende namen: verraadt niets.
    ip = throttle.client_ip(request.remote_addr)
    ip_key = throttle.key("password_ip", ip)
    pair_key = throttle.key("password_account_ip", username, ip)
    minutes = throttle.locked_minutes(ip_key, pair_key)
    if minutes:
        return render_template("auth.html", error=throttle.message(minutes)), *throttle.refusal(minutes)
    row = query(
        "SELECT id, totp_enabled, session_version FROM users WHERE username = %s AND password = %s",
        (username, password), one=True,
    )
    if row is None:
        minutes = max(throttle.fail("password_ip", ip_key), throttle.fail("password_account_ip", pair_key))
        error = throttle.message(minutes) if minutes else "Onjuiste gebruikersnaam of wachtwoord."
        return render_template("auth.html", error=error), *throttle.refusal(minutes)
    # Alleen de accountteller weg, zodat een eigen account de adresteller niet kan resetten.
    throttle.reset(pair_key)

    session.clear()
    if row.totp_enabled:
        # Factor 1 van 2: alleen pending_user_id, en daarmee opent geen enkele route (MIT-05).
        session["pending_user_id"] = row.id
        session["pending_version"] = row.session_version
        session["pending_since"] = int(time.time())
        return redirect(url_for("auth.login_code"))
    # Nog geen tweestapsverificatie: na het wachtwoord eerst instellen (MIT-12).
    start_session(row.id, row.session_version)
    return redirect(url_for("account.setup_2fa"))


# De gebruiker van de halve login, of None als die te oud is of de sessieversie veranderde.
def pending_login():
    user_id = session.get("pending_user_id")
    if user_id is None:
        return None
    if time.time() - session.get("pending_since", 0) > PENDING_MAX_SECONDS:
        session.clear()
        flash("Dat duurde te lang. Log opnieuw in.")
        return None
    row = query("SELECT session_version FROM users WHERE id = %s", (user_id,), one=True)
    if row is None or row.session_version != session.get("pending_version"):
        session.clear()
        flash("Je sessie is niet meer geldig. Log opnieuw in.")
        return None
    return user_id


# De tweede stap: de code uit de authenticator-app (AU-05).
@bp.route("/login/2fa", methods=["GET", "POST"])
@logged_out_only
def login_code():
    user_id = pending_login()
    if user_id is None:
        return redirect(url_for("auth.login"))
    if request.method == "GET":
        return render_template("login_code.html")

    error = check_code(user_id)
    if error:
        return render_template("login_code.html", error=error.message), *throttle.refusal(error.minutes)
    # Pas nu ingelogd; start_session gooit de halve login helemaal weg.
    start_session(user_id, session["pending_version"])
    return redirect(url_for("notes.index"))


# Een nieuwe herstelcode van 128 bits, om één keer te tonen; een eerdere code vervalt.
def new_recovery_code(user_id):
    code = secrets.token_hex(16)
    # Alleen de SHA-256: bij 128 willekeurige bits is een trage hash niet nodig.
    query("UPDATE users SET recovery_hash = %s WHERE id = %s", (hashlib.sha256(code.encode()).hexdigest(), user_id))
    return "-".join(code[i:i + 4] for i in range(0, len(code), 4))


# De herstelcode in plaats van de code uit de app, voor wie de telefoon kwijt is (AU-07).
@bp.route("/login/recover", methods=["GET", "POST"])
@logged_out_only
def login_recover():
    user_id = pending_login()
    if user_id is None:
        return redirect(url_for("auth.login"))
    if request.method == "GET":
        return render_template("login_recover.html")

    k = throttle.key("recovery_account", user_id)
    minutes = throttle.locked_minutes(k)
    if minutes:
        return render_template("login_recover.html", error=throttle.message(minutes)), *throttle.refusal(minutes)
    given = hashlib.sha256(re.sub(r"[\s-]", "", request.form.get("code", "")).lower().encode()).hexdigest()
    stored = query("SELECT recovery_hash FROM users WHERE id = %s", (user_id,), one=True)
    if not (stored and stored.recovery_hash and hmac.compare_digest(given, stored.recovery_hash)):
        minutes = throttle.fail("recovery_account", k)
        error = throttle.message(minutes) if minutes else "Onjuiste herstelcode."
        return render_template("login_recover.html", error=error), *throttle.refusal(minutes)
    # Werkt één keer: 2FA uit, sessies ongeldig; de hash in de WHERE laat één verzoek winnen.
    row = query(
        "UPDATE users SET recovery_hash = NULL, totp_secret = NULL, totp_enabled = false, totp_last_step = NULL,"
        " session_version = session_version + 1 WHERE id = %s AND recovery_hash = %s RETURNING session_version",
        (user_id, given), one=True,
    )
    if row is None:
        return render_template("login_recover.html", error="Onjuiste herstelcode."), 400
    throttle.reset(k)
    start_session(user_id, row.session_version)
    flash("Je herstelcode is gebruikt. Stel tweestapsverificatie opnieuw in met je nieuwe telefoon.")
    return redirect(url_for("account.setup_2fa"))


@bp.route("/logout", methods=["POST"])
def logout():
    # Versie omhoog: ook een gekopieerde cookie vervalt (MC-04), op alle apparaten.
    if g.user is not None:
        query("UPDATE users SET session_version = session_version + 1 WHERE id = %s", (g.user.id,))
    session.clear()
    return redirect(url_for("auth.login"))


# Controleert de TOTP-code uit het formulier: None als hij klopt, anders een CodeError.
def check_code(user_id):
    k = throttle.key("totp_account", user_id)
    user = query("SELECT totp_secret FROM users WHERE id = %s", (user_id,), one=True)
    if user is None or user.totp_secret is None:
        return CodeError("Er is geen tweestapsverificatie ingesteld.", 0)
    # Op slot: dan wordt ook de juiste code geweigerd (MIT-06).
    minutes = throttle.locked_minutes(k)
    if minutes:
        return CodeError(throttle.message(minutes), minutes)
    step = totp.matching_step(user.totp_secret, request.form.get("code", ""))
    # Eenmalig gebruik (MIT-07) en blokkade in één UPDATE: van twee verzoeken wint er één.
    if step is not None and query(
        "UPDATE users SET totp_last_step = %s"
        " WHERE id = %s AND (totp_last_step IS NULL OR totp_last_step < %s)"
        " AND NOT EXISTS (SELECT 1 FROM auth_throttle WHERE key = %s AND locked_until > now()) RETURNING id",
        (step, user_id, step, k), one=True,
    ):
        throttle.reset(k)
        return None
    # Fout, of al eens gebruikt: telt als mislukte poging.
    minutes = throttle.fail("totp_account", k)
    return CodeError(throttle.message(minutes) if minutes else "Onjuiste of al gebruikte code.", minutes)
