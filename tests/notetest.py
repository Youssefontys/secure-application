"""Notes: lengths, creating, editing and deleting, only on your own notes, and at most 25 per account
(MIT-04, MIT-15, MIT-30). Runs through securitytest.py."""
from securitytest import *


def run():
    print("== notes")
    a = account("testacc7")[0]
    check("note empty", req(a, "/", {"title": "", "body": ""})[0], 400)
    check("title 16", req(a, "/", {"title": "x" * 16, "body": "y"})[0], 400)
    check("note 251", req(a, "/", {"title": "x", "body": "y" * 251})[0], 400)
    check("create (15/250)", loc(req(a, "/", {"title": "x" * 15, "body": "y" * 250})), "302 /")
    nid = re.search(r"notes/(\d+)/edit", req(a, "/")[1]).group(1)
    check("edit GET", req(a, f"/notes/{nid}/edit")[0], 200)
    check("edit empty", req(a, f"/notes/{nid}/edit", {"title": "", "body": ""})[0], 400)
    check("edit", loc(req(a, f"/notes/{nid}/edit", {"title": "T2", "body": "Changed"})), "302 /")
    check("edited visible", "edited" in req(a, "/")[1], True)
    cb = account("testacc8")[0]
    check("owner (MIT-15): testacc8 opens the note of testacc7", req(cb, f"/notes/{nid}/edit")[0], 404)
    check("  testacc8 edits the note of testacc7", req(cb, f"/notes/{nid}/edit", {"title": "x", "body": "y"})[0], 404)
    check("  testacc8 deletes the note of testacc7", req(cb, f"/notes/{nid}/delete", {})[0], 404)
    check("  the note of testacc7 unchanged", all(s in req(a, f"/notes/{nid}/edit")[1] for s in ("T2", "Changed")), True)
    check("  unknown id", req(a, "/notes/999999/edit")[0], 404)
    check("delete", loc(req(a, f"/notes/{nid}/delete", {})), "302 /")
    check("profile", req(a, "/account")[0], 200)

    print("== limit on notes (MIT-30)")
    made = [req(a, "/", {"title": f"n{i}", "body": "x"})[0] for i in range(26)]
    check("notes: 25 per account, the 26th refused", (made.count(302), made[-1]), (25, 400))
    check("  with a message, and the counter on the page", (msg(req(a, "/", {"title": "x", "body": "y"})[1]), "25 of 25 notes" in req(a, "/")[1]),
          ("You have reached the maximum of 25 notes. Delete one first.", True))
