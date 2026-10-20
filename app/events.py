# Security events (MIT-31): one JSON line per event to stderr, so locally in docker compose logs and on
# Azure in the log of Container Apps. JSON escapes line breaks and other control characters: input makes no false line.
# Never a password, code or secret. The IP address and username are personal data (A-11).

import json
import logging
import sys
from datetime import UTC, datetime

from flask import g, has_request_context, request

_log = logging.getLogger("security")
_log.addHandler(logging.StreamHandler(sys.stderr))
_log.setLevel(logging.INFO)
_log.propagate = False


# What happened, when, from which address and by which account; fields without a value are left out.
# Outside a request (a script or job) without address and account: logging must never break the action itself.
def event(name, **fields):
    in_request = has_request_context()
    user = getattr(g, "user", None) if in_request else None
    record = {"time": datetime.now(UTC).isoformat(timespec="seconds"), "event": name,
              "ip": request.remote_addr if in_request else None, "user_id": user.id if user else None, **fields}
    _log.info(json.dumps({key: value for key, value in record.items() if value is not None}))
