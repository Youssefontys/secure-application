"""TOTP volgens RFC 6238: een code van 6 cijfers die elke 30 seconden verandert.

Met alleen de standaardbibliotheek: het algoritme is een HMAC over een teller, en
zo komt er geen extra dependency bij (MC-11). De berekening is gecontroleerd
tegen de testvectoren in RFC 6238 bijlage B en RFC 4226 bijlage D.
"""

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

STEP = 30    # seconden per code, de aanbevolen standaard (RFC 6238, 5.2)
DIGITS = 6
WINDOW = 1   # één stap ervoor of erna telt ook, voor klokverschil; RFC 6238 5.2 raadt hoogstens één aan


def new_secret():
    """160 willekeurige bits in Base32. RFC 4226 (R6) eist minstens 128 en raadt 160 bits aan."""
    return base64.b32encode(secrets.token_bytes(20)).decode()


def code_at(secret, step, digits=DIGITS, digest=hashlib.sha1):
    """De code voor één tijdstap: HOTP (RFC 4226) met de tijdstap als teller."""
    mac = hmac.new(base64.b32decode(secret), struct.pack(">Q", step), digest).digest()
    offset = mac[-1] & 0x0F
    number = int.from_bytes(mac[offset:offset + 4], "big") & 0x7FFFFFFF
    return str(number % 10**digits).zfill(digits)


def matching_step(secret, code, now=None):
    """De tijdstap waar code bij hoort, binnen WINDOW rond nu, of None.

    hmac.compare_digest vergelijkt in constante tijd, zodat de responstijd niet
    verraadt hoeveel cijfers kloppen.
    """
    code = code.replace(" ", "")
    if len(code) != DIGITS or not code.isdigit():
        return None
    step = int((time.time() if now is None else now) // STEP)
    for candidate in range(step - WINDOW, step + WINDOW + 1):
        if hmac.compare_digest(code_at(secret, candidate), code):
            return candidate
    return None


def provisioning_uri(secret, username, issuer="Notities"):
    """De otpauth://-link in de QR-code, in het Key Uri Format dat authenticator-apps lezen."""
    label = quote(f"{issuer}:{username}")
    return (f"otpauth://totp/{label}?secret={secret}&issuer={quote(issuer)}"
            f"&algorithm=SHA1&digits={DIGITS}&period={STEP}")
