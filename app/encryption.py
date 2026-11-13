# Encryption of data the app must be able to read back: the TOTP secret and the notes (MIT-17, MIT-18).

import base64
import os
import re

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _key(name):
    key = bytes.fromhex(os.environ[name])
    if len(key) != 32:
        raise RuntimeError(f"{name} must be 64 hex characters (256 bits).")
    return key


# 256 bits, outside the database: locally from .env, on Azure from Key Vault (A-09).
# Goes into every stored value as a version, so a new key can sit next to the old one (key rotation, see rotate_key.py).
KEY_VERSION = os.environ.get("DATA_ENCRYPTION_KEY_VERSION", "v1")
_KEYS = {KEY_VERSION: _key("DATA_ENCRYPTION_KEY")}
# During a rotation also the key that was current before, under its own version: only to read values that are not yet re-encrypted.
if os.environ.get("DATA_ENCRYPTION_KEY_PREVIOUS"):
    _previous = os.environ.get("DATA_ENCRYPTION_KEY_PREVIOUS_VERSION", "v1")
    if _previous == KEY_VERSION:
        raise RuntimeError("The previous key must have another version than the current key.")
    _KEYS[_previous] = _key("DATA_ENCRYPTION_KEY_PREVIOUS")
if not all(re.fullmatch(r"v[0-9]+", v) for v in _KEYS):
    raise RuntimeError("A key version looks like v1, v2, ...")


# AES-256-GCM with a new nonce of 96 bits per value; the context binds the value to its place and to the key version.
def encrypt(text, *context):
    nonce = os.urandom(12)
    sealed = AESGCM(_KEYS[KEY_VERSION]).encrypt(nonce, text.encode(), _context(KEY_VERSION, context))
    return f"{KEY_VERSION}:{base64.b64encode(nonce + sealed).decode()}"


# The text back, or None if the value was changed, moved or made with a key this app does not have.
def decrypt(stored, *context):
    version, _, data = stored.partition(":")
    key = _KEYS.get(version)
    if key is None:
        return None
    try:
        raw = base64.b64decode(data, validate=True)
        return AESGCM(key).decrypt(raw[:12], raw[12:], _context(version, context)).decode()
    except (InvalidTag, ValueError):
        return None


# Whether this value is already made with the current key.
def is_current(stored):
    return stored.partition(":")[0] == KEY_VERSION


# The value made again with the current key, or None if it is current already or does not decrypt.
def reencrypt(stored, *context):
    if is_current(stored):
        return None
    text = decrypt(stored, *context)
    return None if text is None else encrypt(text, *context)


def _context(version, parts):
    return "\x00".join((version, *map(str, parts))).encode()
