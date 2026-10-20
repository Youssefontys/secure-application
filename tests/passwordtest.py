"""The password: the strength rule, re-authentication when changing and deleting, forgot password, and old sessions
that expire (MIT-09, MIT-13, MIT-14, MIT-16). Runs through securitytest.py."""
from securitytest import *

M = "Username, recovery code or code is incorrect."


def forgot(c, user, rcode, code, pw=PW2, repeat=None):
    """The forgot password form (MIT-14), with both new passwords equal unless repeat says otherwise."""
    return req(c, "/login/forgot", {"username": user, "recovery_code": rcode, "code": code, "password": pw,
                                    "password_repeat": pw if repeat is None else repeat})


def answer(r):
    return r[0], msg(r[1])


def run():
    print("== strength rule (MIT-13)")
    a, sec, _ = account("testacc3")
    for n, want in ((11, 400), (12, 302), (64, 302), (65, 400)):
        check(f"register with {n} characters", req(client(), "/register", {"username": f"length{n}", "password": "w" * n})[0], want)
    check("  message", msg(req(client(), "/register", {"username": "short", "password": "a"})[1]), "Choose a password of 12 to 64 characters.")
    for n in (11, 65):
        check(f"change to {n} characters", req(a, "/account/password", {"password": "w" * n, "password_repeat": "w" * n})[0], 400)
    check("change, two different ones", req(a, "/account/password", {"password": PW2, "password_repeat": PW})[0], 400)
    check("logging in without the rule (old password keeps working)", loc(req(client(), "/login", {"username": "testacc3", "password": PW})), "302 /login/2fa")

    print("== sessions")
    a2 = login("testacc3", sec)
    change = {"password": PW2, "password_repeat": PW2}
    check("re-authentication (MIT-16): change without the current password", req(a, "/account/password", change)[0], 400)
    check("  with a wrong current password", msg(req(a, "/account/password", {**change, "current_password": "wrong-password"})[1]),
          "Your current password is incorrect.")
    check("  the right password without a code (MIT-16)", req(a, "/account/password", {**change, "current_password": PW})[0], 400)
    check("  the right password with a wrong code", msg(req(a, "/account/password", {**change, "current_password": PW, "code": "000000"})[1]),
          "Incorrect or already used code.")
    check("  the password is still the old one", loc(req(client(), "/login", {"username": "testacc3", "password": PW})), "302 /login/2fa")
    check("change the password, with password and code", loc(req(a, "/account/password", {**change, "current_password": PW, "code": fresh(sec, "testacc3")})),
          "302 /account")
    check("  own session stays", req(a, "/")[0], 200)
    check("  other session expires", loc(req(a2, "/")), "302 /login")
    check("logout", loc(req(a, "/logout", {})), "302 /login")
    check("  old session after logout", loc(req(a, "/")), "302 /login")

    print("== forgot password (MIT-14)")
    unlock()
    cc, secc, rcc = account("testacc4")
    check("link on the login page", 'href="/login/forgot"' in req(client(), "/login")[1], True)
    check("form", req(client(), "/login/forgot")[0], 200)
    check("new password too short", answer(forgot(client(), "testacc4", rcc, "000000", "short")), (400, "Choose a password of 12 to 64 characters."))
    check("two different ones", answer(forgot(client(), "testacc4", rcc, "000000", PW2, PW)), (400, "The two passwords do not match."))
    check("wrong recovery code", answer(forgot(client(), "testacc4", "0" * 32, "000000")), (400, M))
    check("unknown name: same answer", answer(forgot(client(), "nobody", "0" * 32, "000000")), (400, M))
    check("right recovery code, wrong code", answer(forgot(client(), "testacc4", rcc, "000000")), (400, M))
    r = forgot(client(), "testacc4", " " + rcc.upper() + " ", fresh(secc, "testacc4"))
    rc2 = recovery(r[1])
    check("right: new recovery code", (r[0], len(rc2), r[2].get("Cache-Control"), 'href="/login"' in r[1]), (200, 39, "no-store", True))
    check("  other session expires", loc(req(cc, "/")), "302 /login")
    check("  new recovery code is in the same UPDATE", sql("SELECT recovery_hash IS NOT NULL FROM users WHERE username = 'testacc4'"), "t")
    check("  old password", req(client(), "/login", {"username": "testacc4", "password": PW})[0], 400)
    check("  new password", loc(req(client(), "/login", {"username": "testacc4", "password": PW2})), "302 /login/2fa")
    check("  old recovery code again", answer(forgot(client(), "testacc4", rcc, "000000")), (400, M))
    same = fresh(secc, "testacc4")
    res = together([lambda x=x: forgot(x, "testacc4", rc2, same, PW) for x in (client(), client())])
    check("two at the same time with the same codes", sorted(x[0] for x in res), [200, 400])
    rc3 = next((recovery(x[1]) for x in res if x[0] == 200), "")
    check("  then log in with the winning password", loc(req(client(), "/login", {"username": "testacc4", "password": PW})), "302 /login/2fa")
    unlock()
    check("5 wrong recovery codes, the 6th attempt refused (per name per address)", tries([forgot(client(), "testacc4", "0" * 32, "000000") for _ in range(6)]), LOCKED)
    check("  unknown name: exactly the same", tries([forgot(client(), "nobody", "0" * 32, "000000") for _ in range(6)]), LOCKED)
    unlock()
    check("right recovery code, 5 wrong codes, the 6th refused", tries([forgot(client(), "testacc4", rc3, f"{i:06d}") for i in range(6)]), LOCKED)
    check("  the code step at login is locked too (MIT-06)", req(password_step("testacc4"), "/login/2fa", {"code": fresh(secc, "testacc4")})[0], 429)

    print("== delete the account")
    unlock()
    _, secb, _ = account("testacc5")
    cb, cb2 = login("testacc5", secb), login("testacc5", secb)
    req(cb, "/", {"title": "Gone", "body": "x"})
    check("delete without the password", req(cb, "/account/delete", {})[0], 400)
    unlock()
    check("  5 wrong passwords, the 6th attempt refused", tries([req(cb, "/account/delete", {"current_password": f"wrong{i}"}) for i in range(6)]), LOCKED)
    check("  the account still exists", sql("SELECT count(*) FROM users WHERE username = 'testacc5'"), "1")
    check("  also the right password during the lockout", req(cb, "/account/delete", {"current_password": PW})[0], 429)
    unlock()
    check("  the right password without a code (MIT-16)", (req(cb, "/account/delete", {"current_password": PW})[0],
          sql("SELECT count(*) FROM users WHERE username = 'testacc5'")), (400, "1"))
    check("delete the account, with password and code", loc(req(cb, "/account/delete", {"current_password": PW, "code": fresh(secb, "testacc5")})), "302 /login")
    check("  other session", loc(req(cb2, "/")), "302 /login")
    check("  login afterwards", req(client(), "/login", {"username": "testacc5", "password": PW})[0], 400)
    check("  notes without an owner", sql("SELECT count(*) FROM notes WHERE user_id NOT IN (SELECT id FROM users)"), "0")
