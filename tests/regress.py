"""Regressietest van de hele app, tegen de lokale stack op http://127.0.0.1:5000: per onderwerp de normale werking en
de aanval, met de maatregel (MIT-..) uit BoK/Threat Analysis/entries.md in de kop. LET OP: maakt de tabellen users en
auth_throttle leeg, dus alle lokale accounts en notities zijn daarna weg. Daarom draait hij alleen met --wis:

    python scripts/deployment.py lokaal
    python tests/regress.py --wis

Alleen de standaardbibliotheek en docker compose; werkt op Windows en Linux. Exit 1 als een controle faalt.
"""
import base64, hashlib, hmac, http.cookiejar, json, os, re, struct, subprocess, sys, threading, time, zlib
import urllib.error, urllib.parse, urllib.request

if "--wis" not in sys.argv:
    sys.exit(__doc__)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = "http://127.0.0.1:5000"
# Alleen de log van deze run telt; een vorige run legt bewust een fout vast (veilig falen).
STARTED = str(int(time.time()))
# Testwachtwoorden voor de lokale stack, lang genoeg voor de sterkte-eis (MIT-13).
PW, PW2 = "regressie-wachtwoord", "regressie-wachtwoord-2"
# Vijf keer fout mag, de zesde poging wordt geweigerd, en dan 15 minuten wachten (MIT-06, MIT-10).
LOCKED = ([400] * 5 + [429], "900")
# Elke uitkomst, en elk geheim dat de test ziet: die mogen aan het eind niet in de log staan.
results, secrets_seen, last = [], [], {}


def compose(*args):
    """Een docker compose-opdracht in de repo, met de uitvoer als tekst."""
    return subprocess.run(["docker", "compose", *args], capture_output=True, text=True, cwd=REPO)


def in_app(src, *env, run=("python", "-c")):
    """Python in de container van de app, met de omgeving van de app, plus eventueel NAAM=waarde."""
    return compose("exec", "-T", *(a for e in env for a in ("-e", e)), "app", *run, src)


def sql(q):
    return compose("exec", "-T", "db", "psql", "-U", "notities", "-d", "notities", "-tAc", q).stdout.strip()


def unlock():
    """Alle tellers en blokkades weg, zodat de volgende proef schoon begint."""
    sql("DELETE FROM auth_throttle")


def client():
    """Een eigen browser: een eigen cookie, en redirects niet volgen zodat de Location te zien is."""
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar), NoRedirect)
    opener.jar = jar
    return opener


def csrf_of(c):
    """Het CSRF-token in de sessiecookie van deze browser: ondertekend, niet versleuteld, dus leesbaar."""
    value = next((k.value for k in c.jar if k.name == "session"), "")
    if not value:
        return None
    payload = value.split(".")[1] if value.startswith(".") else value.split(".")[0]
    raw = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
    return json.loads(zlib.decompress(raw) if value.startswith(".") else raw).get("csrf")


def register_key():
    """De sleutel van de registratieteller (MIT-30) voor het adres waarmee deze test bij de app aankomt: de gateway van Docker."""
    gw = subprocess.run(["docker", "network", "inspect", f"{os.path.basename(REPO).lower()}_default", "--format",
                         "{{(index .IPAM.Config 0).Gateway}}"], capture_output=True, text=True).stdout.strip()
    return in_app(f"import throttle; print(throttle.limit('register_ip', throttle.client_ip({gw!r})).key)").stdout.strip()


# De test registreert veel meer dan 10 accounts; behalve in de limiet-test zelf telt een registratie daarom niet.
REGISTER_KEY, free_register = register_key(), True


def req(c, path, data=None, csrf=True):
    """(status, body, headers) van een GET, of van een POST als er data is; een POST krijgt het CSRF-token mee, zoals in een formulier."""
    if path == "/register" and data is not None and free_register:
        sql(f"DELETE FROM auth_throttle WHERE key = '{REGISTER_KEY}'")
    if data is not None and csrf and "csrf_token" not in data:
        if not csrf_of(c):
            try:
                c.open(B + "/login")
            except urllib.error.HTTPError:
                pass
        data = {**data, "csrf_token": csrf_of(c) or ""}
    try:
        r = c.open(B + path, urllib.parse.urlencode(data).encode() if data is not None else None)
        return r.status, r.read().decode(), r.headers
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace"), e.headers


def loc(r):
    return f"{r[0]} {r[2].get('Location') or ''}".strip()


def msg(body):
    """De eerste melding (fout of bevestiging) op de pagina."""
    m = re.search(r'class="(error|notice)">([^<]*)', body)
    return m.group(2) if m else "-"


def secret(body):
    """Het TOTP-geheim op de instelpagina, zonder spaties."""
    secrets_seen.append(s := re.search(r'class="secret">([A-Z2-7 ]+)<', body).group(1).replace(" ", ""))
    return s


def recovery(body):
    """De herstelcode op de pagina, of "" als er geen staat."""
    m = re.search(r'class="secret">([0-9a-f-]+)<', body)
    secrets_seen.extend(m.groups() if m else ())
    return m.group(1) if m else ""


def tries(rs):
    """De statuscodes van een reeks pogingen, en de Retry-After van de laatste."""
    return [r[0] for r in rs], rs[-1][2]["Retry-After"]


def together(fns):
    """Start alle functies op hetzelfde moment, elk in een eigen thread, en geeft de uitkomsten."""
    go, out = threading.Barrier(len(fns)), []
    threads = [threading.Thread(target=lambda f=f: (go.wait(), out.append(f()))) for f in fns]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return out


def check(name, got, want):
    ok = want(got) if callable(want) else got == want
    results.append((name, ok))
    print(f"{'ok ' if ok else 'FOUT'} {name:58} {got}")


def code(key, offset=0):
    """De TOTP-code die een authenticator-app nu (plus offset stappen) zou tonen (RFC 6238)."""
    mac = hmac.new(base64.b32decode(key), struct.pack(">Q", int(time.time() // 30) + offset), hashlib.sha1).digest()
    o = mac[-1] & 15
    return f"{(int.from_bytes(mac[o:o + 4], 'big') & 0x7FFFFFFF) % 1000000:06d}"


def fresh(sec, u):
    """Een code van een tijdstap die voor dit account nog niet is gebruikt."""
    now = int(time.time() // 30)
    step = max(last.get(u, now - 2) + 1, now - 1)
    # De vorige stap alleen als de huidige nog even duurt; anders is de code bij aankomst al te oud.
    if step == now - 1 and time.time() % 30 > 25:
        step = now
    while step > int(time.time() // 30) + 1:
        time.sleep(1)
    last[u] = step
    return code(sec, step - int(time.time() // 30))


def password_step(u, pw=PW):
    """Een browser na de eerste stap van inloggen: het wachtwoord is goed, de code komt nog."""
    c = client()
    req(c, "/login", {"username": u, "password": pw})
    return c


def login(u, sec, pw=PW):
    c = password_step(u, pw)
    req(c, "/login/2fa", {"code": fresh(sec, u)})
    return c


def account(u, pw=PW):
    """Registreert, logt in en zet tweestapsverificatie aan. Geeft (sessie, geheim, herstelcode)."""
    req(client(), "/register", {"username": u, "password": pw})
    c = password_step(u, pw)
    sec = secret(req(c, "/account/2fa")[1])
    return c, sec, recovery(req(c, "/account/2fa", {"code": fresh(sec, u)})[1])


def forgot(c, user, rcode, code, pw=PW2, repeat=None):
    """Het formulier wachtwoord vergeten (MIT-14), met beide nieuwe wachtwoorden gelijk tenzij repeat iets anders zegt."""
    return req(c, "/login/forgot", {"username": user, "recovery_code": rcode, "code": code, "password": pw,
                                    "password_repeat": pw if repeat is None else repeat})


def answer(r):
    return r[0], msg(r[1])


def starts(*env):
    """"start" als de app met deze instellingen start, anders de foutmelding waarmee hij stopt (MIT-23)."""
    r = in_app("import app", *env)
    return "start" if r.returncode == 0 else r.stderr.strip().splitlines()[-1].split(": ", 1)[-1]


def took(name):
    """Hoe lang een mislukte login voor deze naam duurt, in seconden."""
    s = time.perf_counter()
    req(client(), "/login", {"username": name, "password": "fout-wachtwoord-123"})
    return time.perf_counter() - s


sql("DELETE FROM auth_throttle; DELETE FROM users;")

print("== verplichte tweestapsverificatie")
c = client()
req(c, "/register", {"username": "anna", "password": PW})
r = req(c, "/login", {"username": "anna", "password": PW})
check("login zonder 2FA", loc(r), "302 /account/2fa")
check("  sessiecookie met SameSite=Lax en HttpOnly", ("SameSite=Lax" in r[2]["Set-Cookie"], "HttpOnly" in r[2]["Set-Cookie"]), (True, True))
check("/ voor het instellen", loc(req(c, "/")), "302 /account/2fa")
check("/account voor het instellen", loc(req(c, "/account")), "302 /account/2fa")
check("notitie aanmaken voor het instellen", loc(req(c, "/", {"title": "x", "body": "y"})), "302 /account/2fa")
r = req(c, "/account/2fa")
sec = secret(r[1])
check("instelpagina", f"{r[0]} {r[2].get('Cache-Control')}", "200 no-store")
check("verversen houdt hetzelfde geheim", secret(req(c, "/account/2fa")[1]), sec)
check("qr.svg tijdens instellen", req(c, "/account/2fa/qr.svg")[0], 200)
check("foute code bij instellen", req(c, "/account/2fa", {"code": "000000"})[0], 400)
r = req(c, "/account/2fa", {"code": fresh(sec, "anna")})
rc = recovery(r[1])
check("aanzetten: herstelcode getoond", f"{r[0]} {len(rc)} {r[2].get('Cache-Control')}", "200 39 no-store")
check("  Verder gaat naar de notities", re.search(r'id="recovery-done" href="([^"]+)"', r[1]).group(1), "/")
check("daarna /", req(c, "/")[0], 200)
check("qr.svg na aanzetten", req(c, "/account/2fa/qr.svg")[0], 404)
check("instelpagina na aanzetten", loc(req(c, "/account/2fa")), "302 /account")
check("uitloggen vanaf de instelpagina kan", loc(req(client(), "/logout", {})), "302 /login")

print("== inloggen")
a = client()
check("wachtwoord", loc(req(a, "/login", {"username": "anna", "password": PW})), "302 /login/2fa")
check("halve login: /", loc(req(a, "/")), "302 /login")
check("foute code", req(a, "/login/2fa", {"code": "000000"})[0], 400)
check("code met Arabisch-Indische cijfers", req(a, "/login/2fa", {"code": "١٢٣٤٥٦"})[0], 400)
check("juiste code", loc(req(a, "/login/2fa", {"code": fresh(sec, "anna")})), "302 /")
r = req(client(), "/login", {"username": "anna", "password": "x"})
check("login fout wachtwoord", (r[0], r[2]["WWW-Authenticate"], r[2]["Retry-After"]), (400, None, None))
check("GET /login als ingelogd", loc(req(a, "/login")), "302 /")
check("GET /register als ingelogd", loc(req(a, "/register")), "302 /")
check("register dubbel", req(client(), "/register", {"username": "anna", "password": PW})[0], 409)

print("== sterkte-eis (MIT-13)")
for n, want in ((11, 400), (12, 302), (64, 302), (65, 400)):
    check(f"registreren met {n} tekens", req(client(), "/register", {"username": f"lengte{n}", "password": "w" * n})[0], want)
check("  melding", msg(req(client(), "/register", {"username": "kort", "password": "a"})[1]), "Choose a password of 12 to 64 characters.")
for n in (11, 65):
    check(f"wijzigen naar {n} tekens", req(a, "/account/password", {"password": "w" * n, "password_repeat": "w" * n})[0], 400)
check("wijzigen, twee verschillende", req(a, "/account/password", {"password": PW2, "password_repeat": PW})[0], 400)
check("inloggen zonder eis (oud wachtwoord blijft werken)", loc(req(client(), "/login", {"username": "anna", "password": PW})), "302 /login/2fa")

print("== notities")
check("notitie leeg", req(a, "/", {"title": "", "body": ""})[0], 400)
check("titel 16", req(a, "/", {"title": "x" * 16, "body": "y"})[0], 400)
check("notitie 251", req(a, "/", {"title": "x", "body": "y" * 251})[0], 400)
check("aanmaken (15/250)", loc(req(a, "/", {"title": "x" * 15, "body": "y" * 250})), "302 /")
nid = re.search(r"notes/(\d+)/edit", req(a, "/")[1]).group(1)
check("edit GET", req(a, f"/notes/{nid}/edit")[0], 200)
check("edit leeg", req(a, f"/notes/{nid}/edit", {"title": "", "body": ""})[0], 400)
check("edit", loc(req(a, f"/notes/{nid}/edit", {"title": "T2", "body": "Aangepast"})), "302 /")
check("bewerkt zichtbaar", "edited" in req(a, "/")[1], True)
cb, secb, _ = account("bram")
check("eigenaar (MIT-15): bram opent notitie van anna", req(cb, f"/notes/{nid}/edit")[0], 404)
check("  bram past notitie van anna aan", req(cb, f"/notes/{nid}/edit", {"title": "x", "body": "y"})[0], 404)
check("  bram verwijdert notitie van anna", req(cb, f"/notes/{nid}/delete", {})[0], 404)
check("  notitie van anna ongewijzigd", all(s in req(a, f"/notes/{nid}/edit")[1] for s in ("T2", "Aangepast")), True)
check("  onbekend id", req(a, "/notes/999999/edit")[0], 404)
check("delete", loc(req(a, f"/notes/{nid}/delete", {})), "302 /")
check("profiel", req(a, "/account")[0], 200)

print("== sessies")
a2 = login("anna", sec)
change = {"password": PW2, "password_repeat": PW2}
check("herauthenticatie (MIT-16): wijzigen zonder huidig wachtwoord", req(a, "/account/password", change)[0], 400)
check("  met een fout huidig wachtwoord", msg(req(a, "/account/password", {**change, "current_password": "fout-wachtwoord"})[1]),
      "Your current password is incorrect.")
check("  het juiste wachtwoord zonder code (MIT-16)", req(a, "/account/password", {**change, "current_password": PW})[0], 400)
check("  het juiste wachtwoord met een foute code", msg(req(a, "/account/password", {**change, "current_password": PW, "code": "000000"})[1]),
      "Incorrect or already used code.")
check("  het wachtwoord is nog het oude", loc(req(client(), "/login", {"username": "anna", "password": PW})), "302 /login/2fa")
check("wachtwoord wijzigen, met wachtwoord en code", loc(req(a, "/account/password", {**change, "current_password": PW, "code": fresh(sec, "anna")})),
      "302 /account")
check("  eigen sessie blijft", req(a, "/")[0], 200)
check("  andere sessie vervalt", loc(req(a2, "/")), "302 /login")
check("logout", loc(req(a, "/logout", {})), "302 /login")
check("  oude sessie na logout", loc(req(a, "/")), "302 /login")

print("== opnieuw instellen, nieuwe herstelcode")
a = login("anna", sec, PW2)
check("nieuwe herstelcode met foute code", req(a, "/account/2fa/recovery", {"current_password": PW2, "code": "000000"})[0], 400)
check("  met een goede code maar zonder wachtwoord (MC-29)", req(a, "/account/2fa/recovery", {"code": fresh(sec, "anna")})[0], 400)
r = req(a, "/account/2fa/recovery", {"current_password": PW2, "code": fresh(sec, "anna")})
rc_new = recovery(r[1])
check("nieuwe herstelcode met wachtwoord en code", f"{r[0]} {r[2].get('Cache-Control')}", "200 no-store")
check("  Verder gaat terug naar het profiel", re.search(r'id="recovery-done" href="([^"]+)"', r[1]).group(1), "/account")
a3 = login("anna", sec, PW2)
check("opnieuw instellen met foute code", req(a, "/account/2fa/reset", {"current_password": PW2, "code": "000000"})[0], 400)
check("  met een goede code maar zonder wachtwoord (MC-29)", (req(a, "/account/2fa/reset", {"code": fresh(sec, "anna")})[0],
      sql("SELECT totp_enabled FROM users WHERE username = 'anna'")), (400, "t"))
check("opnieuw instellen met wachtwoord en code", loc(req(a, "/account/2fa/reset", {"current_password": PW2, "code": fresh(sec, "anna")})),
      "302 /account/2fa")
check("  daarna /", loc(req(a, "/")), "302 /account/2fa")
check("  andere sessie vervalt", loc(req(a3, "/")), "302 /login")
sec = secret(req(a, "/account/2fa")[1])
last.pop("anna", None)
rc = recovery(req(a, "/account/2fa", {"code": fresh(sec, "anna")})[1])
check("  nieuw ingesteld", req(a, "/")[0], 200)

print("== herstelcode")
h = password_step("anna", PW2)
check("codepagina heeft herstellink", 'href="/login/recover"' in req(h, "/login/2fa")[1], True)
check("foute herstelcode", req(h, "/login/recover", {"code": "0" * 32})[0], 400)
check("herstelcode van vóór het opnieuw instellen", req(h, "/login/recover", {"code": rc_new})[0], 400)
check("juiste herstelcode", loc(req(h, "/login/recover", {"code": " " + rc.upper() + " "})), "302 /account/2fa")
check("  melding", msg(req(h, "/account/2fa")[1]).startswith("Your recovery code has been used"), True)
check("  daarna / zonder 2FA", loc(req(h, "/")), "302 /account/2fa")
check("  andere sessie vervalt", loc(req(a, "/")), "302 /login")
check("  database: hash weg, 2FA uit", sql("SELECT (recovery_hash IS NULL) || ',' || totp_enabled FROM users WHERE username='anna'"), "true,false")

print("== wachtwoord vergeten (MIT-14)")
unlock()
cc, secc, rcc = account("carla")
M = "Username, recovery code or code is incorrect."

check("link op de inlogpagina", 'href="/login/forgot"' in req(client(), "/login")[1], True)
check("formulier", req(client(), "/login/forgot")[0], 200)
check("te kort nieuw wachtwoord", answer(forgot(client(), "carla", rcc, "000000", "kort")), (400, "Choose a password of 12 to 64 characters."))
check("twee verschillende", answer(forgot(client(), "carla", rcc, "000000", PW2, PW)), (400, "The two passwords do not match."))
check("foute herstelcode", answer(forgot(client(), "carla", "0" * 32, "000000")), (400, M))
check("onbekende naam: zelfde antwoord", answer(forgot(client(), "niemand", "0" * 32, "000000")), (400, M))
check("juiste herstelcode, foute code", answer(forgot(client(), "carla", rcc, "000000")), (400, M))
r = forgot(client(), "carla", " " + rcc.upper() + " ", fresh(secc, "carla"))
rc2 = recovery(r[1])
check("juist: nieuwe herstelcode", (r[0], len(rc2), r[2].get("Cache-Control"), 'href="/login"' in r[1]), (200, 39, "no-store", True))
check("  andere sessie vervalt", loc(req(cc, "/")), "302 /login")
check("  nieuwe herstelcode staat in dezelfde UPDATE", sql("SELECT recovery_hash IS NOT NULL FROM users WHERE username = 'carla'"), "t")
check("  oud wachtwoord", req(client(), "/login", {"username": "carla", "password": PW})[0], 400)
check("  nieuw wachtwoord", loc(req(client(), "/login", {"username": "carla", "password": PW2})), "302 /login/2fa")
check("  oude herstelcode opnieuw", answer(forgot(client(), "carla", rcc, "000000")), (400, M))
same = fresh(secc, "carla")
res = together([lambda x=x: forgot(x, "carla", rc2, same, PW) for x in (client(), client())])
check("twee gelijktijdig met dezelfde codes", sorted(x[0] for x in res), [200, 400])
rc3 = next((recovery(x[1]) for x in res if x[0] == 200), "")
check("  daarna inloggen met het winnende wachtwoord", loc(req(client(), "/login", {"username": "carla", "password": PW})), "302 /login/2fa")
unlock()
check("5 foute herstelcodes, de 6e poging geweigerd (per naam per adres)", tries([forgot(client(), "carla", "0" * 32, "000000") for _ in range(6)]), LOCKED)
check("  onbekende naam: precies hetzelfde", tries([forgot(client(), "niemand", "0" * 32, "000000") for _ in range(6)]), LOCKED)
unlock()
check("juiste herstelcode, 5 foute codes, de 6e geweigerd", tries([forgot(client(), "carla", rc3, f"{i:06d}") for i in range(6)]), LOCKED)
check("  ook de codestap bij inloggen op slot (MIT-06)", req(password_step("carla"), "/login/2fa", {"code": fresh(secc, "carla")})[0], 429)

print("== limieten")
unlock()
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
check("hackweek: 100 per adres, demoaccount zonder teller per naam, 5 min op slot",
      in_app(HACK, "THROTTLE_IP_MODE=hackweek", "THROTTLE_PAIR_EXEMPT_USERS=hackingweek").stdout.split(), ["100", "2", "100", "5", "5"])
check("  hackweek: 60 nieuwe accounts per uur per adres, 5 min op slot",
      in_app("import throttle; print(*throttle.POLICIES['register_ip'])", "THROTTLE_IP_MODE=hackweek").stdout.split(), ["60", "60", "5", "5"])
bad = in_app("import throttle", "THROTTLE_IP_MODE=hackwek")
check("  typfout in de stand: de app start niet", (bad.returncode != 0, "Onbekende THROTTLE_IP_MODE" in bad.stderr), (True, True))
check("  zonder instelling streng", in_app("import throttle; print(throttle.POLICIES['password_ip'].max_failures,"
                                           " len(throttle.password_limits('hackingweek', '198.51.100.1')))").stdout.split(), ["20", "2"])
unlock()

print("== configuratie is invoer (MIT-23)")

check("TRUSTED_PROXIES 0 en 1 starten", (starts("TRUSTED_PROXIES=0"), starts("TRUSTED_PROXIES=1")), ("start", "start"))
check("  -1 en 2 starten niet", (starts("TRUSTED_PROXIES=-1"), starts("TRUSTED_PROXIES=2")),
      ("TRUSTED_PROXIES moet 0 of 1 zijn, niet '-1'.", "TRUSTED_PROXIES moet 0 of 1 zijn, niet '2'."))
check("  HTTPS_ONLY=ja start niet", starts("HTTPS_ONLY=ja"), "HTTPS_ONLY moet 0 of 1 zijn, niet 'ja'.")
check("  te korte FLASK_SECRET_KEY start niet", starts("FLASK_SECRET_KEY=kort"), "FLASK_SECRET_KEY moet minstens 32 tekens zijn.")
check("zonder HTTPS_ONLY: cookie alleen over HTTPS (standaard veilig)", in_app(
    "import app; print(app.app.config['SESSION_COOKIE_SECURE'])", run=("env", "-u", "HTTPS_ONLY", "python", "-c")).stdout.strip(), "True")

print("== invoercontrole (MIT-22)")
NAME_RULE = "Choose a username of 3 to 20 characters: letters, digits and _."
for name in ("<script>alert(1)</script>", "ab", "a" * 21, "met spatie", "anna-b"):
    r = req(client(), "/register", {"username": name, "password": PW})
    check(f"registreren als {name[:24]!r}", (r[0], msg(r[1])), (400, NAME_RULE))
check("  3 en 20 tekens, met _ en cijfers", [req(client(), "/register", {"username": n, "password": PW})[0] for n in ("abc", "a_b_c_1234567890_xyz")], [302, 302])
unlock()
r = req(client(), "/login", {"username": "<script>alert(1)</script>", "password": PW})
check("  inloggen met een ongeldige naam: zelfde antwoord als onbekend", (r[0], msg(r[1])), (400, "Incorrect username or password."))
try:
    big = urllib.request.urlopen(urllib.request.Request(B + "/login", data=b"username=" + b"a" * (17 * 1024) + b"&password=x", method="POST")).status
except urllib.error.HTTPError as e:
    big = e.code
check("verzoek van 17 KiB: 413, niet ingelezen", big, 413)
sql("DELETE FROM auth_throttle; DELETE FROM users WHERE username IN ('abc', 'a_b_c_1234567890_xyz')")

print("== standaard dicht (MIT-24)")
rules = json.loads(in_app("import app, json, auth; print(json.dumps([[r.endpoint, r.rule, sorted(r.methods)]"
                          " for r in app.app.url_map.iter_rules() if r.endpoint not in auth.PUBLIC_ENDPOINTS]))").stdout)
closed = [(e, loc(req(client(), rule.replace("<int:note_id>", "1"), None if "GET" in methods else {}))) for e, rule, methods in rules]
check(f"alle {len(rules)} niet-publieke routes sturen een anonieme bezoeker naar /login", [x for x in closed if x[1] != "302 /login"], [])
check("  publiek zijn alleen inloggen, registreren, de herstelroutes, uitloggen en static",
      in_app("import auth; print(sorted(auth.PUBLIC_ENDPOINTS))").stdout.strip(),
      "['auth.forgot_password', 'auth.login', 'auth.login_code', 'auth.login_recover', 'auth.logout', 'auth.register', 'static']")

print("== beveiligingsheaders (MIT-21)")
CSP = "default-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
for path in ("/login", "/", "/bestaat-niet"):
    h = req(client(), path)[2]
    check(f"headers op {path}", (h.get("Content-Security-Policy"), h.get("X-Frame-Options"), h.get("X-Content-Type-Options"), h.get("Referrer-Policy")),
          (CSP, "DENY", "nosniff", "same-origin"))
check("  lokaal op HTTP geen HSTS", req(client(), "/login")[2].get("Strict-Transport-Security"), None)

print("== CSRF-token (MIT-20)")
ca = account("gert")[0]
before = sql("SELECT count(*) FROM notes")
r = req(ca, "/", {"title": "Zonder token", "body": "x"}, csrf=False)
check("notitie aanmaken zonder token: 400, niets aangemaakt", (r[0], sql("SELECT count(*) FROM notes")), (400, before))
check("  met een fout token: 400", req(ca, "/", {"title": "Fout token", "body": "x", "csrf_token": "x" * 43})[0], 400)
other = client()
req(other, "/login")
check("  met het token van een andere sessie: 400", req(ca, "/", {"title": "Ander token", "body": "x", "csrf_token": csrf_of(other)})[0], 400)
check("  uitloggen zonder token: 400, nog ingelogd", (req(ca, "/logout", {}, csrf=False)[0], req(ca, "/")[0]), (400, 200))
check("  met het eigen token: aangemaakt", loc(req(ca, "/", {"title": "Met token", "body": "x"})), "302 /")
check("  inloggen zonder token: 400", req(client(), "/login", {"username": "gert", "password": PW}, csrf=False)[0], 400)

print("== alleen POST voert uit")
unlock()
heads = [urllib.request.urlopen(urllib.request.Request(B + "/login", method="HEAD")).status for _ in range(3)]
check("3 keer HEAD /login: gewoon 200, telt niet als poging", (heads, sql("SELECT count(*) FROM auth_throttle")), ([200] * 3, "0"))

print("== versleuteling (MIT-17)")
unlock()
cdora, secd, _ = account("dora")
ceva = account("eva")[0]
raw = sql("SELECT totp_secret FROM users WHERE username = 'dora'")
check("TOTP-geheim versleuteld opgeslagen", (raw.startswith("v1:"), secd in raw, len(raw) > len(secd)), (True, False, True))
check("  twee accounts, twee verschillende waarden", raw != sql("SELECT totp_secret FROM users WHERE username = 'eva'"), True)
sql(f"UPDATE users SET totp_secret = '{raw}' WHERE username = 'eva'")
check("versleuteld geheim van dora in de rij van eva: geweigerd", req(password_step("eva"), "/login/2fa", {"code": fresh(secd, "dora")})[0], 400)
check("  dora logt gewoon in", loc(req(client(), "/login", {"username": "dora", "password": PW})), "302 /login/2fa")
req(client(), "/register", {"username": "fien", "password": PW})
f = password_step("fien")
req(f, "/account/2fa")
sql("UPDATE users SET totp_secret = 'v1:AAAA' WHERE username = 'fien'")
check("half ingesteld geheim dat niet ontsleutelt: opnieuw beginnen", loc(req(f, "/account/2fa")), "302 /account/2fa")
r = req(f, "/account/2fa")
check("  nieuw geheim, en instellen lukt", (r[0], req(f, "/account/2fa", {"code": fresh(secret(r[1]), "fien")})[0]), (200, 200))

print("== wachtwoorden gehasht (MIT-19)")
hd, he = sql("SELECT password_hash FROM users WHERE username = 'dora'"), sql("SELECT password_hash FROM users WHERE username = 'eva'")
check("Argon2id met de OWASP-instelling, zonder het wachtwoord", (hd.startswith("$argon2id$v=19$m=19456,t=2,p=1$"), PW in hd), (True, False))
check("  zelfde wachtwoord, andere hash (eigen salt)", hd != he, True)
old = in_app("import os; from cryptography.hazmat.primitives.kdf.argon2 import Argon2id; print(Argon2id(salt=os.urandom(16),"
             f" length=32, iterations=5, memory_cost=7168, lanes=1).derive_phc_encoded({PW!r}.encode()))").stdout.strip()
sql(f"UPDATE users SET password_hash = '{old}' WHERE username = 'dora'")
check("  hash met oude instelling: inloggen lukt", loc(req(client(), "/login", {"username": "dora", "password": PW})), "302 /login/2fa")
check("  en daarna staat er een nieuwe hash", sql("SELECT password_hash FROM users WHERE username = 'dora'").startswith("$argon2id$v=19$m=19456,t=2,p=1$"), True)
unlock()

known, unknown = sorted(took("dora") for _ in range(4)), sorted(took(f"bestaatniet{i}") for i in range(4))
check("  onbekende naam rekent ook: zelfde orde van responstijd", 0.5 < unknown[1] / known[1] < 2, True)
print(f"      (mediaan bekend {known[1]*1000:.0f} ms, onbekend {unknown[1]*1000:.0f} ms)")
unlock()

print("== notities versleuteld (MIT-18)")
req(cdora, "/", {"title": "Fietsslot", "body": "Open met 4821."})
req(ceva, "/", {"title": "Van eva", "body": "Eigen tekst."})
row = sql("SELECT title || ' ' || body FROM notes WHERE user_id = (SELECT id FROM users WHERE username = 'dora')")
check("titel en inhoud versleuteld opgeslagen", (row.count("v1:"), "Fietsslot" in row, "4821" in row), (2, False, False))
check("  de eigenaar leest ze gewoon", all(s in req(cdora, "/")[1] for s in ("Fietsslot", "Open met 4821.")), True)
sql("UPDATE notes SET title = d.title, body = d.body FROM notes d WHERE d.user_id = (SELECT id FROM users WHERE username = 'dora')"
    " AND notes.user_id = (SELECT id FROM users WHERE username = 'eva')")
page = req(ceva, "/")[1]
check("  notitie van dora in de rij van eva: niet te lezen", (page.count("(unreadable)"), "4821" in page), (2, False))
sql("UPDATE notes SET title = body, body = title WHERE user_id = (SELECT id FROM users WHERE username = 'dora')")
check("  titel en inhoud omgewisseld: niet te lezen", req(cdora, "/")[1].count("(unreadable)"), 2)

print("== account verwijderen")
cb, cb2 = login("bram", secb), login("bram", secb)
req(cb, "/", {"title": "Weg", "body": "x"})
check("verwijderen zonder wachtwoord", req(cb, "/account/delete", {})[0], 400)
unlock()
check("  5 foute wachtwoorden, de 6e poging geweigerd", tries([req(cb, "/account/delete", {"current_password": f"fout{i}"}) for i in range(6)]), LOCKED)
check("  het account bestaat nog", sql("SELECT count(*) FROM users WHERE username = 'bram'"), "1")
check("  ook het juiste wachtwoord tijdens de blokkade", req(cb, "/account/delete", {"current_password": PW})[0], 429)
unlock()
check("  het juiste wachtwoord zonder code (MIT-16)", (req(cb, "/account/delete", {"current_password": PW})[0],
      sql("SELECT count(*) FROM users WHERE username = 'bram'")), (400, "1"))
check("account verwijderen, met wachtwoord en code", loc(req(cb, "/account/delete", {"current_password": PW, "code": fresh(secb, "bram")})), "302 /login")
check("  andere sessie", loc(req(cb2, "/")), "302 /login")
check("  login daarna", req(client(), "/login", {"username": "bram", "password": PW})[0], 400)
check("  notities zonder eigenaar", sql("SELECT count(*) FROM notes WHERE user_id NOT IN (SELECT id FROM users)"), "0")

print("== cache, sessieduur en limieten (MIT-28 tot MIT-30)")
ch = account("hugo")[0]
cache = [req(ch, p)[2].get("Cache-Control") for p in ("/", "/account")] + [req(client(), p)[2].get("Cache-Control") for p in ("/login", "/bestaat-niet")]
check("no-store op pagina's, ook ingelogd en bij een 404", cache, ["no-store"] * 4)
check("  statische bestanden mogen in de cache", req(client(), "/static/style.css")[2].get("Cache-Control") != "no-store", True)
AGE_PROBE = """import json, time, urllib.error, urllib.request
from unittest import mock
import app, db
with app.app.app_context():
    u = db.query("SELECT id, session_version FROM users WHERE username = 'hugo'", one=True)
signer = app.app.session_interface.get_signing_serializer(app.app)
class Stop(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args): return None
out = []
for hours in (7, 9, 24 * 30):
    with mock.patch("time.time", return_value=time.time() - hours * 3600):
        cookie = signer.dumps({"user_id": u.id, "session_version": u.session_version})
    try:
        out.append(urllib.request.build_opener(Stop).open(urllib.request.Request("http://127.0.0.1:5000/", headers={"Cookie": "session=" + cookie})).status)
    except urllib.error.HTTPError as e:
        out.append(f"{e.code} {e.headers.get('Location')}")
print(json.dumps(out))"""
check("sessie van 7 uur werkt, van 9 uur en 30 dagen niet", json.loads(in_app(AGE_PROBE).stdout), [200, "302 /login", "302 /login"])
free_register = False
sql(f"DELETE FROM auth_throttle WHERE key = '{REGISTER_KEY}'")
regs = [req(client(), "/register", {"username": f"limiet_{i}", "password": PW}) for i in range(11)]
check("registreren: 10 per uur per adres, de 11e 429", ([r[0] for r in regs], regs[-1][2].get("Retry-After")), ([302] * 10 + [429], "3600"))
check("  met een melding", msg(regs[-1][1]), "Too many new accounts from this address. Try again in 60 minutes.")
check("  geen 11e account", sql("SELECT count(*) FROM users WHERE username LIKE 'limiet\\_%'"), "10")
free_register = True
sql("DELETE FROM users WHERE username LIKE 'limiet\\_%'")
made = [req(ch, "/", {"title": f"n{i}", "body": "x"})[0] for i in range(26)]
check("notities: 25 per account, de 26e geweigerd", (made.count(302), made[-1]), (25, 400))
check("  met een melding, en de teller op de pagina", (msg(req(ch, "/", {"title": "x", "body": "y"})[1]), "25 of 25 notes" in req(ch, "/")[1]),
      ("You have reached the maximum of 25 notes. Delete one first.", True))

print("== databaserol (MIT-27)")
# Draait in de app-container met de DATABASE_URL van de app; elk statement wordt teruggedraaid.
ROLE_PROBE = """import json, os, psycopg
c = psycopg.connect(os.environ["DATABASE_URL"])
out = {"rol": c.execute("SELECT current_user, rolsuper FROM pg_roles WHERE rolname = current_user").fetchone()}
for stmt in ("SELECT count(*) FROM users", "CREATE TABLE proef (x int)", "DROP TABLE notes", "TRUNCATE notes",
             "ALTER TABLE users ADD COLUMN x int", "CREATE ROLE indringer", "COPY (SELECT 1) TO PROGRAM 'true'"):
    try:
        with c.transaction():
            c.execute(stmt)
            raise psycopg.Rollback()
        out[stmt] = "mag"
    except psycopg.errors.InsufficientPrivilege:
        out[stmt] = "geweigerd"
print(json.dumps(out))"""
probe = json.loads(in_app(ROLE_PROBE).stdout)
check("de app logt in als notities_app, geen superuser", probe.pop("rol"), ["notities_app", False])
# De waarde uit .env, niet de naam: vroeger zat het wachtwoord in DATABASE_URL. Wordt nooit geprint.
owner_pw = next(l.partition("=")[2].strip() for l in open(os.path.join(REPO, ".env"), encoding="utf-8") if l.startswith("POSTGRES_PASSWORD="))
check("  het wachtwoord van de eigenaar staat niet in de omgeving van de app", (len(owner_pw) >= 16, owner_pw in compose("exec", "-T", "app", "env").stdout),
      (True, False))
check("  alleen lezen en schrijven mag", probe, {"SELECT count(*) FROM users": "mag", "CREATE TABLE proef (x int)": "geweigerd",
      "DROP TABLE notes": "geweigerd", "TRUNCATE notes": "geweigerd", "ALTER TABLE users ADD COLUMN x int": "geweigerd",
      "CREATE ROLE indringer": "geweigerd", "COPY (SELECT 1) TO PROGRAM 'true'": "geweigerd"})
check("tracebacks in de log", compose("logs", "app", "--since", STARTED).stdout.count("Traceback"), 0)

print("== security-events (MIT-31)")
req(client(), "/login", {"username": 'x\n{"event": "vals"}', "password": "y"})
# Een wachtwoord per ongeluk in het naamveld, en een script dat doorgaat tijdens een blokkade.
unlock()
mark = str(int(time.time()))
req(client(), "/login", {"username": "Zomervakantie2026", "password": "y"})
flood = [req(client(), "/login", {"username": "vloed", "password": f"fout{i}"})[0] for i in range(26)]
time.sleep(1)
recent = compose("logs", "app", "--since", mark, "--no-log-prefix").stdout
locks = sorted(r["scope"] for r in (json.loads(l) for l in recent.splitlines() if l.startswith("{")) if r["event"] == "lockout_started")
check("een naam die geen account is, komt niet in de log", ("Zomervakantie2026" in recent, '"known": false' in recent), (False, True))
# Poging 6 zet de naam op slot, poging 21 het adres: twee blokkades, dus twee regels, niet 21.
check("  26 pogingen, 21 geweigerd: één regel per blokkade", (flood.count(429), locks), (21, ["password_account_ip", "password_ip"]))
unlock()
time.sleep(1)
lines = compose("logs", "app", "--since", STARTED, "--no-log-prefix").stdout.splitlines()
records = [json.loads(l) for l in lines if l.startswith("{")]
seen = {r["event"] for r in records}
# Elke soort die de code kan loggen, zoals hij er staat: een nieuwe soort zonder test valt hier op.
app_code = "".join(open(os.path.join(REPO, "app", f), encoding="utf-8").read() for f in os.listdir(os.path.join(REPO, "app")) if f.endswith(".py"))
want = set(re.findall(r'events\.event\("([a-z_]+)"', app_code))
check(f"alle {len(want)} soorten uit de code staan in de log", sorted(want - seen), [])
check("  elke regel heeft tijd, soort en adres", all({"time", "event", "ip"} <= r.keys() for r in records), True)
joined = "\n".join(lines)
check("  geen wachtwoord, TOTP-geheim of herstelcode in de log", (len(secrets_seen) > 3, [s for s in [PW, PW2, *secrets_seen] if s in joined]), (True, []))
check("  een naam met een regeleinde komt er niet in, en maakt geen valse regel", ("vals" in seen, any(r.get("username", "").startswith("x") for r in records)),
      (False, False))

print("== veilig falen (MIT-25)")
r404 = req(client(), "/bestaat-niet")
check("404 met de eigen pagina", (r404[0], "This page does not exist." in r404[1]), (404, True))
r405 = req(client(), "/logout")
check("  405 met Allow-header", (r405[0], "POST" in r405[2].get("Allow", "")), (405, True))
cz = account("zoe")[0]
# Vanaf hier zoeken, niet "de laatste 2 minuten": als Docker traag is, duurt stoppen en starten langer.
fail_mark = str(int(time.time()))
compose("stop", "db")
r500 = req(cz, "/%0aVALSE%20REGEL")
compose("start", "db")
compose("up", "-d", "--wait", "db")
check("database weg: 500 met een korte melding, zonder details", (r500[0], "Something went wrong." in r500[1], "psycopg" in r500[1], "Traceback" in r500[1]),
      (500, True, False, False))
lines = compose("logs", "app", "--since", fail_mark).stdout.splitlines()
logged = [l for l in lines if "Onverwachte fout" in l]
check("  in de log: de fout, met het regeleinde als \\n", (len(logged), "'/\\nVALSE REGEL'" in (logged or [""])[-1], any(l.rstrip().endswith("| VALSE REGEL'") for l in lines)),
      (1, True, False))
sql("DELETE FROM auth_throttle; DELETE FROM users;")
fails = [name for name, ok in results if not ok]
print(f"\nALLES GOED: {len(results)} controles" if not fails else f"\n{len(fails)} van {len(results)} FOUT: {fails}")
sys.exit(1 if fails else 0)
