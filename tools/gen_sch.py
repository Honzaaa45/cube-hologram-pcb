"""Genere hw/cube.kicad_sch a partir de design.py.

Style : chaque broche recoit un troncon de fil court termine par une etiquette
de net (ou un symbole d'alimentation). C'est le style "net labels", lisible et
surtout genere de facon deterministe et verifiable.
"""
import os
import uuid as _uuid
import datetime

import sexpr
import symlib
import design as D
from sexpr import Sym, find, first

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(os.path.dirname(HERE), "hw")
GRID = 1.27
STUB = 2.54          # longueur du troncon de fil sur chaque broche
FONT = 1.27

_seen_uuid = {}


def uid(key=None):
    """UUID stable si une cle est fournie -> regeneration reproductible."""
    if key is None:
        return str(_uuid.uuid4())
    if key not in _seen_uuid:
        _seen_uuid[key] = str(_uuid.uuid5(_uuid.NAMESPACE_URL, "cube/" + key))
    return _seen_uuid[key]


def snap(v):
    return round(round(v / GRID) * GRID, 4)


# --------------------------------------------------------------------------
# Symboles
# --------------------------------------------------------------------------
def build_custom_symbol(name, spec):
    """Construit un symbole KiCad pour le lecteur microSD maison."""
    left = [p for p in spec["pins"] if p[3] == "L"]
    right = [p for p in spec["pins"] if p[3] == "R"]
    rows = max(len(left), len(right))
    half_h = (rows + 1) * GRID
    hw = 8.89  # demi-largeur du corps

    body = [Sym("symbol"), name + "_0_1",
            [Sym("rectangle"),
             [Sym("start"), Sym("%g" % -hw), Sym("%g" % half_h)],
             [Sym("end"), Sym("%g" % hw), Sym("%g" % -half_h)],
             [Sym("stroke"), [Sym("width"), Sym("0.254")], [Sym("type"), Sym("default")]],
             [Sym("fill"), [Sym("type"), Sym("background")]]]]

    unit = [Sym("symbol"), name + "_1_1"]
    for side, lst, xpos, ang in (("L", left, -hw - 2.54, 0), ("R", right, hw + 2.54, 180)):
        y = (len(lst) - 1) * GRID
        for num, pname, ptype, _ in lst:
            unit.append([
                Sym("pin"), Sym(ptype), Sym("line"),
                [Sym("at"), Sym("%g" % xpos), Sym("%g" % y), Sym(str(ang))],
                [Sym("length"), Sym("2.54")],
                [Sym("name"), pname, [Sym("effects"), [Sym("font"),
                    [Sym("size"), Sym("1.27"), Sym("1.27")]]]],
                [Sym("number"), num, [Sym("effects"), [Sym("font"),
                    [Sym("size"), Sym("1.27"), Sym("1.27")]]]],
            ])
            y -= 2 * GRID

    sym = [Sym("symbol"), name,
           [Sym("pin_names"), [Sym("offset"), Sym("1.016")]],
           [Sym("exclude_from_sim"), Sym("no")],
           [Sym("in_bom"), Sym("yes")],
           [Sym("on_board"), Sym("yes")]]
    for pname, pval, hide in (("Reference", "J", False), ("Value", name, False),
                              ("Footprint", spec["fp"], True), ("Datasheet", "", True),
                              ("Description", spec["desc"], True)):
        eff = [Sym("effects"), [Sym("font"), [Sym("size"), Sym("1.27"), Sym("1.27")]]]
        if hide:
            eff.append([Sym("hide"), Sym("yes")])
        sym.append([Sym("property"), pname, pval,
                    [Sym("at"), Sym("0"), Sym("%g" % (half_h + 2.54)), Sym("0")], eff])
    sym.append(body)
    sym.append(unit)
    return sym


def lib_symbol_node(lib, name):
    """Definition complete d'un symbole, renommee 'Lib:Name' pour lib_symbols."""
    if lib == "cube":
        node = build_custom_symbol(name, D.CUSTOM_SYMBOLS[name])
    else:
        node = symlib.get_symbol(lib, name)
    out = [Sym("symbol"), "%s:%s" % (lib, name)]
    for c in node[2:]:
        out.append(c)
    return out


def sym_pins(lib, name):
    """[(numero, nom, type, (sx, sy), angle)] en coordonnees symbole."""
    node = lib_symbol_node(lib, name)
    res = []
    for u in find(node, Sym("symbol")):
        for p in find(u, Sym("pin")):
            at = first(p, Sym("at"))
            res.append((first(p, Sym("number"))[1], first(p, Sym("name"))[1],
                        str(p[1]), (float(at[1]), float(at[2])),
                        int(float(at[3])) if len(at) > 3 else 0))
    return res


def sym_bbox(lib, name):
    """Boite englobante approximative (corps + broches) en coordonnees symbole."""
    node = lib_symbol_node(lib, name)
    xs, ys = [], []

    def scan(n):
        if not isinstance(n, list) or not n:
            return
        tag = n[0]
        if tag in (Sym("start"), Sym("end"), Sym("mid"), Sym("center"), Sym("xy")):
            try:
                xs.append(float(n[1])); ys.append(float(n[2]))
            except (ValueError, IndexError):
                pass
        for c in n:
            if isinstance(c, list):
                scan(c)

    for u in find(node, Sym("symbol")):
        for g in u[2:]:
            if isinstance(g, list) and g[0] != Sym("pin"):
                scan(g)
        for p in find(u, Sym("pin")):
            at = first(p, Sym("at"))
            xs.append(float(at[1])); ys.append(float(at[2]))
    if not xs:
        xs, ys = [-1.27, 1.27], [-1.27, 1.27]
    return min(xs), min(ys), max(xs), max(ys)


def pin_abs(part_xy, sxy):
    """Broche en coordonnees schema (l'axe Y du symbole est inverse)."""
    return (part_xy[0] + sxy[0], part_xy[1] - sxy[1])


# angle de broche -> (direction du troncon, angle d'etiquette)
STUB_DIR = {0: ((-1, 0), 180), 180: ((1, 0), 0), 90: ((0, 1), 270), 270: ((0, -1), 90)}


# --------------------------------------------------------------------------
# Placement des composants dans les blocs
# --------------------------------------------------------------------------
def layout():
    """ref -> (x, y). Rangement en etageres a l'interieur de chaque bloc."""
    pos = {}
    blocks = {b[0]: b for b in D.BLOCKS}
    by_block = {}
    for ref, p in D.PARTS.items():
        by_block.setdefault(p["block"], []).append(ref)

    for bid, refs in by_block.items():
        _, _, bx, by, bw, bh = blocks[bid]
        cx, cy = bx + 6, by + 12          # marge interne, sous le titre
        row_h = 0
        for ref in refs:
            p = D.PARTS[ref]
            x0, y0, x1, y1 = sym_bbox(p["lib"], p["sym"])
            pins = sym_pins(p["lib"], p["sym"])
            angs = {a for *_, a in pins}
            # marge pour les etiquettes de net
            ml = 23 if 0 in angs else 3
            mr = 23 if 180 in angs else 3
            mt = 9 if 270 in angs else 3
            mb = 9 if 90 in angs else 3
            w = (x1 - x0) + ml + mr
            h = (y1 - y0) + mt + mb
            if cx + w > bx + bw - 4 and cx > bx + 6:
                cx = bx + 6
                cy += row_h + 6
                row_h = 0
            # origine du symbole = coin haut-gauche de la cellule + marges
            pos[ref] = (snap(cx + ml - x0), snap(cy + mt + y1))
            cx += w + 6
            row_h = max(row_h, h)
    return pos


# --------------------------------------------------------------------------
# Generation
# --------------------------------------------------------------------------
def effects(size=FONT, justify=None, hide=False):
    e = [Sym("effects"), [Sym("font"), [Sym("size"), Sym("%g" % size), Sym("%g" % size)]]]
    if justify:
        e.append([Sym("justify")] + [Sym(j) for j in justify])
    if hide:
        e.append([Sym("hide"), Sym("yes")])
    return e


def wire(p1, p2, key):
    return [Sym("wire"),
            [Sym("pts"), [Sym("xy"), Sym("%g" % p1[0]), Sym("%g" % p1[1])],
             [Sym("xy"), Sym("%g" % p2[0]), Sym("%g" % p2[1])]],
            [Sym("stroke"), [Sym("width"), Sym("0")], [Sym("type"), Sym("default")]],
            [Sym("uuid"), uid(key)]]


def label(name, xy, angle, key):
    just = ["right", "bottom"] if angle == 180 else ["left", "bottom"]
    return [Sym("label"), name,
            [Sym("at"), Sym("%g" % xy[0]), Sym("%g" % xy[1]), Sym(str(angle))],
            effects(FONT, just), [Sym("uuid"), uid(key)]]


def build():
    root_uuid = uid("root-sheet")
    pos = layout()

    doc = [Sym("kicad_sch"),
           [Sym("version"), Sym("20250114")],
           [Sym("generator"), "eeschema"],
           [Sym("generator_version"), "9.0"],
           [Sym("uuid"), uid("doc")],
           [Sym("paper"), "A2"],
           [Sym("title_block"),
            [Sym("title"), D.TITLE],
            [Sym("date"), datetime.date.today().isoformat()],
            [Sym("rev"), D.REV],
            [Sym("comment"), Sym("1"), "ESP32-S3-WROOM-1U-N16R8 / AMOLED QSPI / microSD SDIO"],
            [Sym("comment"), Sym("2"), "GPIO35-37 reserves PSRAM octale : ne jamais utiliser"]]]

    # ---- lib_symbols ----
    used = sorted({(p["lib"], p["sym"]) for p in D.PARTS.values()} |
                  {tuple(v.split(":")) for v in D.POWER_NETS.values()} |
                  {("power", "PWR_FLAG")})
    libs = [Sym("lib_symbols")]
    for lib, name in used:
        libs.append(lib_symbol_node(lib, name))
    doc.append(libs)

    # ---- cadres et titres de blocs ----
    for bid, title, bx, by, bw, bh in D.BLOCKS:
        doc.append([Sym("rectangle"),
                    [Sym("start"), Sym("%g" % bx), Sym("%g" % by)],
                    [Sym("end"), Sym("%g" % (bx + bw)), Sym("%g" % (by + bh))],
                    [Sym("stroke"), [Sym("width"), Sym("0.254")], [Sym("type"), Sym("dash")]],
                    [Sym("fill"), [Sym("type"), Sym("none")]],
                    [Sym("uuid"), uid("rect-" + bid)]])
        doc.append([Sym("text"), title,
                    [Sym("at"), Sym("%g" % (bx + 3)), Sym("%g" % (by + 6)), Sym("0")],
                    effects(2.5, ["left", "bottom"]),
                    [Sym("uuid"), uid("txt-" + bid)]])

    # ---- table des broches par net (pour savoir quoi etiqueter) ----
    pin_net = {}
    for net, conns in D.NETS.items():
        for ref, pin in conns:
            pin_net[(ref, pin)] = net
    nc = set(D.NO_CONNECT)

    graphics, symbols = [], []

    for ref, p in D.PARTS.items():
        x, y = pos[ref]
        pins = sym_pins(p["lib"], p["sym"])
        x0, y0, x1, y1 = sym_bbox(p["lib"], p["sym"])

        # --- instance du symbole ---
        s = [Sym("symbol"),
             [Sym("lib_id"), "%s:%s" % (p["lib"], p["sym"])],
             [Sym("at"), Sym("%g" % x), Sym("%g" % y), Sym("0")],
             [Sym("unit"), Sym("1")],
             [Sym("exclude_from_sim"), Sym("no")],
             [Sym("in_bom"), Sym("yes")],
             [Sym("on_board"), Sym("yes")],
             [Sym("dnp"), Sym("yes" if p["dnp"] else "no")],
             [Sym("uuid"), uid("sym-" + ref)]]
        ref_y = y - y1 - 2.0
        val_y = y - y0 + 2.0
        fields = [("Reference", ref, ref_y, False),
                  ("Value", p["val"], val_y, False),
                  ("Footprint", p["fp"], val_y, True),
                  ("Datasheet", "~", val_y, True),
                  ("Description", p["desc"], val_y, True)]
        if p["mpn"]:
            fields.append(("MPN", p["mpn"], val_y, True))
        for fname, fval, fy, hide in fields:
            s.append([Sym("property"), fname, fval,
                      [Sym("at"), Sym("%g" % x), Sym("%g" % fy), Sym("0")],
                      effects(FONT, ["left"] if not hide else None, hide)])
        for num, *_ in pins:
            s.append([Sym("pin"), num, [Sym("uuid"), uid("pin-%s-%s" % (ref, num))]])
        s.append([Sym("instances"),
                  [Sym("project"), D.PROJECT,
                   [Sym("path"), "/" + root_uuid,
                    [Sym("reference"), ref], [Sym("unit"), Sym("1")]]]])
        symbols.append(s)

        # --- troncons + etiquettes ---
        for num, pname, ptype, sxy, ang in pins:
            px, py = pin_abs((x, y), sxy)
            (dx, dy), lab_ang = STUB_DIR.get(ang, ((-1, 0), 180))
            ex, ey = px + dx * STUB, py + dy * STUB
            key = "%s-%s" % (ref, num)

            if (ref, num) in nc:
                graphics.append([Sym("no_connect"),
                                 [Sym("at"), Sym("%g" % px), Sym("%g" % py)],
                                 [Sym("uuid"), uid("nc-" + key)]])
                continue

            net = pin_net.get((ref, num))
            if net is None:
                continue
            graphics.append(wire((px, py), (ex, ey), "w-" + key))

            if net in D.POWER_NETS:
                lib_id = D.POWER_NETS[net]
                # le symbole d'alim se connecte exactement sur son origine
                rot = 0 if net == "GND" else 0
                ps = [Sym("symbol"),
                      [Sym("lib_id"), lib_id],
                      [Sym("at"), Sym("%g" % ex), Sym("%g" % ey), Sym(str(rot))],
                      [Sym("unit"), Sym("1")],
                      [Sym("exclude_from_sim"), Sym("no")],
                      [Sym("in_bom"), Sym("yes")],
                      [Sym("on_board"), Sym("yes")],
                      [Sym("dnp"), Sym("no")],
                      [Sym("uuid"), uid("pwr-" + key)],
                      [Sym("property"), "Reference", "#PWR?",
                       [Sym("at"), Sym("%g" % ex), Sym("%g" % ey), Sym("0")],
                       effects(FONT, None, True)],
                      [Sym("property"), "Value", net,
                       [Sym("at"), Sym("%g" % ex),
                        Sym("%g" % (ey + (3.0 if net == "GND" else -3.0))), Sym("0")],
                       effects(FONT)],
                      [Sym("property"), "Footprint", "",
                       [Sym("at"), Sym("%g" % ex), Sym("%g" % ey), Sym("0")],
                       effects(FONT, None, True)],
                      [Sym("property"), "Datasheet", "",
                       [Sym("at"), Sym("%g" % ex), Sym("%g" % ey), Sym("0")],
                       effects(FONT, None, True)],
                      [Sym("pin"), "1", [Sym("uuid"), uid("pwrpin-" + key)]],
                      [Sym("instances"),
                       [Sym("project"), D.PROJECT,
                        [Sym("path"), "/" + root_uuid,
                         [Sym("reference"), "#PWR?"], [Sym("unit"), Sym("1")]]]]]
                symbols.append(ps)
            else:
                graphics.append(label(net, (ex, ey), lab_ang, "lab-" + key))

    # ---- PWR_FLAG : declare les rails comme alimentes (ERC) ----
    fx, fy = 20.32, 261.62
    for net in ("+5V", "+3V3", "GND", "VBUS", "VDD_AMP"):
        graphics.append(wire((fx, fy), (fx, fy - STUB), "pf-w-" + net))
        graphics.append(label(net, (fx, fy - STUB), 90, "pf-l-" + net))
        symbols.append([
            Sym("symbol"), [Sym("lib_id"), "power:PWR_FLAG"],
            [Sym("at"), Sym("%g" % fx), Sym("%g" % fy), Sym("0")],
            [Sym("unit"), Sym("1")],
            [Sym("exclude_from_sim"), Sym("no")], [Sym("in_bom"), Sym("yes")],
            [Sym("on_board"), Sym("yes")], [Sym("dnp"), Sym("no")],
            [Sym("uuid"), uid("pwrflag-" + net)],
            [Sym("property"), "Reference", "#FLG?",
             [Sym("at"), Sym("%g" % fx), Sym("%g" % fy), Sym("0")], effects(FONT, None, True)],
            [Sym("property"), "Value", "PWR_FLAG",
             [Sym("at"), Sym("%g" % fx), Sym("%g" % (fy + 3)), Sym("0")],
             effects(FONT, None, True)],
            [Sym("property"), "Footprint", "",
             [Sym("at"), Sym("%g" % fx), Sym("%g" % fy), Sym("0")], effects(FONT, None, True)],
            [Sym("property"), "Datasheet", "",
             [Sym("at"), Sym("%g" % fx), Sym("%g" % fy), Sym("0")], effects(FONT, None, True)],
            [Sym("pin"), "1", [Sym("uuid"), uid("pwrflagpin-" + net)]],
            [Sym("instances"), [Sym("project"), D.PROJECT,
                                [Sym("path"), "/" + root_uuid,
                                 [Sym("reference"), "#FLG?"], [Sym("unit"), Sym("1")]]]]])
        fx += 25.4

    doc.extend(graphics)
    doc.extend(symbols)
    doc.append([Sym("sheet_instances"), [Sym("path"), "/", [Sym("page"), "1"]]])
    doc.append([Sym("embedded_fonts"), Sym("no")])
    return doc, root_uuid


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    doc, root_uuid = build()
    path = os.path.join(OUT_DIR, D.PROJECT + ".kicad_sch")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(sexpr.dump(doc) + "\n")
    print("ecrit %s  (%d octets)" % (path, os.path.getsize(path)))
    return root_uuid


if __name__ == "__main__":
    main()
