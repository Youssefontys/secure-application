"""Baseline notitie-app: registreren, inloggen, notities beheren.

Bewust het minimale om te werken. Beveiliging komt stap voor stap erbij, en
elke stap krijgt een entry in BoK/Threat Analysis. Wat hier ontbreekt is dus
geen vergissing; de bekende gaten staan als misuse case in die map.
"""

import os
from functools import wraps

import psycopg
from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for
from psycopg.rows import namedtuple_row

# De website (HTML-templates en statische bestanden) staat in web/, los van de code.
app = Flask(__name__, template_folder="web/templates", static_folder="web/static")
# Flask heeft een sleutel nodig om de sessiecookie te ondertekenen.
app.secret_key = os.environ["FLASK_SECRET_KEY"]

DATABASE_URL = os.environ["DATABASE_URL"]


def db():
    """Nieuwe databaseverbinding per aanroep. Het with-blok commit bij succes.

    Rijen komen terug als namedtuple, zodat code en templates `note.title`
    schrijven in plaats van `note[1]`.
    """
    return psycopg.connect(DATABASE_URL, row_factory=namedtuple_row)


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
    with db() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, username FROM users WHERE id = %s", (user_id,))
        g.user = cur.fetchone()


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
        return render_template("register.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    if not username or not password:
        return render_template("register.html", error="Vul een gebruikersnaam en wachtwoord in."), 400

    try:
        with db() as conn, conn.cursor() as cur:
            # De waarden gaan los van de SQL-tekst mee (psycopg), dus invoer
            # wordt nooit als SQL uitgevoerd.
            cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
    except psycopg.errors.UniqueViolation:
        return render_template("register.html", error="Die gebruikersnaam is al in gebruik."), 409
    flash("Je account is aangemaakt. Je kunt nu inloggen.")
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
@logged_out_only
def login():
    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    with db() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM users WHERE username = %s AND password = %s", (username, password))
        row = cur.fetchone()
    if row is None:
        return render_template("login.html", error="Onjuiste gebruikersnaam of wachtwoord."), 401

    session.clear()
    session["user_id"] = row.id
    return redirect(url_for("notes"))


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/account/password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "GET":
        return render_template("change_password.html")

    password = request.form.get("password", "")
    repeat = request.form.get("password_repeat", "")
    if not password:
        return render_template("change_password.html", error="Vul een nieuw wachtwoord in."), 400
    if password != repeat:
        return render_template("change_password.html", error="De twee wachtwoorden zijn niet gelijk."), 400

    # Het huidige wachtwoord wordt niet gevraagd: wie de sessie heeft, kan het
    # wachtwoord wijzigen. Andere sessies blijven geldig. Zie MC-12.
    with db() as conn, conn.cursor() as cur:
        cur.execute("UPDATE users SET password = %s WHERE id = %s", (password, g.user.id))
    flash("Je wachtwoord is gewijzigd.")
    return redirect(url_for("notes"))


@app.route("/", methods=["GET", "POST"])
@login_required
def notes():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()
        if not title or not body:
            return render_template(
                "notes.html", notes=fetch_notes(), error="Vul een titel en een notitie in.",
                form_title=title, form_body=body,
            ), 400
        with db() as conn, conn.cursor() as cur:
            cur.execute("INSERT INTO notes (user_id, title, body) VALUES (%s, %s, %s)", (g.user.id, title, body))
        return redirect(url_for("notes"))

    return render_template("notes.html", notes=fetch_notes())


def fetch_notes():
    with db() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, title, body, created_at FROM notes WHERE user_id = %s ORDER BY created_at DESC",
            (g.user.id,),
        )
        return cur.fetchall()


@app.route("/notes/<int:note_id>/edit", methods=["GET", "POST"])
@login_required
def edit_note(note_id):
    # BASELINE: er wordt gecontroleerd of je bent ingelogd, maar niet of de
    # notitie van jou is. Zie MC-02 in BoK/Threat Analysis.
    with db() as conn, conn.cursor() as cur:
        cur.execute("SELECT title, body FROM notes WHERE id = %s", (note_id,))
        note = cur.fetchone()
        if note is None:
            abort(404)
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            body = request.form.get("body", "").strip()
            if title and body:
                cur.execute("UPDATE notes SET title = %s, body = %s WHERE id = %s", (title, body, note_id))
                return redirect(url_for("notes"))
            return render_template("edit_note.html", title=title, body=body)
    return render_template("edit_note.html", title=note.title, body=note.body)


@app.route("/notes/<int:note_id>/delete", methods=["POST"])
@login_required
def delete_note(note_id):
    # BASELINE: ook hier geen eigenaarscontrole, zie MC-02.
    with db() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM notes WHERE id = %s", (note_id,))
    return redirect(url_for("notes"))
