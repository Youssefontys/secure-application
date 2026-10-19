"""Proef voor de stap VEX controleren: het jq-programma uit image.yml op de echte VEX en op kapotte varianten.
Gebruik: python jqproef.py <repo> <lege-map>"""
import copy
import json
import pathlib
import re
import subprocess
import sys

repo, out = pathlib.Path(sys.argv[1]).resolve(), pathlib.Path(sys.argv[2]).resolve()
out.mkdir(parents=True, exist_ok=True)
text = (repo / ".github/workflows/image.yml").read_text(encoding="utf-8")
prog = re.search(r"jq -e '\n(.*?)\n\s*' vex/openvex\.json", text, re.S).group(1)
(out / "prog.jq").write_bytes(prog.encode("utf-8"))
vex = json.loads((repo / "vex/openvex.json").read_text(encoding="utf-8"))


def variant(fn):
    v = copy.deepcopy(vex)
    fn(v["statements"][-1])
    return v


cases = {
    "echt": vex,
    "na-zonder-uitleg": variant(lambda s: s.pop("impact_statement")),
    "na-foute-justification": variant(lambda s: s.update(justification="not_reachable")),
    "purl-zonder-versie": variant(lambda s: s.update(products=[{"@id": "pkg:deb/debian/perl-base"}])),
    "status-fixed": variant(lambda s: s.update(status="fixed")),
    "affected-zonder-actie": variant(lambda s: s.update(status="affected")),
    "affected-met-actie": variant(lambda s: s.update(status="affected", action_statement="Upgrade when Debian has a fix.")),
}
for name, doc in cases.items():
    (out / f"{name}.json").write_text(json.dumps(doc), encoding="utf-8")
    p = subprocess.run(["docker", "run", "--rm", "--mount", f"type=bind,source={out},target=/w,readonly",
                        "ghcr.io/jqlang/jq:1.7.1", "-e", "-f", "/w/prog.jq", f"/w/{name}.json"],
                       capture_output=True, text=True)
    print(f"{name:24} exit {p.returncode} {(p.stdout + p.stderr).strip()[:120]}")
