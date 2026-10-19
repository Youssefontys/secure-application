"""Proef na deelvraag 3: psycopg zonder binary, met de libpq van Debian. Past app/ aan in de werkmap van de runner, nooit
op main: requirements.txt zonder psycopg-binary, en libpq5 uit Debian in de Dockerfile. Gebruik: python lab/psycopg/variant.py"""
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]


def patch(rel, old, new):
    p = REPO / rel
    s = p.read_text(encoding="utf-8")
    assert s.count(old) == 1, (rel, old, s.count(old))
    p.write_text(s.replace(old, new), encoding="utf-8", newline="\n")


req = (REPO / "app/requirements.txt").read_text(encoding="utf-8").splitlines()
binary = [line for line in req if line.startswith("psycopg-binary==")]
assert len(binary) == 1, binary
(REPO / "app/requirements.txt").write_text("\n".join(line for line in req if line not in binary) + "\n",
                                           encoding="utf-8", newline="\n")
patch("app/requirements.txt", "psycopg[binary]==3.3.6", "psycopg==3.3.6")
# Zonder vaste versie: de proef meet wat Debian nu levert; voor main moet de versie wel vast.
patch("app/Dockerfile", "COPY requirements.txt .\n",
      "RUN apt-get update \\\n && apt-get install --yes --no-install-recommends libpq5 \\\n && rm -rf /var/lib/apt/lists/*\n\n"
      "COPY requirements.txt .\n")
print("app/ aangepast: psycopg zonder binary, libpq5 van Debian")
