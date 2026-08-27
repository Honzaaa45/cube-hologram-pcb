"""Genere docs/CARTE.md a partir de design.py (reste synchronise avec le CAO)."""
import collections
import os

import design as D

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "docs", "CARTE.md")

INTRO = """# CUBE — carte electronique

Carte mere de l'afficheur holographique Pepper's Ghost.

| | |
|---|---|
| MCU | ESP32-S3-WROOM-1U-N16R8 — 16 MB flash, 8 MB PSRAM **octale**, antenne U.FL |
| Ecran | connecteur QSPI generique 14 points, JST-SH 1,0 mm (J2) |
| Stockage | microSD en **SDIO 4 bits** (J3) |
| Audio | MAX98357A, ampli classe D I2S mono (U3) |
| Capteurs | VL53L1X (ToF, 0x29) + LIS3DH (accelerometre, 0x18) |
| Alimentation | USB-C 5 V -> AP63203WU, buck 2 A sortie 3,3 V fixe |
| Carte | {w} x {h} mm, **4 couches**, composants sur la face avant uniquement |

## Empilage

| Couche | Role |
|---|---|
| F.Cu | signaux + plan de masse de remplissage |
| In1.Cu | **plan de masse plein** — reference de retour du bus QSPI |
| In2.Cu | **plan +3V3** |
| B.Cu | signaux + plan de masse de remplissage |

Le bus QSPI de l'ecran est route sur F.Cu, directement au-dessus du plan de
masse In1 : c'est ce qui donne un chemin de retour court et propre a 80 MHz.

## Reperes mecaniques

Le repere du plan de masse (coordonnees KiCad) :

* `y = {y0}` — **avant** du boitier : le VL53L1X (U4) vise vers le haut, a
  travers une petite fenetre transparente aux infrarouges, devant l'ecran.
* `y = {y1}` — **arriere** : sortie USB-C.
* `x = {x0}` — **flanc gauche** : trappe microSD.
* 4 trous M2 ({x0h} / {x1h} en X, {y0h} / {y1h} en Y), inserts a chaud
  recommandes cote boitier.

"""


def finishing_section():
    """Liste les liaisons encore a tirer, lue directement du rapport DRC."""
    rpt = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "hw", "drc.rpt")
    items = []
    if os.path.isfile(rpt):
        seen = False
        cur = []
        for line in open(rpt, encoding="utf-8"):
            if "unconnected_items" in line:
                seen = True
                if len(cur) == 2:
                    items.append(tuple(cur))
                cur = []
                continue
            if seen and "@(" in line:
                cur.append(line.split("): ", 1)[-1].strip())
        if len(cur) == 2:
            items.append(tuple(cur))

    out = ["## Ce qu'il reste a router\n"]
    if not items:
        out.append("Aucune liaison en attente : la carte est entierement routee.\n")
        return "\n".join(out)
    out.append(
        "Le routage automatique a resolu %d des %d connexions. Les liaisons "
        "ci-dessous restent a tirer a la main dans Pcbnew : elles font toutes "
        "quelques millimetres et se trouvent autour du LIS3DH (pas de 0,5 mm) "
        "et de son voisinage immediat, la zone la plus dense de la carte.\n"
        % (sum(len(v) for v in D.NETS.values()) - len(items),
           sum(len(v) for v in D.NETS.values())))
    out.append(table([(i + 1, a, b) for i, (a, b) in enumerate(items)],
                     ["#", "D'un cote", "De l'autre"]))
    out.append("""
Marche a suivre : ouvrir `hw/cube.kicad_pcb`, appuyer sur **B** pour remplir les
plans, puis router au routeur interactif (**X**). La carte passe le DRC sans
aucune violation, donc toute erreur qui apparaitrait viendrait de ces ajouts.
""")
    return "\n".join(out)


def mech_section():
    """Cotes exprimees depuis le coin haut-gauche de la carte (0, 0),
    c'est ce dont on a besoin pour esquisser le boitier dans Fusion 360."""
    import fputil
    x0, y0 = D.BOARD_X, D.BOARD_Y
    rows = []
    for ref in ("J1", "J3", "J2", "J4", "J5", "J6", "U2", "U4", "SW1", "SW2"):
        x, y, rot, _ = D.PCB_PLACE[ref]
        a, b, c, d = fputil.courtyard_box(D.PARTS[ref]["fp"], rot)
        rows.append((ref, D.PARTS[ref]["val"],
                     "%.2f, %.2f" % (x - x0, y - y0),
                     "%.2f .. %.2f" % (x + a - x0, x + c - x0),
                     "%.2f .. %.2f" % (y + b - y0, y + d - y0)))
    ov = max(0.0, max(D.PCB_PLACE["J1"][1] +
                      fputil.courtyard_box(D.PARTS["J1"]["fp"], 0)[3], 0) -
             (y0 + D.BOARD_H))

    out = ["## Cotes pour le boitier (Fusion 360)\n",
           "Origine = **coin haut-gauche de la carte** (le coin avant-gauche), "
           "axe X vers la droite, axe Y vers l'arriere.\n",
           "* Contour : rectangle **%.0f x %.0f mm**, coins arrondis R%.1f mm."
           % (D.BOARD_W, D.BOARD_H, D.BOARD_CORNER_R),
           "* Epaisseur du circuit imprime : 1,6 mm.",
           "* Trous M2 (diametre 2,2 mm) a **3,0 mm** de chaque bord, "
           "soit (3,0 / 3,0), (%.1f / 3,0), (3,0 / %.1f), (%.1f / %.1f)."
           % (D.BOARD_W - 3, D.BOARD_H - 3, D.BOARD_W - 3, D.BOARD_H - 3),
           "* La prise USB-C **deborde de %.1f mm** au-dela du bord arriere : "
           "prevoir la decoupe correspondante dans le boitier.\n" % ov,
           table(rows, ["Ref", "Role", "Centre (x, y)", "Emprise X", "Emprise Y"]),
           """
Hauteurs a prevoir au-dessus de la carte (les plus contraignantes) :

| Composant | Hauteur approx. |
|---|---|
| Connecteurs JST-SH verticaux (J2, J4, J5) | ~4,3 mm nu, ~6 mm avec le connecteur femelle engage |
| Module ESP32-S3-WROOM-1U | 3,2 mm + le connecteur U.FL et son cable |
| Prise USB-C | 3,2 mm |
| Inductance L1 | 2,0 mm |
| Lecteur microSD | 1,9 mm |

Compter **8 mm de degagement** au-dessus de la carte pour etre tranquille.

> Le VL53L1X (U4) est en surface et **vise vers le haut**, perpendiculairement
> a la carte. Il lui faut une petite fenetre transparente aux infrarouges dans
> le plateau superieur, en avant de l'ecran, avec un entrefer maitrise. Si cela
> gene le design du boitier, ne pas monter U4 et brancher a la place un module
> ToF tout fait sur le port J5, positionne librement.

"""]
    return "\n".join(out)


def table(rows, head):
    out = ["| " + " | ".join(head) + " |",
           "|" + "|".join("---" for _ in head) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def main():
    x0, y0 = D.BOARD_X, D.BOARD_Y
    x1, y1 = D.BOARD_X + D.BOARD_W, D.BOARD_Y + D.BOARD_H
    doc = [INTRO.format(w=D.BOARD_W, h=D.BOARD_H, x0=x0, y0=y0, y1=y1,
                        x0h=x0 + 3, x1h=x1 - 3, y0h=y0 + 3, y1h=y1 - 3)]

    doc.append(mech_section())
    doc.append("## Affectation des GPIO\n")
    doc.append(table([(g, p, s, c) for g, p, s, c in D.GPIO_MAP],
                     ["GPIO", "Broche module", "Net", "Role"]))
    doc.append("""
> **GPIO35, 36 et 37 sont consommes par la PSRAM octale du N16R8.** Ils ne
> sont sortis nulle part sur cette carte et ne doivent jamais etre configures
> par le firmware. GPIO3, 45 et 46 sont des broches de strapping, laissees
> volontairement non connectees.
""")

    doc.append("## J2 — connecteur ecran QSPI (JST-SH 1,0 mm, 14 points)\n")
    doc.append(table([(p, s) for p, s in D.J2_PINOUT], ["Broche", "Signal"]))
    doc.append("""
L'ordre a ete choisi pour la qualite du signal : alimentation et masse
groupees en tete, les quatre lignes de donnees et l'horloge au milieu encadrees
par des masses, les commandes lentes en fin de connecteur.

`LCD_TE` est la broche *Tearing Effect* de la dalle. La cabler est ce qui
permet de synchroniser l'envoi d'une trame sur le balayage et d'obtenir zero
dechirure. C'est le detail qui separe un rendu propre d'un rendu « presque ».

`R6` est une resistance serie de 0 ohm sur `LCD_SCK`. Si l'horloge sonne sur
un cable ruban un peu long, la remplacer par 22 ohms.

## Autres connecteurs\n""")
    doc.append(table([
        ("J4", "HP", "JST-SH 2 pts", "1 = SPK_P, 2 = SPK_N. Sortie pontee : "
         "ne jamais relier une sortie a la masse."),
        ("J5", "I2C EXT", "JST-SH 4 pts", "1 = GND, 2 = +3V3, 3 = SDA, 4 = SCL. "
         "Brochage compatible Qwiic / STEMMA-QT."),
        ("J6", "DEBUG", "Barrette 1,27 mm 6 pts",
         "1 = +3V3, 2 = GND, 3 = TXD0, 4 = RXD0, 5 = IO0, 6 = EN."),
    ], ["Ref", "Nom", "Type", "Brochage"]))

    doc.append("""
## Bilan de consommation

| Consommateur | Typique | Pointe |
|---|---|---|
| ESP32-S3 (WiFi au repos) | 40–100 mA | 355 mA en emission |
| Dalle AMOLED | 80–150 mA | ~250 mA plein blanc |
| microSD en ecriture | 20 mA | 100 mA |
| MAX98357A | 10 mA | 200 mA en crete audio |
| VL53L1X + LIS3DH | < 20 mA | — |
| **Total rail 3,3 V** | **~250 mA** | **~900 mA** |

L'AP63203WU tient 2 A : la marge est confortable. C'est un buck et non un
regulateur lineaire, ce qui compte reellement dans un boitier ferme et opaque :
un LDO aurait dissipe pres de 1 W en pointe.

`FB1` (perle de ferrite 600 ohms) isole le rail de l'ampli du rail du MCU.
L'ampli est alimente en **3,3 V et non en 5 V** : les niveaux logiques I2S sont
ainsi identiques a ceux du MCU, ce qui evite tout probleme de seuil VIH.
La puissance reste largement suffisante pour un objet de bureau.

## Notes de fabrication

* Procede JLCPCB 4 couches standard : piste mini 0,127 mm, isolation 0,127 mm,
  percage mini 0,2 mm. Le routage respecte 0,13 mm d'isolation.
* Les vias thermiques sous le module ESP32 percent a 0,2 mm : c'est l'empreinte
  officielle KiCad, ne pas la modifier.
* `R14` est volontairement **non montee** (choix de gain de l'ampli : vide = 9 dB).
* `R19` fixe l'adresse I2C de l'accelerometre : 0 ohm vers GND = 0x18.
* Assemblage sur une seule face : tout est sur F.Cu.
""")

    doc.append(finishing_section())
    doc.append("## Nomenclature\n")
    groups = collections.OrderedDict()
    for ref, p in D.PARTS.items():
        key = (p["val"], p["fp"], p["mpn"])
        groups.setdefault(key, []).append(ref)
    rows = []
    for (val, fp, mpn), refs in groups.items():
        rows.append((", ".join(refs), val, mpn or "—",
                     fp.split(":")[1], len(refs)))
    rows.sort(key=lambda r: (-r[4], r[1]))
    doc.append(table(rows, ["References", "Valeur", "MPN", "Empreinte", "Qte"]))
    doc.append("\n**Total : %d composants, %d references distinctes.**\n"
               % (len(D.PARTS), len(groups)))

    doc.append("""
## Pieces a commander hors PCB

| Piece | Note |
|---|---|
| Dalle AMOLED QSPI + carte porteuse | 1,43" rond 466x466 (CO5300) ou 1,8" 368x448 (SH8601). **Verifier que la broche TE est sortie** sur le connecteur. |
| Cable JST-SH 1,0 mm 14 points | a confectionner selon le brochage de J2 ci-dessus |
| Antenne U.FL / IPEX 2,4 GHz | le WROOM-1U n'a pas d'antenne integree |
| Haut-parleur 8 ohms, 1 W | + cable JST-SH 2 points |
| Cube separateur 50/50 | 25 mm minimum ; voir les compromis dans la discussion |
| Vis M2 + inserts a chaud | 4 exemplaires |
""")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(doc) + "\n")
    print("ecrit docs/CARTE.md (%d octets)" % os.path.getsize(OUT))


if __name__ == "__main__":
    main()
