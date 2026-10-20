# TOTP (RFC 6238) without a dependency (MC-11), tested with the RFC test vectors (T-35).

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

# Seconds per code, the recommended default (RFC 6238 5.2).
STEP = 30
DIGITS = 6
# One step before or after counts too, for clock drift; RFC 6238 5.2 recommends at most one.
WINDOW = 1


# 160 random bits in Base32; RFC 4226 (R6) requires at least 128 and recommends 160.
def new_secret():
    return base64.b32encode(secrets.token_bytes(20)).decode()


# The code for one time step: HOTP (RFC 4226) with the time step as counter.
def code_at(secret, step, digits=DIGITS, digest=hashlib.sha1):
    mac = hmac.new(base64.b32decode(secret), struct.pack(">Q", step), digest).digest()
    offset = mac[-1] & 0x0F
    number = int.from_bytes(mac[offset:offset + 4], "big") & 0x7FFFFFFF
    return str(number % 10**digits).zfill(digits)


# The time step the code belongs to, within WINDOW around now, or None.
def matching_step(secret, code, now=None):
    code = code.replace(" ", "")
    # Only 0-9: isdigit() also accepts other digits, and compare_digest fails on those.
    if len(code) != DIGITS or not (code.isascii() and code.isdigit()):
        return None
    step = int((time.time() if now is None else now) // STEP)
    # Compare in constant time: the response time does not reveal how many digits are right.
    for candidate in range(step - WINDOW, step + WINDOW + 1):
        if hmac.compare_digest(code_at(secret, candidate), code):
            return candidate
    return None


# The otpauth:// link in the QR code, in the Key Uri Format that authenticator apps read.
def provisioning_uri(secret, username, issuer="Notes"):
    label = quote(f"{issuer}:{username}")
    return (f"otpauth://totp/{label}?secret={secret}&issuer={quote(issuer)}"
            f"&algorithm=SHA1&digits={DIGITS}&period={STEP}")
