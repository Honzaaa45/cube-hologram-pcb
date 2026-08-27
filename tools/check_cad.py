"""Verrou de non-regression sur la CAO : lance l'ERC et le DRC de KiCad et
verifie que les resultats ne se degradent pas.

Les seuils ci-dessous decrivent l'etat verifie du projet. Ameliorer est
autorise (les controles sont des maximums), regresser fait echouer la CI.

    python tools/check_cad.py
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kicadpath  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HW = os.path.join(ROOT, "hw")
SCH = os.path.join(HW, "cube.kicad_sch")
PCB = os.path.join(HW, "cube.kicad_pcb")

# Etat verifie le 2026-08-27 (voir README, section « Etat verifie »).
MAX_ERC_ERRORS = 0
MAX_ERC_WARNINGS = 1      # pad thermique du MAX98357A type « Unspecified » en librairie
MAX_DRC_VIOLATIONS = 0
MAX_UNCONNECTED = 0       # carte entierement routee depuis le 2026-08-27
MAX_PARITY = 0

FAILS = []


def run(args):
    r = subprocess.run([kicadpath.cli()] + args, capture_output=True, text=True)
    return (r.stdout or "") + (r.stderr or "")


def num(pattern, text, default=None):
    m = re.search(pattern, text)
    return int(m.group(1)) if m else default


def check(label, value, limit):
    ok = value is not None and value <= limit
    print("  %-46s %s (max %d)%s"
          % (label, "?" if value is None else value, limit,
             "" if ok else "   <-- ECHEC"))
    if not ok:
        FAILS.append(label)


def main():
    print("ERC")
    erc = os.path.join(HW, "erc.rpt")
    run(["sch", "erc", "--severity-all", "--output", erc, SCH])
    txt = open(erc, encoding="utf-8", errors="replace").read()
    # KiCad ecrit le bilan en anglais ou en francais selon la locale.
    errors = num(r"(?:Errors|Erreurs)\s+(\d+)", txt)
    warns = num(r"(?:Warnings|Avertissements)\s+(\d+)", txt)
    check("erreurs", errors, MAX_ERC_ERRORS)
    check("avertissements", warns, MAX_ERC_WARNINGS)

    print("DRC + parite schema/PCB")
    drc = os.path.join(HW, "drc.rpt")
    run(["pcb", "drc", "--schematic-parity", "--severity-error",
         "--format", "report", "--output", drc, PCB])
    txt = open(drc, encoding="utf-8", errors="replace").read()
    viol = num(r"(?:Found|Trouv\S*)\s+(\d+)\s+DRC", txt)
    unco = num(r"(?:Found|Trouv\S*)\s+(\d+)\s+unconnected", txt)
    if unco is None:
        unco = len(re.findall(r"\[unconnected_items\]", txt))
    par = num(r"(?:Found|Trouv\S*)\s+(\d+)\s+schematic parity", txt)
    if par is None:
        par = len(re.findall(r"\[schematic_parity\]", txt))
    check("violations DRC", viol, MAX_DRC_VIOLATIONS)
    check("liaisons non routees", unco, MAX_UNCONNECTED)
    check("ecarts schema/PCB", par, MAX_PARITY)

    print()
    if FAILS:
        print("ECHEC : %s" % ", ".join(FAILS))
        return 1
    print("CAO conforme a l'etat verifie.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
