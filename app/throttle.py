# Poginglimieten (MIT-06, MIT-10) in de database: een sessie begint een aanvaller zelf opnieuw.

import hashlib
import hmac
import ipaddress
import os
from collections import namedtuple

from db import query

Policy = namedtuple("Policy", "max_failures window_minutes lock_minutes max_lock_minutes")
# Eén teller: de soort (voor de limieten hieronder) en de sleutel in auth_throttle.
Limit = namedtuple("Limit", "kind key")

POLICIES = {
    # Inloggen en wachtwoord vergeten, per IP-adres: tegen één adres dat veel accounts probeert.
    "password_ip": Policy(20, 15, 15, 60),
    # Dezelfde twee, per naam per adres; bewust niet over alle adressen (MC-18: buitensluiten).
    "password_account_ip": Policy(5, 15, 15, 60),
    # Tweede factor, per account: die stap bereik je pas na het juiste wachtwoord.
    "totp_account": Policy(5, 15, 15, 24 * 60),
    # Herstelcode, per account: zelfde afweging als de tweede factor (MIT-11).
    "recovery_account": Policy(5, 15, 15, 24 * 60),
    # Herauthenticatie, per account: alleen met een sessie te bereiken, dus het account mag op slot (MIT-16).
    "reauth_account": Policy(5, 15, 15, 24 * 60),
}
# Een geslaagde poging wist deze teller niet: anders zet een eigen account hem steeds terug.
KEEP_ON_SUCCESS = {"password_ip"}

_SECRET = os.environ["FLASK_SECRET_KEY"].encode()


# De soort en een HMAC van soort en waarden: de tabel bevat geen leesbare IP-adressen of namen.
def limit(kind, *parts):
    return Limit(kind, hmac.new(_SECRET, "\x00".join((kind, *map(str, parts))).encode(), hashlib.sha256).hexdigest())


# De tellers van inloggen en wachtwoord vergeten: per adres en per naam per adres (MIT-10).
def password_limits(username, remote_addr):
    ip = client_ip(remote_addr)
    return limit("password_ip", ip), limit("password_account_ip", username, ip)


# Het IP-adres van de client; bij IPv6 het /64-netwerk, want één aansluiting krijgt er 2^64.
def client_ip(remote_addr):
    # Azure zet soms de poort achter het adres in X-Forwarded-For (203.0.113.9:54321, [2001:db8::1]:54321).
    if remote_addr.startswith("["):
        remote_addr = remote_addr[1:].partition("]")[0]
    elif remote_addr.count(":") == 1:
        remote_addr = remote_addr.partition(":")[0]
    ip = ipaddress.ip_address(remote_addr)
    # Een IPv4-adres achter een IPv6-socket (::ffff:a.b.c.d) telt als dat adres, niet als ::/64.
    if ip.version == 6 and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return str(ipaddress.ip_network(f"{ip}/64", strict=False)) if ip.version == 6 else str(ip)


def message(minutes):
    return f"Te veel foute pogingen. Probeer het over {minutes} minuten opnieuw."


# Blokkade: 429 met Retry-After (RFC 6585); anders 400, want 401 eist WWW-Authenticate.
def refusal(minutes):
    return (429, {"Retry-After": str(minutes * 60)}) if minutes else (400, {})


# Telt vóór de controle en blokkeert zodra de limiet wordt overschreden, in één statement; 0 = mag door.
def attempt(*limits):
    for kind, k in limits:
        policy = POLICIES[kind]
        row = query(
            "INSERT INTO auth_throttle AS t (key, failures, window_start) VALUES (%(key)s, 1, now())"
            " ON CONFLICT (key) DO UPDATE SET"
            # Op slot telt niets; na het venster opnieuw tellen; boven de limiet: op slot en opnieuw beginnen.
            "  failures = CASE WHEN t.locked_until > now() THEN t.failures"
            "   WHEN t.window_start < now() - make_interval(mins => %(window)s) THEN 1"
            "   WHEN t.failures >= %(limit)s THEN 0 ELSE t.failures + 1 END,"
            "  window_start = CASE WHEN t.locked_until > now() THEN t.window_start"
            "   WHEN t.window_start < now() - make_interval(mins => %(window)s) OR t.failures >= %(limit)s THEN now()"
            "   ELSE t.window_start END,"
            # Elke volgende blokkade duurt twee keer zo lang, tot het maximum; na een dag zonder blokkade opnieuw.
            "  locked_until = CASE WHEN t.locked_until > now() THEN t.locked_until"
            "   WHEN t.window_start < now() - make_interval(mins => %(window)s) THEN t.locked_until"
            "   WHEN t.failures >= %(limit)s THEN now() + make_interval(mins => LEAST(%(lock)s * 2 ^ LEAST("
            "    CASE WHEN t.locked_until < now() - interval '1 day' THEN 0 ELSE t.lock_count END, 10), %(max)s)::int)"
            "   ELSE t.locked_until END,"
            "  lock_count = CASE WHEN t.locked_until < now() - interval '1 day' THEN 0 ELSE t.lock_count END"
            "   + CASE WHEN t.locked_until > now() OR t.window_start < now() - make_interval(mins => %(window)s) THEN 0"
            "     WHEN t.failures >= %(limit)s THEN 1 ELSE 0 END"
            " RETURNING failures = 0 AND window_start = now() AS locked_now,"
            "  GREATEST(ceil(extract(epoch FROM locked_until - now()) / 60), 0) AS minutes",
            {"key": k, "window": policy.window_minutes, "limit": policy.max_failures,
             "lock": policy.lock_minutes, "max": policy.max_lock_minutes}, one=True,
        )
        if row.locked_now:
            # Bij een blokkade (zeldzaam) ook oude tellers opruimen: venster en blokkade een dag voorbij.
            query("DELETE FROM auth_throttle WHERE window_start < now() - interval '1 day'"
                  " AND (locked_until IS NULL OR locked_until < now() - interval '1 day')")
        if row.minutes:
            return int(row.minutes)
    return 0


# Na een geslaagde controle: de teller weg, of bij KEEP_ON_SUCCESS alleen deze poging eraf.
def succeeded(*limits):
    for kind, k in limits:
        if kind in KEEP_ON_SUCCESS:
            query("UPDATE auth_throttle SET failures = GREATEST(failures - 1, 0) WHERE key = %s", (k,))
        else:
            query("DELETE FROM auth_throttle WHERE key = %s", (k,))
