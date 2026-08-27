"""Sorties de fabrication et de controle via kicad-cli.

Produit dans hw/fab :
  gerbers + percage (reglages JLCPCB), fichier de placement CPL, nomenclature,
  modele STEP pour Fusion 360, rendus PNG, PDF du schema.
"""
import os
import shutil
import subprocess
import sys
import zipfile

import kicadpath

KICAD = kicadpath.cli()
HW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hw")
FAB = os.path.join(HW, "fab")
PCB = os.path.join(HW, "cube.kicad_pcb")
SCH = os.path.join(HW, "cube.kicad_sch")

GERBER_LAYERS = ("F.Cu,In1.Cu,In2.Cu,B.Cu,"
                 "F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts")


def run(args, label):
    r = subprocess.run([KICAD] + args, capture_output=True, text=True)
    ok = r.returncode == 0
    print(("  OK   " if ok else "  ECHEC ") + label)
    if not ok:
        print("      " + (r.stderr or r.stdout).strip().replace("\n", "\n      ")[:500])
    return ok


def main():
    if os.path.isdir(FAB):
        shutil.rmtree(FAB)
    os.makedirs(FAB)
    gdir = os.path.join(FAB, "gerber")
    os.makedirs(gdir)

    print("Fabrication :")
    run(["pcb", "export", "gerbers", "--output", gdir + os.sep,
         "--layers", GERBER_LAYERS, "--no-protel-ext",
         "--subtract-soldermask", "--use-drill-file-origin", PCB], "gerbers")
    run(["pcb", "export", "drill", "--output", gdir + os.sep,
         "--format", "excellon", "--drill-origin", "plot",
         "--excellon-units", "mm", "--excellon-separate-th",
         "--generate-map", "--map-format", "gerberx2", PCB], "percage")
    run(["pcb", "export", "pos", "--output", os.path.join(FAB, "cube-cpl-top.csv"),
         "--format", "csv", "--units", "mm", "--side", "front",
         "--use-drill-file-origin", PCB], "fichier de placement (CPL)")

    print("Controle et mecanique :")
    run(["pcb", "export", "step", "--output", os.path.join(FAB, "cube.step"),
         "--subst-models", "--no-dnp", PCB], "modele STEP (Fusion 360)")
    run(["pcb", "render", "--output", os.path.join(FAB, "cube-dessus.png"),
         "--side", "top", "--width", "1400", "--height", "1500",
         "--quality", "high", "--background", "opaque", PCB], "rendu dessus")
    run(["pcb", "render", "--output", os.path.join(FAB, "cube-dessous.png"),
         "--side", "bottom", "--width", "1400", "--height", "1500",
         "--quality", "high", "--background", "opaque", PCB], "rendu dessous")
    # Rendus a fond transparent pour le README : ils restent lisibles en theme
    # clair comme en theme sombre, contrairement a un fond opaque.
    media = os.path.join(os.path.dirname(FAB), "..", "docs", "media")
    media = os.path.normpath(media)
    os.makedirs(media, exist_ok=True)
    for side, name in (("top", "board-top"), ("bottom", "board-bottom")):
        run(["pcb", "render", "--output", os.path.join(media, name + ".png"),
             "--side", side, "--width", "1100", "--height", "1180",
             "--quality", "high", "--background", "transparent", PCB],
            "rendu %s (fond transparent, docs/media)" % side)

    run(["pcb", "export", "pdf", "--output", os.path.join(FAB, "cube-implantation.pdf"),
         "--layers", "F.Cu,F.SilkS,F.Mask,Edge.Cuts", "--include-border-title", PCB],
        "plan d'implantation")
    run(["sch", "export", "pdf", "--output", os.path.join(FAB, "cube-schema.pdf"), SCH],
        "schema PDF")
    run(["sch", "export", "bom", "--output", os.path.join(FAB, "cube-bom.csv"),
         "--fields", "Reference,Value,Footprint,MPN,Description,${QUANTITY}",
         "--group-by", "Value,Footprint,MPN", SCH], "nomenclature")

    # archive prete a envoyer au fabricant
    zpath = os.path.join(FAB, "cube-gerbers-jlcpcb.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(gdir)):
            z.write(os.path.join(gdir, f), f)
    print("  OK   archive %s (%d fichiers)" %
          (os.path.basename(zpath), len(os.listdir(gdir))))

    print("\nContenu de hw/fab :")
    for f in sorted(os.listdir(FAB)):
        p = os.path.join(FAB, f)
        if os.path.isfile(p):
            print("   %-32s %8.0f Ko" % (f, os.path.getsize(p) / 1024))
        else:
            print("   %-32s (%d fichiers)" % (f + os.sep, len(os.listdir(p))))


if __name__ == "__main__":
    sys.exit(main())
