# Regels voor een nieuw wachtwoord en de controle van het huidige: één plek voor alle routes.

from db import query

# 12 tot 64 tekens en verder geen eisen aan cijfers of leestekens (MIT-13, NIST SP 800-63B-4).
PASSWORD_MIN = 12
PASSWORD_MAX = 64


# De foutmelding als het nieuwe wachtwoord niet mag, anders None; repeat alleen waar het formulier herhaalt.
def password_problem(password, repeat=None):
    if not PASSWORD_MIN <= len(password) <= PASSWORD_MAX:
        return f"Kies een wachtwoord van {PASSWORD_MIN} tot {PASSWORD_MAX} tekens."
    if repeat is not None and password != repeat:
        return "De twee wachtwoorden zijn niet gelijk."
    return None


# Klopt het huidige wachtwoord van dit account (AU-04)? Eén plek, zodat bij Argon2 alleen dit verandert.
def is_current(user_id, password):
    return query("SELECT 1 FROM users WHERE id = %s AND password = %s", (user_id, password), one=True) is not None
