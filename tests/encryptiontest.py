"""Versleuteling: het TOTP-geheim en de notities versleuteld en aan hun plek gebonden, de wachtwoorden met Argon2id
(MIT-17 tot MIT-19). Draait via securitytest.py."""
from securitytest import *


def took(name):
    """Hoe lang een mislukte login voor deze naam duurt, in seconden."""
    s = time.perf_counter()
    req(client(), "/login", {"username": name, "password": "fout-wachtwoord-123"})
    return time.perf_counter() - s


def run():
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
    check("  en daarna staat er een nieuwe hash", sql("SELECT password_hash FROM users WHERE username = 'dora'").startswith("$argon2id$v=19$m=19456,t=2,p=1$"),
          True)
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
