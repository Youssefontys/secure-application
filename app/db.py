"""De databaseverbinding: één helper voor alle SQL."""

import os

import psycopg
from psycopg.rows import namedtuple_row

DATABASE_URL = os.environ["DATABASE_URL"]
# De app is Nederlandstalig; tijden worden in Nederlandse tijd getoond.
TIMEZONE = "Europe/Amsterdam"


def query(sql, params=(), one=False):
    """Voert één SQL-opdracht uit in een eigen verbinding, commit, en geeft de rijen terug.

    De waarden in params gaan los van de SQL-tekst naar de database, dus invoer
    wordt nooit als SQL uitgevoerd (MIT-02). Rijen zijn namedtuples, zodat code en
    templates `note.title` schrijven in plaats van `note[1]`. Tijden komen terug in
    TIMEZONE; de database zelf staat op UTC. Met one=True: de eerste rij of None.
    """
    with psycopg.connect(DATABASE_URL, row_factory=namedtuple_row, options=f"-c TimeZone={TIMEZONE}") as conn:
        cur = conn.execute(sql, params)
        rows = cur.fetchall() if cur.description else []
    return (rows[0] if rows else None) if one else rows
