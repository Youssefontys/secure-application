# Regels voor een nieuw wachtwoord, het hashen en de controle: één plek voor alle routes.

import os

from cryptography.exceptions import InvalidKey
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id

from db import query

# 12 tot 64 tekens en verder geen eisen aan cijfers of leestekens (MIT-13, NIST SP 800-63B-4).
PASSWORD_MIN = 12
PASSWORD_MAX = 64
# Argon2id met de minimale instelling van OWASP: 19 MiB, 2 iteraties, 1 thread (MIT-19).
_PARAMS = {"memory_cost": 19456, "iterations": 2, "lanes": 1}
# Zo begint een hash met deze instellingen (PHC-formaat); een andere krijgt bij de login een nieuwe hash.
_CURRENT = f"$argon2id$v=19$m={_PARAMS['memory_cost']},t={_PARAMS['iterations']},p={_PARAMS['lanes']}$"


# Een nieuwe hash met een eigen salt van 128 bits; het wachtwoord zelf wordt nergens bewaard (MIT-19).
def hash_password(password):
    return Argon2id(salt=os.urandom(16), length=32, **_PARAMS).derive_phc_encoded(password.encode())


# Voor een onbekende naam toch één berekening, zodat de responstijd niet verraadt of de naam bestaat (MC-09).
_NO_ACCOUNT = hash_password("geen account")


# De foutmelding als het nieuwe wachtwoord niet mag, anders None; repeat alleen waar het formulier herhaalt.
def password_problem(password, repeat=None):
    if not PASSWORD_MIN <= len(password) <= PASSWORD_MAX:
        return f"Choose a password of {PASSWORD_MIN} to {PASSWORD_MAX} characters."
    if repeat is not None and password != repeat:
        return "The two passwords do not match."
    return None


# Hoort het wachtwoord bij deze hash? Zonder hash (onbekende naam) wordt er toch gerekend, en is het nee.
def matches(stored_hash, password):
    try:
        Argon2id.verify_phc_encoded(password.encode(), stored_hash or _NO_ACCOUNT)
    except InvalidKey:
        return False
    return stored_hash is not None


# Na een geslaagde login: is de hash met oudere instellingen gemaakt, dan nu een nieuwe (OWASP: bij de volgende login).
def rehash_if_needed(user_id, stored_hash, password):
    if not stored_hash.startswith(_CURRENT):
        query("UPDATE users SET password_hash = %s WHERE id = %s", (hash_password(password), user_id))


# Klopt het huidige wachtwoord van dit account (AU-04)?
def is_current(user_id, password):
    row = query("SELECT password_hash FROM users WHERE id = %s", (user_id,), one=True)
    return matches(row and row.password_hash, password)
