"""Tekent het use case-diagram en de misuse case-diagrammen als SVG, uit entries.md en risk-matrix.md.
Welke use case een misuse case bedreigt, welke maatregelen hem tegenhouden en zijn risico komen uit de BoK zelf;
alleen de indeling per doel en de namen van de aanvallers staan hier. Gebruik: python make_diagrams.py"""
import html
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
ENTRIES = (HERE.parent / "entries.md").read_text(encoding="utf-8")
MATRIX = (HERE.parent / "risk-matrix.md").read_text(encoding="utf-8")
FONT = "Segoe UI, Helvetica, Arial, sans-serif"
HALO = ' paint-order="stroke" stroke="#ffffff" stroke-width="4" stroke-linejoin="round"'
RISK_COLOR = {"laag": "#2e7d32", "midden": "#e65100", "hoog": "#c62828"}

# Elke misuse case staat in precies één diagram, naar het doel van de aanvaller (zoals in attack-trees.md).
GROUPS = [
    ("misuse-1-inloggen", "Doel: inloggen als een ander", "Aanvaller van buiten",
     ["MC-01", "MC-03", "MC-09", "MC-15", "MC-16", "MC-17", "MC-19", "MC-20", "MC-21"]),
    ("misuse-2-sessie", "Doel: handelen met de sessie van een ander", "Aanvaller met een sessie of een eigen site",
     ["MC-04", "MC-05", "MC-12", "MC-13", "MC-24", "MC-27", "MC-29"]),
    ("misuse-3-notities", "Doel: de notities van een ander lezen of wijzigen", "Andere gebruiker of bezoeker",
     ["MC-02", "MC-06", "MC-07", "MC-23", "MC-25"]),
    ("misuse-4-dienst", "Doel: de dienst onbruikbaar maken of geen spoor laten", "Bezoeker of script",
     ["MC-10", "MC-18", "MC-26", "MC-28"]),
    ("misuse-5-omgeving", "Doel: de app of de omgeving op Azure overnemen", "Aanvaller op de app, de pipeline of de beheerder",
     ["MC-08", "MC-11", "MC-14", "MC-22", "MC-30", "MC-31"]),
]
ACTORS = {"Bezoeker": ["UC-01"], "Gebruiker": [f"UC-{n:02d}" for n in range(2, 10)], "Beheerder": ["UC-10", "UC-11"], "Red Teamer": ["UC-12"], "Blue Teamer": ["UC-11"]}


# Elk blok in entries.md dat begint met "### <prefix>-".
def blocks(prefix):
    for block in re.split(r"\n(?=### )", ENTRIES):
        m = re.match(rf"### ({prefix}-\d+) (.*)", block)
        if m:
            yield m.group(1), m.group(2).strip(), block


def field(block, name):
    m = re.search(rf"^- {name}: (.*)$", block, re.M)
    return m.group(1) if m else ""


# "UC-01 tot UC-03", "UC-02, UC-04" of "alle" naar een lijst use cases.
def use_cases_of(text, all_ucs):
    if text.strip().startswith("alle"):
        return list(all_ucs)
    found = []
    for a, b in re.findall(r"UC-(\d+)(?: tot UC-(\d+))?", text):
        found += [f"UC-{n:02d}" for n in range(int(a), int(b or a) + 1)]
    return found


UC = {i: name.replace("`", "") for i, name, _ in blocks("UC")}
MIT = {i: name.replace("`", "") for i, name, _ in blocks("MIT")}
MC = {i: {"name": name.replace("`", ""), "ucs": use_cases_of(field(b, "Gerelateerde use case"), UC),
          "whole": bool(re.search(r"\btot\b|^alle", field(b, "Gerelateerde use case"))),
          "mits": sorted(set(re.findall(r"MIT-\d+", field(b, "Mitigaties"))), key=lambda m: int(m[4:]))}
      for i, name, b in blocks("MC")}
# Het risico van nu: de vierde kolom van de tabel per misuse case.
RISK = {m: int(r) for m, r in re.findall(r"^\| (MC-\d+) \| [^|]* \| \d × \d = \d \| \d × \d = (\d) \|", MATRIX, re.M)}
assert set(RISK) == set(MC), sorted(set(MC) ^ set(RISK))
assert sorted(m for g in GROUPS for m in g[3]) == sorted(MC), "elke misuse case in precies één diagram"


def level(r):
    return "laag" if r <= 2 else "midden" if r <= 4 else "hoog"


def esc(s):
    return html.escape(s, quote=True)


# Woorden over regels verdelen, op ongeveer zoveel tekens per regel.
def wrap(text, width):
    lines, cur = [], ""
    for word in text.split():
        if cur and len(cur) + 1 + len(word) > width:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    return lines + [cur] if cur else lines


class Svg:
    def __init__(self, width, height, title):
        self.w, self.h, self.parts = width, height, []
        self.parts.append(f'<rect width="{width}" height="{height}" fill="#ffffff"/>')
        self.text(24, 34, title, size=19, weight="600")

    def text(self, x, y, s, size=13, weight="normal", fill="#1a1a1a", anchor="start", style=""):
        self.parts.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
                          f'text-anchor="{anchor}" font-family="{FONT}"{style}>{esc(s)}</text>')

    def lines_in(self, cx, cy, lines, size, fill, first_bold=True):
        top = cy - (len(lines) - 1) * size * 0.62
        for n, line in enumerate(lines):
            self.text(cx, top + n * size * 1.24 + size * 0.35, line, size=size, fill=fill, anchor="middle",
                      weight="600" if first_bold and n == 0 else "normal")

    def ellipse(self, cx, cy, w, h, fill, stroke):
        self.parts.append(f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{w / 2:.1f}" ry="{h / 2:.1f}" fill="{fill}" '
                          f'stroke="{stroke}" stroke-width="1.5"/>')

    def line(self, x1, y1, x2, y2, dashed=False, arrow=False, color="#444"):
        dash = ' stroke-dasharray="6 4"' if dashed else ""
        head = ' marker-end="url(#open)"' if arrow else ""
        self.parts.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" '
                          f'stroke-width="1.3"{dash}{head}/>')

    def rect(self, x, y, w, h, label):
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="#fafafa" stroke="#666" stroke-width="1.3"/>')
        self.text(x + 12, y + 22, label, size=13, weight="600", fill="#444")

    # Een poppetje; zwart voor een aanvaller (misuser), zoals bij Sindre en Opdahl.
    def actor(self, x, y, label, misuser=False):
        c = "#111" if misuser else "#333"
        fill = "#111" if misuser else "#fff"
        self.parts.append(f'<circle cx="{x}" cy="{y - 30}" r="10" fill="{fill}" stroke="{c}" stroke-width="1.6"/>')
        body = (f"M{x},{y - 20} L{x},{y + 8} M{x - 16},{y - 10} L{x + 16},{y - 10} "
                f"M{x},{y + 8} L{x - 13},{y + 30} M{x},{y + 8} L{x + 13},{y + 30}")
        self.parts.append(f'<path d="{body}" fill="none" stroke="{c}" stroke-width="{3 if misuser else 1.6}"/>')
        for n, line in enumerate(wrap(label, 18)):
            self.text(x, y + 50 + n * 16, line, size=13, weight="600", anchor="middle")

    def save(self, name):
        defs = ('<defs><marker id="open" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" '
                'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10" fill="none" stroke="#444" stroke-width="1.5"/></marker></defs>')
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}">'
               f'{defs}{"".join(self.parts)}</svg>\n')
        (HERE / f"{name}.svg").write_text(svg, encoding="utf-8", newline="\n")
        print("geschreven:", f"{name}.svg")


# Een use case: wit, met ID en naam.
def draw_uc(svg, cx, cy, uc, w=260, h=58):
    svg.ellipse(cx, cy, w, h, "#ffffff", "#333")
    svg.lines_in(cx, cy, [uc] + wrap(UC[uc], 30)[:2], 12, "#1a1a1a")


def use_case_diagram():
    ucs = [f"UC-{n:02d}" for n in range(1, 10)] + ["UC-12"]
    row, top = 74, 90
    height = top + row * len(ucs) + 40
    svg = Svg(1100, height, "Use cases van de notitie-app")
    svg.rect(200, 60, 360, row * len(ucs) + 30, "Notitie-app")
    svg.rect(640, 60, 330, 260, "Uitrol en beheer: GitHub en Azure")
    pos = {}
    for n, uc in enumerate(ucs):
        pos[uc] = (380, top + 20 + n * row)
    pos["UC-10"], pos["UC-11"] = (805, 150), (805, 250)
    actors = {"Bezoeker": (80, pos["UC-01"][1] + 10), "Gebruiker": (80, top + row * 5), "Beheerder": (1030, 230), "Red Teamer": (80, pos["UC-12"][1] + 10), "Blue Teamer": (1030, 370)}
    for actor, (ax, ay) in actors.items():
        for uc in ACTORS[actor]:
            ux, uy = pos[uc]
            if actor == "Beheerder":
                svg.line(ax - 18, ay - 10, ux + 130, uy)
            else:
                svg.line(ax + 18, ay - 10, ux - 130, uy)
        svg.actor(ax, ay, actor)
    for uc, (x, y) in pos.items():
        draw_uc(svg, x, y, uc)
    svg.save("use-cases")


def misuse_diagram(name, title, misuser, mcs):
    mcs = sorted(mcs, key=lambda m: (int(MC[m]["ucs"][0][3:]) if not MC[m]["whole"] else 99, int(m[3:])))
    ucs = sorted({u for m in mcs for u in MC[m]["ucs"] if not MC[m]["whole"]}, key=lambda u: int(u[3:]))
    row, top = 118, 100
    height = max(top + row * len(mcs), top + 80 * len(ucs)) + 30
    mits = sorted({x for m in mcs for x in MC[m]["mits"]}, key=lambda m: int(m[4:]))
    legend_lines = [f"{m}  {MIT[m]}" for m in mits]
    legend_h = 40 + 17 * len(legend_lines) + 30
    svg = Svg(1240, height + legend_h, title)
    box_x, box_w = 150, 330
    svg.rect(box_x, 60, box_w, height - 70, "Notitie-app")
    mc_x, mc_w, mc_h = 750, 300, 62
    mc_pos = {m: (mc_x, top + 30 + n * row) for n, m in enumerate(mcs)}
    span = (top + 30, top + 30 + row * (len(mcs) - 1))
    uc_pos, last = {}, None
    for uc in ucs:
        ys = [mc_pos[m][1] for m in mcs if uc in MC[m]["ucs"] and not MC[m]["whole"]]
        y = sum(ys) / len(ys)
        y = y if last is None else max(y, last + 78)
        uc_pos[uc], last = (box_x + box_w / 2 + 10, y), y
    # De gewone actoren links, bij hun use cases.
    for actor, own in ACTORS.items():
        mine = [u for u in ucs if u in own]
        if not mine:
            continue
        ay = sum(uc_pos[u][1] for u in mine) / len(mine)
        for u in mine:
            svg.line(78, ay - 10, uc_pos[u][0] - 130, uc_pos[u][1])
        svg.actor(60, ay, actor)
    for uc, (x, y) in uc_pos.items():
        draw_uc(svg, x, y, uc)
    # Misuse cases: zwart, met «threatens» naar de use case en de maatregelen eronder («mitigates»).
    for m, (x, y) in mc_pos.items():
        targets = MC[m]["ucs"]
        if MC[m]["whole"]:
            svg.line(x - mc_w / 2, y, box_x + box_w, y, dashed=True, arrow=True)
            label = "alle use cases" if len(targets) == len(UC) else f"{targets[0]} tot {targets[-1]}"
            svg.text(box_x + box_w + 8, y - 22, "«threatens»", size=10.5, fill="#444", style=HALO)
            svg.text(box_x + box_w + 8, y - 8, label, size=10.5, fill="#444", style=HALO)
        else:
            for u in targets:
                ux, uy = uc_pos[u]
                svg.line(x - mc_w / 2, y, ux + 130, uy, dashed=True, arrow=True)
            svg.text(x - mc_w / 2 - 6, y - 8, "«threatens»", size=10.5, fill="#444", anchor="end", style=HALO)
        svg.ellipse(x, y, mc_w, mc_h, "#161616", "#000")
        svg.lines_in(x, y, [m] + wrap(MC[m]["name"], 36)[:2], 12, "#ffffff")
        r = RISK[m]
        bx, by = x + mc_w / 2 - 14, y - mc_h / 2 + 2
        svg.parts.append(f'<circle cx="{bx}" cy="{by}" r="14" fill="{RISK_COLOR[level(r)]}" stroke="#fff" stroke-width="2"/>')
        svg.text(bx, by + 4.5, str(r), size=13, weight="700", fill="#fff", anchor="middle")
        if MC[m]["mits"]:
            my = y + mc_h / 2 + 34
            text = " · ".join(MC[m]["mits"])
            svg.ellipse(x, my, max(170, 7.2 * len(text) + 30), 30, "#e8f1fb", "#4a7bb7")
            svg.text(x, my + 4, text, size=11.5, anchor="middle", fill="#1a3a5c")
            svg.line(x, my - 15, x, y + mc_h / 2 + 1, dashed=True, arrow=True, color="#4a7bb7")
            svg.text(x + 8, y + mc_h / 2 + 14, "«mitigates»", size=10.5, fill="#4a7bb7", style=HALO)
        svg.line(1120 - 18, (span[0] + span[1]) / 2 - 10, x + mc_w / 2, y)
    svg.actor(1120, (span[0] + span[1]) / 2, misuser, misuser=True)
    # Legenda: de maatregelen met hun naam uit entries.md, en de kleuren van het risico.
    ly = height + 10
    svg.text(24, ly + 6, "Maatregelen (MIT) in dit diagram", size=13, weight="600")
    for n, line in enumerate(legend_lines):
        svg.text(24, ly + 28 + n * 17, line, size=12, fill="#333")
    lx = 760
    svg.text(lx, ly + 6, "Risico nu (risk-matrix.md)", size=13, weight="600")
    for n, (lvl, c) in enumerate(RISK_COLOR.items()):
        svg.parts.append(f'<circle cx="{lx + 10}" cy="{ly + 24 + n * 22}" r="9" fill="{c}"/>')
        svg.text(lx + 26, ly + 29 + n * 22, {"laag": "1 of 2: laag", "midden": "3 of 4: midden", "hoog": "6 of 9: hoog"}[lvl], size=12)
    svg.save(name)


use_case_diagram()
for group in GROUPS:
    misuse_diagram(*group)
