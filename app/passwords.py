# Regels voor een nieuw wachtwoord, het hashen en de controle: één plek voor alle routes.

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from db import query

# 12 tot 64 tekens en verder geen eisen aan cijfers of leestekens (MIT-13, NIST SP 800-63B-4).
PASSWORD_MIN = 12
PASSWORD_MAX = 64
# Argon2id met de minimale instelling van OWASP: 19 MiB, 2 iteraties, 1 thread. De salt maakt de library zelf (MIT-19).
_HASHER = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
# Voor een onbekende naam toch één berekening, zodat de responstijd niet verraadt of de naam bestaat (MC-09).
_NO_ACCOUNT = _HASHER.hash("geen account")


# De foutmelding als het nieuwe wachtwoord niet mag, anders None; repeat alleen waar het formulier herhaalt.
def password_problem(password, repeat=None):
    if not PASSWORD_MIN <= len(password) <= PASSWORD_MAX:
        return f"Kies een wachtwoord van {PASSWORD_MIN} tot {PASSWORD_MAX} tekens."
    if repeat is not None and password != repeat:
        return "De twee wachtwoorden zijn niet gelijk."
    return None


# Een nieuwe hash met een eigen salt; het wachtwoord zelf wordt nergens bewaard (MIT-19).
def hash_password(password):
    return _HASHER.hash(password)


# Hoort het wachtwoord bij deze hash? Zonder hash (onbekende naam) wordt er toch gerekend, en is het nee.
def matches(stored_hash, password):
    try:
        return _HASHER.verify(stored_hash or _NO_ACCOUNT, password) and stored_hash is not None
    except (VerificationError, InvalidHashError):
        return False


# Na een geslaagde login: is de hash met oudere instellingen gemaakt, dan nu een nieuwe (OWASP: bij de volgende login).
def rehash_if_needed(user_id, stored_hash, password):
    if _HASHER.check_needs_rehash(stored_hash):
        query("UPDATE users SET password_hash = %s WHERE id = %s", (hash_password(password), user_id))


# Klopt het huidige wachtwoord van dit account (AU-04)?
def is_current(user_id, password):
    row = query("SELECT password_hash FROM users WHERE id = %s", (user_id,), one=True)
    return matches(row and row.password_hash, password)
