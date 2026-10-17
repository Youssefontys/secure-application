# CSRF-token per sessie (MIT-20): elk formulier stuurt het mee, en een andere site kent het niet (MC-05).

import hmac
import secrets

from flask import render_template, request, session

# Wat de bezoeker ziet als het token ontbreekt of niet klopt.
REFUSED = "Dit formulier kwam niet van deze site, of de pagina was te oud. Laad de pagina opnieuw en probeer het nog eens."


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
    if request.method == "POST":
        sent = request.form.get("csrf_token", "")
        if not hmac.compare_digest(sent.encode(), expected.encode()):
            return render_template("error.html", message=REFUSED), 400
    return None
