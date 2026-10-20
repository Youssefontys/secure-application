"""Encryption: the TOTP secret and the notes encrypted and bound to their place, the passwords with Argon2id
(MIT-17 to MIT-19). Runs through securitytest.py."""
from securitytest import *


def took(name):
    """How long a failed login for this name takes, in seconds."""
    s = time.perf_counter()
    req(client(), "/login", {"username": name, "password": "wrong-password-123"})
    return time.perf_counter() - s


def run():
    print("== encryption (MIT-17)")
    unlock()
    cdora, secd, _ = account("dora")
    ceva = account("eva")[0]
    raw = sql("SELECT totp_secret FROM users WHERE username = 'dora'")
    check("TOTP secret stored encrypted", (raw.startswith("v1:"), secd in raw, len(raw) > len(secd)), (True, False, True))
    check("  two accounts, two different values", raw != sql("SELECT totp_secret FROM users WHERE username = 'eva'"), True)
    sql(f"UPDATE users SET totp_secret = '{raw}' WHERE username = 'eva'")
    check("encrypted secret of dora in the row of eva: refused", req(password_step("eva"), "/login/2fa", {"code": fresh(secd, "dora")})[0], 400)
    check("  dora logs in as usual", loc(req(client(), "/login", {"username": "dora", "password": PW})), "302 /login/2fa")
    req(client(), "/register", {"username": "fien", "password": PW})
    f = password_step("fien")
    req(f, "/account/2fa")
    sql("UPDATE users SET totp_secret = 'v1:AAAA' WHERE username = 'fien'")
    check("half set up secret that does not decrypt: start again", loc(req(f, "/account/2fa")), "302 /account/2fa")
    r = req(f, "/account/2fa")
    check("  new secret, and the setup works", (r[0], req(f, "/account/2fa", {"code": fresh(secret(r[1]), "fien")})[0]), (200, 200))

    print("== passwords hashed (MIT-19)")
    hd, he = sql("SELECT password_hash FROM users WHERE username = 'dora'"), sql("SELECT password_hash FROM users WHERE username = 'eva'")
    check("Argon2id with the OWASP setting, without the password", (hd.startswith("$argon2id$v=19$m=19456,t=2,p=1$"), PW in hd), (True, False))
    check("  same password, different hash (own salt)", hd != he, True)
    old = in_app("import os; from cryptography.hazmat.primitives.kdf.argon2 import Argon2id; print(Argon2id(salt=os.urandom(16),"
                 f" length=32, iterations=5, memory_cost=7168, lanes=1).derive_phc_encoded({PW!r}.encode()))").stdout.strip()
    sql(f"UPDATE users SET password_hash = '{old}' WHERE username = 'dora'")
    check("  hash with an old setting: logging in works", loc(req(client(), "/login", {"username": "dora", "password": PW})), "302 /login/2fa")
    check("  and after that there is a new hash", sql("SELECT password_hash FROM users WHERE username = 'dora'").startswith("$argon2id$v=19$m=19456,t=2,p=1$"),
          True)
    unlock()
    known, unknown = sorted(took("dora") for _ in range(4)), sorted(took(f"nosuchuser{i}") for i in range(4))
    check("  unknown name calculates too: same order of response time", 0.5 < unknown[1] / known[1] < 2, True)
    print(f"      (median known {known[1]*1000:.0f} ms, unknown {unknown[1]*1000:.0f} ms)")
    unlock()

    print("== notes encrypted (MIT-18)")
    req(cdora, "/", {"title": "Bike lock", "body": "Opens with 4821."})
    req(ceva, "/", {"title": "From eva", "body": "Own text."})
    row = sql("SELECT title || ' ' || body FROM notes WHERE user_id = (SELECT id FROM users WHERE username = 'dora')")
    check("title and body stored encrypted", (row.count("v1:"), "Bike lock" in row, "4821" in row), (2, False, False))
    check("  the owner reads them as usual", all(s in req(cdora, "/")[1] for s in ("Bike lock", "Opens with 4821.")), True)
    sql("UPDATE notes SET title = d.title, body = d.body FROM notes d WHERE d.user_id = (SELECT id FROM users WHERE username = 'dora')"
        " AND notes.user_id = (SELECT id FROM users WHERE username = 'eva')")
    page = req(ceva, "/")[1]
    check("  note of dora in the row of eva: unreadable", (page.count("(unreadable)"), "4821" in page), (2, False))
    sql("UPDATE notes SET title = body, body = title WHERE user_id = (SELECT id FROM users WHERE username = 'dora')")
    check("  title and body swapped: unreadable", req(cdora, "/")[1].count("(unreadable)"), 2)
