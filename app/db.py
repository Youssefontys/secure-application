# De databaseverbinding: één helper voor alle SQL.

import os

import psycopg
from psycopg.rows import namedtuple_row

DATABASE_URL = os.environ["DATABASE_URL"]
# De app is Nederlandstalig; tijden worden in Nederlandse tijd getoond.
TIMEZONE = "Europe/Amsterdam"


# Eén SQL-opdracht in een eigen verbinding die commit; met one=True de eerste rij of None.
def query(sql, params=(), one=False):
    # Tijden in TIMEZONE (de database staat op UTC); rijen als namedtuple, dus note.title.
    with psycopg.connect(DATABASE_URL, row_factory=namedtuple_row, options=f"-c TimeZone={TIMEZONE}") as conn:
        # SQL en waarden gaan los naar de database, dus invoer wordt nooit SQL (MIT-02).
        cur = conn.execute(sql, params)
        rows = cur.fetchall() if cur.description else []
    return (rows[0] if rows else None) if one else rows
