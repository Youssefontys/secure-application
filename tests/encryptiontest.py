"""Encryption: the TOTP secret and the notes encrypted and bound to their place, the passwords with Argon2id
(MIT-17 to MIT-19), and the rotation of the data key. Runs through securitytest.py."""
from securitytest import *


def took(name):
    """How long a failed login for this name takes, in seconds."""
    s = time.perf_counter()
    req(client(), "/login", {"username": name, "password": "wrong-password-123"})
    return time.perf_counter() - s


def run():
    print("== encryption (MIT-17)")
    unlock()
    c9, secd, _ = account("testacc9")
    c10 = account("testacc10")[0]
    raw = sql("SELECT totp_secret FROM users WHERE username = 'testacc9'")
    check("TOTP secret stored encrypted", (raw.startswith("v1:"), secd in raw, len(raw) > len(secd)), (True, False, True))
    check("  two accounts, two different values", raw != sql("SELECT totp_secret FROM users WHERE username = 'testacc10'"), True)
    sql(f"UPDATE users SET totp_secret = '{raw}' WHERE username = 'testacc10'")
    check("encrypted secret of testacc9 in the row of testacc10: refused", req(password_step("testacc10"), "/login/2fa", {"code": fresh(secd, "testacc9")})[0], 400)
    check("  testacc9 logs in as usual", loc(req(client(), "/login", {"username": "testacc9", "password": PW})), "302 /login/2fa")
    req(client(), "/register", {"username": "testacc11", "password": PW})
    f = password_step("testacc11")
    req(f, "/account/2fa")
    sql("UPDATE users SET totp_secret = 'v1:AAAA' WHERE username = 'testacc11'")
    check("half set up secret that does not decrypt: start again", loc(req(f, "/account/2fa")), "302 /account/2fa")
    r = req(f, "/account/2fa")
    check("  new secret, and the setup works", (r[0], req(f, "/account/2fa", {"code": fresh(secret(r[1]), "testacc11")})[0]), (200, 200))

    print("== passwords hashed (MIT-19)")
    hd, he = sql("SELECT password_hash FROM users WHERE username = 'testacc9'"), sql("SELECT password_hash FROM users WHERE username = 'testacc10'")
    check("Argon2id with the OWASP setting, without the password", (hd.startswith("$argon2id$v=19$m=19456,t=2,p=1$"), PW in hd), (True, False))
    check("  same password, different hash (own salt)", hd != he, True)
    old = in_app("import os; from cryptography.hazmat.primitives.kdf.argon2 import Argon2id; print(Argon2id(salt=os.urandom(16),"
                 f" length=32, iterations=5, memory_cost=7168, lanes=1).derive_phc_encoded({PW!r}.encode()))").stdout.strip()
    sql(f"UPDATE users SET password_hash = '{old}' WHERE username = 'testacc9'")
    check("  hash with an old setting: logging in works", loc(req(client(), "/login", {"username": "testacc9", "password": PW})), "302 /login/2fa")
    check("  and after that there is a new hash", sql("SELECT password_hash FROM users WHERE username = 'testacc9'").startswith("$argon2id$v=19$m=19456,t=2,p=1$"),
          True)
    unlock()
    known, unknown = sorted(took("testacc9") for _ in range(4)), sorted(took(f"nosuchuser{i}") for i in range(4))
    check("  unknown name calculates too: same order of response time", 0.5 < unknown[1] / known[1] < 2, True)
    print(f"      (median known {known[1]*1000:.0f} ms, unknown {unknown[1]*1000:.0f} ms)")
    unlock()

    print("== notes encrypted (MIT-18)")
    req(c9, "/", {"title": "Bike lock", "body": "Opens with 4821."})
    req(c10, "/", {"title": "From testacc10", "body": "Own text."})
    row = sql("SELECT title || ' ' || body FROM notes WHERE user_id = (SELECT id FROM users WHERE username = 'testacc9')")
    check("title and body stored encrypted", (row.count("v1:"), "Bike lock" in row, "4821" in row), (2, False, False))
    check("  the owner reads them as usual", all(s in req(c9, "/")[1] for s in ("Bike lock", "Opens with 4821.")), True)
    sql("UPDATE notes SET title = d.title, body = d.body FROM notes d WHERE d.user_id = (SELECT id FROM users WHERE username = 'testacc9')"
        " AND notes.user_id = (SELECT id FROM users WHERE username = 'testacc10')")
    page = req(c10, "/")[1]
    check("  note of testacc9 in the row of testacc10: unreadable", (page.count("(unreadable)"), "4821" in page), (2, False))
    sql("UPDATE notes SET title = body, body = title WHERE user_id = (SELECT id FROM users WHERE username = 'testacc9')")
    check("  title and body swapped: unreadable", req(c9, "/")[1].count("(unreadable)"), 2)

    print("== key rotation (MIT-17, MIT-18)")
    cr, _, _ = account("testrot1")
    req(cr, "/", {"title": "Rotate me", "body": "Same text after."})
    old_key = in_app("import os; print(os.environ['DATA_ENCRYPTION_KEY'])").stdout.strip()
    new_key = in_app("import secrets; print(secrets.token_hex(32))").stdout.strip()
    uid = sql("SELECT id FROM users WHERE username = 'testrot1'")
    forward = (f"DATA_ENCRYPTION_KEY={new_key}", "DATA_ENCRYPTION_KEY_VERSION=v2", f"DATA_ENCRYPTION_KEY_PREVIOUS={old_key}")
    # Only the values of this account count: rows that earlier tests broke on purpose stay unreadable, in both directions.
    other = lambda like: sql(f"SELECT count(*) FROM (SELECT totp_secret AS v FROM users WHERE id = {uid} UNION ALL SELECT title FROM notes WHERE user_id = {uid}"
                             f" UNION ALL SELECT body FROM notes WHERE user_id = {uid}) x WHERE v IS NOT NULL AND v NOT LIKE '{like}'")
    out = in_app("rotate_key.py", *forward, run=("python",))
    check("rotation to v2 ran, and prints only numbers", ("rotated to v2" in out.stdout, new_key in out.stdout + out.stderr, old_key in out.stdout + out.stderr), (True, False, False))
    check("  every encrypted value of the test account is v2 now", other("v2:%"), "0")
    title = sql(f"SELECT title FROM notes WHERE user_id = {uid}")
    read = lambda *env: in_app(f"import encryption; print(encryption.decrypt({title!r}, 'note_title', {uid}))", *env).stdout.strip()
    check("  with the new key the note still reads as before", read(*forward), "Rotate me")
    check("  the old key alone cannot read it", read(), "None")
    again = in_app("rotate_key.py", *forward, run=("python",)).stdout
    check("  a second run changes nothing", "rotated to v2: 0" in again, True)
    back = (f"DATA_ENCRYPTION_KEY={old_key}", f"DATA_ENCRYPTION_KEY_PREVIOUS={new_key}", "DATA_ENCRYPTION_KEY_PREVIOUS_VERSION=v2")
    in_app("rotate_key.py", *back, run=("python",))
    check("  and back to v1, so the rest of the tests read as before", other("v1:%"), "0")
    check("  the app reads the note again", "Rotate me" in req(cr, "/")[1], True)
