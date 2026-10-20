# The database connection: one helper for all SQL.

import os

import psycopg
from flask import g
from psycopg.rows import namedtuple_row

DATABASE_URL = os.environ["DATABASE_URL"]
# Times are shown in Dutch time, also now that the interface is English.
TIMEZONE = "Europe/Amsterdam"


# One connection per request: a new one costs about 100 ms here, an open connection a few ms.
def connection():
    if "db" not in g:
        # autocommit: every statement is final at once, as before with a connection per query.
        # Times in TIMEZONE (the database runs on UTC); rows as namedtuple, so note.title.
        g.db = psycopg.connect(DATABASE_URL, autocommit=True, row_factory=namedtuple_row, options=f"-c TimeZone={TIMEZONE}")
    return g.db


# At the end of every request (see app.py): close the connection of this request.
def close_connection(error=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


# One SQL statement; with one=True the first row, or None.
def query(sql, params=(), one=False):
    # SQL and values go to the database separately, so input never becomes SQL (MIT-02).
    cur = connection().execute(sql, params)
    rows = cur.fetchall() if cur.description else []
    return (rows[0] if rows else None) if one else rows
