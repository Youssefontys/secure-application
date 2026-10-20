"""Notities: lengtes, aanmaken, aanpassen en verwijderen, alleen bij je eigen notities, en hooguit 25 per account
(MIT-04, MIT-15, MIT-30). Draait via securitytest.py."""
from securitytest import *


def run():
    print("== notities")
    a = account("nora")[0]
    check("notitie leeg", req(a, "/", {"title": "", "body": ""})[0], 400)
    check("titel 16", req(a, "/", {"title": "x" * 16, "body": "y"})[0], 400)
    check("notitie 251", req(a, "/", {"title": "x", "body": "y" * 251})[0], 400)
    check("aanmaken (15/250)", loc(req(a, "/", {"title": "x" * 15, "body": "y" * 250})), "302 /")
    nid = re.search(r"notes/(\d+)/edit", req(a, "/")[1]).group(1)
    check("edit GET", req(a, f"/notes/{nid}/edit")[0], 200)
    check("edit leeg", req(a, f"/notes/{nid}/edit", {"title": "", "body": ""})[0], 400)
    check("edit", loc(req(a, f"/notes/{nid}/edit", {"title": "T2", "body": "Aangepast"})), "302 /")
    check("bewerkt zichtbaar", "edited" in req(a, "/")[1], True)
    cb = account("otto")[0]
    check("eigenaar (MIT-15): otto opent notitie van nora", req(cb, f"/notes/{nid}/edit")[0], 404)
    check("  otto past notitie van nora aan", req(cb, f"/notes/{nid}/edit", {"title": "x", "body": "y"})[0], 404)
    check("  otto verwijdert notitie van nora", req(cb, f"/notes/{nid}/delete", {})[0], 404)
    check("  notitie van nora ongewijzigd", all(s in req(a, f"/notes/{nid}/edit")[1] for s in ("T2", "Aangepast")), True)
    check("  onbekend id", req(a, "/notes/999999/edit")[0], 404)
    check("delete", loc(req(a, f"/notes/{nid}/delete", {})), "302 /")
    check("profiel", req(a, "/account")[0], 200)

    print("== limiet op notities (MIT-30)")
    made = [req(a, "/", {"title": f"n{i}", "body": "x"})[0] for i in range(26)]
    check("notities: 25 per account, de 26e geweigerd", (made.count(302), made[-1]), (25, 400))
    check("  met een melding, en de teller op de pagina", (msg(req(a, "/", {"title": "x", "body": "y"})[1]), "25 of 25 notes" in req(a, "/")[1]),
          ("You have reached the maximum of 25 notes. Delete one first.", True))
