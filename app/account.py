# Het eigen account: profiel, tweestapsverificatie, wachtwoord wijzigen, account verwijderen.

import io

import segno
from flask import Blueprint, Response, abort, flash, g, redirect, render_template, request, session, url_for

import encryption
import passwords
import throttle
import totp
from auth import check_code, keep_this_session, new_recovery_code
from db import query

bp = Blueprint("account", __name__, url_prefix="/account")


@bp.route("")
def index():
    return render_account()


# De profielpagina, altijd van de ingelogde gebruiker zelf (AZ-08).
def render_account(error=None, status=200, headers=None):
    profile = query(
        "SELECT username, created_at, totp_enabled,"
        " (SELECT count(*) FROM notes WHERE user_id = users.id) AS note_count"
        " FROM users WHERE id = %s",
        (g.user.id,), one=True,
    )
    return render_template("account.html", profile=profile, error=error), status, headers or {}


@bp.route("/2fa", methods=["GET", "POST"])
def setup_2fa():
    if g.user.totp_enabled:
        return redirect(url_for("account.index"))
    # Een nieuw geheim telt pas na een eerste geldige code, zodat je jezelf niet buitensluit.
    # Het geheim staat alleen versleuteld in de database (MIT-17).
    query(
        "UPDATE users SET totp_secret = %s, totp_last_step = NULL WHERE id = %s AND totp_secret IS NULL",
        (encryption.encrypt(totp.new_secret(), "totp_secret", g.user.id), g.user.id),
    )
    user = query("SELECT totp_secret FROM users WHERE id = %s", (g.user.id,), one=True)
    secret = encryption.decrypt(user.totp_secret, "totp_secret", g.user.id)
    # Ontsleutelt niet meer (bijvoorbeeld een nieuwe sleutel): het geheim werkte nog nergens, dus opnieuw beginnen.
    if secret is None:
        query("UPDATE users SET totp_secret = NULL WHERE id = %s AND NOT totp_enabled", (g.user.id,))
        return redirect(url_for("account.setup_2fa"))
    # De sleutel in groepjes van vier, om over te typen als scannen niet lukt.
    grouped = " ".join(secret[i:i + 4] for i in range(0, len(secret), 4))
    if request.method != "POST":
        return render_template("setup_2fa.html", secret=grouped)

    if error := check_code(g.user.id):
        return render_template("setup_2fa.html", secret=grouped, error=error.message), *throttle.refusal(error.minutes)
    # Sessies van vóór de tweede factor zijn met alleen een wachtwoord gestart; die vervallen nu.
    keep_this_session(query(
        "UPDATE users SET totp_enabled = true, session_version = session_version + 1"
        " WHERE id = %s RETURNING session_version",
        (g.user.id,), one=True,
    ))
    # De herstelcode staat alleen in dit ene antwoord, nergens later terug te zien (MIT-11).
    return render_template("recovery_code.html", code=new_recovery_code(g.user.id), first=True)


@bp.route("/2fa/recovery", methods=["POST"])
def new_recovery():
    # Vraagt een code uit de app: met alleen de sessie krijg je geen herstelcode (AU-06).
    if error := check_code(g.user.id):
        return render_account(error.message, *throttle.refusal(error.minutes))
    return render_template("recovery_code.html", code=new_recovery_code(g.user.id), first=False)


@bp.route("/2fa/qr.svg")
def qr_2fa():
    # Alleen zolang het instellen loopt; daarna is het geheim niet meer op te vragen.
    user = query("SELECT username, totp_secret FROM users WHERE id = %s AND NOT totp_enabled", (g.user.id,), one=True)
    secret = user and user.totp_secret and encryption.decrypt(user.totp_secret, "totp_secret", g.user.id)
    if not secret:
        abort(404)
    svg = io.BytesIO()
    segno.make(totp.provisioning_uri(secret, user.username), error="m").save(svg, kind="svg", scale=6, border=2)
    return Response(svg.getvalue(), mimetype="image/svg+xml")


# Opnieuw instellen voor een nieuwe telefoon; daarna kan alleen het instellen nog (MIT-12).
@bp.route("/2fa/reset", methods=["POST"])
def reset_2fa():
    # Vraagt een code: met alleen de sessie haal je de tweede factor niet weg (AU-06).
    if error := check_code(g.user.id):
        return render_account(error.message, *throttle.refusal(error.minutes))
    keep_this_session(query(
        "UPDATE users SET totp_secret = NULL, totp_enabled = false, totp_last_step = NULL, recovery_hash = NULL,"
        " session_version = session_version + 1 WHERE id = %s RETURNING session_version",
        (g.user.id,), one=True,
    ))
    flash("Stel tweestapsverificatie opnieuw in met je nieuwe telefoon.")
    return redirect(url_for("account.setup_2fa"))


# Het huidige wachtwoord opnieuw vragen, met een limiet per account (MIT-16): None als het klopt.
def refuse_without_password():
    reauth_limit = throttle.limit("reauth_account", g.user.id)
    if minutes := throttle.attempt(reauth_limit):
        return render_account(throttle.message(minutes), *throttle.refusal(minutes))
    if not passwords.is_current(g.user.id, request.form.get("current_password", "")):
        return render_account("Je huidige wachtwoord klopt niet.", 400)
    throttle.succeeded(reauth_limit)
    return None


@bp.route("/password", methods=["POST"])
def change_password():
    password = request.form.get("password", "")
    if error := passwords.password_problem(password, request.form.get("password_repeat", "")):
        return render_account(error, 400)
    if refused := refuse_without_password():
        return refused

    # Alle andere sessies vervallen, in dezelfde UPDATE als het nieuwe wachtwoord (MIT-09).
    keep_this_session(query(
        "UPDATE users SET password_hash = %s, session_version = session_version + 1 WHERE id = %s RETURNING session_version",
        (passwords.hash_password(password), g.user.id), one=True,
    ))
    flash("Je wachtwoord is gewijzigd.")
    return redirect(url_for("account.index"))


@bp.route("/delete", methods=["POST"])
def delete_account():
    if refused := refuse_without_password():
        return refused
    # De notities gaan mee via ON DELETE CASCADE; andere sessies vervallen via load_user.
    query("DELETE FROM users WHERE id = %s", (g.user.id,))
    session.clear()
    flash("Je account en je notities zijn verwijderd.")
    return redirect(url_for("auth.login"))
