"""Logging en veilig falen: de security-events, de controles over de hele log van deze run, en als laatste een fout met
de database weg (MIT-25, MIT-31). Draait daarom als laatste. Draait via securitytest.py."""
import securitytest
from securitytest import *


def logs(since, prefix=False):
    return compose("logs", "app", "--since", since, *(() if prefix else ("--no-log-prefix",))).stdout


def run():
    print("== security-events (MIT-31)")
    req(client(), "/login", {"username": 'x\n{"event": "vals"}', "password": "y"})
    # Een wachtwoord per ongeluk in het naamveld, en een script dat doorgaat tijdens een blokkade.
    unlock()
    mark = str(int(time.time()))
    req(client(), "/login", {"username": "Zomervakantie2026", "password": "y"})
    flood = [req(client(), "/login", {"username": "vloed", "password": f"fout{i}"})[0] for i in range(26)]
    time.sleep(1)
    recent = logs(mark)
    locks = sorted(r["scope"] for r in (json.loads(l) for l in recent.splitlines() if l.startswith("{")) if r["event"] == "lockout_started")
    check("een naam die geen account is, komt niet in de log", ("Zomervakantie2026" in recent, '"known": false' in recent), (False, True))
    # Poging 6 zet de naam op slot, poging 21 het adres: twee blokkades, dus twee regels, niet 21.
    check("  26 pogingen, 21 geweigerd: één regel per blokkade", (flood.count(429), locks), (21, ["password_account_ip", "password_ip"]))
    unlock()
    time.sleep(1)
    lines = logs(STARTED).splitlines()
    records = [json.loads(l) for l in lines if l.startswith("{")]
    seen = {r["event"] for r in records}
    check("  elke regel heeft tijd, soort en adres", all({"time", "event", "ip"} <= r.keys() for r in records), True)
    check("  een naam met een regeleinde komt er niet in, en maakt geen valse regel", ("vals" in seen, any(r.get("username", "").startswith("x") for r in records)),
          (False, False))
    check("tracebacks in de log", logs(STARTED, prefix=True).count("Traceback"), 0)
    if securitytest.full:
        # Elke soort die de code kan loggen, zoals hij er staat: een nieuwe soort zonder test valt hier op.
        app_code = "".join(open(os.path.join(REPO, "app", f), encoding="utf-8").read() for f in os.listdir(os.path.join(REPO, "app")) if f.endswith(".py"))
        want = set(re.findall(r'events\.event\("([a-z_]+)"', app_code))
        check(f"alle {len(want)} soorten uit de code staan in de log", sorted(want - seen), [])
        joined = "\n".join(lines)
        check("  geen wachtwoord, TOTP-geheim of herstelcode in de log", (len(secrets_seen) > 3, [s for s in [PW, PW2, *secrets_seen] if s in joined]), (True, []))

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
    lines = logs(fail_mark, prefix=True).splitlines()
    logged = [l for l in lines if "Onverwachte fout" in l]
    check("  in de log: de fout, met het regeleinde als \\n", (len(logged), "'/\\nVALSE REGEL'" in (logged or [""])[-1],
          any(l.rstrip().endswith("| VALSE REGEL'") for l in lines)), (1, True, False))
