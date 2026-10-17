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

import encryption
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
# De enige routes zonder login; elke andere route is standaard dicht (MIT-24).
PUBLIC_ENDPOINTS = {"auth.register", "auth.login", "auth.login_code", "auth.login_recover", "auth.forgot_password", "auth.logout", "static"}
# 3 tot 20 tekens: letters, cijfers en _ (MIT-22). Bij inloggen telt een andere naam als onbekend.
USERNAME = re.compile(r"[A-Za-z0-9_]{3,20}")
# Eén melding voor elke fout bij wachtwoord vergeten, ook voor een onbekende naam (MC-21).
FORGOT_WRONG = "Gebruikersnaam, herstelcode of code klopt niet."


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


# Standaard dicht (MIT-24): ingelogd (AU-02) en met tweestapsverificatie, anders alleen het instellen (MIT-12).
# Een nieuwe route is zo nooit per ongeluk open; alleen PUBLIC_ENDPOINTS mag zonder login. Na load_user.
@bp.before_app_request
def require_login():
    if request.endpoint in PUBLIC_ENDPOINTS or request.endpoint is None:
        return None
    if g.user is None:
        return redirect(url_for("auth.login"))
    if not g.user.totp_enabled and request.endpoint not in SETUP_ENDPOINTS:
        return redirect(url_for("account.setup_2fa"))
    return None


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
    if request.method != "POST":
        return render_template("auth.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    if not username or not password:
        return render_template("auth.html", error="Vul een gebruikersnaam en wachtwoord in."), 400
    if not USERNAME.fullmatch(username):
        return render_template("auth.html", error="Kies een gebruikersnaam van 3 tot 20 tekens: letters, cijfers en _."), 400
    if error := passwords.password_problem(password):
        return render_template("auth.html", error=error), 400

    try:
        query("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, passwords.hash_password(password)))
    except psycopg.errors.UniqueViolation:
        return render_template("auth.html", error="Die gebruikersnaam is al in gebruik."), 409
    flash("Je account is aangemaakt. Je kunt nu inloggen.")
    return redirect(url_for("auth.login"))


@bp.route("/login", methods=["GET", "POST"])
@logged_out_only
def login():
    # Alleen POST telt als poging; HEAD viel eerst onder "niet GET" en telde mee voor de limiet.
    if request.method != "POST":
        return render_template("auth.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    # Tellen per adres en per naam per adres (MIT-10), ook voor onbekende namen: verraadt niets.
    limits = throttle.password_limits(username, request.remote_addr)
    if minutes := throttle.attempt(*limits):
        return render_template("auth.html", error=throttle.message(minutes)), *throttle.refusal(minutes)
    row = USERNAME.fullmatch(username) and query(
        "SELECT id, password_hash, totp_enabled, session_version FROM users WHERE username = %s", (username,), one=True,
    )
    if not passwords.matches(row and row.password_hash, password):
        return render_template("auth.html", error="Onjuiste gebruikersnaam of wachtwoord."), 400
    throttle.succeeded(*limits)
    passwords.rehash_if_needed(row.id, row.password_hash, password)

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
    if request.method != "POST":
        return render_template("login_code.html")

    if error := check_code(user_id):
        return render_template("login_code.html", error=error.message), *throttle.refusal(error.minutes)
    # Pas nu ingelogd; start_session gooit de halve login helemaal weg.
    start_session(user_id, session["pending_version"])
    return redirect(url_for("notes.index"))


# Alleen de SHA-256 van een herstelcode: bij 128 willekeurige bits is een trage hash niet nodig.
def hash_recovery_code(text):
    return hashlib.sha256(re.sub(r"[\s-]", "", text).lower().encode()).hexdigest()


# Een nieuwe herstelcode van 128 bits: de code om één keer te tonen, en de hash om te bewaren.
def make_recovery_code():
    code = secrets.token_hex(16)
    return "-".join(code[i:i + 4] for i in range(0, len(code), 4)), hash_recovery_code(code)


# Zet een nieuwe herstelcode voor dit account en geeft hem terug; een eerdere code vervalt.
def new_recovery_code(user_id):
    code, recovery_hash = make_recovery_code()
    query("UPDATE users SET recovery_hash = %s WHERE id = %s", (recovery_hash, user_id))
    return code


# De herstelcode in plaats van de code uit de app, voor wie de telefoon kwijt is (AU-07).
@bp.route("/login/recover", methods=["GET", "POST"])
@logged_out_only
def login_recover():
    user_id = pending_login()
    if user_id is None:
        return redirect(url_for("auth.login"))
    if request.method != "POST":
        return render_template("login_recover.html")

    recovery_limit = throttle.limit("recovery_account", user_id)
    if minutes := throttle.attempt(recovery_limit):
        return render_template("login_recover.html", error=throttle.message(minutes)), *throttle.refusal(minutes)
    given = hash_recovery_code(request.form.get("code", ""))
    stored = query("SELECT recovery_hash FROM users WHERE id = %s", (user_id,), one=True)
    if not (stored and stored.recovery_hash and hmac.compare_digest(given, stored.recovery_hash)):
        return render_template("login_recover.html", error="Onjuiste herstelcode."), 400
    # Werkt één keer: 2FA uit, sessies ongeldig; de hash in de WHERE laat één verzoek winnen.
    row = query(
        "UPDATE users SET recovery_hash = NULL, totp_secret = NULL, totp_enabled = false, totp_last_step = NULL,"
        " session_version = session_version + 1 WHERE id = %s AND recovery_hash = %s RETURNING session_version",
        (user_id, given), one=True,
    )
    if row is None:
        return render_template("login_recover.html", error="Onjuiste herstelcode."), 400
    throttle.succeeded(recovery_limit)
    start_session(user_id, row.session_version)
    flash("Je herstelcode is gebruikt. Stel tweestapsverificatie opnieuw in met je nieuwe telefoon.")
    return redirect(url_for("account.setup_2fa"))


# Wachtwoord vergeten: herstelcode en code uit de app, twee van de drie factoren (MIT-14).
@bp.route("/login/forgot", methods=["GET", "POST"])
@logged_out_only
def forgot_password():
    if request.method != "POST":
        return render_template("login_forgot.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    if problem := passwords.password_problem(password, request.form.get("password_repeat", "")):
        return render_template("login_forgot.html", error=problem), 400
    # Bereikbaar zonder wachtwoord, dus dezelfde tellers als bij inloggen: per adres en per naam per adres.
    limits = throttle.password_limits(username, request.remote_addr)
    if minutes := throttle.attempt(*limits):
        return render_template("login_forgot.html", error=throttle.message(minutes)), *throttle.refusal(minutes)
    user = USERNAME.fullmatch(username) and query(
        "SELECT id, recovery_hash FROM users WHERE username = %s AND totp_enabled", (username,), one=True,
    )
    given = hash_recovery_code(request.form.get("recovery_code", ""))
    if not (user and user.recovery_hash and hmac.compare_digest(given, user.recovery_hash)):
        return render_template("login_forgot.html", error=FORGOT_WRONG), 400
    throttle.succeeded(*limits)
    # De herstelcode klopt; pas nu telt een foute code per account, met de blokkade van de codestap (MIT-06).
    if code_error := check_code(user.id):
        error = code_error.message if code_error.minutes else FORGOT_WRONG
        return render_template("login_forgot.html", error=error), *throttle.refusal(code_error.minutes)
    # Alles in één UPDATE: wachtwoord, nieuwe herstelcode, sessies; de oude hash in de WHERE.
    new_code, new_hash = make_recovery_code()
    row = query(
        "UPDATE users SET password_hash = %s, recovery_hash = %s, session_version = session_version + 1"
        " WHERE id = %s AND recovery_hash = %s RETURNING id",
        (passwords.hash_password(password), new_hash, user.id, given), one=True,
    )
    if row is None:
        return render_template("login_forgot.html", error=FORGOT_WRONG), 400
    session.clear()
    # Niet automatisch ingelogd; wel meteen de nieuwe herstelcode, anders is er geen meer.
    return render_template("recovery_code.html", code=new_code, first=False, reset=True)


@bp.route("/logout", methods=["POST"])
def logout():
    # Versie omhoog: ook een gekopieerde cookie vervalt (MC-04), op alle apparaten.
    if g.user is not None:
        query("UPDATE users SET session_version = session_version + 1 WHERE id = %s", (g.user.id,))
    session.clear()
    return redirect(url_for("auth.login"))


# Controleert de TOTP-code uit het formulier: None als hij klopt, anders een CodeError.
def check_code(user_id):
    code_limit = throttle.limit("totp_account", user_id)
    user = query("SELECT totp_secret FROM users WHERE id = %s", (user_id,), one=True)
    # Niet te ontsleutelen (gewijzigd, verplaatst, andere sleutel) telt als geen geheim: dan wordt elke code geweigerd.
    secret = user and user.totp_secret and encryption.decrypt(user.totp_secret, "totp_secret", user_id)
    if not secret:
        return CodeError("Er is geen tweestapsverificatie ingesteld.", 0)
    # Op slot: dan wordt ook de juiste code geweigerd (MIT-06).
    if minutes := throttle.attempt(code_limit):
        return CodeError(throttle.message(minutes), minutes)
    step = totp.matching_step(secret, request.form.get("code", ""))
    # Eenmalig gebruik (MIT-07) en blokkade in één UPDATE: van twee verzoeken wint er één.
    if step is not None and query(
        "UPDATE users SET totp_last_step = %s"
        " WHERE id = %s AND (totp_last_step IS NULL OR totp_last_step < %s)"
        " AND NOT EXISTS (SELECT 1 FROM auth_throttle WHERE key = %s AND locked_until > now()) RETURNING id",
        (step, user_id, step, code_limit.key), one=True,
    ):
        throttle.succeeded(code_limit)
        return None
    # Fout, of al eens gebruikt: de poging is al geteld.
    return CodeError("Onjuiste of al gebruikte code.", 0)
