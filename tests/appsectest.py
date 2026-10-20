"""Applicatiebeveiliging: configuratie als invoer, invoercontrole, standaard dicht, headers, CSRF, alleen POST, cache en
sessieduur, en de rechten van de databaserol (MIT-20 tot MIT-29). Draait via securitytest.py."""
from securitytest import *

CSP = "default-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
NAME_RULE = "Choose a username of 3 to 20 characters: letters, digits and _."
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


def starts(*env):
    """"start" als de app met deze instellingen start, anders de foutmelding waarmee hij stopt (MIT-23)."""
    r = in_app("import app", *env)
    return "start" if r.returncode == 0 else r.stderr.strip().splitlines()[-1].split(": ", 1)[-1]


def run():
    print("== configuratie is invoer (MIT-23)")
    check("TRUSTED_PROXIES 0 en 1 starten", (starts("TRUSTED_PROXIES=0"), starts("TRUSTED_PROXIES=1")), ("start", "start"))
    check("  -1 en 2 starten niet", (starts("TRUSTED_PROXIES=-1"), starts("TRUSTED_PROXIES=2")),
          ("TRUSTED_PROXIES moet 0 of 1 zijn, niet '-1'.", "TRUSTED_PROXIES moet 0 of 1 zijn, niet '2'."))
    check("  HTTPS_ONLY=ja start niet", starts("HTTPS_ONLY=ja"), "HTTPS_ONLY moet 0 of 1 zijn, niet 'ja'.")
    check("  te korte FLASK_SECRET_KEY start niet", starts("FLASK_SECRET_KEY=kort"), "FLASK_SECRET_KEY moet minstens 32 tekens zijn.")
    check("zonder HTTPS_ONLY: cookie alleen over HTTPS (standaard veilig)", in_app(
        "import app; print(app.app.config['SESSION_COOKIE_SECURE'])", run=("env", "-u", "HTTPS_ONLY", "python", "-c")).stdout.strip(), "True")

    print("== invoercontrole (MIT-22)")
    for name in ("<script>alert(1)</script>", "ab", "a" * 21, "met spatie", "anna-b"):
        r = req(client(), "/register", {"username": name, "password": PW})
        check(f"registreren als {name[:24]!r}", (r[0], msg(r[1])), (400, NAME_RULE))
    check("  3 en 20 tekens, met _ en cijfers", [req(client(), "/register", {"username": n, "password": PW})[0] for n in ("abc", "a_b_c_1234567890_xyz")],
          [302, 302])
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

    print("== cache en sessieduur (MIT-28, MIT-29)")
    ch = account("hugo")[0]
    cache = [req(ch, p)[2].get("Cache-Control") for p in ("/", "/account")] + [req(client(), p)[2].get("Cache-Control") for p in ("/login", "/bestaat-niet")]
    check("no-store op pagina's, ook ingelogd en bij een 404", cache, ["no-store"] * 4)
    check("  statische bestanden mogen in de cache", req(client(), "/static/style.css")[2].get("Cache-Control") != "no-store", True)
    check("sessie van 7 uur werkt, van 9 uur en 30 dagen niet", json.loads(in_app(AGE_PROBE).stdout), [200, "302 /login", "302 /login"])

    print("== databaserol (MIT-27)")
    probe = json.loads(in_app(ROLE_PROBE).stdout)
    check("de app logt in als notities_app, geen superuser", probe.pop("rol"), ["notities_app", False])
    # De waarde uit .env, niet de naam: vroeger zat het wachtwoord in DATABASE_URL. Wordt nooit geprint.
    owner_pw = next(l.partition("=")[2].strip() for l in open(os.path.join(REPO, ".env"), encoding="utf-8") if l.startswith("POSTGRES_PASSWORD="))
    check("  het wachtwoord van de eigenaar staat niet in de omgeving van de app", (len(owner_pw) >= 16, owner_pw in compose("exec", "-T", "app", "env").stdout),
          (True, False))
    check("  alleen lezen en schrijven mag", probe, {"SELECT count(*) FROM users": "mag", "CREATE TABLE proef (x int)": "geweigerd",
          "DROP TABLE notes": "geweigerd", "TRUNCATE notes": "geweigerd", "ALTER TABLE users ADD COLUMN x int": "geweigerd",
          "CREATE ROLE indringer": "geweigerd", "COPY (SELECT 1) TO PROGRAM 'true'": "geweigerd"})
