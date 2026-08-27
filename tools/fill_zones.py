"""Remplit les zones de cuivre avec le moteur officiel de KiCad et sauvegarde.

A lancer avec le Python embarque de KiCad :
    "C:\\Program Files\\KiCad\\9.0\\bin\\python.exe" tools/fill_zones.py

Sans cette etape, kicad-cli voit les zones vides et signale comme "non
connectees" toutes les pastilles de masse qui comptent sur le plan.
"""
import os
import sys

import pcbnew

HW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hw")
PCB = os.path.join(HW, "cube.kicad_pcb")


def main():
    board = pcbnew.LoadBoard(PCB)
    zones = board.Zones()
    print("zones : %d" % len(zones))

    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(zones)
    board.BuildConnectivity()

    conn = board.GetConnectivity()
    unconn = conn.GetUnconnectedCount(True)
    print("liaisons restantes (chevelu) : %d" % unconn)

    # detail par net des pastilles encore isolees
    ratsnest = {}
    for net in board.GetNetsByNetcode().values():
        code = net.GetNetCode()
        if code == 0:
            continue
        n = conn.GetRatsnestForNet(code)
        if n:
            cnt = n.GetEdges().size() if hasattr(n, "GetEdges") else 0
            if cnt:
                ratsnest[net.GetNetname()] = cnt
    if ratsnest:
        print("par net : %s" % dict(sorted(ratsnest.items(),
                                           key=lambda kv: -kv[1])))

    pcbnew.SaveBoard(PCB, board)
    print("carte sauvegardee (%d octets)" % os.path.getsize(PCB))
    return 0


if __name__ == "__main__":
    sys.exit(main())
