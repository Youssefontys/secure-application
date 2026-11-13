# Key rotation (MIT-17, MIT-18): makes every encrypted value again with the current key, so the previous key can go away.
#
# A new key goes next to the old one: DATA_ENCRYPTION_KEY is the new key with its version (DATA_ENCRYPTION_KEY_VERSION, for example v2),
# DATA_ENCRYPTION_KEY_PREVIOUS the old key with its version (DATA_ENCRYPTION_KEY_PREVIOUS_VERSION, default v1). Then, in the container of the app:
#   python rotate_key.py
# Safe to run twice, and while the app runs: every value changes in one statement that only works if the value is still the one that was read.
# It prints only numbers, never a value. Exit code 1 if a value could not be read: then the old key must stay.

import os
import sys

import psycopg

import encryption

# What is encrypted: table, column and the context the app uses where it writes it.
COLUMNS = (("users", "totp_secret", "totp_secret"), ("notes", "title", "note_title"), ("notes", "body", "note_body"))


def main():
    done = current = unreadable = lost_race = 0
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as conn:
        for table, column, kind in COLUMNS:
            owner = "id" if table == "users" else "user_id"
            rows = conn.execute(f"SELECT id, {owner}, {column} FROM {table} WHERE {column} IS NOT NULL").fetchall()
            for row_id, user_id, stored in rows:
                if encryption.is_current(stored):
                    current += 1
                    continue
                fresh = encryption.reencrypt(stored, kind, user_id)
                if fresh is None:
                    unreadable += 1
                    continue
                # Only if the value is still the one we read: a note that changed in the meantime is already current.
                changed = conn.execute(f"UPDATE {table} SET {column} = %s WHERE id = %s AND {column} = %s", (fresh, row_id, stored)).rowcount
                done, lost_race = done + changed, lost_race + (1 - changed)
    print(f"rotated to {encryption.KEY_VERSION}: {done}; already current: {current}; changed in the meantime: {lost_race}; not readable: {unreadable}")
    return 1 if unreadable else 0


if __name__ == "__main__":
    sys.exit(main())
