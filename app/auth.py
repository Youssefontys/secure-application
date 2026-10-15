"""Inloggen: registreren, het wachtwoord, de tweede stap met een TOTP-code, uitloggen.

Ook de decorators die bepalen wie een route mag openen, en de controle van een
TOTP-code, die het profiel ook gebruikt bij het aan- en uitzetten.
"""

import hashlib
import hmac
import re
import secrets
import time
from functools import wraps

import psycopg
from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

import throttle
import totp
from db import query

bp = Blueprint("auth", __name__)

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
    # Twee tellers (MIT-10): per IP-adres, en per account vanaf dat adres. Ze hangen
    # aan wat er is ingevuld, niet aan of het account bestaat, dus een blokkade
    # verraadt niet welke namen bestaan.
    ip = throttle.client_ip(request.remote_addr)
    ip_key = throttle.key("password_ip", ip)
    pair_key = throttle.key("password_account_ip", username, ip)
    minutes = throttle.locked_minutes(ip_key, pair_key)
    if minutes:
        return render_template("auth.html", error=throttle.message(minutes)), 429
    row = query(
        "SELECT id, totp_enabled, session_version FROM users WHERE username = %s AND password = %s",
        (username, password), one=True,
    )
    if row is None:
        minutes = max(throttle.fail("password_ip", ip_key), throttle.fail("password_account_ip", pair_key))
        if minutes:
            return render_template("auth.html", error=throttle.message(minutes)), 429
        return render_template("auth.html", error="Onjuiste gebruikersnaam of wachtwoord."), 401
    # Alleen de teller van dit account wordt gewist, niet die van het IP-adres:
    # anders zet een aanvaller die steeds even met zijn eigen account inlogt zijn
    # IP-teller telkens terug.
    throttle.reset(pair_key)

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


def pending_login():
    """De gebruiker van de halve login (na het wachtwoord), of None als die er niet meer is.

    Een halve login vervalt na PENDING_MAX_SECONDS, en ook als intussen de
    sessieversie is opgehoogd (nieuw wachtwoord, overal uitgelogd).
    """
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


@bp.route("/login/2fa", methods=["GET", "POST"])
@logged_out_only
def login_code():
    """De tweede stap: de code uit de authenticator-app (AU-05)."""
    user_id = pending_login()
    if user_id is None:
        return redirect(url_for("auth.login"))
    if request.method == "GET":
        return render_template("login_code.html")

    error = check_code(user_id)
    if error:
        return render_template("login_code.html", error=error), 401
    # Pas nu is de gebruiker ingelogd. start_session gooit de pending-sessie
    # weg, zodat er niets van de halve login overblijft.
    start_session(user_id, session["pending_version"])
    return redirect(url_for("notes.index"))


def new_recovery_code(user_id):
    """Maakt een nieuwe herstelcode voor dit account en geeft hem terug om één keer te tonen.

    128 willekeurige bits; alleen de SHA-256 wordt bewaard. Een snelle hash is hier
    genoeg: bij 128 willekeurige bits valt er niets te raden of op te zoeken, anders
    dan bij een wachtwoord dat iemand zelf verzint. Een eerdere code vervalt.
    """
    code = secrets.token_hex(16)
    query("UPDATE users SET recovery_hash = %s WHERE id = %s", (hashlib.sha256(code.encode()).hexdigest(), user_id))
    return "-".join(code[i:i + 4] for i in range(0, len(code), 4))


@bp.route("/login/recover", methods=["GET", "POST"])
@logged_out_only
def login_recover():
    """De herstelcode in plaats van de code uit de app, voor wie zijn telefoon kwijt is (AU-07)."""
    user_id = pending_login()
    if user_id is None:
        return redirect(url_for("auth.login"))
    if request.method == "GET":
        return render_template("login_recover.html")

    k = throttle.key("recovery_account", user_id)
    minutes = throttle.locked_minutes(k)
    if minutes:
        return render_template("login_recover.html", error=throttle.message(minutes)), 429
    given = hashlib.sha256(re.sub(r"[\s-]", "", request.form.get("code", "")).lower().encode()).hexdigest()
    stored = query("SELECT recovery_hash FROM users WHERE id = %s", (user_id,), one=True)
    if not (stored and stored.recovery_hash and hmac.compare_digest(given, stored.recovery_hash)):
        minutes = throttle.fail("recovery_account", k)
        error = throttle.message(minutes) if minutes else "Onjuiste herstelcode."
        return render_template("login_recover.html", error=error), 429 if minutes else 401
    # De code werkt één keer. Hij zet de tweede factor uit, want de telefoon is
    # kwijt, en maakt alle andere sessies ongeldig. De WHERE op de hash zorgt dat
    # twee gelijktijdige verzoeken hem niet allebei kunnen gebruiken.
    row = query(
        "UPDATE users SET recovery_hash = NULL, totp_secret = NULL, totp_enabled = false, totp_last_step = NULL,"
        " session_version = session_version + 1 WHERE id = %s AND recovery_hash = %s RETURNING session_version",
        (user_id, given), one=True,
    )
    if row is None:
        return render_template("login_recover.html", error="Onjuiste herstelcode."), 401
    throttle.reset(k)
    start_session(user_id, row.session_version)
    flash("Je herstelcode is gebruikt en je tweestapsverificatie staat uit. Stel hem opnieuw in met je nieuwe telefoon.")
    return redirect(url_for("account.index"))


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

    - Zit de codestap van dit account op slot, dan wordt ook de juiste code
      geweigerd (MIT-06, via throttle.py: 5 fouten, dan 15 minuten, verdubbelend tot 24 uur).
    - Een code die al eens is geaccepteerd, werkt niet nog een keer (MIT-07). RFC 6238
      5.2: de verifier MUST NOT accept the second attempt of the OTP.
    Beide controles staan in de WHERE van één UPDATE. Twee gelijktijdige verzoeken met
    dezelfde code kunnen er dus niet allebei door: de database laat er één winnen.
    """
    k = throttle.key("totp_account", user_id)
    user = query("SELECT totp_secret FROM users WHERE id = %s", (user_id,), one=True)
    if user is None or user.totp_secret is None:
        return "Er is geen tweestapsverificatie ingesteld."
    minutes = throttle.locked_minutes(k)
    if minutes:
        return throttle.message(minutes)
    step = totp.matching_step(user.totp_secret, request.form.get("code", ""))
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
    return throttle.message(minutes) if minutes else "Onjuiste of al gebruikte code."
