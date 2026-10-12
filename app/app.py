"""Baseline notitie-app: registreren, inloggen, notities beheren.

Bewust het minimale om te werken. Beveiliging komt stap voor stap erbij, en
elke stap krijgt een entry in BoK/Threat Analysis. Wat hier ontbreekt is dus
geen vergissing; de bekende gaten staan als misuse case in die map.
"""

import os

import psycopg
from flask import Flask, abort, redirect, render_template, request, session, url_for

# De website (HTML-templates en statische bestanden) staat in web/, los van de code.
app = Flask(__name__, template_folder="web/templates", static_folder="web/static")
# Flask heeft een sleutel nodig om de sessiecookie te ondertekenen.
app.secret_key = os.environ["FLASK_SECRET_KEY"]

DATABASE_URL = os.environ["DATABASE_URL"]


def db():
    """Nieuwe databaseverbinding per aanroep. Het with-blok commit bij succes."""
    return psycopg.connect(DATABASE_URL)


@app.route("/register", methods=["GET", "POST"])
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
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
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
    session["user_id"] = row[0]
    return redirect(url_for("notes"))


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/", methods=["GET", "POST"])
def notes():
    user_id = session.get("user_id")
    if user_id is None:
        return redirect(url_for("login"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()
        if not title or not body:
            return render_template(
                "notes.html", notes=fetch_notes(user_id), error="Vul een titel en een notitie in.",
                form_title=title, form_body=body,
            ), 400
        with db() as conn, conn.cursor() as cur:
            cur.execute("INSERT INTO notes (user_id, title, body) VALUES (%s, %s, %s)", (user_id, title, body))
        return redirect(url_for("notes"))

    return render_template("notes.html", notes=fetch_notes(user_id))


def fetch_notes(user_id):
    with db() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, title, body, created_at FROM notes WHERE user_id = %s ORDER BY created_at DESC",
            (user_id,),
        )
        return cur.fetchall()


@app.route("/notes/<int:note_id>/edit", methods=["GET", "POST"])
def edit_note(note_id):
    if session.get("user_id") is None:
        return redirect(url_for("login"))

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
            note = (title, body)
    return render_template("edit_note.html", title=note[0], body=note[1])


@app.route("/notes/<int:note_id>/delete", methods=["POST"])
def delete_note(note_id):
    if session.get("user_id") is None:
        return redirect(url_for("login"))
    # BASELINE: ook hier geen eigenaarscontrole, zie MC-02.
    with db() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM notes WHERE id = %s", (note_id,))
    return redirect(url_for("notes"))
