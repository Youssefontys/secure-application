# TOTP (RFC 6238) zonder dependency (MC-11), getest met de RFC-testvectoren (T-35).

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

# Seconden per code, de aanbevolen standaard (RFC 6238 5.2).
STEP = 30
DIGITS = 6
# Eén stap ervoor of erna telt ook, voor klokverschil; RFC 6238 5.2 raadt hoogstens één aan.
WINDOW = 1


# 160 willekeurige bits in Base32; RFC 4226 (R6) eist minstens 128 en raadt 160 aan.
def new_secret():
    return base64.b32encode(secrets.token_bytes(20)).decode()


# De code voor één tijdstap: HOTP (RFC 4226) met de tijdstap als teller.
def code_at(secret, step, digits=DIGITS, digest=hashlib.sha1):
    mac = hmac.new(base64.b32decode(secret), struct.pack(">Q", step), digest).digest()
    offset = mac[-1] & 0x0F
    number = int.from_bytes(mac[offset:offset + 4], "big") & 0x7FFFFFFF
    return str(number % 10**digits).zfill(digits)


# De tijdstap waar de code bij hoort, binnen WINDOW rond nu, of None.
def matching_step(secret, code, now=None):
    code = code.replace(" ", "")
    # Alleen 0-9: isdigit() keurt ook andere cijfers goed, en daar loopt compare_digest op vast.
    if len(code) != DIGITS or not (code.isascii() and code.isdigit()):
        return None
    step = int((time.time() if now is None else now) // STEP)
    # Vergelijken in constante tijd: de responstijd verraadt niet hoeveel cijfers kloppen.
    for candidate in range(step - WINDOW, step + WINDOW + 1):
        if hmac.compare_digest(code_at(secret, candidate), code):
            return candidate
    return None


# De otpauth://-link in de QR-code, in het Key Uri Format dat authenticator-apps lezen.
def provisioning_uri(secret, username, issuer="Notes"):
    label = quote(f"{issuer}:{username}")
    return (f"otpauth://totp/{label}?secret={secret}&issuer={quote(issuer)}"
            f"&algorithm=SHA1&digits={DIGITS}&period={STEP}")
