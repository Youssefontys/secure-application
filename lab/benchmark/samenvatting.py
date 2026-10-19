"""Zet alle metingen samen: per variant en image de mediaan, het minimum en het maximum van de tijden, en wat er
gevonden werd. Gebruik: samenvatting.py <map met de artefacten>. Schrijft markdown naar stdout en metingen.csv."""
import csv
import json
import pathlib
import statistics
import sys

root = pathlib.Path(sys.argv[1])
rows = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(root.glob("*/meting.json"))]
fields = ["variant", "image", "herhaling", "ms_database", "ms_genereren", "ms_scannen", "exit_scannen",
          "cyclonedx", "componenten", "kopieen_in_pip", "hoog_kritiek_met_fix"]
with open(root / "metingen.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    w.writerows(sorted(rows, key=lambda r: (r["variant"], r["image"], r["herhaling"])))


def spread(values):
    return f"{statistics.median(values) / 1000:.1f} s ({min(values) / 1000:.1f} tot {max(values) / 1000:.1f})"


print(f"## SBoM-benchmark: {len(rows)} metingen, elk op een eigen runner\n")
print("Mediaan, met tussen haakjes het minimum en het maximum.\n")
print("| Variant | Image | n | Database | Genereren | Scannen | Exit scan | Componenten | Kopieën in pip | HIGH/CRITICAL met fix |")
print("|---|---|---|---|---|---|---|---|---|---|")
for key in sorted({(r["variant"], r["image"]) for r in rows}):
    group = [r for r in rows if (r["variant"], r["image"]) == key]
    exits = sorted({r["exit_scannen"] for r in group})
    comps = sorted({r["componenten"] for r in group})
    vend = sorted({r["kopieen_in_pip"] for r in group})
    found = sorted({r["hoog_kritiek_met_fix"] for r in group})
    print(f"| {key[0]} | {key[1]} | {len(group)} | {spread([r['ms_database'] for r in group])} | "
          f"{spread([r['ms_genereren'] for r in group])} | {spread([r['ms_scannen'] for r in group])} | "
          f"{', '.join(map(str, exits))} | {', '.join(map(str, comps))} | {', '.join(map(str, vend))} | {', '.join(map(str, found))} |")
