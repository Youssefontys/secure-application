# CSRF-token per sessie (MIT-20): elk formulier stuurt het mee, en een andere site kent het niet (MC-05).

import hmac
import secrets

from flask import render_template, request, session


# Het token van deze sessie; de templates zetten het in elk formulier.
def token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


# Elke POST zonder het juiste token wordt geweigerd, ook als de browser de cookie meestuurt.
def check():
    if request.endpoint == "static":
        return None
    expected = token()
    if request.method == "POST" and not hmac.compare_digest(request.form.get("csrf_token", "").encode(), expected.encode()):
        return render_template("error.html", message="Dit formulier kwam niet van deze site, of de pagina was te oud. Laad de pagina opnieuw en probeer het nog eens."), 400
    return None
