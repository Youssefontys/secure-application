"""Proef na deelvraag 3: meet één variant van de app terwijl de lokale stack draait (scripts/deployment.py lokaal): de
regressietest, wat de app laadt, de SBoM en de rem zoals de pipeline (met de VEX), en de snelheid naar de database.
Draait op een runner via .github/workflows/dv3-psycopg.yml, niet lokaal.
Gebruik: python lab/psycopg/meet.py <binary|libpq> <lege uitmap>
         python lab/psycopg/meet.py vergelijk <map met binary/ en libpq/>"""
import collections
import json
import pathlib
import re
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]


def run(cmd, **kw):
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO, **kw)
    if p.returncode != 0:
        sys.exit(f"mislukt ({p.returncode}): {' '.join(cmd[:6])} ...\n{p.stderr[-800:]}")
    return p


def trivy_image():
    text = (REPO / ".github/workflows/image.yml").read_text(encoding="utf-8")
    return re.search(r"^\s*TRIVY: (aquasec/trivy:[0-9.]+@sha256:[0-9a-f]{64})$", text, re.M).group(1)


def in_app(script):
    # Het script in de container van de app zetten en draaien, met de omgeving van de app (DATABASE_URL van de app-rol).
    run(["docker", "compose", "cp", str(HERE.parent / script), f"app:/tmp/{pathlib.Path(script).name}"])
    return json.loads(run(["docker", "compose", "exec", "-T", "app", "python", "-I", f"/tmp/{pathlib.Path(script).name}"]).stdout)


def measure(variant, out):
    res = {"variant": variant}
    # De regressietest eerst, op een verse stack; hij eindigt altijd met exit 0, de laatste regel zegt hoe het ging.
    start = time.monotonic()
    p = subprocess.run([sys.executable, "tests/regress.py", "--wis"], capture_output=True, text=True, cwd=REPO)
    (out / "regressietest.txt").write_text(p.stdout + p.stderr, encoding="utf-8")
    lines = [line for line in p.stdout.splitlines() if line.strip()]
    res["regressietest"] = {"uitkomst": lines[-1] if lines else p.stderr[-300:], "seconden": round(time.monotonic() - start),
                            "controles": sum(line.startswith("ok") for line in lines)}
    truth = in_app("dv3/binnen.py")
    (out / "binnen.json").write_text(json.dumps(truth, indent=1), encoding="utf-8")
    origin = collections.Counter()
    for g in truth["geladen"]:
        src = g["van"]
        origin["meegeleverd door psycopg-binary" if "psycopg_binary.libs/" in g["bestand"] else
               "deb" if src.startswith("deb:") else src] += 1
    res["geladen"] = {"bestanden": len(truth["geladen"]), "per_herkomst": dict(origin),
                      "debian_pakketten": sorted({g["van"][4:] for g in truth["geladen"] if g["van"].startswith("deb:")}),
                      "openssl": sorted({v for g in truth["geladen"] for v in g["versies"].get("openssl", [])}),
                      "libpq": truth["libpq_in_psycopg"], "debian_totaal": len(truth["dpkg"])}
    res["snelheid"] = in_app("psycopg/bench.py")
    # De image van de stack, als tar, met de SBoM en de scan zoals in image.yml.
    image = run(["docker", "inspect", "--format", "{{.Image}}", run(["docker", "compose", "ps", "-q", "app"]).stdout.strip()]).stdout.strip()
    res["image_mb"] = round(int(run(["docker", "image", "inspect", "--format", "{{.Size}}", image]).stdout) / 1e6, 1)
    run(["docker", "save", image, "-o", str(out / "img.tar")])
    trivy = trivy_image()
    w = ["--mount", f"type=bind,source={out},target=/w", "--mount", "type=volume,source=trivycache,target=/root/.cache"]
    run(["docker", "run", "--rm", *w, trivy, "image", "--input", "/w/img.tar", "--format", "cyclonedx",
         "--output", "/w/sbom.json", "--quiet"])
    (out / "img.tar").unlink()
    sbom = json.loads((out / "sbom.json").read_text(encoding="utf-8"))
    res["sbom_componenten"] = sum(1 for c in sbom.get("components", []) if c.get("type") != "file")
    vex = ["--mount", f"type=bind,source={REPO / 'vex'},target=/vex,readonly"]
    run(["docker", "run", "--rm", *w, trivy, "sbom", "/w/sbom.json", "--format", "json", "--output", "/w/scan-alles.json", "--quiet"])
    # De rem van de pipeline: HIGH en CRITICAL, met de VEX van main; exit 1 is hier een uitkomst, geen fout.
    gate = subprocess.run(["docker", "run", "--rm", *w, *vex, trivy, "sbom", "/w/sbom.json", "--severity", "HIGH,CRITICAL",
                           "--vex", "/vex/openvex.json", "--exit-code", "1", "--format", "json", "--output", "/w/scan-rem.json",
                           "--quiet"], capture_output=True, text=True)
    allv = [v for r in json.loads((out / "scan-alles.json").read_text(encoding="utf-8")).get("Results") or []
            for v in r.get("Vulnerabilities") or []]
    left = [v for r in json.loads((out / "scan-rem.json").read_text(encoding="utf-8")).get("Results") or []
            for v in r.get("Vulnerabilities") or []]
    res["scan"] = {"meldingen": len(allv), "lekken": len({v["VulnerabilityID"] for v in allv}),
                   "per_ernst": dict(collections.Counter(v["Severity"] for v in allv)),
                   "rem_exit": gate.returncode,
                   "rem_over": sorted({f"{v['VulnerabilityID']} {v['PkgName']} {v['Severity']} {v.get('Status')}" for v in left})}
    (out / "resultaat.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(res, indent=1, ensure_ascii=False))


def compare(base):
    a, b = (json.loads((base / v / "resultaat.json").read_text(encoding="utf-8")) for v in ("binary", "libpq"))
    rows = [("Regressietest", a["regressietest"]["uitkomst"], b["regressietest"]["uitkomst"]),
            ("Controles", a["regressietest"]["controles"], b["regressietest"]["controles"]),
            ("Geladen bestanden", a["geladen"]["bestanden"], b["geladen"]["bestanden"]),
            ("Per herkomst", a["geladen"]["per_herkomst"], b["geladen"]["per_herkomst"]),
            ("Debian-pakketten geladen", len(a["geladen"]["debian_pakketten"]), len(b["geladen"]["debian_pakketten"])),
            ("Debian-pakketten in de image", a["geladen"]["debian_totaal"], b["geladen"]["debian_totaal"]),
            ("OpenSSL in het proces", a["geladen"]["openssl"], b["geladen"]["openssl"]),
            ("libpq", a["geladen"]["libpq"], b["geladen"]["libpq"]),
            ("psycopg", a["snelheid"]["implementatie"], b["snelheid"]["implementatie"]),
            ("Image (MB)", a["image_mb"], b["image_mb"]),
            ("SBoM-onderdelen", a["sbom_componenten"], b["sbom_componenten"]),
            ("Meldingen / lekken", f"{a['scan']['meldingen']} / {a['scan']['lekken']}", f"{b['scan']['meldingen']} / {b['scan']['lekken']}"),
            ("Per ernst", a["scan"]["per_ernst"], b["scan"]["per_ernst"]),
            ("Rem met de VEX van main (exit)", a["scan"]["rem_exit"], b["scan"]["rem_exit"]),
            ("Over na de VEX", a["scan"]["rem_over"], b["scan"]["rem_over"])]
    rows += [(f"{k} (mediaan, ms)", a["snelheid"][k]["mediaan"], b["snelheid"][k]["mediaan"])
             for k in ("verbinden_50", "select_1_5000", "1000_rijen_200")]
    nieuw = sorted(set(b["geladen"]["debian_pakketten"]) - set(a["geladen"]["debian_pakketten"]))
    print("| Wat | psycopg-binary (main) | psycopg + libpq5 van Debian |\n|---|---|---|")
    for name, x, y in rows:
        print(f"| {name} | {x} | {y} |")
    print(f"\nNieuw geladen Debian-pakketten: {', '.join(nieuw)}")


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("binary", "libpq", "vergelijk"):
        sys.exit(__doc__)
    out = pathlib.Path(sys.argv[2]).resolve()
    if sys.argv[1] == "vergelijk":
        compare(out)
        return
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        sys.exit("De uitmap moet leeg zijn.")
    measure(sys.argv[1], out)


main()
