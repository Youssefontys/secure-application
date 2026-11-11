"""Application security: configuration as input, input validation, the consent at registration, closed by default, headers,
CSRF, only POST, cache and session lifetime, the rights of the database role, and the libraries the app loads (MIT-20 to MIT-29, MIT-41, MIT-48). Runs through securitytest.py."""
from securitytest import *

CSP = "default-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
PERMISSIONS = "camera=(), geolocation=(), microphone=(), payment=(), usb=()"
HEADERS = ("Content-Security-Policy", "X-Frame-Options", "X-Content-Type-Options", "Referrer-Policy", "Permissions-Policy",
           "Cross-Origin-Opener-Policy", "Cross-Origin-Resource-Policy", "Cross-Origin-Embedder-Policy")
# Every process in the container, then which of the libraries the VEX says are never used it has loaded (MIT-41).
MAPS_PROBE = """import glob
libs, n = set(), 0
for f in glob.glob('/proc/[0-9]*/maps'):
    try:
        lines = open(f).read().splitlines()
    except OSError:
        continue
    n += 1
    libs |= {l.split()[-1] for l in lines if 'sqlite' in l or 'lastlog2' in l}
print(n, sorted(libs))"""
# The VEX also says the app uses no Kerberos: its database connection is not GSSAPI, and nothing is configured for it (MIT-41).
KRB_PROBE = """import glob, json, os, psycopg
gss = psycopg.connect(os.environ['DATABASE_URL']).execute('SELECT gss_authenticated FROM pg_stat_gssapi WHERE pid = pg_backend_pid()').fetchone()[0]
print(json.dumps([gss, os.path.exists('/etc/krb5.conf'), sorted(k for k in os.environ if k.startswith('KRB5')), glob.glob('/tmp/krb5cc*')]))"""
NAME_RULE = "Choose a username of 3 to 20 characters: letters, digits and _."
CONSENT_RULE = "Tick the box to agree to the privacy statement."
AGE_PROBE = """import json, time, urllib.error, urllib.request
from unittest import mock
import app, db
with app.app.app_context():
    u = db.query("SELECT id, session_version FROM users WHERE username = 'testacc13'", one=True)
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
# Runs in the app container with the DATABASE_URL of the app; every statement is rolled back.
ROLE_PROBE = """import json, os, psycopg
c = psycopg.connect(os.environ["DATABASE_URL"])
out = {"role": c.execute("SELECT current_user, rolsuper FROM pg_roles WHERE rolname = current_user").fetchone()}
for stmt in ("SELECT count(*) FROM users", "CREATE TABLE trial (x int)", "DROP TABLE notes", "TRUNCATE notes",
             "ALTER TABLE users ADD COLUMN x int", "CREATE ROLE intruder", "COPY (SELECT 1) TO PROGRAM 'true'"):
    try:
        with c.transaction():
            c.execute(stmt)
            raise psycopg.Rollback()
        out[stmt] = "allowed"
    except psycopg.errors.InsufficientPrivilege:
        out[stmt] = "refused"
print(json.dumps(out))"""


def starts(*env):
    """"start" if the app starts with these settings, otherwise the error message it stops with (MIT-23)."""
    r = in_app("import app", *env)
    return "start" if r.returncode == 0 else r.stderr.strip().splitlines()[-1].split(": ", 1)[-1]


def run():
    print("== configuration is input (MIT-23)")
    check("TRUSTED_PROXIES 0 and 1 start", (starts("TRUSTED_PROXIES=0"), starts("TRUSTED_PROXIES=1")), ("start", "start"))
    check("  -1 and 2 do not start", (starts("TRUSTED_PROXIES=-1"), starts("TRUSTED_PROXIES=2")),
          ("TRUSTED_PROXIES must be 0 or 1, not '-1'.", "TRUSTED_PROXIES must be 0 or 1, not '2'."))
    check("  HTTPS_ONLY=yes does not start", starts("HTTPS_ONLY=yes"), "HTTPS_ONLY must be 0 or 1, not 'yes'.")
    check("  too short FLASK_SECRET_KEY does not start", starts("FLASK_SECRET_KEY=short"), "FLASK_SECRET_KEY must be at least 32 characters.")
    check("without HTTPS_ONLY: cookie only over HTTPS (safe by default)", in_app(
        "import app; print(app.app.config['SESSION_COOKIE_SECURE'])", run=("env", "-u", "HTTPS_ONLY", "python", "-c")).stdout.strip(), "True")

    print("== input validation (MIT-22)")
    for name in ("<script>alert(1)</script>", "ab", "a" * 21, "with space", "testacc1-b"):
        r = req(client(), "/register", {"username": name, "password": PW})
        check(f"register as {name[:24]!r}", (r[0], msg(r[1])), (400, NAME_RULE))
    check("  3 and 20 characters, with _ and digits", [req(client(), "/register", {"username": n, "password": PW})[0] for n in ("abc", "a_b_c_1234567890_xyz")],
          [302, 302])
    unlock()
    r = req(client(), "/login", {"username": "<script>alert(1)</script>", "password": PW})
    check("  logging in with an invalid name: same answer as unknown", (r[0], msg(r[1])), (400, "Incorrect username or password."))
    try:
        big = urllib.request.urlopen(urllib.request.Request(B + "/login", data=b"username=" + b"a" * (17 * 1024) + b"&password=x", method="POST")).status
    except urllib.error.HTTPError as e:
        big = e.code
    check("request of 17 KiB: 413, not read", big, 413)
    sql("DELETE FROM auth_throttle; DELETE FROM users WHERE username IN ('abc', 'a_b_c_1234567890_xyz')")

    print("== consent at registration (MIT-48)")
    form = req(client(), "/register")[1]
    check("the form has the box, required and not ticked", bool(re.search(r'<input type="checkbox" name="consent" value="yes" required>', form)), True)
    check("  with a link to the privacy statement", 'href="/privacy"' in form, True)
    check("the privacy statement is public", (req(client(), "/privacy")[0], "Privacy statement" in req(client(), "/privacy")[1]), (200, True))
    before = sql("SELECT count(*) FROM users")
    r = req(client(), "/register", {"username": "consent1", "password": PW}, consent=False)
    check("register without the box: 400, no account", (r[0], msg(r[1]), sql("SELECT count(*) FROM users")), (400, CONSENT_RULE, before))
    r = req(client(), "/register", {"username": "consent1", "password": PW, "consent": "no"}, consent=False)
    check("  with another value than yes: the same", (r[0], msg(r[1])), (400, CONSENT_RULE))
    check("  with the box: the account is made (not 409)", req(client(), "/register", {"username": "consent1", "password": PW})[0], 302)
    sql("DELETE FROM users WHERE username = 'consent1'")

    print("== closed by default (MIT-24)")
    rules = json.loads(in_app("import app, json, auth; print(json.dumps([[r.endpoint, r.rule, sorted(r.methods)]"
                              " for r in app.app.url_map.iter_rules() if r.endpoint not in auth.PUBLIC_ENDPOINTS]))").stdout)
    closed = [(e, loc(req(client(), rule.replace("<int:note_id>", "1"), None if "GET" in methods else {}))) for e, rule, methods in rules]
    check(f"all {len(rules)} non-public routes send an anonymous visitor to /login", [x for x in closed if x[1] != "302 /login"], [])
    check("  only login, register, the recovery routes, logout, the privacy statement and static are public",
          in_app("import auth; print(sorted(auth.PUBLIC_ENDPOINTS))").stdout.strip(),
          "['auth.forgot_password', 'auth.login', 'auth.login_code', 'auth.login_recover', 'auth.logout', 'auth.privacy', 'auth.register', 'static']")

    print("== security headers (MIT-21)")
    for path in ("/login", "/", "/does-not-exist"):
        h = req(client(), path)[2]
        check(f"headers on {path}", tuple(h.get(name) for name in HEADERS),
              (CSP, "DENY", "nosniff", "same-origin", PERMISSIONS, "same-origin", "same-origin", "require-corp"))
    check("  locally on HTTP no HSTS", req(client(), "/login")[2].get("Strict-Transport-Security"), None)

    print("== CSRF token (MIT-20)")
    ca = account("testacc12")[0]
    before = sql("SELECT count(*) FROM notes")
    r = req(ca, "/", {"title": "No token", "body": "x"}, csrf=False)
    check("create a note without a token: 400, nothing created", (r[0], sql("SELECT count(*) FROM notes")), (400, before))
    check("  with a wrong token: 400", req(ca, "/", {"title": "Wrong token", "body": "x", "csrf_token": "x" * 43})[0], 400)
    other = client()
    req(other, "/login")
    check("  with the token of another session: 400", req(ca, "/", {"title": "Other token", "body": "x", "csrf_token": csrf_of(other)})[0], 400)
    check("  logging out without a token: 400, still logged in", (req(ca, "/logout", {}, csrf=False)[0], req(ca, "/")[0]), (400, 200))
    check("  with the own token: created", loc(req(ca, "/", {"title": "With token", "body": "x"})), "302 /")
    check("  logging in without a token: 400", req(client(), "/login", {"username": "testacc12", "password": PW}, csrf=False)[0], 400)

    print("== only POST acts")
    unlock()
    heads = [urllib.request.urlopen(urllib.request.Request(B + "/login", method="HEAD")).status for _ in range(3)]
    check("3 times HEAD /login: plain 200, does not count as an attempt", (heads, sql("SELECT count(*) FROM auth_throttle")), ([200] * 3, "0"))

    print("== cache and session lifetime (MIT-28, MIT-29)")
    ch = account("testacc13")[0]
    cache = [req(ch, p)[2].get("Cache-Control") for p in ("/", "/account")] + [req(client(), p)[2].get("Cache-Control") for p in ("/login", "/does-not-exist")]
    check("no-store on pages, also logged in and on a 404", cache, ["no-store"] * 4)
    check("  static files may be cached", req(client(), "/static/style.css")[2].get("Cache-Control") != "no-store", True)
    check("session of 7 hours works, of 9 hours and 30 days not", json.loads(in_app(AGE_PROBE).stdout), [200, "302 /login", "302 /login"])

    print("== database role (MIT-27)")
    probe = json.loads(in_app(ROLE_PROBE).stdout)
    check("the app logs in as notes_app, no superuser", probe.pop("role"), ["notes_app", False])
    # The value from .env, not the name: the password used to be in DATABASE_URL. Never printed.
    owner_pw = next(l.partition("=")[2].strip() for l in open(os.path.join(REPO, ".env"), encoding="utf-8") if l.startswith("POSTGRES_PASSWORD="))
    check("  the password of the owner is not in the environment of the app", (len(owner_pw) >= 16, owner_pw in compose("exec", "-T", "app", "env").stdout),
          (True, False))
    check("  only reading and writing is allowed", probe, {"SELECT count(*) FROM users": "allowed", "CREATE TABLE trial (x int)": "refused",
          "DROP TABLE notes": "refused", "TRUNCATE notes": "refused", "ALTER TABLE users ADD COLUMN x int": "refused",
          "CREATE ROLE intruder": "refused", "COPY (SELECT 1) TO PROGRAM 'true'": "refused"})

    print("== libraries the app loads (MIT-41)")
    # vex/openvex.json says libsqlite3-0 is not in the execute path: it is there because liblastlog2-2 needs it, and the app
    # never loads either. After all tests above, every process (gunicorn and its workers) has been in use.
    seen = in_app(MAPS_PROBE).stdout.strip()
    check("no process of the app has loaded libsqlite3 or liblastlog2", (int(seen.split()[0]) >= 3, seen.split(" ", 1)[1]), (True, "[]"))
    check("  no Kerberos: the database login is not GSSAPI, no krb5.conf, no KRB5 variable, no ticket cache",
          json.loads(in_app(KRB_PROBE).stdout), [False, False, [], []])
