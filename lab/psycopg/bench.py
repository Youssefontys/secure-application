"""Draait in de container van de app: hoe snel praat psycopg met de database? Alleen lezen, geen tabellen.
Per meting vijf herhalingen, in milliseconden. Gebruik: python -I /tmp/bench.py"""
import json
import os
import time

import psycopg

URL = os.environ["DATABASE_URL"]


def connect(n):
    for _ in range(n):
        with psycopg.connect(URL):
            pass


def select1(n):
    with psycopg.connect(URL, autocommit=True) as c:
        for _ in range(n):
            c.execute("select 1").fetchone()


def rows(n):
    with psycopg.connect(URL, autocommit=True) as c:
        for _ in range(n):
            c.execute("select g, md5(g::text) from generate_series(1, 1000) g").fetchall()


result = {"implementatie": psycopg.pq.__impl__, "libpq": psycopg.pq.version()}
for name, fn, n in (("verbinden_50", connect, 50), ("select_1_5000", select1, 5000), ("1000_rijen_200", rows, 200)):
    fn(5)
    times = []
    for _ in range(5):
        start = time.perf_counter()
        fn(n)
        times.append(round((time.perf_counter() - start) * 1000, 1))
    result[name] = {"ms": times, "mediaan": sorted(times)[2]}
print(json.dumps(result))
