# Regels voor een nieuw wachtwoord: één plek voor registreren, wijzigen en herstellen.

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
