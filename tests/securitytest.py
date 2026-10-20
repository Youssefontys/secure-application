"""Security test of the whole app, against the local stack on http://127.0.0.1:5000: one file per topic
(twofactortest.py and onwards, see TESTS), each with the normal flow and the attack, and the mitigation (MIT-..) from
BoK/Threat Analysis/entries.md in its header. NOTE: empties the tables users and auth_throttle, so all local
accounts and notes are gone afterwards. That is why it only runs with --wipe:

    python scripts/deployment.py local
    python tests/securitytest.py --wipe                all tests
    python tests/securitytest.py --wipe bruteforce     only bruteforcetest.py; more names are allowed too

Asks nothing. Only the standard library and docker compose; works on Windows and Linux. Exit 1 if a check fails.
"""
import base64, hashlib, hmac, http.cookiejar, importlib, json, os, re, struct, subprocess, sys, threading, time, zlib
import urllib.error, urllib.parse, urllib.request

# The tests import their helpers from this file. As a script it is called __main__; this way it is the same module
# under both names, with the same results.
sys.modules.setdefault("securitytest", sys.modules[__name__])
TESTS = ("twofactor", "password", "bruteforce", "note", "encryption", "appsec", "logging")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = "http://127.0.0.1:5000"
# Only the log of this run counts; an earlier run deliberately records an error (fail safely).
STARTED = str(int(time.time()))
# Test passwords for the local stack, long enough for the strength rule (MIT-13).
PW, PW2 = "security-test-password", "security-test-password-2"
# Five wrong attempts are allowed, the sixth is refused, and then 15 minutes of waiting (MIT-06, MIT-10).
LOCKED = ([400] * 5 + [429], "900")
# Every result, and every secret a test sees: those must not be in the log at the end.
results, secrets_seen, last = [], [], {}
# The tests register many more than 10 accounts; except in the limit test a registration therefore does not count (MIT-30).
count_registrations, register_key = False, None
# True if all tests run; only then can the log contain every kind of event.
full = False


def compose(*args):
    """A docker compose command in the repo, with the output as text."""
    return subprocess.run(["docker", "compose", *args], capture_output=True, text=True, cwd=REPO)


def in_app(src, *env, run=("python", "-c")):
    """Python in the container of the app, with the environment of the app, plus NAME=value if given."""
    return compose("exec", "-T", *(a for e in env for a in ("-e", e)), "app", *run, src)


def sql(q):
    return compose("exec", "-T", "db", "psql", "-U", "notes_owner", "-d", "notes", "-tAc", q).stdout.strip()


def unlock():
    """All counters and lockouts gone, so the next trial starts clean."""
    sql("DELETE FROM auth_throttle")


def client():
    """A browser of its own: its own cookie, and redirects not followed, so the Location can be seen."""
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar), NoRedirect)
    opener.jar = jar
    return opener


def csrf_of(c):
    """The CSRF token in the session cookie of this browser: signed, not encrypted, so readable."""
    value = next((k.value for k in c.jar if k.name == "session"), "")
    if not value:
        return None
    payload = value.split(".")[1] if value.startswith(".") else value.split(".")[0]
    raw = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
    return json.loads(zlib.decompress(raw) if value.startswith(".") else raw).get("csrf")


def registration_counter():
    """The key of the registration counter for the address the tests reach the app from: the gateway of Docker."""
    global register_key
    if register_key is None:
        gw = subprocess.run(["docker", "network", "inspect", f"{os.path.basename(REPO).lower()}_default", "--format",
                             "{{(index .IPAM.Config 0).Gateway}}"], capture_output=True, text=True).stdout.strip()
        register_key = in_app(f"import throttle; print(throttle.limit('register_ip', throttle.client_ip({gw!r})).key)").stdout.strip()
    return register_key


def req(c, path, data=None, csrf=True):
    """(status, body, headers) of a GET, or of a POST if there is data; a POST gets the CSRF token, as in a form."""
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
    """The first message (error or confirmation) on the page."""
    m = re.search(r'class="(error|notice)">([^<]*)', body)
    return m.group(2) if m else "-"


def secret(body):
    """The TOTP secret on the setup page, without spaces."""
    secrets_seen.append(s := re.search(r'class="secret">([A-Z2-7 ]+)<', body).group(1).replace(" ", ""))
    return s


def recovery(body):
    """The recovery code on the page, or "" if there is none."""
    m = re.search(r'class="secret">([0-9a-f-]+)<', body)
    secrets_seen.extend(m.groups() if m else ())
    return m.group(1) if m else ""


def tries(rs):
    """The status codes of a series of attempts, and the Retry-After of the last one."""
    return [r[0] for r in rs], rs[-1][2]["Retry-After"]


def together(fns):
    """Starts all functions at the same moment, each in a thread of its own, and returns the results."""
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
    print(f"{'ok  ' if ok else 'FAIL'} {name:58} {got}")


def code(key, offset=0):
    """The TOTP code an authenticator app would show now (plus offset steps) (RFC 6238)."""
    mac = hmac.new(base64.b32decode(key), struct.pack(">Q", int(time.time() // 30) + offset), hashlib.sha1).digest()
    o = mac[-1] & 15
    return f"{(int.from_bytes(mac[o:o + 4], 'big') & 0x7FFFFFFF) % 1000000:06d}"


def fresh(sec, u):
    """A code from a time step that has not been used for this account yet."""
    now = int(time.time() // 30)
    step = max(last.get(u, now - 2) + 1, now - 1)
    # The previous step only if the current one still lasts a while; otherwise the code is too old on arrival.
    if step == now - 1 and time.time() % 30 > 25:
        step = now
    while step > int(time.time() // 30) + 1:
        time.sleep(1)
    last[u] = step
    return code(sec, step - int(time.time() // 30))


def password_step(u, pw=PW):
    """A browser after the first step of logging in: the password is right, the code is still to come."""
    c = client()
    req(c, "/login", {"username": u, "password": pw})
    return c


def login(u, sec, pw=PW):
    c = password_step(u, pw)
    req(c, "/login/2fa", {"code": fresh(sec, u)})
    return c


def account(u, pw=PW):
    """Registers, logs in and turns on two-step verification. Returns (session, secret, recovery code)."""
    req(client(), "/register", {"username": u, "password": pw})
    c = password_step(u, pw)
    sec = secret(req(c, "/account/2fa")[1])
    return c, sec, recovery(req(c, "/account/2fa", {"code": fresh(sec, u)})[1])


if __name__ == "__main__":
    chosen = [a for a in sys.argv[1:] if a != "--wipe"]
    if "--wipe" not in sys.argv:
        sys.exit(__doc__)
    if unknown := sorted(set(chosen) - set(TESTS)):
        sys.exit(f"Unknown test: {', '.join(unknown)}. Choose from: {', '.join(TESTS)}.")
    # Always in the order of TESTS: logging searches the log of the tests before it, and stops the database last.
    chosen = [t for t in TESTS if t in chosen] or list(TESTS)
    full = chosen == list(TESTS)
    sql("DELETE FROM auth_throttle; DELETE FROM users;")
    for name in chosen:
        print(f"\n#### {name}test.py")
        importlib.import_module(f"{name}test").run()
    sql("DELETE FROM auth_throttle; DELETE FROM users;")
    fails = [n for n, ok in results if not ok]
    print(f"\nALL GOOD: {len(results)} checks" if not fails else f"\n{len(fails)} of {len(results)} FAILED: {fails}")
    sys.exit(1 if fails else 0)
