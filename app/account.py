# Het eigen account: profiel, tweestapsverificatie, wachtwoord wijzigen, account verwijderen.

import io

import segno
from flask import Blueprint, Response, abort, flash, g, redirect, render_template, request, session, url_for

import passwords
import throttle
import totp
from auth import check_code, end_other_sessions, login_required, new_recovery_code
from db import query

bp = Blueprint("account", __name__, url_prefix="/account")


@bp.route("")
@login_required
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


# Geheim en herstelcode niet in een browser- of proxycache laten staan (MIT-08, MIT-11).
@bp.after_request
def no_store(response):
    if request.endpoint in ("account.setup_2fa", "account.qr_2fa", "account.new_recovery"):
        response.headers["Cache-Control"] = "no-store"
    return response


@bp.route("/2fa", methods=["GET", "POST"])
@login_required
def setup_2fa():
    if g.user.totp_enabled:
        return redirect(url_for("account.index"))
    # Een nieuw geheim telt pas na een eerste geldige code, zodat je jezelf niet buitensluit.
    query(
        "UPDATE users SET totp_secret = %s, totp_last_step = NULL WHERE id = %s AND totp_secret IS NULL",
        (totp.new_secret(), g.user.id),
    )
    user = query("SELECT totp_secret FROM users WHERE id = %s", (g.user.id,), one=True)
    # De sleutel in groepjes van vier, om over te typen als scannen niet lukt.
    grouped = " ".join(user.totp_secret[i:i + 4] for i in range(0, len(user.totp_secret), 4))
    if request.method == "GET":
        return render_template("setup_2fa.html", secret=grouped)

    error = check_code(g.user.id)
    if error:
        return render_template("setup_2fa.html", secret=grouped, error=error.message), *throttle.refusal(error.minutes)
    query("UPDATE users SET totp_enabled = true WHERE id = %s", (g.user.id,))
    # Sessies van vóór de tweede factor zijn met alleen een wachtwoord gestart.
    end_other_sessions(g.user.id)
    # De herstelcode staat alleen in dit ene antwoord, nergens later terug te zien (MIT-11).
    return render_template("recovery_code.html", code=new_recovery_code(g.user.id), first=True)


@bp.route("/2fa/recovery", methods=["POST"])
@login_required
def new_recovery():
    # Vraagt een code uit de app: met alleen de sessie krijg je geen herstelcode (AU-06).
    error = check_code(g.user.id)
    if error:
        return render_account(error.message, *throttle.refusal(error.minutes))
    return render_template("recovery_code.html", code=new_recovery_code(g.user.id), first=False)


@bp.route("/2fa/qr.svg")
@login_required
def qr_2fa():
    # Alleen zolang het instellen loopt; daarna is het geheim niet meer op te vragen.
    user = query("SELECT username, totp_secret FROM users WHERE id = %s AND NOT totp_enabled", (g.user.id,), one=True)
    if user is None or user.totp_secret is None:
        abort(404)
    svg = io.BytesIO()
    segno.make(totp.provisioning_uri(user.totp_secret, user.username), error="m").save(svg, kind="svg", scale=6, border=2)
    return Response(svg.getvalue(), mimetype="image/svg+xml")


# Opnieuw instellen voor een nieuwe telefoon; daarna kan alleen het instellen nog (MIT-12).
@bp.route("/2fa/reset", methods=["POST"])
@login_required
def reset_2fa():
    # Vraagt een code: met alleen de sessie haal je de tweede factor niet weg (AU-06).
    error = check_code(g.user.id)
    if error:
        return render_account(error.message, *throttle.refusal(error.minutes))
    query(
        "UPDATE users SET totp_secret = NULL, totp_enabled = false, totp_last_step = NULL, recovery_hash = NULL"
        " WHERE id = %s",
        (g.user.id,),
    )
    end_other_sessions(g.user.id)
    flash("Stel tweestapsverificatie opnieuw in met je nieuwe telefoon.")
    return redirect(url_for("account.setup_2fa"))


@bp.route("/password", methods=["POST"])
@login_required
def change_password():
    password = request.form.get("password", "")
    error = passwords.password_problem(password, request.form.get("password_repeat", ""))
    if error:
        return render_account(error, 400)

    # Vraagt het huidige wachtwoord niet (MC-12); andere sessies vervallen wel (MIT-09).
    query("UPDATE users SET password = %s WHERE id = %s", (password, g.user.id))
    end_other_sessions(g.user.id)
    flash("Je wachtwoord is gewijzigd.")
    return redirect(url_for("account.index"))


@bp.route("/delete", methods=["POST"])
@login_required
def delete_account():
    # Vraagt het wachtwoord niet opnieuw (MC-13).
    # De notities gaan mee via ON DELETE CASCADE; andere sessies vervallen via load_user.
    query("DELETE FROM users WHERE id = %s", (g.user.id,))
    session.clear()
    flash("Je account en je notities zijn verwijderd.")
    return redirect(url_for("auth.login"))
