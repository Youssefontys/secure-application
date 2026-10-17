# Security-events (MIT-31): één JSON-regel per gebeurtenis naar stderr, dus lokaal in docker compose logs en op
# Azure in de log van Container Apps. JSON escapet regeleindes en andere stuurtekens: invoer maakt geen valse regel.
# Nooit een wachtwoord, code of geheim. IP-adres en gebruikersnaam zijn wel persoonsgegevens (A-11).

import json
import logging
import sys
from datetime import UTC, datetime

from flask import g, has_request_context, request

_log = logging.getLogger("security")
_log.addHandler(logging.StreamHandler(sys.stderr))
_log.setLevel(logging.INFO)
_log.propagate = False


# Wat er gebeurde, wanneer, vanaf welk adres en van welk account; velden zonder waarde blijven weg.
# Buiten een verzoek (een script of job) zonder adres en account: loggen mag de handeling zelf nooit breken.
def event(name, **fields):
    in_request = has_request_context()
    user = getattr(g, "user", None) if in_request else None
    record = {"time": datetime.now(UTC).isoformat(timespec="seconds"), "event": name,
              "ip": request.remote_addr if in_request else None, "user_id": user.id if user else None, **fields}
    _log.info(json.dumps({key: value for key, value in record.items() if value is not None}))
