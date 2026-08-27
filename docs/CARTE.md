# CUBE — carte electronique

Carte mere de l'afficheur holographique Pepper's Ghost.

| | |
|---|---|
| MCU | ESP32-S3-WROOM-1U-N16R8 — 16 MB flash, 8 MB PSRAM **octale**, antenne U.FL |
| Ecran | connecteur QSPI generique 14 points, JST-SH 1,0 mm (J2) |
| Stockage | microSD en **SDIO 4 bits** (J3) |
| Audio | MAX98357A, ampli classe D I2S mono (U3) |
| Capteurs | VL53L1X (ToF, 0x29) + LIS3DH (accelerometre, 0x18) |
| Alimentation | USB-C 5 V -> AP63203WU, buck 2 A sortie 3,3 V fixe |
| Carte | 48.0 x 52.0 mm, **4 couches**, composants sur la face avant uniquement |

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

* `y = 100.0` — **avant** du boitier : le VL53L1X (U4) vise vers le haut, a
  travers une petite fenetre transparente aux infrarouges, devant l'ecran.
* `y = 152.0` — **arriere** : sortie USB-C.
* `x = 100.0` — **flanc gauche** : trappe microSD.
* 4 trous M2 (103.0 / 145.0 en X, 103.0 / 149.0 en Y), inserts a chaud
  recommandes cote boitier.


## Cotes pour le boitier (Fusion 360)

Origine = **coin haut-gauche de la carte** (le coin avant-gauche), axe X vers la droite, axe Y vers l'arriere.

* Contour : rectangle **48 x 52 mm**, coins arrondis R2.0 mm.
* Epaisseur du circuit imprime : 1,6 mm.
* Trous M2 (diametre 2,2 mm) a **3,0 mm** de chaque bord, soit (3,0 / 3,0), (45.0 / 3,0), (3,0 / 49.0), (45.0 / 49.0).
* La prise USB-C **deborde de 1.7 mm** au-dela du bord arriere : prevoir la decoupe correspondante dans le boitier.

| Ref | Role | Centre (x, y) | Emprise X | Emprise Y |
|---|---|---|---|---|
| J1 | USB-C | 24.00, 49.50 | 18.68 .. 29.32 | 44.23 .. 53.65 |
| J3 | microSD | 7.20, 24.00 | 0.65 .. 13.70 | 17.16 .. 30.84 |
| J2 | ECRAN QSPI | 24.00, 10.50 | 15.10 .. 32.90 | 7.90 .. 13.10 |
| J4 | HP | 43.50, 32.00 | 40.90 .. 46.10 | 29.10 .. 34.90 |
| J5 | I2C EXT | 4.00, 13.00 | 1.40 .. 6.60 | 9.10 .. 16.90 |
| J6 | DEBUG | 36.70, 37.15 | 35.15 .. 38.25 | 36.01 .. 44.64 |
| U2 | ESP32-S3-WROOM-1U-N16R8 | 24.00, 26.50 | 14.25 .. 33.75 | 16.65 .. 36.80 |
| U4 | VL53L1X | 28.00, 2.60 | 25.30 .. 30.70 | 1.10 .. 4.10 |
| SW1 | RESET | 34.50, 47.75 | 32.10 .. 36.90 | 46.10 .. 49.40 |
| SW2 | BOOT | 39.50, 47.75 | 37.10 .. 41.90 | 46.10 .. 49.40 |

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


## Affectation des GPIO

| GPIO | Broche module | Net | Role |
|---|---|---|---|
| IO12 | 20 | LCD_SCK_MCU | Horloge QSPI, devient LCD_SCK apres R6 |
| IO11 | 19 | LCD_D0 | Donnee QSPI 0 |
| IO13 | 21 | LCD_D1 | Donnee QSPI 1 |
| IO14 | 22 | LCD_D2 | Donnee QSPI 2 |
| IO10 | 18 | LCD_D3 | Donnee QSPI 3 |
| IO9 | 17 | LCD_CS | Selection ecran |
| IO8 | 12 | LCD_RST | Reset ecran |
| IO18 | 11 | LCD_TE | Tearing Effect - synchro anti-dechirure |
| IO17 | 10 | LCD_PWR_EN | Activation alimentation dalle |
| IO39 | 32 | SD_CLK | Horloge SDIO |
| IO38 | 31 | SD_CMD | Commande SDIO |
| IO40 | 33 | SD_D0 | Donnee SDIO 0 |
| IO41 | 34 | SD_D1 | Donnee SDIO 1 |
| IO42 | 35 | SD_D2 | Donnee SDIO 2 |
| IO21 | 23 | SD_D3 | Donnee SDIO 3 |
| IO47 | 24 | SD_DET | Detection de carte |
| IO5 | 5 | I2S_BCLK | Horloge bit I2S |
| IO6 | 6 | I2S_LRCLK | Horloge mot I2S |
| IO7 | 7 | I2S_DOUT | Donnee I2S |
| IO15 | 8 | AMP_EN | Activation ampli (bas = eteint) |
| IO1 | 39 | I2C_SDA | I2C donnee |
| IO2 | 38 | I2C_SCL | I2C horloge |
| IO16 | 9 | TOF_XSHUT | Reset du VL53L1X |
| IO4 | 4 | TOF_INT | Interruption ToF |
| IO48 | 25 | ACC_INT1 | Interruption accelerometre |
| IO19 | 13 | USB_D- | USB natif |
| IO20 | 14 | USB_D+ | USB natif |
| IO43 | 37 | UART_TX | Console de debug |
| IO44 | 36 | UART_RX | Console de debug |
| IO0 | 27 | BOOT | Strapping - bouton BOOT |
| IO35 | 28 | -- INTERDIT | PSRAM octale (N16R8) |
| IO36 | 29 | -- INTERDIT | PSRAM octale (N16R8) |
| IO37 | 30 | -- INTERDIT | PSRAM octale (N16R8) |
| IO3 | 15 | libre | Strapping JTAG - laisse non connecte |
| IO45 | 26 | libre | Strapping VDD_SPI - laisse non connecte |
| IO46 | 16 | libre | Strapping log ROM - laisse non connecte |

> **GPIO35, 36 et 37 sont consommes par la PSRAM octale du N16R8.** Ils ne
> sont sortis nulle part sur cette carte et ne doivent jamais etre configures
> par le firmware. GPIO3, 45 et 46 sont des broches de strapping, laissees
> volontairement non connectees.

## J2 — connecteur ecran QSPI (JST-SH 1,0 mm, 14 points)

| Broche | Signal |
|---|---|
| 1 | GND |
| 2 | +3V3 |
| 3 | +3V3 |
| 4 | GND |
| 5 | LCD_SCK |
| 6 | LCD_D0 |
| 7 | LCD_D1 |
| 8 | LCD_D2 |
| 9 | LCD_D3 |
| 10 | LCD_CS |
| 11 | GND |
| 12 | LCD_RST |
| 13 | LCD_TE |
| 14 | LCD_PWR_EN |

L'ordre a ete choisi pour la qualite du signal : alimentation et masse
groupees en tete, les quatre lignes de donnees et l'horloge au milieu encadrees
par des masses, les commandes lentes en fin de connecteur.

`LCD_TE` est la broche *Tearing Effect* de la dalle. La cabler est ce qui
permet de synchroniser l'envoi d'une trame sur le balayage et d'obtenir zero
dechirure. C'est le detail qui separe un rendu propre d'un rendu « presque ».

`R6` est une resistance serie de 0 ohm sur `LCD_SCK`. Si l'horloge sonne sur
un cable ruban un peu long, la remplacer par 22 ohms.

## Autres connecteurs

| Ref | Nom | Type | Brochage |
|---|---|---|---|
| J4 | HP | JST-SH 2 pts | 1 = SPK_P, 2 = SPK_N. Sortie pontee : ne jamais relier une sortie a la masse. |
| J5 | I2C EXT | JST-SH 4 pts | 1 = GND, 2 = +3V3, 3 = SDA, 4 = SCL. Brochage compatible Qwiic / STEMMA-QT. |
| J6 | DEBUG | Barrette 1,27 mm 6 pts | 1 = +3V3, 2 = GND, 3 = TXD0, 4 = RXD0, 5 = IO0, 6 = EN. |

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

## Ce qu'il reste a router

Aucune liaison en attente : la carte est entierement routee.

## Nomenclature

| References | Valeur | MPN | Empreinte | Qte |
|---|---|---|---|---|
| C2, C3, C6, C9, C12, C14, C16, C17, C18, C19 | 100nF | — | C_0402_1005Metric | 10 |
| R4, R5, R7, R8, R9, R10, R11, R12, R15, R16 | 10k | — | R_0402_1005Metric | 10 |
| C7, C4, C5, C8, C13 | 22uF/10V | — | C_0805_2012Metric | 5 |
| H1, H2, H3, H4 | M2 | — | MountingHole_2.2mm_M2 | 4 |
| R6, R19 | 0R | — | R_0402_1005Metric | 2 |
| R3, R13 | 100k | — | R_0402_1005Metric | 2 |
| C11, C15 | 10uF/10V | — | C_0805_2012Metric | 2 |
| R17, R18 | 4.7k | — | R_0402_1005Metric | 2 |
| R1, R2 | 5.1k | — | R_0402_1005Metric | 2 |
| TP2 | +3V3 | — | TestPoint_Pad_D1.0mm | 1 |
| TP1 | +5V | — | TestPoint_Pad_D1.0mm | 1 |
| F1 | 1.1A | MF-MSMF110-2 | Fuse_0805_2012Metric | 1 |
| C1 | 10uF/25V | — | C_0805_2012Metric | 1 |
| C10 | 1uF | — | C_0402_1005Metric | 1 |
| L1 | 2.2uH/3A | NR4018T2R2M | L_Taiyo-Yuden_NR-40xx | 1 |
| FB1 | 600R@100MHz | BLM21PG600SN1D | L_0805_2012Metric | 1 |
| U1 | AP63203WU | AP63203WU-7 | TSOT-23-6 | 1 |
| SW2 | BOOT | B3U-1000P | SW_SPST_B3U-1000P | 1 |
| J6 | DEBUG | — | PinHeader_1x06_P1.27mm_Vertical | 1 |
| R14 | DNP | — | R_0402_1005Metric | 1 |
| J2 | ECRAN QSPI | BM14B-SRSS-TB | JST_SH_BM14B-SRSS-TB_1x14-1MP_P1.00mm_Vertical | 1 |
| U2 | ESP32-S3-WROOM-1U-N16R8 | ESP32-S3-WROOM-1U-N16R8 | ESP32-S3-WROOM-1U | 1 |
| TP3 | GND | — | TestPoint_Pad_D1.0mm | 1 |
| J4 | HP | BM02B-SRSS-TB | JST_SH_BM02B-SRSS-TB_1x02-1MP_P1.00mm_Vertical | 1 |
| J5 | I2C EXT | BM04B-SRSS-TB | JST_SH_BM04B-SRSS-TB_1x04-1MP_P1.00mm_Vertical | 1 |
| TP4 | LCD_SCK | — | TestPoint_Pad_D1.0mm | 1 |
| U5 | LIS3DH | LIS3DHTR | LGA-16_3x3mm_P0.5mm_LayoutBorder3x5y | 1 |
| U3 | MAX98357A | MAX98357AETE+T | TQFN-16-1EP_3x3mm_P0.5mm_EP1.23x1.23mm | 1 |
| SW1 | RESET | B3U-1000P | SW_SPST_B3U-1000P | 1 |
| J1 | USB-C | TYPE-C-31-M-12 | USB_C_Receptacle_HRO_TYPE-C-31-M-12 | 1 |
| D1 | USBLC6-2SC6 | USBLC6-2SC6 | SOT-23-6 | 1 |
| U4 | VL53L1X | VL53L1CXV0FY/1 | ST_VL53L1x | 1 |
| J3 | microSD | 104031-0811 | microSD_HC_Molex_104031-0811 | 1 |

**Total : 63 composants, 33 references distinctes.**


## Pieces a commander hors PCB

| Piece | Note |
|---|---|
| Dalle AMOLED QSPI + carte porteuse | 1,43" rond 466x466 (CO5300) ou 1,8" 368x448 (SH8601). **Verifier que la broche TE est sortie** sur le connecteur. |
| Cable JST-SH 1,0 mm 14 points | a confectionner selon le brochage de J2 ci-dessus |
| Antenne U.FL / IPEX 2,4 GHz | le WROOM-1U n'a pas d'antenne integree |
| Haut-parleur 8 ohms, 1 W | + cable JST-SH 2 points |
| Cube separateur 50/50 | 25 mm minimum ; voir les compromis dans la discussion |
| Vis M2 + inserts a chaud | 4 exemplaires |

