"""Proef voor deelvraag 2: welke VEX-statussen, PURL-vormen en ignore-regels laat Trivy een melding wegfilteren bij een
scan van een SBoM? Draait Trivy met dezelfde versie en digest als image.yml, in Docker, op Windows en Linux.
Gebruik: python lab/vex/proef.py <sbom.cdx.json> <lege-map-voor-uitvoer> [vex.json]"""
import datetime
import json
import pathlib
import re
import shutil
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]

# De proefmelding: één rij, perl-base, zonder fix (fix_deferred bij Debian).
CVE = "CVE-2026-9538"
PURL = "pkg:deb/debian/perl-base@5.40.1-6%2Bdeb13u1"
QUALIFIERS = "?arch=amd64&distro=debian-13.7"
# Een tweede melding met een epoch als qualifier, voor de vraag of een PURL zonder qualifiers die ook raakt.
CVE_EPOCH = "CVE-2026-78408"
PURL_EPOCH = "pkg:deb/debian/bsdutils@2.41.5-0%2Bdeb13u1"


def trivy_image():
    # Dezelfde Trivy als de pipeline: de regel TRIVY: uit image.yml, en alleen in de vorm naam:versie@sha256:digest.
    text = (REPO / ".github/workflows/image.yml").read_text(encoding="utf-8")
    m = re.search(r"^\s*TRIVY: (aquasec/trivy:[0-9.]+@sha256:[0-9a-f]{64})$", text, re.M)
    if not m:
        sys.exit("TRIVY niet gevonden in image.yml")
    return m.group(1)


def openvex(statements):
    now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"@context": "https://openvex.dev/ns/v0.2.0", "@id": "https://example.invalid/proef", "author": "proef",
            "timestamp": now, "version": 1, "statements": statements}


def statement(cve, purl, status, **extra):
    return {"vulnerability": {"name": cve}, "products": [{"@id": purl}], "status": status, **extra}


NA = {"justification": "vulnerable_code_not_present"}
CASES = {
    # Statussen, telkens met de PURL zonder qualifiers.
    "status-not_affected": openvex([statement(CVE, PURL, "not_affected", **NA)]),
    "status-fixed": openvex([statement(CVE, PURL, "fixed")]),
    "status-affected": openvex([statement(CVE, PURL, "affected", action_statement="proef")]),
    "status-under_investigation": openvex([statement(CVE, PURL, "under_investigation")]),
    # not_affected zonder justification: de spec vraagt justification of impact_statement.
    "na-alleen-impact": openvex([statement(CVE, PURL, "not_affected", impact_statement="proef")]),
    "na-zonder-reden": openvex([statement(CVE, PURL, "not_affected")]),
    # PURL-vormen.
    "purl-exact": openvex([statement(CVE, PURL + QUALIFIERS, "not_affected", **NA)]),
    "purl-zonder-versie": openvex([statement(CVE, "pkg:deb/debian/perl-base", "not_affected", **NA)]),
    "purl-andere-versie": openvex([statement(CVE, "pkg:deb/debian/perl-base@5.40.1-6%2Bdeb13u0", "not_affected", **NA)]),
    "purl-andere-distro": openvex([statement(CVE, PURL + "?distro=debian-13.6", "not_affected", **NA)]),
    "purl-epoch": openvex([statement(CVE_EPOCH, PURL_EPOCH, "not_affected", **NA)]),
    # Een andere CVE dan de melding: mag niets wegfilteren.
    "andere-cve": openvex([statement("CVE-2026-0000", PURL, "not_affected", **NA)]),
}
# Ignore-regels van Trivy zelf, met en zonder verlopen datum.
IGNORE = {
    "ignore-geldig": f"vulnerabilities:\n  - id: {CVE}\n    purls: [\"pkg:deb/debian/perl-base\"]\n    expired_at: 2099-01-01\n",
    "ignore-verlopen": f"vulnerabilities:\n  - id: {CVE}\n    purls: [\"pkg:deb/debian/perl-base\"]\n    expired_at: 2020-01-01\n",
}


def scan(image, out, name, extra):
    report = f"{name}.trivy.json"
    cmd = ["docker", "run", "--rm", "--mount", f"type=bind,source={out},target=/scan",
           "--mount", "type=volume,source=trivycache,target=/root/.cache", image,
           "sbom", "/scan/sbom.cdx.json", "--severity", "HIGH,CRITICAL", "--format", "json",
           "--output", f"/scan/{report}", "--quiet", "--exit-code", "1", *extra]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode not in (0, 1):
        return p.returncode, None, p.stderr.strip().splitlines()[-1:]
    data = json.loads((out / report).read_text(encoding="utf-8"))
    rows = [(v["VulnerabilityID"], v["PkgName"]) for r in data.get("Results", []) for v in r.get("Vulnerabilities") or []]
    return p.returncode, rows, p.stderr.strip().splitlines()[-1:]


def main():
    if len(sys.argv) not in (3, 4):
        sys.exit(__doc__)
    sbom, out = pathlib.Path(sys.argv[1]).resolve(), pathlib.Path(sys.argv[2]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        sys.exit("De uitvoermap moet leeg zijn.")
    shutil.copyfile(sbom, out / "sbom.cdx.json")
    image = trivy_image()
    # Eerst één keer de database ophalen; daarna draait elke scan op precies dezelfde database.
    code, base, _ = scan(image, out, "zonder-vex", [])
    db = json.loads((out / "zonder-vex.trivy.json").read_text(encoding="utf-8")).get("CreatedAt")
    print(f"Trivy {image.split('@')[0]}, scan {db}; zonder VEX: {len(base)} rijen HIGH/CRITICAL, exit {code}")
    fixed = ["--skip-db-update"]
    for name, doc in CASES.items():
        (out / f"{name}.vex.json").write_text(json.dumps(doc, indent=2), encoding="utf-8")
        code, rows, err = scan(image, out, name, fixed + ["--vex", f"/scan/{name}.vex.json"])
        report(name, base, rows, code, err)
    for name, text in IGNORE.items():
        (out / f"{name}.trivyignore.yaml").write_text(text, encoding="utf-8")
        code, rows, err = scan(image, out, name, fixed + ["--ignorefile", f"/scan/{name}.trivyignore.yaml"])
        report(name, base, rows, code, err)
    # De echte VEX uit de repo, als die is meegegeven: blijft er dan nog iets over voor de rem?
    if len(sys.argv) == 4:
        shutil.copyfile(sys.argv[3], out / "repo.vex.json")
        code, rows, err = scan(image, out, "repo-vex", fixed + ["--vex", "/scan/repo.vex.json"])
        report("repo-vex", base, rows, code, err)
        for cve, pkg in rows or []:
            print(f"    over: {cve} {pkg}")


def report(name, base, rows, code, err):
    if rows is None:
        print(f"  {name:28} FOUT exit {code}: {' '.join(err)}")
        return
    weg = sorted(set(base) - set(rows))
    print(f"  {name:28} exit {code}, {len(rows):3} rijen, weggefilterd: {len(weg)} "
          f"{', '.join(f'{c} {p}' for c, p in weg[:3])}{' ...' if len(weg) > 3 else ''}")


main()
