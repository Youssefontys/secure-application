# Rules for a new password, the hashing and the check: one place for all routes.

import os

from cryptography.exceptions import InvalidKey
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id

from db import query

# 12 to 64 characters and no further rules on digits or punctuation (MIT-13, NIST SP 800-63B-4).
PASSWORD_MIN = 12
PASSWORD_MAX = 64
# Argon2id with the minimum setting of OWASP: 19 MiB, 2 iterations, 1 thread (MIT-19).
_PARAMS = {"memory_cost": 19456, "iterations": 2, "lanes": 1}
# This is how a hash with these settings starts (PHC format); another one gets a new hash at the login.
_CURRENT = f"$argon2id$v=19$m={_PARAMS['memory_cost']},t={_PARAMS['iterations']},p={_PARAMS['lanes']}$"


# A new hash with its own salt of 128 bits; the password itself is stored nowhere (MIT-19).
def hash_password(password):
    return Argon2id(salt=os.urandom(16), length=32, **_PARAMS).derive_phc_encoded(password.encode())


# For an unknown name still one calculation, so the response time does not reveal whether the name exists (MC-09).
_NO_ACCOUNT = hash_password("no account")


# The error message if the new password is not allowed, otherwise None; repeat only where the form repeats it.
def password_problem(password, repeat=None):
    if not PASSWORD_MIN <= len(password) <= PASSWORD_MAX:
        return f"Choose a password of {PASSWORD_MIN} to {PASSWORD_MAX} characters."
    if repeat is not None and password != repeat:
        return "The two passwords do not match."
    return None


# Does the password belong to this hash? Without a hash (unknown name) it still calculates, and the answer is no.
def matches(stored_hash, password):
    try:
        Argon2id.verify_phc_encoded(password.encode(), stored_hash or _NO_ACCOUNT)
    except InvalidKey:
        return False
    return stored_hash is not None


# After a successful login: if the hash was made with older settings, make a new one now (OWASP: at the next login).
def rehash_if_needed(user_id, stored_hash, password):
    if not stored_hash.startswith(_CURRENT):
        query("UPDATE users SET password_hash = %s WHERE id = %s", (hash_password(password), user_id))


# Is this the current password of this account (AU-04)?
def is_current(user_id, password):
    row = query("SELECT password_hash FROM users WHERE id = %s", (user_id,), one=True)
    return matches(row and row.password_hash, password)
