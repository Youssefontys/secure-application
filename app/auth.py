"""Inloggen: registreren, het wachtwoord, de tweede stap met een TOTP-code, uitloggen.

Ook de decorators die bepalen wie een route mag openen, en de controle van een
TOTP-code, die het profiel ook gebruikt bij het aan- en uitzetten.
"""

import time
from functools import wraps

import psycopg
from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

import totp
from db import query

bp = Blueprint("auth", __name__)

# Na zoveel foute codes op rij gaat de codestap van dat account op slot (MIT-06).
TOTP_MAX_FAILURES = 5
TOTP_LOCK_MINUTES = 15
TOTP_LOCKED = f"Te veel foute codes. Probeer het over {TOTP_LOCK_MINUTES} minuten opnieuw."
# Zo lang heb je na het wachtwoord om de code in te vullen.
PENDING_MAX_SECONDS = 300


@bp.before_app_request
def load_user():
    """Haalt de ingelogde gebruiker één keer per verzoek op, in g.user.

    De sessie telt alleen als het account nog bestaat en de sessieversie in de
    cookie gelijk is aan die in de database (MIT-09). Na uitloggen, een nieuw
    wachtwoord of een wijziging aan de tweestapsverificatie is de versie in de
    database opgehoogd, en dan werkt een oudere cookie niet meer, ook geen kopie.
    """
    g.user = None
    user_id = session.get("user_id")
    if user_id is None or request.endpoint == "static":
        return
    user = query("SELECT id, username, session_version FROM users WHERE id = %s", (user_id,), one=True)
    if user is None or user.session_version != session.get("session_version"):
        session.clear()
        flash("Je sessie is niet meer geldig. Log opnieuw in.")
        return
    g.user = user


def start_session(user_id, version):
    """Een verse sessie voor deze gebruiker, met zijn huidige sessieversie."""
    session.clear()
    session["user_id"] = user_id
    session["session_version"] = version


def end_other_sessions(user_id):
    """Hoogt de sessieversie op, zodat elke andere sessie van dit account niet meer telt.

    De huidige sessie krijgt de nieuwe versie en blijft dus geldig.
    """
    row = query(
        "UPDATE users SET session_version = session_version + 1 WHERE id = %s RETURNING session_version",
        (user_id,), one=True,
    )
    session["session_version"] = row.session_version


def login_required(view):
    """Alleen voor ingelogde gebruikers; de rest gaat naar /login (AU-02)."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapper


def logged_out_only(view):
    """Wie al is ingelogd, hoeft niet opnieuw in te loggen of te registreren."""
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
    row = query(
        "SELECT id, totp_enabled, session_version FROM users WHERE username = %s AND password = %s",
        (username, password), one=True,
    )
    if row is None:
        return render_template("auth.html", error="Onjuiste gebruikersnaam of wachtwoord."), 401

    session.clear()
    if row.totp_enabled:
        # Het wachtwoord is pas de eerste factor. De sessie krijgt alleen een
        # pending_user_id; daarmee kom je nergens in, want login_required en
        # load_user kijken naar user_id (MIT-05).
        session["pending_user_id"] = row.id
        session["pending_version"] = row.session_version
        session["pending_since"] = int(time.time())
        return redirect(url_for("auth.login_code"))
    start_session(row.id, row.session_version)
    return redirect(url_for("notes.index"))


@bp.route("/login/2fa", methods=["GET", "POST"])
@logged_out_only
def login_code():
    """De tweede stap: de code uit de authenticator-app (AU-05)."""
    user_id = session.get("pending_user_id")
    if user_id is None:
        return redirect(url_for("auth.login"))
    if time.time() - session.get("pending_since", 0) > PENDING_MAX_SECONDS:
        session.clear()
        flash("Dat duurde te lang. Log opnieuw in.")
        return redirect(url_for("auth.login"))
    # Is intussen het wachtwoord gewijzigd of overal uitgelogd, dan vervalt ook
    # deze halve login.
    version = query("SELECT session_version FROM users WHERE id = %s", (user_id,), one=True)
    if version is None or version.session_version != session.get("pending_version"):
        session.clear()
        flash("Je sessie is niet meer geldig. Log opnieuw in.")
        return redirect(url_for("auth.login"))
    if request.method == "GET":
        return render_template("login_code.html")

    error = check_code(user_id)
    if error:
        return render_template("login_code.html", error=error), 401
    # Pas nu is de gebruiker ingelogd. start_session gooit de pending-sessie
    # weg, zodat er niets van de halve login overblijft.
    start_session(user_id, version.session_version)
    return redirect(url_for("notes.index"))


@bp.route("/logout", methods=["POST"])
def logout():
    # Uitloggen hoogt de sessieversie op: ook een gekopieerde cookie werkt daarna
    # niet meer (MC-04). De prijs: alle apparaten van dit account zijn uitgelogd.
    # Preciezer kan alleen met sessies die op de server worden bijgehouden.
    if g.user is not None:
        query("UPDATE users SET session_version = session_version + 1 WHERE id = %s", (g.user.id,))
    session.clear()
    return redirect(url_for("auth.login"))


def check_code(user_id):
    """Controleert de TOTP-code uit het formulier voor dit account. None als hij klopt, anders de foutmelding.

    - Zit de codestap op slot, dan wordt ook de juiste code geweigerd (MIT-06).
    - Een code die al eens is geaccepteerd, werkt niet nog een keer (MIT-07). RFC 6238
      5.2: de verifier MUST NOT accept the second attempt of the OTP.
    Beide controles staan in de WHERE van één UPDATE. Twee gelijktijdige verzoeken met
    dezelfde code kunnen er dus niet allebei door: de database laat er één winnen.
    """
    user = query("SELECT totp_secret, totp_locked_until > now() AS locked FROM users WHERE id = %s", (user_id,), one=True)
    if user is None or user.totp_secret is None:
        return "Er is geen tweestapsverificatie ingesteld."
    if user.locked:
        return TOTP_LOCKED
    step = totp.matching_step(user.totp_secret, request.form.get("code", ""))
    if step is not None and query(
        "UPDATE users SET totp_last_step = %s, totp_failures = 0, totp_locked_until = NULL"
        " WHERE id = %s AND (totp_last_step IS NULL OR totp_last_step < %s)"
        " AND (totp_locked_until IS NULL OR totp_locked_until <= now()) RETURNING id",
        (step, user_id, step), one=True,
    ):
        return None
    # Fout, of al eens gebruikt: telt als mislukte poging. De teller staat in de
    # database en niet in de sessie, want een sessie kan de aanvaller gewoon opnieuw beginnen.
    locked = query(
        "UPDATE users SET"
        " totp_locked_until = CASE WHEN totp_failures + 1 >= %(max)s"
        "   THEN now() + make_interval(mins => %(mins)s) ELSE totp_locked_until END,"
        " totp_failures = CASE WHEN totp_failures + 1 >= %(max)s THEN 0 ELSE totp_failures + 1 END"
        " WHERE id = %(id)s RETURNING totp_locked_until > now() AS locked",
        {"max": TOTP_MAX_FAILURES, "mins": TOTP_LOCK_MINUTES, "id": user_id}, one=True,
    )
    if locked and locked.locked:
        return TOTP_LOCKED
    return "Onjuiste of al gebruikte code."
