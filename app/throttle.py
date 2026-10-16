# Poginglimieten (MIT-06, MIT-10) in de database: een sessie begint een aanvaller zelf opnieuw.

import hashlib
import hmac
import ipaddress
import os
from collections import namedtuple

from db import query

Policy = namedtuple("Policy", "max_failures window_minutes lock_minutes max_lock_minutes")

POLICIES = {
    # Wachtwoord, per IP-adres: tegen één adres dat veel accounts probeert.
    "password_ip": Policy(20, 15, 15, 60),
    # Wachtwoord, per account per adres; bewust niet over alle adressen (MC-18: buitensluiten).
    "password_account_ip": Policy(5, 15, 15, 60),
    # Tweede factor, per account: die stap bereik je pas na het juiste wachtwoord.
    "totp_account": Policy(5, 15, 15, 24 * 60),
    # Herstelcode, per account: zelfde afweging als de tweede factor (MIT-11).
    "recovery_account": Policy(5, 15, 15, 24 * 60),
}

_SECRET = os.environ["FLASK_SECRET_KEY"].encode()


# Een HMAC van soort en waarden: de tabel bevat geen leesbare IP-adressen of namen.
def key(kind, *parts):
    return hmac.new(_SECRET, "\x00".join((kind, *map(str, parts))).encode(), hashlib.sha256).hexdigest()


# Het IP-adres van de client; bij IPv6 het /64-netwerk, want één aansluiting krijgt er 2^64.
def client_ip(remote_addr):
    ip = ipaddress.ip_address(remote_addr)
    return str(ipaddress.ip_network(f"{ip}/64", strict=False)) if ip.version == 6 else str(ip)


def message(minutes):
    return f"Te veel foute pogingen. Probeer het over {minutes} minuten opnieuw."


# Blokkade: 429 met Retry-After (RFC 6585); anders 400, want 401 eist WWW-Authenticate.
def refusal(minutes):
    return (429, {"Retry-After": str(minutes * 60)}) if minutes else (400, {})


# Hoeveel minuten de langste blokkade onder deze sleutels nog duurt, of 0.
def locked_minutes(*keys):
    row = query(
        "SELECT ceil(extract(epoch FROM max(locked_until) - now()) / 60) AS minutes"
        " FROM auth_throttle WHERE key = ANY(%s) AND locked_until > now()",
        (list(keys),), one=True,
    )
    return int(row.minutes or 0)


# Telt een foute poging; geeft de duur van een blokkade die nu ingaat, in minuten, anders 0.
def fail(kind, k):
    policy = POLICIES[kind]
    # Na het venster opnieuw tellen; na een dag zonder blokkade opnieuw verdubbelen.
    row = query(
        "INSERT INTO auth_throttle AS t (key, failures, window_start) VALUES (%(key)s, 1, now())"
        " ON CONFLICT (key) DO UPDATE SET"
        "  failures = CASE WHEN t.window_start < now() - make_interval(mins => %(window)s) THEN 1 ELSE t.failures + 1 END,"
        "  window_start = CASE WHEN t.window_start < now() - make_interval(mins => %(window)s) THEN now() ELSE t.window_start END,"
        "  lock_count = CASE WHEN t.locked_until < now() - interval '1 day' THEN 0 ELSE t.lock_count END"
        " RETURNING failures, lock_count",
        {"key": k, "window": policy.window_minutes}, one=True,
    )
    if row.failures < policy.max_failures:
        return 0
    # Elke volgende blokkade duurt twee keer zo lang, tot het maximum.
    minutes = min(policy.lock_minutes * 2 ** row.lock_count, policy.max_lock_minutes)
    query(
        "UPDATE auth_throttle SET locked_until = now() + make_interval(mins => %s), lock_count = lock_count + 1,"
        " failures = 0, window_start = now() WHERE key = %s",
        (minutes, k),
    )
    return minutes


# Na een geslaagde poging: teller en verdubbeling van deze sleutel weg.
def reset(k):
    query("DELETE FROM auth_throttle WHERE key = %s", (k,))
