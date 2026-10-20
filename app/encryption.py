# Encryption of data the app must be able to read back: the TOTP secret and the notes (MIT-17, MIT-18).

import base64
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# 256 bits, outside the database: locally from .env, on Azure from Key Vault (A-09).
_KEY = bytes.fromhex(os.environ["DATA_ENCRYPTION_KEY"])
if len(_KEY) != 32:
    raise RuntimeError("DATA_ENCRYPTION_KEY must be 64 hex characters (256 bits).")
# Goes into every stored value, so a new key can later sit next to the old one.
KEY_VERSION = "v1"


# AES-256-GCM with a new nonce of 96 bits per value; the context binds the value to its place.
def encrypt(text, *context):
    nonce = os.urandom(12)
    sealed = AESGCM(_KEY).encrypt(nonce, text.encode(), _context(context))
    return f"{KEY_VERSION}:{base64.b64encode(nonce + sealed).decode()}"


# The text back, or None if the value was changed, moved or made with another key.
def decrypt(stored, *context):
    version, _, data = stored.partition(":")
    if version != KEY_VERSION:
        return None
    try:
        raw = base64.b64decode(data, validate=True)
        return AESGCM(_KEY).decrypt(raw[:12], raw[12:], _context(context)).decode()
    except (InvalidTag, ValueError):
        return None


def _context(parts):
    return "\x00".join((KEY_VERSION, *map(str, parts))).encode()
