# De databaseverbinding: één helper voor alle SQL.

import os

import psycopg
from flask import g
from psycopg.rows import namedtuple_row

DATABASE_URL = os.environ["DATABASE_URL"]
# De app is Nederlandstalig; tijden worden in Nederlandse tijd getoond.
TIMEZONE = "Europe/Amsterdam"


# Eén verbinding per verzoek: een nieuwe kost hier zo'n 100 ms, een open verbinding een paar ms.
def connection():
    if "db" not in g:
        # autocommit: elke opdracht staat meteen vast, net als eerst met een verbinding per query.
        # Tijden in TIMEZONE (de database staat op UTC); rijen als namedtuple, dus note.title.
        g.db = psycopg.connect(DATABASE_URL, autocommit=True, row_factory=namedtuple_row, options=f"-c TimeZone={TIMEZONE}")
    return g.db


# Aan het eind van elk verzoek (zie app.py): de verbinding van dit verzoek dicht.
def close_connection(error=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


# Eén SQL-opdracht; met one=True de eerste rij of None.
def query(sql, params=(), one=False):
    # SQL en waarden gaan los naar de database, dus invoer wordt nooit SQL (MIT-02).
    cur = connection().execute(sql, params)
    rows = cur.fetchall() if cur.description else []
    return (rows[0] if rows else None) if one else rows
