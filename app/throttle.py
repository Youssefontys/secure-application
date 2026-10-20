# Attempt limits (MIT-06, MIT-10) in the database: an attacker can start a new session at will.

import hashlib
import hmac
import ipaddress
import os
from collections import namedtuple

import events
from db import query

Policy = namedtuple("Policy", "max_failures window_minutes lock_minutes max_lock_minutes")
# One counter: the kind (for the limits below) and the key in auth_throttle.
Limit = namedtuple("Limit", "kind key")

POLICIES = {
    # Login and forgot password, per IP address: against one address that tries many accounts.
    "password_ip": Policy(20, 15, 15, 60),
    # The same two, per name per address; deliberately not across all addresses (MC-18: locking others out).
    "password_account_ip": Policy(5, 15, 15, 60),
    # Second factor, per account: you only reach that step after the right password.
    "totp_account": Policy(5, 15, 15, 24 * 60),
    # Recovery code, per account: the same trade-off as the second factor (MIT-11).
    "recovery_account": Policy(5, 15, 15, 24 * 60),
    # Re-authentication, per account: only reachable with a session, so the account may be locked (MIT-16).
    "reauth_account": Policy(5, 15, 15, 24 * 60),
    # New accounts per address, successful ones too: every registration costs an Argon2id calculation of 19 MiB (MIT-30).
    "register_ip": Policy(10, 60, 60, 4 * 60),
}
# Hackmode for the hacking week: a class behind one school address. Wider, and a fixed lockout of
# 5 minutes without doubling: a scanner is still slowed down, the class waits at most 5 minutes (MC-18).
IP_MODES = {"strict": {}, "hackweek": {"password_ip": Policy(100, 15, 5, 5), "register_ip": Policy(60, 60, 5, 5)}}
_mode = os.environ.get("THROTTLE_IP_MODE", "strict")
if _mode not in IP_MODES:
    raise RuntimeError(f"Unknown THROTTLE_IP_MODE {_mode!r}; choose from {', '.join(IP_MODES)}.")
POLICIES.update(IP_MODES[_mode])
# Names without a counter per name per address, for the demo account: otherwise one classmate locks it for the class.
PAIR_EXEMPT = {name.strip() for name in os.environ.get("THROTTLE_PAIR_EXEMPT_USERS", "").split(",") if name.strip()}
# A successful attempt does not clear this counter: otherwise an own account keeps resetting it.
KEEP_ON_SUCCESS = {"password_ip"}

_SECRET = os.environ["FLASK_SECRET_KEY"].encode()


# The kind and an HMAC of kind and values: the table holds no readable IP addresses or names.
def limit(kind, *parts):
    return Limit(kind, hmac.new(_SECRET, "\x00".join((kind, *map(str, parts))).encode(), hashlib.sha256).hexdigest())


# The counters of login and forgot password: per address and per name per address (MIT-10).
def password_limits(username, remote_addr):
    ip = client_ip(remote_addr)
    if username in PAIR_EXEMPT:
        return (limit("password_ip", ip),)
    return limit("password_ip", ip), limit("password_account_ip", username, ip)


# The IP address of the client; for IPv6 the /64 network, because one connection gets 2^64 of them.
def client_ip(remote_addr):
    # Azure sometimes puts the port after the address in X-Forwarded-For (203.0.113.9:54321, [2001:db8::1]:54321).
    if remote_addr.startswith("["):
        remote_addr = remote_addr[1:].partition("]")[0]
    elif remote_addr.count(":") == 1:
        remote_addr = remote_addr.partition(":")[0]
    ip = ipaddress.ip_address(remote_addr)
    # An IPv4 address behind an IPv6 socket (::ffff:a.b.c.d) counts as that address, not as ::/64.
    if ip.version == 6 and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return str(ipaddress.ip_network(f"{ip}/64", strict=False)) if ip.version == 6 else str(ip)


# Singular for 1: the lockout counts down to the last minute.
def try_again(minutes):
    return f"Try again in {minutes} minute{'' if minutes == 1 else 's'}."


def message(minutes):
    return f"Too many failed attempts. {try_again(minutes)}"


# Lockout: 429 with Retry-After (RFC 6585); otherwise 400, because 401 requires WWW-Authenticate.
def refusal(minutes):
    return (429, {"Retry-After": str(minutes * 60)}) if minutes else (400, {})


# Counts before the check and locks as soon as the limit is exceeded, in one statement; 0 = may pass.
def attempt(*limits):
    for kind, k in limits:
        policy = POLICIES[kind]
        row = query(
            "INSERT INTO auth_throttle AS t (key, failures, window_start) VALUES (%(key)s, 1, now())"
            " ON CONFLICT (key) DO UPDATE SET"
            # Locked counts nothing; after the window, count again; over the limit: lock and start again.
            "  failures = CASE WHEN t.locked_until > now() THEN t.failures"
            "   WHEN t.window_start < now() - make_interval(mins => %(window)s) THEN 1"
            "   WHEN t.failures >= %(limit)s THEN 0 ELSE t.failures + 1 END,"
            "  window_start = CASE WHEN t.locked_until > now() THEN t.window_start"
            "   WHEN t.window_start < now() - make_interval(mins => %(window)s) OR t.failures >= %(limit)s THEN now()"
            "   ELSE t.window_start END,"
            # Every next lockout lasts twice as long, up to the maximum; after a day without a lockout, start again.
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
            # One log line per lockout, not per refused attempt: otherwise a script fills the log (MIT-31).
            events.event("lockout_started", scope=kind, minutes=int(row.minutes))
            # On a lockout (rare), also clean up old counters: window and lockout more than a day ago.
            query("DELETE FROM auth_throttle WHERE window_start < now() - interval '1 day'"
                  " AND (locked_until IS NULL OR locked_until < now() - interval '1 day')")
        if row.minutes:
            return int(row.minutes)
    return 0


# After a successful check: remove the counter, or for KEEP_ON_SUCCESS only take this attempt off.
def succeeded(*limits):
    for kind, k in limits:
        if kind in KEEP_ON_SUCCESS:
            query("UPDATE auth_throttle SET failures = GREATEST(failures - 1, 0) WHERE key = %s", (k,))
        else:
            query("DELETE FROM auth_throttle WHERE key = %s", (k,))
