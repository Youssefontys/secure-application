# Versleuteling van gegevens die de app terug moet kunnen lezen: het TOTP-geheim en de notities (MIT-17, MIT-18).

import base64
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# 256 bits, buiten de database: lokaal uit .env, op Azure uit Key Vault (A-09).
_KEY = bytes.fromhex(os.environ["DATA_ENCRYPTION_KEY"])
if len(_KEY) != 32:
    raise RuntimeError("DATA_ENCRYPTION_KEY moet 64 hextekens zijn (256 bits).")
# Gaat mee in elke opgeslagen waarde, zodat een nieuwe sleutel later naast de oude kan.
KEY_VERSION = "v1"


# AES-256-GCM met een nieuwe nonce van 96 bits per waarde; de context bindt de waarde aan haar plek.
def encrypt(text, *context):
    nonce = os.urandom(12)
    sealed = AESGCM(_KEY).encrypt(nonce, text.encode(), _context(context))
    return f"{KEY_VERSION}:{base64.b64encode(nonce + sealed).decode()}"


# De tekst terug, of None als de waarde is gewijzigd, verplaatst of met een andere sleutel gemaakt.
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
