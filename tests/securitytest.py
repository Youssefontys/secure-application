"""Securitytest van de hele app, tegen de lokale stack op http://127.0.0.1:5000: per onderwerp een eigen bestand
(twofactortest.py en verder, zie TESTS), elk met de normale werking en de aanval, en de maatregel (MIT-..) uit
BoK/Threat Analysis/entries.md in de kop. LET OP: maakt de tabellen users en auth_throttle leeg, dus alle lokale
accounts en notities zijn daarna weg. Daarom draait hij alleen met --wipe:

    python scripts/deployment.py lokaal
    python tests/securitytest.py --wipe                alle tests
    python tests/securitytest.py --wipe bruteforce     alleen bruteforcetest.py; meer namen mag ook

Vraagt niets. Alleen de standaardbibliotheek en docker compose; werkt op Windows en Linux. Exit 1 als een controle faalt.
"""
import base64, hashlib, hmac, http.cookiejar, importlib, json, os, re, struct, subprocess, sys, threading, time, zlib
import urllib.error, urllib.parse, urllib.request

# De tests importeren hun helpers uit dit bestand. Als script heet het __main__; zo is het onder beide namen dezelfde
# module, met dezelfde uitkomsten.
sys.modules.setdefault("securitytest", sys.modules[__name__])
TESTS = ("twofactor", "password", "bruteforce", "note", "encryption", "appsec", "logging")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = "http://127.0.0.1:5000"
# Alleen de log van deze run telt; een vorige run legt bewust een fout vast (veilig falen).
STARTED = str(int(time.time()))
# Testwachtwoorden voor de lokale stack, lang genoeg voor de sterkte-eis (MIT-13).
PW, PW2 = "regressie-wachtwoord", "regressie-wachtwoord-2"
# Vijf keer fout mag, de zesde poging wordt geweigerd, en dan 15 minuten wachten (MIT-06, MIT-10).
LOCKED = ([400] * 5 + [429], "900")
# Elke uitkomst, en elk geheim dat een test ziet: die mogen aan het eind niet in de log staan.
results, secrets_seen, last = [], [], {}
# De tests registreren veel meer dan 10 accounts; behalve in de limiet-test telt een registratie daarom niet (MIT-30).
count_registrations, register_key = False, None
# True als alle tests draaien; alleen dan kan de log alle soorten gebeurtenissen bevatten.
full = False


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


def registration_counter():
    """De sleutel van de registratieteller voor het adres waarmee de tests bij de app aankomen: de gateway van Docker."""
    global register_key
    if register_key is None:
        gw = subprocess.run(["docker", "network", "inspect", f"{os.path.basename(REPO).lower()}_default", "--format",
                             "{{(index .IPAM.Config 0).Gateway}}"], capture_output=True, text=True).stdout.strip()
        register_key = in_app(f"import throttle; print(throttle.limit('register_ip', throttle.client_ip({gw!r})).key)").stdout.strip()
    return register_key


def req(c, path, data=None, csrf=True):
    """(status, body, headers) van een GET, of van een POST als er data is; een POST krijgt het CSRF-token mee, zoals in een formulier."""
    if path == "/register" and data is not None and not count_registrations:
        sql(f"DELETE FROM auth_throttle WHERE key = '{registration_counter()}'")
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


if __name__ == "__main__":
    chosen = [a for a in sys.argv[1:] if a != "--wipe"]
    if "--wipe" not in sys.argv:
        sys.exit(__doc__)
    if unknown := sorted(set(chosen) - set(TESTS)):
        sys.exit(f"Onbekende test: {', '.join(unknown)}. Kies uit: {', '.join(TESTS)}.")
    # Altijd in de volgorde van TESTS: logging zoekt in de log van de tests ervoor, en stopt als laatste de database.
    chosen = [t for t in TESTS if t in chosen] or list(TESTS)
    full = chosen == list(TESTS)
    sql("DELETE FROM auth_throttle; DELETE FROM users;")
    for name in chosen:
        print(f"\n#### {name}test.py")
        importlib.import_module(f"{name}test").run()
    sql("DELETE FROM auth_throttle; DELETE FROM users;")
    fails = [n for n, ok in results if not ok]
    print(f"\nALLES GOED: {len(results)} controles" if not fails else f"\n{len(fails)} van {len(results)} FOUT: {fails}")
    sys.exit(1 if fails else 0)
