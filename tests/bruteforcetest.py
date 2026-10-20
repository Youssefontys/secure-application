"""Brute force: the attempt limits per name and per address, simultaneous requests, hack mode and the limit on registering
(MIT-06, MIT-10, MIT-30, MC-18). Runs through securitytest.py."""
import securitytest
from securitytest import *

HACK = """
import app, throttle
from db import query
with app.app.app_context():
    a, = throttle.password_limits("hackingweek", "198.51.100.1")
    b = throttle.password_limits("anna", "198.51.100.1")
    first = [throttle.attempt(a) for _ in range(101)]
    query("UPDATE auth_throttle SET locked_until = now() - interval '1 minute', lock_count = 3,"
          " window_start = now() - interval '20 minutes' WHERE key = %s", (a.key,))
    again = [throttle.attempt(a) for _ in range(101)]
    print(throttle.POLICIES["password_ip"].max_failures, len(b), first.count(0), first[-1], again[-1])
"""


def run():
    print("== limits")
    unlock()
    _, secb, _ = account("bram")
    sql("INSERT INTO auth_throttle (key, failures, window_start) VALUES ('old', 1, now() - interval '2 days'), ('fresh', 1, now())")
    check("5 wrong passwords, the 6th attempt refused", tries([req(client(), "/login", {"username": "bram", "password": f"wrong{i}"}) for i in range(6)]), LOCKED)
    check("  old counter cleaned up, fresh one stays", sql("SELECT string_agg(key, ',' ORDER BY key) FROM auth_throttle WHERE key IN ('old', 'fresh')"), "fresh")
    check("right password during the lockout", req(client(), "/login", {"username": "bram", "password": PW})[0], 429)
    unlock()
    d = password_step("bram")
    st = [req(d, "/login/2fa", {"code": f"{i:06d}"}) for i in range(6)]
    check("5 wrong codes, the 6th refused", (*tries(st), msg(st[-1][1])[:24]), (*LOCKED, "Too many failed attempts"))
    check("right code during the lockout", req(d, "/login/2fa", {"code": fresh(secb, "bram")})[0], 429)
    check("5 wrong recovery codes, the 6th refused", tries([req(d, "/login/recover", {"code": f"{i:032d}"}) for i in range(6)]), LOCKED)
    unlock()
    pair, same = (password_step("bram"), password_step("bram")), fresh(secb, "bram")
    check("two at the same time with the same code", sorted(together([lambda x=x: req(x, "/login/2fa", {"code": same})[0] for x in pair])), [302, 400])
    unlock()
    res = together([lambda i=i: req(client(), "/login", {"username": "bram", "password": f"together{i}"})[0] for i in range(40)])
    check("40 at once: exactly 5 checked, the rest refused", sorted(res), [400] * 5 + [429] * 35)
    check("  doubling counter up only once", sql("SELECT max(lock_count) FROM auth_throttle"), "1")
    unlock()
    check("IPv4 behind IPv6, IPv6 per /64, plain IPv4", in_app(
        "import throttle; print(*(throttle.client_ip(a) for a in ('::ffff:203.0.113.7', '2001:db8::1', '192.0.2.1')))").stdout.strip(),
        "203.0.113.7 2001:db8::/64 192.0.2.1")
    check("  with the port after it, as Azure sends it", in_app(
        "import throttle; print(*(throttle.client_ip(a) for a in ('203.0.113.9:54321', '[2001:db8::1]:54321', '[2001:db8::1]')))").stdout.strip(),
        "203.0.113.9 2001:db8::/64 2001:db8::/64")

    print("== hack mode (MC-18)")
    check("hackweek: 100 per address, demo account without a counter per name, 5 min locked",
          in_app(HACK, "THROTTLE_IP_MODE=hackweek", "THROTTLE_PAIR_EXEMPT_USERS=hackingweek").stdout.split(), ["100", "2", "100", "5", "5"])
    check("  hackweek: 60 new accounts per hour per address, 5 min locked",
          in_app("import throttle; print(*throttle.POLICIES['register_ip'])", "THROTTLE_IP_MODE=hackweek").stdout.split(), ["60", "60", "5", "5"])
    bad = in_app("import throttle", "THROTTLE_IP_MODE=hackwek")
    check("  typo in the mode: the app does not start", (bad.returncode != 0, "Unknown THROTTLE_IP_MODE" in bad.stderr), (True, True))
    check("  strict without a setting", in_app("import throttle; print(throttle.POLICIES['password_ip'].max_failures,"
                                               " len(throttle.password_limits('hackingweek', '198.51.100.1')))").stdout.split(), ["20", "2"])
    unlock()

    print("== registering (MIT-30)")
    securitytest.count_registrations = True
    sql(f"DELETE FROM auth_throttle WHERE key = '{registration_counter()}'")
    regs = [req(client(), "/register", {"username": f"limit_{i}", "password": PW}) for i in range(11)]
    check("registering: 10 per hour per address, the 11th 429", ([r[0] for r in regs], regs[-1][2].get("Retry-After")), ([302] * 10 + [429], "3600"))
    check("  with a message", msg(regs[-1][1]), "Too many new accounts from this address. Try again in 60 minutes.")
    check("  no 11th account", sql("SELECT count(*) FROM users WHERE username LIKE 'limit\\_%'"), "10")
    securitytest.count_registrations = False
    sql("DELETE FROM users WHERE username LIKE 'limit\\_%'")
    unlock()
