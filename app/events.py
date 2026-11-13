# Security events (MIT-31): one JSON line per event to stderr, so locally in docker compose logs and on
# Azure in the log of Container Apps. JSON escapes line breaks and other control characters: input makes no false line.
# Never a password, code or secret. The IP address and username are personal data (A-11).

import json
import logging
import sys
from datetime import UTC, datetime

from flask import g, has_request_context, request

# Per kind: the level and the category. INFO is what a normal user does, WARNING what is refused or fails (a possible attack),
# ERROR what needs attention at once: a lockout that starts, and a value that does not decrypt (changed, moved or another key).
# Categories: authentication, account, session, request and integrity. A kind that is not here is WARNING and "other"; the test of the log catches that.
KINDS = {
    "login_ok": ("INFO", "authentication"), "login_failed": ("WARNING", "authentication"), "totp_failed": ("WARNING", "authentication"),
    "recovery_used": ("INFO", "authentication"), "recovery_failed": ("WARNING", "authentication"), "forgot_failed": ("WARNING", "authentication"),
    "reauth_failed": ("WARNING", "authentication"), "lockout_started": ("ERROR", "authentication"),
    "account_created": ("INFO", "account"), "register_taken": ("WARNING", "account"), "account_deleted": ("INFO", "account"),
    "password_changed": ("INFO", "account"), "password_reset": ("INFO", "account"), "twofa_enabled": ("INFO", "account"),
    "twofa_reset": ("INFO", "account"), "recovery_code_new": ("INFO", "account"),
    "logout": ("INFO", "session"), "session_rejected": ("WARNING", "session"),
    "csrf_refused": ("WARNING", "request"), "note_limit": ("WARNING", "request"),
    "note_unreadable": ("ERROR", "integrity"),
}

_log = logging.getLogger("security")
_log.addHandler(logging.StreamHandler(sys.stderr))
_log.setLevel(logging.INFO)
_log.propagate = False


# What happened, when, how serious, from which address and by which account; fields without a value are left out.
# Outside a request (a script or job) without address and account: logging must never break the action itself.
def event(name, **fields):
    in_request = has_request_context()
    user = getattr(g, "user", None) if in_request else None
    level, category = KINDS.get(name, ("WARNING", "other"))
    record = {"time": datetime.now(UTC).isoformat(timespec="seconds"), "level": level, "category": category, "event": name,
              "ip": request.remote_addr if in_request else None, "user_id": user.id if user else None, **fields}
    _log.log(getattr(logging, level), json.dumps({key: value for key, value in record.items() if value is not None}))
