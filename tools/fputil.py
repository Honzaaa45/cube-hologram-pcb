"""Utilitaires d'empreintes : contour de courtoisie, pastilles, rotation."""
import math

import symlib
from sexpr import Sym, find, first

_cy_cache = {}
_pad_cache = {}


def rot_pt(x, y, deg):
    """Rotation KiCad : angle positif = sens antihoraire a l'ecran.

    L'axe Y du PCB pointe vers le bas, donc une rotation antihoraire visuelle
    s'ecrit (x*cos + y*sin, -x*sin + y*cos). Verification : (1,0) a 90 deg
    doit donner (0,-1), c'est-a-dire "vers le haut" de l'ecran.
    """
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    return (x * c + y * s, -x * s + y * c)


def _collect_pts(node, want_layers):
    """Points des primitives graphiques posees sur l'une des couches voulues."""
    pts = []

    def walk(n):
        if not isinstance(n, list) or not n:
            return
        lay = first(n, Sym("layer"))
        if lay and len(lay) > 1 and str(lay[1]) in want_layers:
            for tag in (Sym("start"), Sym("end"), Sym("center"), Sym("mid")):
                for e in find(n, tag):
                    try:
                        pts.append((float(e[1]), float(e[2])))
                    except (ValueError, IndexError):
                        pass
            for pl in find(n, Sym("pts")):
                for e in find(pl, Sym("xy")):
                    pts.append((float(e[1]), float(e[2])))
            # cercle : englober le rayon
            if n[0] == Sym("fp_circle"):
                c = first(n, Sym("center")); e = first(n, Sym("end"))
                if c and e:
                    cx, cy = float(c[1]), float(c[2])
                    r = math.hypot(float(e[1]) - cx, float(e[2]) - cy)
                    pts.extend([(cx - r, cy - r), (cx + r, cy + r)])
        for c in n:
            if isinstance(c, list):
                walk(c)

    walk(node)
    return pts


def pads(fp_name):
    """[(numero, x, y, w, h, angle, type, couches, percage, forme)]."""
    if fp_name in _pad_cache:
        return _pad_cache[fp_name]
    f = symlib.load_footprint(fp_name)
    out = []
    for p in find(f, Sym("pad")):
        num = str(p[1])
        ptype = str(p[2])
        shape = str(p[3])
        at = first(p, Sym("at"))
        size = first(p, Sym("size"))
        layers = [str(x) for x in first(p, Sym("layers"))[1:]]
        dr = first(p, Sym("drill"))
        drill = 0.0
        if dr:
            vals = [x for x in dr[1:] if not isinstance(x, list) and str(x) != "oval"]
            if vals:
                drill = max(float(v) for v in vals)
        out.append((num, float(at[1]), float(at[2]),
                    float(size[1]), float(size[2]),
                    float(at[3]) if len(at) > 3 else 0.0, ptype, layers, drill, shape))
    _pad_cache[fp_name] = out
    return out


def courtyard_box(fp_name, rot=0.0, pad_margin=0.25):
    """Boite englobante du contour de courtoisie (ou des pastilles), tournee."""
    key = (fp_name, rot, pad_margin)
    if key in _cy_cache:
        return _cy_cache[key]
    f = symlib.load_footprint(fp_name)
    pts = _collect_pts(f, {"F.CrtYd", "B.CrtYd"})
    if not pts:
        for _, x, y, w, h, a, _, _, _, _ in pads(fp_name):
            hw, hh = w / 2 + pad_margin, h / 2 + pad_margin
            for dx, dy in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)):
                lx, ly = rot_pt(dx, dy, a)
                pts.append((x + lx, y + ly))
    if not pts:
        pts = [(-0.5, -0.5), (0.5, 0.5)]
    rp = [rot_pt(x, y, rot) for x, y in pts]
    box = (min(p[0] for p in rp), min(p[1] for p in rp),
           max(p[0] for p in rp), max(p[1] for p in rp))
    _cy_cache[key] = box
    return box


def pad_box(fp_name, rot=0.0, margin=0.0):
    """Boite englobante des pastilles seules (utile pour le contour de carte)."""
    ps = pads(fp_name)
    if not ps:
        return (0.0, 0.0, 0.0, 0.0)
    pts = []
    for _, x, y, w, h, a, _, _, _, _ in ps:
        hw, hh = w / 2 + margin, h / 2 + margin
        for dx, dy in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)):
            lx, ly = rot_pt(dx, dy, a)
            pts.append(rot_pt(x + lx, y + ly, rot))
    return (min(p[0] for p in pts), min(p[1] for p in pts),
            max(p[0] for p in pts), max(p[1] for p in pts))


def abs_pads(fp_name, at_x, at_y, rot):
    """Pastilles en coordonnees carte, percage inclus."""
    out = []
    for num, x, y, w, h, a, ptype, layers, drill, shape in pads(fp_name):
        rx, ry = rot_pt(x, y, rot)
        out.append((num, at_x + rx, at_y + ry, w, h, (a + rot) % 360.0,
                    ptype, layers, drill, shape))
    return out
