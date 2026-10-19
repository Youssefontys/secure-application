"""Labmeting voor deelvraag 3: wat missen SBoM's van dezelfde image, en hoeveel verschillen ze per generator en scanner?
Drie SBoM's (Trivy, Syft, Syft met de sbom-cataloger), elk gescand met Trivy en met Grype, naast wat er echt in de
draaiende image zit (binnen.py). Draait op een runner via .github/workflows/dv3-meting.yml; werkt ook op Windows.
Gebruik: python lab/dv3/meet.py <image> <lege uitmap>"""
import collections
import json
import pathlib
import re
import secrets
import subprocess
import sys
import time
import urllib.request
from urllib.parse import unquote

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
# Dezelfde versies als de labmeting en de benchmark van deelvraag 1; Trivy uit image.yml.
SYFT = "anchore/syft:v1.54.1@sha256:3eb5379ba7b409c3f4069b686110527af0c47df993fa5c10d13e7cf34f49b1aa"
GRYPE = "anchore/grype:v0.120.1@sha256:e4a44ef45d285b829ce6efe2642980329661bd2d18eab5fc539138d4adaebbbe"
SBOMS = ("trivy", "syft", "syft-sbom")
SCANNERS = ("trivy", "grype")
PORT = 5056


def trivy_image():
    text = (REPO / ".github/workflows/image.yml").read_text(encoding="utf-8")
    m = re.search(r"^\s*TRIVY: (aquasec/trivy:[0-9.]+@sha256:[0-9a-f]{64})$", text, re.M)
    if not m:
        sys.exit("TRIVY niet gevonden in image.yml")
    return m.group(1)


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit(f"mislukt ({p.returncode}): {' '.join(cmd[:6])} ...\n{p.stderr[-800:]}")
    return p


def mount(src, dst, ro=False):
    return ["--mount", f"type=bind,source={src},target={dst}" + (",readonly" if ro else "")]


def generate(out, trivy):
    w = mount(out, "/w")
    run(["docker", "run", "--rm", *w, "--mount", "type=volume,source=trivycache,target=/root/.cache", trivy,
         "image", "--input", "/w/img.tar", "--format", "cyclonedx", "--output", "/w/sbom-trivy.json", "--quiet"])
    run(["docker", "run", "--rm", *w, SYFT, "docker-archive:/w/img.tar", "-o", "cyclonedx-json=/w/sbom-syft.json", "-q"])
    run(["docker", "run", "--rm", *w, SYFT, "docker-archive:/w/img.tar", "--select-catalogers", "+sbom-cataloger",
         "-o", "cyclonedx-json=/w/sbom-syft-sbom.json", "-q"])


def scan(out, trivy):
    w = mount(out, "/w")
    tcache = ["--mount", "type=volume,source=trivycache,target=/root/.cache"]
    gcache = ["--mount", "type=volume,source=grypecache,target=/cache", "-e", "GRYPE_DB_CACHE_DIR=/cache"]
    # Eerst de databases bijwerken; daarna scant alles op dezelfde database.
    run(["docker", "run", "--rm", *tcache, trivy, "image", "--download-db-only", "--quiet"])
    run(["docker", "run", "--rm", *gcache, GRYPE, "db", "update", "-q"])
    # Een scan die faalt, is ook een uitkomst (Trivy weigerde in run 39333438742 een SBoM met rpm en deb): de fout gaat
    # naar scan-<scanner>-<sbom>.fout.txt, en de meting gaat door.
    meta = {"fouten": {}}
    for s in SBOMS:
        for sc, cmd in (("trivy", [*w, *tcache, trivy, "sbom", f"/w/sbom-{s}.json", "--skip-db-update", "--format", "json",
                                   "--output", f"/w/scan-trivy-{s}.json", "--quiet"]),
                        ("grype", [*w, *gcache, "-e", "GRYPE_DB_AUTO_UPDATE=false", GRYPE, f"sbom:/w/sbom-{s}.json",
                                   "-o", "json", "--file", f"/w/scan-grype-{s}.json", "-q"])):
            p = subprocess.run(["docker", "run", "--rm", *cmd], capture_output=True, text=True)
            if p.returncode != 0:
                (out / f"scan-{sc}-{s}.fout.txt").write_text(p.stderr, encoding="utf-8")
                meta["fouten"][f"{sc} op {s}"] = p.stderr.strip().splitlines()[-1][-300:] if p.stderr.strip() else str(p.returncode)
    meta["trivy"] = json.loads((out / "scan-trivy-trivy.json").read_text(encoding="utf-8")).get("CreatedAt")
    p = subprocess.run(["docker", "run", "--rm", *gcache, GRYPE, "db", "status", "-o", "json"], capture_output=True, text=True)
    meta["grype_db"] = p.stdout.strip()[:400]
    return meta


def inside(out, image):
    # De app starten zoals in deelvraag 2 (T-114), met wegwerpsleutels en zonder database; daarna binnen.py erin.
    name = "dv3-meting"
    subprocess.run(["docker", "rm", "-f", name], capture_output=True)
    run(["docker", "run", "-d", "--name", name, "-p", f"127.0.0.1:{PORT}:5000", *mount(HERE, "/lab", ro=True),
         "-e", f"FLASK_SECRET_KEY={secrets.token_urlsafe(32)}", "-e", f"DATA_ENCRYPTION_KEY={secrets.token_hex(32)}",
         "-e", "HTTPS_ONLY=0", "-e", "DATABASE_URL=postgresql://x:y@127.0.0.1:1/x", image])
    try:
        for _ in range(30):
            try:
                if urllib.request.urlopen(f"http://127.0.0.1:{PORT}/login", timeout=2).status == 200:
                    break
            except OSError:
                time.sleep(1)
        else:
            sys.exit("de app kwam niet op")
        p = run(["docker", "exec", name, "python", "-I", "/lab/binnen.py"])
        (out / "binnen.json").write_text(p.stdout, encoding="utf-8")
        return json.loads(p.stdout)
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)


def walk(components):
    for c in components or []:
        yield c
        yield from walk(c.get("components"))


def norm_name(kind, name):
    return re.sub(r"[-_.]+", "-", name.lower()) if kind == "pypi" else name


def parse_purl(purl):
    # De namespace alleen vóór de @, anders telt een / in een qualifier (download_url=https://...) mee.
    m = re.match(r"pkg:([^/]+)/(?:[^@?#]*/)?([^/@?#]+)(?:@([^?#]+))?", purl or "")
    if not m:
        return None
    kind, name, version = m.group(1), unquote(m.group(2)), unquote(m.group(3) or "")
    return kind, norm_name(kind, name), re.sub(r"^\d+:", "", version)


def sbom_components(path):
    doc = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for c in walk(doc.get("components")):
        if c.get("type") == "file":
            continue
        p = parse_purl(c.get("purl"))
        out.append(p if p else (c.get("type", "?"), c.get("name", "?"), c.get("version", "")))
    return out


def findings(path, scanner):
    doc = json.loads(path.read_text(encoding="utf-8"))
    out = set()
    if scanner == "trivy":
        for r in doc.get("Results") or []:
            for v in r.get("Vulnerabilities") or []:
                out.add((v["VulnerabilityID"], v["PkgName"], v.get("Severity", "?").upper()))
    else:
        for m in doc.get("matches", []):
            v = m["vulnerability"]
            cves = [r["id"] for r in m.get("relatedVulnerabilities", []) if r.get("id", "").startswith("CVE-")]
            vid = v["id"] if v["id"].startswith("CVE-") or not cves else cves[0]
            out.add((vid, m["artifact"]["name"], v.get("severity", "?").upper()))
    return out


def analyse(out, truth, meta):
    deb = {(row[0], re.sub(r"^\d+:", "", row[1])) for row in truth["dpkg"]}
    deb_names = {n for n, _ in deb}
    pypi = {(norm_name("pypi", n), v) for n, v in truth["dists"]}
    res = {"meta": meta, "waarheid": {
        "deb": len(deb), "pypi": len(pypi), "python": truth["python"], "ssl_van_python": truth["ssl_van_python"],
        "openssl_in_cryptography": truth["openssl_in_cryptography"], "libpq_in_psycopg": truth["libpq_in_psycopg"],
        "wheel_sboms": {k: len(v) for k, v in truth["wheel_sboms"].items()}}, "sboms": {}, "scans": {}}
    hidden_words = ("python", "openssl", "libssl", "libcrypto", "libpq", "postgres", "krb5", "pcre", "sasl", "ldap",
                    "selinux", "keyutils", "com_err", "libcrypt", "xcrypt")
    for s in SBOMS:
        comps = sbom_components(out / f"sbom-{s}.json")
        kinds = collections.Counter(k for k, _, _ in comps)
        got_deb = {(n, v) for k, n, v in comps if k == "deb"}
        got_pypi = {(n, v) for k, n, v in comps if k == "pypi"}
        extra = sorted({f"{k}:{n}@{v}" for k, n, v in comps if k not in ("deb", "pypi")
                        and any(w in n.lower() for w in hidden_words)})
        res["sboms"][s] = {
            "componenten": len(comps), "soorten": dict(kinds),
            "deb_gevonden": len(got_deb & deb), "deb_gemist": sorted(f"{n}@{v}" for n, v in deb - got_deb),
            "deb_extra": sorted(f"{n}@{v}" for n, v in got_deb - deb),
            "pypi_gevonden": len(got_pypi & pypi), "pypi_gemist": sorted(f"{n}@{v}" for n, v in pypi - got_pypi),
            "pypi_extra": sorted(f"{n}@{v}" for n, v in got_pypi - pypi),
            "verborgen_gezien": extra}
    for s in SBOMS:
        for sc in SCANNERS:
            if not (out / f"scan-{sc}-{s}.json").exists():
                res["scans"][f"{sc} op {s}"] = {"fout": meta["fouten"].get(f"{sc} op {s}", "geen uitvoer")}
                continue
            f = findings(out / f"scan-{sc}-{s}.json", sc)
            res["scans"][f"{sc} op {s}"] = {
                "meldingen": len(f), "lekken": len({i for i, _, _ in f}),
                "per_ernst": dict(collections.Counter(sev for _, _, sev in f)),
                "op_verborgen": sorted({f"{i} {p} {sev}" for i, p, sev in f if p not in deb_names
                                        and norm_name("pypi", p) not in {n for n, _ in pypi}})[:60]}
    ids = {k: {i for i, _, _ in findings(out / f"scan-{k.split(' op ')[0]}-{k.split(' op ')[1]}.json", k.split(' op ')[0])}
           for k in res["scans"] if "fout" not in res["scans"][k]}
    keys = list(ids)
    res["overlap"] = {f"{a} | {b}": [len(ids[a] & ids[b]), len(ids[a] | ids[b])] for i, a in enumerate(keys) for b in keys[i + 1:]}
    loaded = collections.Counter()
    for g in truth["geladen"]:
        src = g["van"]
        if "psycopg_binary.libs/" in g["bestand"]:
            src = "pypi:psycopg-binary (meegeleverde bibliotheek)"
        loaded[src.split(":")[0] if src.startswith("deb:") else src] += 1
    res["geladen"] = {"bestanden": len(truth["geladen"]), "per_herkomst": dict(loaded),
                      "met_versie": [f"{g['bestand'].split('/')[-1]} {g['versies']}" for g in truth["geladen"] if g["versies"]]}
    (out / "resultaten.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    return res


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    image, out = sys.argv[1], pathlib.Path(sys.argv[2]).resolve()
    if not re.fullmatch(r"ghcr\.io/[a-z0-9_.-]+/[a-z0-9_.-]+:[0-9a-f]{40}", image):
        sys.exit("Alleen een image van ghcr.io met een commit als tag.")
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        sys.exit("De uitmap moet leeg zijn.")
    trivy = trivy_image()
    run(["docker", "pull", "-q", image])
    digest = run(["docker", "image", "inspect", "--format", "{{index .RepoDigests 0}}", image]).stdout.strip()
    run(["docker", "save", image, "-o", str(out / "img.tar")])
    generate(out, trivy)
    # De scans lezen alleen de SBoM's; de tar (ruim 170 MB) hoort niet in het artifact.
    (out / "img.tar").unlink()
    meta = scan(out, trivy)
    meta.update(image=image, digest=digest, trivy=trivy, syft=SYFT, grype=GRYPE, scan_trivy_db=meta.pop("trivy"))
    truth = inside(out, image)
    res = analyse(out, truth, meta)
    print(json.dumps({k: res[k] for k in ("waarheid", "geladen")}, indent=1, ensure_ascii=False))
    for s, v in res["sboms"].items():
        print(f"SBoM {s:10} {v['componenten']:4} componenten {v['soorten']}; deb {v['deb_gevonden']}/{res['waarheid']['deb']}, "
              f"pypi {v['pypi_gevonden']}/{res['waarheid']['pypi']}; verborgen gezien: {v['verborgen_gezien']}")
    for k, v in res["scans"].items():
        if "fout" in v:
            print(f"{k:22} FOUT: {v['fout']}")
        else:
            print(f"{k:22} {v['meldingen']:4} meldingen, {v['lekken']:4} lekken {v['per_ernst']}")


main()
