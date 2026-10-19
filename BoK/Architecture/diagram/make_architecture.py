"""Tekent de architectuur op Azure als SVG: de onderdelen (C-), de datastromen (F-) en de trust boundaries (B-).
De plek van elk blok staat hier; de ID's worden gecontroleerd tegen components.md, data-flows.md en
trust-boundaries.md, zodat het diagram geen onderdeel noemt dat er niet is. Gebruik: python make_architecture.py"""
import html
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
ARCH = HERE.parent
FONT = "Segoe UI, Helvetica, Arial, sans-serif"
HALO = ' paint-order="stroke" stroke="#ffffff" stroke-width="4" stroke-linejoin="round"'
KNOWN = set(re.findall(r"^\| ((?:C|F|B)-\d+) \|", "".join((ARCH / f).read_text(encoding="utf-8") for f in
                                                          ("components.md", "data-flows.md", "trust-boundaries.md")), re.M))

# Zones: (x, y, breedte, hoogte, label, stippellijn)
ZONES = [
    (20, 60, 260, 560, "Internet, buiten ons beheer", True),
    (330, 60, 460, 220, "GitHub", True),
    (330, 320, 1150, 600, "Azure, France Central", True),
    (470, 420, 300, 210, "Container Apps-omgeving", False),
    (1010, 420, 300, 290, "Privé-netwerk van de database", False),
    (1150, 760, 310, 140, "Resource group voor de state", False),
    (20, 660, 260, 260, "De beheerder", True),
]
# Blokken: id -> (midden x, midden y, regel 1, regel 2)
BOXES = {
    "C-11": (150, 160, "C-11 Bijdrager", "Een branch of een fork"),
    "C-01": (150, 420, "C-01 Browser", "Bezoeker of gebruiker"),
    "C-06a": (450, 170, "C-06 GitHub Actions", "Check en image"),
    "C-06b": (680, 170, "C-06 ghcr.io", "Het pakket, openbaar"),
    "C-02": (620, 525, "C-02 Webapplicatie", "Gunicorn als app, en de schema-job"),
    "C-07": (890, 375, "C-07 Key Vaults", "kv- en kvdb-"),
    "C-03": (1160, 500, "C-03 Database", "PostgreSQL 18, B1ms"),
    "C-04": (1160, 640, "C-04 Opslag", "Versleuteld door Azure"),
    "C-05": (620, 790, "C-05 Log Analytics", "30 dagen"),
    "C-08": (880, 790, "C-08 Alert", "Bij een blokkade"),
    "C-09": (1305, 840, "C-09 State-opslag", "Eigen RSA-4096-sleutel"),
    "C-10": (150, 750, "C-10 Uitrolplek", "Terraform en de Azure CLI"),
    "mail": (150, 865, "Mailbox", "Van de beheerder"),
}
BW, BH = 200, 54
# Datastromen: (id-label, punten van de lijn, waar het label staat, pijl aan beide kanten)
FLOWS = [
    ("F-12 pull request", [(250, 160), (350, 168)], (300, 148), False),
    ("F-06 image", [(550, 170), (580, 170)], (565, 134), False),
    ("F-07 image ophalen", [(680, 197), (640, 498)], (700, 300), False),
    ("F-01 en F-02 HTTPS", [(250, 425), (520, 520)], (415, 470), True),
    ("F-03 TLS 1.3", [(720, 520), (1060, 500)], (890, 495), True),
    ("F-04", [(1160, 527), (1160, 613)], (1185, 575), False),
    ("F-05 security-events", [(620, 552), (620, 763)], (700, 690), False),
    ("F-08 geheimen", [(860, 402), (700, 498)], (820, 455), False),
    ("F-09 aantal", [(720, 790), (780, 790)], (750, 772), False),
    ("F-09 mail", [(880, 817), (880, 905), (315, 905), (315, 865), (250, 865)], (560, 897), False),
    ("F-10 Terraform", [(250, 735), (420, 735), (420, 640), (520, 552)], (400, 725), False),
    ("F-11 state", [(250, 765), (300, 765), (300, 940), (1305, 940), (1305, 867)], (800, 932), True),
]
# Trust boundaries: (id, x, y), op de plek waar een stroom de grens overgaat
BOUNDARIES = [("B-06", 330, 166), ("B-04", 665, 320), ("B-01", 330, 453), ("B-02", 1010, 503),
              ("B-03", 1135, 575), ("B-05", 330, 735), ("B-05", 1305, 920)]


def esc(s):
    return html.escape(s, quote=True)


def check():
    # C-06 staat er twee keer, als GitHub Actions en als ghcr.io; alleen het nummer telt.
    used = {re.match(r"C-\d+", i).group(0) for i in BOXES if i.startswith("C-")}
    used |= {f.split()[0] for f, *_ in FLOWS} | {"F-02"} | {b for b, *_ in BOUNDARIES}
    missing = sorted(used - KNOWN)
    assert not missing, f"niet in de architectuur: {missing}"


def draw():
    parts, w, h = [], 1500, 990
    parts.append(f'<rect width="{w}" height="{h}" fill="#ffffff"/>')
    parts.append(f'<text x="24" y="36" font-size="20" font-weight="600" font-family="{FONT}" fill="#1a1a1a">'
                 'Architectuur op Azure: onderdelen, datastromen en trust boundaries</text>')
    for x, y, zw, zh, label, dashed in ZONES:
        dash = ' stroke-dasharray="8 5"' if dashed else ""
        fill = "#f6f8fb" if dashed else "#ffffff"
        parts.append(f'<rect x="{x}" y="{y}" width="{zw}" height="{zh}" rx="10" fill="{fill}" stroke="#8a94a6" stroke-width="1.5"{dash}/>')
        parts.append(f'<text x="{x + 12}" y="{y + 22}" font-size="13" font-weight="600" font-family="{FONT}" fill="#4a5568">{esc(label)}</text>')
    for label, pts, (lx, ly), both in FLOWS:
        d = "M" + " L".join(f"{px},{py}" for px, py in pts)
        start = ' marker-start="url(#pijl)"' if both else ""
        parts.append(f'<path d="{d}" fill="none" stroke="#2b6cb0" stroke-width="1.8" marker-end="url(#pijl)"{start}/>')
        parts.append(f'<text x="{lx}" y="{ly}" font-size="12" font-family="{FONT}" fill="#2b6cb0" text-anchor="middle"{HALO}>{esc(label)}</text>')
    for key, (cx, cy, l1, l2) in BOXES.items():
        x, y = cx - BW / 2, cy - BH / 2
        stroke = "#2d3748" if key != "mail" else "#8a94a6"
        parts.append(f'<rect x="{x}" y="{y}" width="{BW}" height="{BH}" rx="6" fill="#ffffff" stroke="{stroke}" stroke-width="1.6"/>')
        parts.append(f'<text x="{cx}" y="{cy - 4}" font-size="13" font-weight="600" font-family="{FONT}" fill="#1a1a1a" text-anchor="middle">{esc(l1)}</text>')
        parts.append(f'<text x="{cx}" y="{cy + 14}" font-size="11.5" font-family="{FONT}" fill="#4a5568" text-anchor="middle">{esc(l2)}</text>')
    for bid, bx, by in BOUNDARIES:
        parts.append(f'<rect x="{bx - 22}" y="{by - 11}" width="44" height="20" rx="10" fill="#c53030"/>')
        parts.append(f'<text x="{bx}" y="{by + 4}" font-size="11.5" font-weight="700" font-family="{FONT}" fill="#ffffff" text-anchor="middle">{bid}</text>')
    parts.append(f'<text x="1480" y="980" font-size="11.5" font-family="{FONT}" fill="#4a5568" text-anchor="end">'
                 'Blauw: een datastroom (F-). Rood: een trust boundary (B-). Gestippeld: een domein; doorgetrokken: een zone erbinnen.</text>')
    defs = ('<defs><marker id="pijl" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
            '<path d="M0,0 L10,5 L0,10 z" fill="#2b6cb0"/></marker></defs>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{defs}{"".join(parts)}</svg>\n')
    (HERE / "architecture.svg").write_text(svg, encoding="utf-8", newline="\n")
    print("geschreven: architecture.svg")


check()
draw()
