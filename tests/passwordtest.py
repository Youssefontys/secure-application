"""Het wachtwoord: de sterkte-eis, herauthenticatie bij wijzigen en verwijderen, wachtwoord vergeten, en oude sessies
die vervallen (MIT-09, MIT-13, MIT-14, MIT-16). Draait via securitytest.py."""
from securitytest import *

M = "Username, recovery code or code is incorrect."


def forgot(c, user, rcode, code, pw=PW2, repeat=None):
    """Het formulier wachtwoord vergeten (MIT-14), met beide nieuwe wachtwoorden gelijk tenzij repeat iets anders zegt."""
    return req(c, "/login/forgot", {"username": user, "recovery_code": rcode, "code": code, "password": pw,
                                    "password_repeat": pw if repeat is None else repeat})


def answer(r):
    return r[0], msg(r[1])


def run():
    print("== sterkte-eis (MIT-13)")
    a, sec, _ = account("wim")
    for n, want in ((11, 400), (12, 302), (64, 302), (65, 400)):
        check(f"registreren met {n} tekens", req(client(), "/register", {"username": f"lengte{n}", "password": "w" * n})[0], want)
    check("  melding", msg(req(client(), "/register", {"username": "kort", "password": "a"})[1]), "Choose a password of 12 to 64 characters.")
    for n in (11, 65):
        check(f"wijzigen naar {n} tekens", req(a, "/account/password", {"password": "w" * n, "password_repeat": "w" * n})[0], 400)
    check("wijzigen, twee verschillende", req(a, "/account/password", {"password": PW2, "password_repeat": PW})[0], 400)
    check("inloggen zonder eis (oud wachtwoord blijft werken)", loc(req(client(), "/login", {"username": "wim", "password": PW})), "302 /login/2fa")

    print("== sessies")
    a2 = login("wim", sec)
    change = {"password": PW2, "password_repeat": PW2}
    check("herauthenticatie (MIT-16): wijzigen zonder huidig wachtwoord", req(a, "/account/password", change)[0], 400)
    check("  met een fout huidig wachtwoord", msg(req(a, "/account/password", {**change, "current_password": "fout-wachtwoord"})[1]),
          "Your current password is incorrect.")
    check("  het juiste wachtwoord zonder code (MIT-16)", req(a, "/account/password", {**change, "current_password": PW})[0], 400)
    check("  het juiste wachtwoord met een foute code", msg(req(a, "/account/password", {**change, "current_password": PW, "code": "000000"})[1]),
          "Incorrect or already used code.")
    check("  het wachtwoord is nog het oude", loc(req(client(), "/login", {"username": "wim", "password": PW})), "302 /login/2fa")
    check("wachtwoord wijzigen, met wachtwoord en code", loc(req(a, "/account/password", {**change, "current_password": PW, "code": fresh(sec, "wim")})),
          "302 /account")
    check("  eigen sessie blijft", req(a, "/")[0], 200)
    check("  andere sessie vervalt", loc(req(a2, "/")), "302 /login")
    check("logout", loc(req(a, "/logout", {})), "302 /login")
    check("  oude sessie na logout", loc(req(a, "/")), "302 /login")

    print("== wachtwoord vergeten (MIT-14)")
    unlock()
    cc, secc, rcc = account("carla")
    check("link op de inlogpagina", 'href="/login/forgot"' in req(client(), "/login")[1], True)
    check("formulier", req(client(), "/login/forgot")[0], 200)
    check("te kort nieuw wachtwoord", answer(forgot(client(), "carla", rcc, "000000", "kort")), (400, "Choose a password of 12 to 64 characters."))
    check("twee verschillende", answer(forgot(client(), "carla", rcc, "000000", PW2, PW)), (400, "The two passwords do not match."))
    check("foute herstelcode", answer(forgot(client(), "carla", "0" * 32, "000000")), (400, M))
    check("onbekende naam: zelfde antwoord", answer(forgot(client(), "niemand", "0" * 32, "000000")), (400, M))
    check("juiste herstelcode, foute code", answer(forgot(client(), "carla", rcc, "000000")), (400, M))
    r = forgot(client(), "carla", " " + rcc.upper() + " ", fresh(secc, "carla"))
    rc2 = recovery(r[1])
    check("juist: nieuwe herstelcode", (r[0], len(rc2), r[2].get("Cache-Control"), 'href="/login"' in r[1]), (200, 39, "no-store", True))
    check("  andere sessie vervalt", loc(req(cc, "/")), "302 /login")
    check("  nieuwe herstelcode staat in dezelfde UPDATE", sql("SELECT recovery_hash IS NOT NULL FROM users WHERE username = 'carla'"), "t")
    check("  oud wachtwoord", req(client(), "/login", {"username": "carla", "password": PW})[0], 400)
    check("  nieuw wachtwoord", loc(req(client(), "/login", {"username": "carla", "password": PW2})), "302 /login/2fa")
    check("  oude herstelcode opnieuw", answer(forgot(client(), "carla", rcc, "000000")), (400, M))
    same = fresh(secc, "carla")
    res = together([lambda x=x: forgot(x, "carla", rc2, same, PW) for x in (client(), client())])
    check("twee gelijktijdig met dezelfde codes", sorted(x[0] for x in res), [200, 400])
    rc3 = next((recovery(x[1]) for x in res if x[0] == 200), "")
    check("  daarna inloggen met het winnende wachtwoord", loc(req(client(), "/login", {"username": "carla", "password": PW})), "302 /login/2fa")
    unlock()
    check("5 foute herstelcodes, de 6e poging geweigerd (per naam per adres)", tries([forgot(client(), "carla", "0" * 32, "000000") for _ in range(6)]), LOCKED)
    check("  onbekende naam: precies hetzelfde", tries([forgot(client(), "niemand", "0" * 32, "000000") for _ in range(6)]), LOCKED)
    unlock()
    check("juiste herstelcode, 5 foute codes, de 6e geweigerd", tries([forgot(client(), "carla", rc3, f"{i:06d}") for i in range(6)]), LOCKED)
    check("  ook de codestap bij inloggen op slot (MIT-06)", req(password_step("carla"), "/login/2fa", {"code": fresh(secc, "carla")})[0], 429)

    print("== account verwijderen")
    unlock()
    _, secb, _ = account("bas")
    cb, cb2 = login("bas", secb), login("bas", secb)
    req(cb, "/", {"title": "Weg", "body": "x"})
    check("verwijderen zonder wachtwoord", req(cb, "/account/delete", {})[0], 400)
    unlock()
    check("  5 foute wachtwoorden, de 6e poging geweigerd", tries([req(cb, "/account/delete", {"current_password": f"fout{i}"}) for i in range(6)]), LOCKED)
    check("  het account bestaat nog", sql("SELECT count(*) FROM users WHERE username = 'bas'"), "1")
    check("  ook het juiste wachtwoord tijdens de blokkade", req(cb, "/account/delete", {"current_password": PW})[0], 429)
    unlock()
    check("  het juiste wachtwoord zonder code (MIT-16)", (req(cb, "/account/delete", {"current_password": PW})[0],
          sql("SELECT count(*) FROM users WHERE username = 'bas'")), (400, "1"))
    check("account verwijderen, met wachtwoord en code", loc(req(cb, "/account/delete", {"current_password": PW, "code": fresh(secb, "bas")})), "302 /login")
    check("  andere sessie", loc(req(cb2, "/")), "302 /login")
    check("  login daarna", req(client(), "/login", {"username": "bas", "password": PW})[0], 400)
    check("  notities zonder eigenaar", sql("SELECT count(*) FROM notes WHERE user_id NOT IN (SELECT id FROM users)"), "0")
