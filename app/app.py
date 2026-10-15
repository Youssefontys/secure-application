"""Notitie-app: registreren, inloggen (met tweestapsverificatie als die aan staat),
wachtwoord wijzigen, account verwijderen en notities beheren.

De bekende zwakke plekken staan als misuse case in BoK/Threat Analysis/entries.md.
Waar zo'n zwakke plek in de code zit, staat het MC-nummer erbij.
"""

import io
import os
from datetime import datetime
from functools import wraps
from zoneinfo import ZoneInfo

import psycopg
import segno
from flask import Flask, Response, abort, flash, g, redirect, render_template, request, session, url_for
from psycopg.rows import namedtuple_row

import totp

# De website (HTML-templates en statische bestanden) staat in web/, los van de code.
app = Flask(__name__, template_folder="web/templates", static_folder="web/static")
# Flask heeft een sleutel nodig om de sessiecookie te ondertekenen.
app.secret_key = os.environ["FLASK_SECRET_KEY"]

DATABASE_URL = os.environ["DATABASE_URL"]
# De app is Nederlandstalig; tijden worden in Nederlandse tijd getoond.
TIMEZONE = "Europe/Amsterdam"
# Maximale lengte van een notitie, in tekens (MIT-04). Ook beschikbaar in de
# templates, voor maxlength.
TITLE_MAX = 15
BODY_MAX = 250
app.jinja_env.globals.update(TITLE_MAX=TITLE_MAX, BODY_MAX=BODY_MAX)
# Na zoveel foute codes op rij gaat de codestap van dat account op slot (MIT-06).
TOTP_MAX_FAILURES = 5
TOTP_LOCK_MINUTES = 15


def query(sql, params=(), one=False):
    """Voert één SQL-opdracht uit in een eigen verbinding, commit, en geeft de rijen terug.

    De waarden in params gaan los van de SQL-tekst naar de database, dus invoer
    wordt nooit als SQL uitgevoerd (MIT-02). Rijen zijn namedtuples, zodat code en
    templates `note.title` schrijven in plaats van `note[1]`. Tijden komen terug in
    TIMEZONE; de database zelf staat op UTC. Met one=True: de eerste rij of None.
    """
    with psycopg.connect(DATABASE_URL, row_factory=namedtuple_row, options=f"-c TimeZone={TIMEZONE}") as conn:
        cur = conn.execute(sql, params)
        rows = cur.fetchall() if cur.description else []
    return (rows[0] if rows else None) if one else rows


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


@app.before_request
def load_user():
    """Haalt de ingelogde gebruiker één keer per verzoek op, in g.user.

    Staat de id uit de sessie niet meer in de database, bijvoorbeeld omdat het
    account in een andere sessie is verwijderd, dan geldt het verzoek als niet
    ingelogd.
    """
    g.user = None
    user_id = session.get("user_id")
    if user_id is None or request.endpoint == "static":
        return
    g.user = query("SELECT id, username FROM users WHERE id = %s", (user_id,), one=True)


def login_required(view):
    """Alleen voor ingelogde gebruikers; de rest gaat naar /login (AU-02)."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapper


def logged_out_only(view):
    """Wie al is ingelogd, hoeft niet opnieuw in te loggen of te registreren."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if g.user is not None:
            return redirect(url_for("notes"))
        return view(*args, **kwargs)
    return wrapper


@app.route("/register", methods=["GET", "POST"])
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
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
@logged_out_only
def login():
    if request.method == "GET":
        return render_template("auth.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    row = query("SELECT id FROM users WHERE username = %s AND password = %s", (username, password), one=True)
    if row is None:
        return render_template("auth.html", error="Onjuiste gebruikersnaam of wachtwoord."), 401

    session.clear()
    session["user_id"] = row.id
    return redirect(url_for("notes"))


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/account")
@login_required
def account():
    return render_account()


def render_account(error=None, status=200):
    """De profielpagina, altijd van de ingelogde gebruiker zelf (AZ-08)."""
    profile = query(
        "SELECT username, created_at, totp_enabled,"
        " (SELECT count(*) FROM notes WHERE user_id = users.id) AS note_count"
        " FROM users WHERE id = %s",
        (g.user.id,), one=True,
    )
    return render_template("account.html", profile=profile, error=error), status


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
        return f"Te veel foute codes. Probeer het over {TOTP_LOCK_MINUTES} minuten opnieuw."
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
        return f"Te veel foute codes. Probeer het over {TOTP_LOCK_MINUTES} minuten opnieuw."
    return "Onjuiste of al gebruikte code."


@app.route("/account/2fa/start", methods=["POST"])
@login_required
def start_2fa():
    # Een nieuw geheim, nog niet actief. Pas na een eerste geldige code staat de
    # tweede factor aan, zodat je jezelf niet buitensluit met een verkeerd ingestelde app.
    query(
        "UPDATE users SET totp_secret = %s, totp_last_step = NULL WHERE id = %s AND NOT totp_enabled",
        (totp.new_secret(), g.user.id),
    )
    return redirect(url_for("setup_2fa"))


def no_store(response):
    """Pagina's met het TOTP-geheim niet in een browser- of proxycache laten staan."""
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/account/2fa", methods=["GET", "POST"])
@login_required
def setup_2fa():
    user = query("SELECT totp_secret, totp_enabled FROM users WHERE id = %s", (g.user.id,), one=True)
    if user.totp_enabled or user.totp_secret is None:
        return redirect(url_for("account"))
    # De sleutel in groepjes van vier, om over te typen als scannen niet lukt.
    grouped = " ".join(user.totp_secret[i:i + 4] for i in range(0, len(user.totp_secret), 4))
    if request.method == "GET":
        return no_store(app.make_response(render_template("setup_2fa.html", secret=grouped)))

    error = check_code(g.user.id)
    if error:
        return no_store(app.make_response((render_template("setup_2fa.html", secret=grouped, error=error), 400)))
    query("UPDATE users SET totp_enabled = true WHERE id = %s", (g.user.id,))
    flash("Tweestapsverificatie staat aan. Inloggen vraagt vanaf nu ook een code uit je app.")
    return redirect(url_for("account"))


@app.route("/account/2fa/qr.svg")
@login_required
def qr_2fa():
    # Alleen zolang het instellen loopt. Daarna is het geheim niet meer op te vragen.
    user = query("SELECT username, totp_secret FROM users WHERE id = %s AND NOT totp_enabled", (g.user.id,), one=True)
    if user is None or user.totp_secret is None:
        abort(404)
    svg = io.BytesIO()
    segno.make(totp.provisioning_uri(user.totp_secret, user.username), error="m").save(svg, kind="svg", scale=6, border=2)
    return no_store(Response(svg.getvalue(), mimetype="image/svg+xml"))


@app.route("/account/2fa/disable", methods=["POST"])
@login_required
def disable_2fa():
    # Uitzetten vraagt een geldige code: wie alleen de sessie heeft, kan de
    # tweede factor niet weghalen.
    error = check_code(g.user.id)
    if error:
        return render_account(error, 400)
    query(
        "UPDATE users SET totp_secret = NULL, totp_enabled = false, totp_last_step = NULL,"
        " totp_failures = 0, totp_locked_until = NULL WHERE id = %s",
        (g.user.id,),
    )
    flash("Tweestapsverificatie staat uit.")
    return redirect(url_for("account"))


@app.route("/account/password", methods=["POST"])
@login_required
def change_password():
    password = request.form.get("password", "")
    repeat = request.form.get("password_repeat", "")
    if not password:
        return render_account("Vul een nieuw wachtwoord in.", 400)
    if password != repeat:
        return render_account("De twee wachtwoorden zijn niet gelijk.", 400)

    # Het huidige wachtwoord wordt niet gevraagd: wie de sessie heeft, kan het
    # wachtwoord wijzigen. Andere sessies blijven geldig. Zie MC-12.
    query("UPDATE users SET password = %s WHERE id = %s", (password, g.user.id))
    flash("Je wachtwoord is gewijzigd.")
    return redirect(url_for("account"))


@app.route("/account/delete", methods=["POST"])
@login_required
def delete_account():
    # Ook hier wordt het wachtwoord niet opnieuw gevraagd: wie de sessie
    # heeft, kan het account verwijderen (MC-13). De notities gaan mee via
    # ON DELETE CASCADE in db/schema.sql; andere sessies van dit account
    # gelden daarna als uitgelogd (load_user).
    query("DELETE FROM users WHERE id = %s", (g.user.id,))
    session.clear()
    flash("Je account en je notities zijn verwijderd.")
    return redirect(url_for("login"))


@app.route("/", methods=["GET", "POST"])
@login_required
def notes():
    if request.method == "POST":
        title, body, error = read_note_form()
        if error:
            return render_template("notes.html", notes=fetch_notes(), error=error, title=title, body=body), 400
        query("INSERT INTO notes (user_id, title, body) VALUES (%s, %s, %s)", (g.user.id, title, body))
        return redirect(url_for("notes"))

    return render_template("notes.html", notes=fetch_notes())


def read_note_form():
    """Titel en inhoud uit het formulier, plus een foutmelding als er een leeg of te lang is."""
    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    error = None
    if not title or not body:
        error = "Vul een titel en een notitie in."
    elif len(title) > TITLE_MAX:
        error = f"De titel mag maximaal {TITLE_MAX} tekens zijn."
    elif len(body) > BODY_MAX:
        error = f"De notitie mag maximaal {BODY_MAX} tekens zijn."
    return title, body, error


def fetch_notes():
    return query(
        "SELECT id, title, body, created_at, updated_at FROM notes WHERE user_id = %s ORDER BY created_at DESC",
        (g.user.id,),
    )


@app.route("/notes/<int:note_id>/edit", methods=["GET", "POST"])
@login_required
def edit_note(note_id):
    # Alleen "ingelogd?" wordt gecontroleerd, niet of de notitie van jou is:
    # met het id van een ander lees en wijzig je zijn notitie (MC-02).
    note = query("SELECT title, body FROM notes WHERE id = %s", (note_id,), one=True)
    if note is None:
        abort(404)
    if request.method == "GET":
        return render_template("edit_note.html", title=note.title, body=note.body)

    title, body, error = read_note_form()
    if error:
        return render_template("edit_note.html", title=title, body=body, error=error), 400
    query("UPDATE notes SET title = %s, body = %s, updated_at = now() WHERE id = %s", (title, body, note_id))
    return redirect(url_for("notes"))


@app.route("/notes/<int:note_id>/delete", methods=["POST"])
@login_required
def delete_note(note_id):
    # Ook hier geen controle op de eigenaar (MC-02).
    query("DELETE FROM notes WHERE id = %s", (note_id,))
    return redirect(url_for("notes"))
