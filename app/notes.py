# Notities: aanmaken, tonen, aanpassen en verwijderen.

from flask import Blueprint, abort, g, redirect, render_template, request, url_for

import encryption
from auth import login_required
from db import query

bp = Blueprint("notes", __name__)

# Maximale lengte in tekens (MIT-04); de templates gebruiken ze ook voor maxlength.
TITLE_MAX = 15
BODY_MAX = 250
# Wat er staat als een titel of inhoud niet ontsleutelt (gewijzigd, verplaatst of een andere sleutel).
UNREADABLE = "(niet te lezen)"


@bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        title, body, error = read_note_form()
        if error:
            return render_template("notes.html", notes=fetch_notes(), error=error, title=title, body=body), 400
        query("INSERT INTO notes (user_id, title, body) VALUES (%s, %s, %s)", (g.user.id, *sealed(title, body)))
        return redirect(url_for("notes.index"))

    return render_template("notes.html", notes=fetch_notes())


# Titel en inhoud uit het formulier, plus een foutmelding als er een leeg of te lang is.
def read_note_form():
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
    rows = query(
        "SELECT id, title, body, created_at, updated_at FROM notes WHERE user_id = %s ORDER BY created_at DESC",
        (g.user.id,),
    )
    return [readable(note) for note in rows]


# Titel en inhoud staan alleen versleuteld in de database, gebonden aan de eigenaar (MIT-18).
def sealed(title, body):
    return encryption.encrypt(title, "note_title", g.user.id), encryption.encrypt(body, "note_body", g.user.id)


# Ontsleuteld voor de pagina; wat niet ontsleutelt, telt niet als tekst van de gebruiker.
def readable(note):
    return note._replace(
        title=encryption.decrypt(note.title, "note_title", g.user.id) or UNREADABLE,
        body=encryption.decrypt(note.body, "note_body", g.user.id) or UNREADABLE,
    )


# De notitie van de ingelogde gebruiker, anders 404: ook andermans notitie lijkt niet te bestaan (MIT-15).
def own_note(note_id):
    note = query("SELECT title, body FROM notes WHERE id = %s AND user_id = %s", (note_id, g.user.id), one=True)
    if note is None:
        abort(404)
    return readable(note)


@bp.route("/notes/<int:note_id>/edit", methods=["GET", "POST"])
@login_required
def edit_note(note_id):
    note = own_note(note_id)
    if request.method != "POST":
        return render_template("edit_note.html", title=note.title, body=note.body)

    title, body, error = read_note_form()
    if error:
        return render_template("edit_note.html", title=title, body=body, error=error), 400
    query(
        "UPDATE notes SET title = %s, body = %s, updated_at = now() WHERE id = %s AND user_id = %s",
        (*sealed(title, body), note_id, g.user.id),
    )
    return redirect(url_for("notes.index"))


@bp.route("/notes/<int:note_id>/delete", methods=["POST"])
@login_required
def delete_note(note_id):
    # Alleen de eigen notitie; andermans notitie geeft 404, net als bij aanpassen (MIT-15).
    if query("DELETE FROM notes WHERE id = %s AND user_id = %s RETURNING id", (note_id, g.user.id), one=True) is None:
        abort(404)
    return redirect(url_for("notes.index"))
