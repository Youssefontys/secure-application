"""Bruteforce: de poginglimieten per naam en per adres, gelijktijdige verzoeken, de hackstand en de limiet op registreren
(MIT-06, MIT-10, MIT-30, MC-18). Draait via securitytest.py."""
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
    print("== limieten")
    unlock()
    _, secb, _ = account("bram")
    sql("INSERT INTO auth_throttle (key, failures, window_start) VALUES ('oud', 1, now() - interval '2 days'), ('vers', 1, now())")
    check("5 foute wachtwoorden, de 6e poging geweigerd", tries([req(client(), "/login", {"username": "bram", "password": f"fout{i}"}) for i in range(6)]), LOCKED)
    check("  oude teller opgeruimd, verse blijft", sql("SELECT string_agg(key, ',' ORDER BY key) FROM auth_throttle WHERE key IN ('oud', 'vers')"), "vers")
    check("juist wachtwoord tijdens blokkade", req(client(), "/login", {"username": "bram", "password": PW})[0], 429)
    unlock()
    d = password_step("bram")
    st = [req(d, "/login/2fa", {"code": f"{i:06d}"}) for i in range(6)]
    check("5 foute codes, de 6e geweigerd", (*tries(st), msg(st[-1][1])[:24]), (*LOCKED, "Too many failed attempts"))
    check("juiste code tijdens blokkade", req(d, "/login/2fa", {"code": fresh(secb, "bram")})[0], 429)
    check("5 foute herstelcodes, de 6e geweigerd", tries([req(d, "/login/recover", {"code": f"{i:032d}"}) for i in range(6)]), LOCKED)
    unlock()
    pair, same = (password_step("bram"), password_step("bram")), fresh(secb, "bram")
    check("twee gelijktijdig met dezelfde code", sorted(together([lambda x=x: req(x, "/login/2fa", {"code": same})[0] for x in pair])), [302, 400])
    unlock()
    res = together([lambda i=i: req(client(), "/login", {"username": "bram", "password": f"tegelijk{i}"})[0] for i in range(40)])
    check("40 tegelijk: precies 5 gecontroleerd, de rest geweigerd", sorted(res), [400] * 5 + [429] * 35)
    check("  verdubbelteller maar één keer omhoog", sql("SELECT max(lock_count) FROM auth_throttle"), "1")
    unlock()
    check("IPv4 achter IPv6, IPv6 per /64, gewoon IPv4", in_app(
        "import throttle; print(*(throttle.client_ip(a) for a in ('::ffff:203.0.113.7', '2001:db8::1', '192.0.2.1')))").stdout.strip(),
        "203.0.113.7 2001:db8::/64 192.0.2.1")
    check("  met de poort erachter, zoals Azure het meestuurt", in_app(
        "import throttle; print(*(throttle.client_ip(a) for a in ('203.0.113.9:54321', '[2001:db8::1]:54321', '[2001:db8::1]')))").stdout.strip(),
        "203.0.113.9 2001:db8::/64 2001:db8::/64")

    print("== hackstand (MC-18)")
    check("hackweek: 100 per adres, demoaccount zonder teller per naam, 5 min op slot",
          in_app(HACK, "THROTTLE_IP_MODE=hackweek", "THROTTLE_PAIR_EXEMPT_USERS=hackingweek").stdout.split(), ["100", "2", "100", "5", "5"])
    check("  hackweek: 60 nieuwe accounts per uur per adres, 5 min op slot",
          in_app("import throttle; print(*throttle.POLICIES['register_ip'])", "THROTTLE_IP_MODE=hackweek").stdout.split(), ["60", "60", "5", "5"])
    bad = in_app("import throttle", "THROTTLE_IP_MODE=hackwek")
    check("  typfout in de stand: de app start niet", (bad.returncode != 0, "Onbekende THROTTLE_IP_MODE" in bad.stderr), (True, True))
    check("  zonder instelling streng", in_app("import throttle; print(throttle.POLICIES['password_ip'].max_failures,"
                                               " len(throttle.password_limits('hackingweek', '198.51.100.1')))").stdout.split(), ["20", "2"])
    unlock()

    print("== registreren (MIT-30)")
    securitytest.count_registrations = True
    sql(f"DELETE FROM auth_throttle WHERE key = '{registration_counter()}'")
    regs = [req(client(), "/register", {"username": f"limiet_{i}", "password": PW}) for i in range(11)]
    check("registreren: 10 per uur per adres, de 11e 429", ([r[0] for r in regs], regs[-1][2].get("Retry-After")), ([302] * 10 + [429], "3600"))
    check("  met een melding", msg(regs[-1][1]), "Too many new accounts from this address. Try again in 60 minutes.")
    check("  geen 11e account", sql("SELECT count(*) FROM users WHERE username LIKE 'limiet\\_%'"), "10")
    securitytest.count_registrations = False
    sql("DELETE FROM users WHERE username LIKE 'limiet\\_%'")
    unlock()
