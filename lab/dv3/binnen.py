"""Draait in de container van de app (deelvraag 3): wat er echt in de image zit en wat de app laadt, als JSON.
Alleen de standaardbibliotheek; leest, verandert niets. Gebruik: python -I /lab/binnen.py"""
import glob
import importlib.metadata
import json
import os
import re
import subprocess
import sys

SITE = f"/usr/local/lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages"
# Versieteksten in binaire bestanden: zo is te zien welke bibliotheek er echt in zit, ook zonder pakketbeheer.
PATTERNS = {
    "openssl": rb"OpenSSL \d+\.\d+\.\d+[a-z]?(?:-[\w.]+)? +\d+ \w+ \d{4}",
    "pcre": rb"\b8\.\d\d \d{4}-\d\d-\d\d",
}


def dpkg():
    out = subprocess.run(["dpkg-query", "-W", "-f", "${Package}\t${Version}\t${source:Package}\n"],
                         capture_output=True, text=True, check=True).stdout
    return [line.split("\t") for line in out.splitlines() if line]


def owner_deb(path):
    p = subprocess.run(["dpkg-query", "-S", path], capture_output=True, text=True)
    if p.returncode != 0 and path.startswith("/usr/lib/"):
        p = subprocess.run(["dpkg-query", "-S", path.removeprefix("/usr")], capture_output=True, text=True)
    return p.stdout.split(":")[0] if p.returncode == 0 else None


def dists():
    out, files = [], {}
    for d in importlib.metadata.distributions():
        name = d.metadata["Name"]
        out.append([name, d.version])
        for f in d.files or []:
            files[os.path.normpath(os.path.join(SITE, str(f)))] = name
    return sorted(out), files


def loaded():
    paths = set()
    for maps in glob.glob("/proc/[0-9]*/maps"):
        try:
            text = open(maps, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        cmd = open(os.path.join(os.path.dirname(maps), "cmdline"), "rb").read()
        if b"gunicorn" not in cmd:
            continue
        paths |= {line.split()[5] for line in text.splitlines() if len(line.split()) >= 6 and line.split()[5].startswith("/")}
    return sorted(paths)


def versions(path):
    try:
        data = open(path, "rb").read()
    except OSError:
        return {}
    return {k: sorted({m.decode(errors="replace") for m in re.findall(p, data)}) for k, p in PATTERNS.items()
            if re.search(p, data)}


def main():
    import ssl
    names, files = dists()
    result = {"python": sys.version.split()[0], "ssl_van_python": ssl.OPENSSL_VERSION, "dpkg": dpkg(), "dists": names}
    try:
        from cryptography.hazmat.backends.openssl.backend import backend
        result["openssl_in_cryptography"] = backend.openssl_version_text()
    except Exception as e:  # noqa: BLE001
        result["openssl_in_cryptography"] = f"fout: {e}"
    try:
        import psycopg
        result["libpq_in_psycopg"] = psycopg.pq.version()
    except Exception as e:  # noqa: BLE001
        result["libpq_in_psycopg"] = f"fout: {e}"
    # De SBoM's die wheels zelf meenemen (.dist-info/sboms/).
    result["wheel_sboms"] = {}
    for f in sorted(glob.glob(f"{SITE}/*.dist-info/sboms/*.json")):
        doc = json.load(open(f, encoding="utf-8"))

        def walk(cs):
            for c in cs or []:
                yield c
                yield from walk(c.get("components"))
        result["wheel_sboms"][f.removeprefix(SITE + "/")] = sorted(
            {f"{c.get('name')}@{c.get('version')} {(c.get('purl') or '').split('?')[0]}" for c in walk(doc.get("components"))})
    # Wat de processen van Gunicorn laden, met per bestand wie het meebracht.
    result["geladen"] = []
    for path in loaded():
        real = os.path.realpath(path)
        if real in files or path in files:
            owner = "pypi:" + files.get(real, files.get(path))
        elif path.startswith("/usr/local/"):
            owner = "cpython"
        else:
            deb = owner_deb(path) or owner_deb(real)
            owner = f"deb:{deb}" if deb else "onbekend"
        result["geladen"].append({"bestand": path, "van": owner, "versies": versions(real)})
    print(json.dumps(result, indent=1))


main()
