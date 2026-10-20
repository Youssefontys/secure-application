"""Logging and failing safely: the security events, the checks over the whole log of this run, and last an error with
the database gone (MIT-25, MIT-31). That is why it runs last. Runs through securitytest.py."""
import securitytest
from securitytest import *


def logs(since, prefix=False):
    return compose("logs", "app", "--since", since, *(() if prefix else ("--no-log-prefix",))).stdout


def run():
    print("== security events (MIT-31)")
    req(client(), "/login", {"username": 'x\n{"event": "fake"}', "password": "y"})
    # A password typed into the name field by accident, and a script that goes on during a lockout.
    unlock()
    mark = str(int(time.time()))
    req(client(), "/login", {"username": "Summerholiday2026", "password": "y"})
    flood = [req(client(), "/login", {"username": "flood", "password": f"wrong{i}"})[0] for i in range(26)]
    time.sleep(1)
    recent = logs(mark)
    locks = sorted(r["scope"] for r in (json.loads(l) for l in recent.splitlines() if l.startswith("{")) if r["event"] == "lockout_started")
    check("a name that is not an account does not go into the log", ("Summerholiday2026" in recent, '"known": false' in recent), (False, True))
    # Attempt 6 locks the name, attempt 21 the address: two lockouts, so two lines, not 21.
    check("  26 attempts, 21 refused: one line per lockout", (flood.count(429), locks), (21, ["password_account_ip", "password_ip"]))
    unlock()
    time.sleep(1)
    lines = logs(STARTED).splitlines()
    records = [json.loads(l) for l in lines if l.startswith("{")]
    seen = {r["event"] for r in records}
    check("  every line has time, kind and address", all({"time", "event", "ip"} <= r.keys() for r in records), True)
    check("  a name with a line break does not get in, and makes no false line", ("fake" in seen, any(r.get("username", "").startswith("x") for r in records)),
          (False, False))
    check("tracebacks in the log", logs(STARTED, prefix=True).count("Traceback"), 0)
    if securitytest.full:
        # Every kind the code can log, as it is written there: a new kind without a test shows up here.
        app_code = "".join(open(os.path.join(REPO, "app", f), encoding="utf-8").read() for f in os.listdir(os.path.join(REPO, "app")) if f.endswith(".py"))
        want = set(re.findall(r'events\.event\("([a-z_]+)"', app_code))
        check(f"all {len(want)} kinds from the code are in the log", sorted(want - seen), [])
        joined = "\n".join(lines)
        check("  no password, TOTP secret or recovery code in the log", (len(secrets_seen) > 3, [s for s in [PW, PW2, *secrets_seen] if s in joined]), (True, []))

    print("== failing safely (MIT-25)")
    r404 = req(client(), "/does-not-exist")
    check("404 with the own page", (r404[0], "This page does not exist." in r404[1]), (404, True))
    r405 = req(client(), "/logout")
    check("  405 with Allow header", (r405[0], "POST" in r405[2].get("Allow", "")), (405, True))
    cz = account("testacc14")[0]
    # Search from here, not "the last 2 minutes": when Docker is slow, stopping and starting takes longer.
    fail_mark = str(int(time.time()))
    compose("stop", "db")
    r500 = req(cz, "/%0aFALSE%20LINE")
    compose("start", "db")
    compose("up", "-d", "--wait", "db")
    check("database gone: 500 with a short message, without details", (r500[0], "Something went wrong." in r500[1], "psycopg" in r500[1], "Traceback" in r500[1]),
          (500, True, False, False))
    lines = logs(fail_mark, prefix=True).splitlines()
    logged = [l for l in lines if "Unexpected error" in l]
    check("  in the log: the error, with the line break as \\n", (len(logged), "'/\\nFALSE LINE'" in (logged or [""])[-1],
          any(l.rstrip().endswith("| FALSE LINE'") for l in lines)), (1, True, False))
