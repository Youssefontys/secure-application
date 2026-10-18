# CSRF-token per sessie (MIT-20): elk formulier stuurt het mee, en een andere site kent het niet (MC-05).

import hmac
import secrets

from flask import render_template, request, session

import events

# Wat de bezoeker ziet als het token ontbreekt of niet klopt.
REFUSED = "This form did not come from this site, or the page was too old. Reload the page and try again."


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
            events.event("csrf_refused", endpoint=request.endpoint)
            return render_template("error.html", code=400, message=REFUSED), 400
    return None
