"""Poginglimieten bij inloggen, bijgehouden in de database (MIT-06, MIT-10).

Per sleutel worden foute pogingen geteld binnen een venster. Bij te veel gaat de
sleutel op slot, en elke volgende blokkade duurt twee keer zo lang, tot een
maximum. De tellers staan in de database en niet in de sessie: een sessie kan
een aanvaller gewoon opnieuw beginnen.

Een sleutel is een HMAC van wat er geteld wordt (een IP-adres, een account), zodat
de tabel geen leesbare IP-adressen of gebruikersnamen bevat.
"""

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
    # Wachtwoord, per account vanaf één IP-adres. Bewust niet per account over alle
    # adressen: dan kan iedereen die een gebruikersnaam kent dat account buitensluiten.
    "password_account_ip": Policy(5, 15, 15, 60),
    # Tweede factor, per account. Die stap bereik je alleen met het juiste
    # wachtwoord, dus hier mag het hele account op slot.
    "totp_account": Policy(5, 15, 15, 24 * 60),
}

_SECRET = os.environ["FLASK_SECRET_KEY"].encode()


def key(kind, *parts):
    """Een HMAC van de soort en de waarden: niet terug te rekenen naar een IP-adres of naam."""
    return hmac.new(_SECRET, "\x00".join((kind, *map(str, parts))).encode(), hashlib.sha256).hexdigest()


def client_ip(remote_addr):
    """Het IP-adres van de client; bij IPv6 het /64-netwerk, want één aansluiting krijgt er 2^64."""
    ip = ipaddress.ip_address(remote_addr)
    return str(ipaddress.ip_network(f"{ip}/64", strict=False)) if ip.version == 6 else str(ip)


def message(minutes):
    return f"Te veel foute pogingen. Probeer het over {minutes} minuten opnieuw."


def locked_minutes(*keys):
    """Hoeveel minuten de langste blokkade onder deze sleutels nog duurt, of 0."""
    row = query(
        "SELECT ceil(extract(epoch FROM max(locked_until) - now()) / 60) AS minutes"
        " FROM auth_throttle WHERE key = ANY(%s) AND locked_until > now()",
        (list(keys),), one=True,
    )
    return int(row.minutes or 0)


def fail(kind, k):
    """Telt een foute poging. Geeft de duur van de blokkade in minuten als die nu ingaat, anders 0."""
    policy = POLICIES[kind]
    # Een nieuw venster begint als het oude verlopen is. Ligt de laatste blokkade
    # meer dan een dag terug, dan begint ook het verdubbelen opnieuw.
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
    minutes = min(policy.lock_minutes * 2 ** row.lock_count, policy.max_lock_minutes)
    query(
        "UPDATE auth_throttle SET locked_until = now() + make_interval(mins => %s), lock_count = lock_count + 1,"
        " failures = 0, window_start = now() WHERE key = %s",
        (minutes, k),
    )
    return minutes


def reset(k):
    """Na een geslaagde poging: teller en verdubbeling van deze sleutel weg."""
    query("DELETE FROM auth_throttle WHERE key = %s", (k,))
