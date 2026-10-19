"""Telt wat één meting opleverde en schrijft meting.json. Gebruik: tel.py <uitmap> <variant> <db_ms> <db_exit> <gen_ms> <gen_exit> <scan_ms> <scan_exit>"""
import collections
import json
import os
import pathlib
import sys

out, variant = pathlib.Path(sys.argv[1]), sys.argv[2]
db_ms, db_exit, gen_ms, gen_exit, scan_ms, scan_exit = map(int, sys.argv[3:9])
# De drie kopieën in pip/_vendor met de vier bekende lekken (BoK, T-105).
VENDORED = ("urllib3", "msgpack", "setuptools")


# CycloneDX kan componenten in componenten zetten; Trivy doet dat bij de Python-pakketten.
def walk(components):
    for c in components or []:
        yield c
        yield from walk(c.get("components"))


sbom = json.loads((out / "sbom.json").read_text(encoding="utf-8"))
# Syft zet ook elk bestand in de SBoM; geteld worden alleen de pakketten, zoals bij Trivy.
components = [c for c in walk(sbom.get("components")) if c.get("type") != "file"]
kinds = collections.Counter(c["purl"].split("/")[0].removeprefix("pkg:") if c.get("purl", "").startswith("pkg:") else c.get("type", "?")
                            for c in components)
pypi = {c["name"].lower() for c in components if c.get("purl", "").startswith("pkg:pypi/")}

scan = json.loads((out / "scan.json").read_text(encoding="utf-8"))
if variant == "trivy":
    findings = {(v["VulnerabilityID"], v["PkgName"]) for r in scan.get("Results") or [] for v in r.get("Vulnerabilities") or []}
else:
    findings = {(m["vulnerability"]["id"], m["artifact"]["name"]) for m in scan.get("matches", [])
                if m["vulnerability"]["severity"].upper() in ("HIGH", "CRITICAL")}

result = {
    "variant": variant, "image": os.environ["IMAGE"], "herhaling": int(os.environ["HERHALING"]),
    "ms_database": db_ms, "ms_genereren": gen_ms, "ms_scannen": scan_ms,
    "exit_database": db_exit, "exit_genereren": gen_exit, "exit_scannen": scan_exit,
    "cyclonedx": sbom.get("specVersion"), "componenten": len(components), "soorten": dict(kinds),
    "kopieen_in_pip": sum(name in pypi for name in VENDORED), "hoog_kritiek_met_fix": len(findings),
    "bevindingen": sorted(f"{i} ({p})" for i, p in findings),
}
(out / "meting.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
print(json.dumps(result))
