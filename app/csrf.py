# CSRF token per session (MIT-20): every form sends it along, and another site does not know it (MC-05).

import hmac
import secrets

from flask import render_template, request, session

import events

# What the visitor sees if the token is missing or wrong.
REFUSED = "This form did not come from this site, or the page was too old. Reload the page and try again."


# The token of this session; the templates put it in every form.
def token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


# Every POST without the right token is refused, even if the browser sends the cookie along.
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
