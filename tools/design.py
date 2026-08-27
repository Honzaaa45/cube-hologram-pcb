"""
CUBE - Afficheur holographique Pepper's Ghost
Definition complete de la carte : composants, netlist, placement PCB.

Source unique de verite pour gen_sch.py et gen_pcb.py.

MCU      : ESP32-S3-WROOM-1U-N16R8  (16 MB flash, 8 MB PSRAM octale)
Ecran    : connecteur QSPI generique 14 pts JST-SH 1.0 mm
Blocs    : microSD SDIO 4 bits, ampli I2S MAX98357A, ToF VL53L1X, accel LIS3DH
Alim     : USB-C 5 V -> AP63203WU (buck 2 A, 3.3 V fixe)
PCB      : 48 x 52 mm, 4 couches (F.Cu / GND / PWR / B.Cu)
"""

PROJECT = "cube"
TITLE = "CUBE - Afficheur holographique Pepper's Ghost"
REV = "A"
COMPANY = ""

# --------------------------------------------------------------------------
# Contour du PCB (mm). Origine coin haut-gauche de la carte.
# --------------------------------------------------------------------------
BOARD_X, BOARD_Y = 100.0, 100.0
BOARD_W, BOARD_H = 48.0, 52.0
BOARD_CORNER_R = 2.0

# --------------------------------------------------------------------------
# Blocs du schema : (id, titre, x, y, largeur, hauteur) en mm sur feuille A2
# --------------------------------------------------------------------------
BLOCKS = [
    ("PWR",  "1 - ENTREE USB-C + REGULATEUR 3V3",      12,  18, 196, 142),
    ("MCU",  "2 - ESP32-S3-WROOM-1U-N16R8",           216,  18, 172, 142),
    ("DISP", "3 - ECRAN AMOLED QSPI",                 396,  18, 186, 142),
    ("SD",   "4 - CARTE microSD (SDIO 4 BITS)",        12, 168, 196, 142),
    ("AUD",  "5 - AUDIO I2S MAX98357A",               216, 168, 172, 142),
    ("SENS", "6 - CAPTEURS I2C (ToF + ACCELERO)",     396, 168, 186, 142),
    ("DBG",  "7 - DEBUG / TEST / MECANIQUE",           12, 320, 372,  70),
]

# --------------------------------------------------------------------------
# Composants
#   ref: (lib, symbole, valeur, empreinte, bloc, description, mpn, dnp)
# --------------------------------------------------------------------------
P = dict  # alias court


def part(lib, sym, val, fp, block, desc="", mpn="", dnp=False):
    return P(lib=lib, sym=sym, val=val, fp=fp, block=block, desc=desc, mpn=mpn, dnp=dnp)


R_FP = "Resistor_SMD:R_0402_1005Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"

PARTS = {
    # ---------------- BLOC 1 : alimentation ----------------
    "J1":  part("Connector", "USB_C_Receptacle_USB2.0_16P", "USB-C",
                "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12", "PWR",
                "Prise USB-C 2.0, 16 pts, montage CMS", "TYPE-C-31-M-12"),
    "F1":  part("Device", "Polyfuse", "1.1A", "Fuse:Fuse_0805_2012Metric", "PWR",
                "Fusible reamorcable PPTC, Ihold 1.1 A", "MF-MSMF110-2"),
    "D1":  part("Power_Protection", "USBLC6-2SC6", "USBLC6-2SC6",
                "Package_TO_SOT_SMD:SOT-23-6", "PWR",
                "Reseau de protection ESD 2 lignes USB", "USBLC6-2SC6"),
    "R1":  part("Device", "R", "5.1k", R_FP, "PWR", "Rd CC1 (role device)"),
    "R2":  part("Device", "R", "5.1k", R_FP, "PWR", "Rd CC2 (role device)"),
    "C7":  part("Device", "C", "22uF/10V", C0805, "PWR", "Reservoir 5 V"),
    "U1":  part("Regulator_Switching", "AP63203WU", "AP63203WU",
                "Package_TO_SOT_SMD:TSOT-23-6", "PWR",
                "Buck synchrone 2 A, 1.1 MHz, sortie 3.3 V fixe", "AP63203WU-7"),
    "R3":  part("Device", "R", "100k", R_FP, "PWR", "Tirage EN du buck vers VIN"),
    "C1":  part("Device", "C", "10uF/25V", C0805, "PWR", "Decouplage entree buck"),
    "C2":  part("Device", "C", "100nF", C0402, "PWR", "Decouplage HF entree buck"),
    "C3":  part("Device", "C", "100nF", C0402, "PWR", "Condensateur bootstrap SW->BST"),
    "L1":  part("Device", "L", "2.2uH/3A", "Inductor_SMD:L_Taiyo-Yuden_NR-40xx", "PWR",
                "Inductance de puissance blindee 4x4 mm", "NR4018T2R2M"),
    "C4":  part("Device", "C", "22uF/10V", C0805, "PWR", "Reservoir sortie 3.3 V"),
    "C5":  part("Device", "C", "22uF/10V", C0805, "PWR", "Reservoir sortie 3.3 V"),
    "C6":  part("Device", "C", "100nF", C0402, "PWR", "Decouplage HF sortie 3.3 V"),

    # ---------------- BLOC 2 : MCU ----------------
    "U2":  part("RF_Module", "ESP32-S3-WROOM-1", "ESP32-S3-WROOM-1U-N16R8",
                "RF_Module:ESP32-S3-WROOM-1U", "MCU",
                "MCU WiFi/BLE, 16 MB flash, 8 MB PSRAM octale, antenne U.FL",
                "ESP32-S3-WROOM-1U-N16R8"),
    "C8":  part("Device", "C", "22uF/10V", C0805, "MCU", "Reservoir 3V3 du module"),
    "C9":  part("Device", "C", "100nF", C0402, "MCU", "Decouplage HF 3V3 du module"),
    "R4":  part("Device", "R", "10k", R_FP, "MCU", "Tirage haut de EN"),
    "C10": part("Device", "C", "1uF", C0402, "MCU", "Retard RC sur EN"),
    "R5":  part("Device", "R", "10k", R_FP, "MCU", "Tirage haut de IO0 (BOOT)"),
    "SW1": part("Switch", "SW_Push", "RESET", "Button_Switch_SMD:SW_SPST_B3U-1000P", "MCU",
                "Bouton RESET (EN vers GND)", "B3U-1000P"),
    "SW2": part("Switch", "SW_Push", "BOOT", "Button_Switch_SMD:SW_SPST_B3U-1000P", "MCU",
                "Bouton BOOT (IO0 vers GND)", "B3U-1000P"),

    # ---------------- BLOC 3 : ecran ----------------
    "J2":  part("Connector_Generic", "Conn_01x14", "ECRAN QSPI",
                "Connector_JST:JST_SH_BM14B-SRSS-TB_1x14-1MP_P1.00mm_Vertical", "DISP",
                "Connecteur ecran AMOLED QSPI, JST-SH 1.0 mm 14 pts", "BM14B-SRSS-TB"),
    "R6":  part("Device", "R", "0R", R_FP, "DISP",
                "Serie sur LCD_SCK - monter 22R si sonnerie"),
    "TP4": part("Connector", "TestPoint", "LCD_SCK", "TestPoint:TestPoint_Pad_D1.0mm",
                "DISP", "Point de test horloge QSPI"),

    # ---------------- BLOC 4 : microSD ----------------
    "J3":  part("cube", "microSD_Molex_104031-0811", "microSD",
                "Connector_Card:microSD_HC_Molex_104031-0811", "SD",
                "Lecteur microSD push-pull avec detection de carte", "104031-0811"),
    "R7":  part("Device", "R", "10k", R_FP, "SD", "Tirage SD_CMD"),
    "R8":  part("Device", "R", "10k", R_FP, "SD", "Tirage SD_D0"),
    "R9":  part("Device", "R", "10k", R_FP, "SD", "Tirage SD_D2"),
    "R10": part("Device", "R", "10k", R_FP, "SD", "Tirage SD_D3"),
    "R11": part("Device", "R", "10k", R_FP, "SD", "Tirage SD_D1"),
    "R12": part("Device", "R", "10k", R_FP, "SD", "Tirage detection de carte"),
    "C11": part("Device", "C", "10uF/10V", C0805, "SD", "Reservoir VDD carte SD"),
    "C12": part("Device", "C", "100nF", C0402, "SD", "Decouplage HF VDD carte SD"),

    # ---------------- BLOC 5 : audio ----------------
    "FB1": part("Device", "L", "600R@100MHz",
                "Inductor_SMD:L_0805_2012Metric", "AUD",
                "Perle de ferrite : isole le rail de l'ampli", "BLM21PG600SN1D"),
    "U3":  part("Audio", "MAX98357A", "MAX98357A",
                "Package_DFN_QFN:TQFN-16-1EP_3x3mm_P0.5mm_EP1.23x1.23mm", "AUD",
                "Ampli classe D I2S mono 3.2 W", "MAX98357AETE+T"),
    "C13": part("Device", "C", "22uF/10V", C0805, "AUD", "Reservoir VDD ampli"),
    "C14": part("Device", "C", "100nF", C0402, "AUD", "Decouplage HF VDD ampli"),
    "R13": part("Device", "R", "100k", R_FP, "AUD",
                "Rappel bas SD_MODE : ampli eteint au boot"),
    "R14": part("Device", "R", "DNP", R_FP, "AUD",
                "Selection de gain : vide=9 dB, 100k vers GND=12 dB", dnp=True),
    "J4":  part("Connector_Generic", "Conn_01x02", "HP",
                "Connector_JST:JST_SH_BM02B-SRSS-TB_1x02-1MP_P1.00mm_Vertical", "AUD",
                "Sortie haut-parleur 4-8 ohms", "BM02B-SRSS-TB"),

    # ---------------- BLOC 6 : capteurs ----------------
    "U4":  part("Sensor_Distance", "VL53L1CXV0FY1", "VL53L1X",
                "Sensor_Distance:ST_VL53L1x", "SENS",
                "Telemetre ToF laser 4 m, I2C 0x29", "VL53L1CXV0FY/1"),
    "C15": part("Device", "C", "10uF/10V", C0805, "SENS", "Reservoir AVDD ToF"),
    "C16": part("Device", "C", "100nF", C0402, "SENS", "Decouplage HF AVDD ToF"),
    "C17": part("Device", "C", "100nF", C0402, "SENS", "Decouplage AVDDVCSEL"),
    "R15": part("Device", "R", "10k", R_FP, "SENS", "Tirage XSHUT"),
    "R16": part("Device", "R", "10k", R_FP, "SENS", "Tirage INT (drain ouvert)"),
    "U5":  part("Sensor_Motion", "LIS3DH", "LIS3DH",
                "Package_LGA:LGA-16_3x3mm_P0.5mm_LayoutBorder3x5y", "SENS",
                "Accelerometre 3 axes, I2C 0x18 (SDO=GND)", "LIS3DHTR"),
    "C18": part("Device", "C", "100nF", C0402, "SENS", "Decouplage VDD accelero"),
    "C19": part("Device", "C", "100nF", C0402, "SENS", "Decouplage VDD_IO accelero"),
    "R17": part("Device", "R", "4.7k", R_FP, "SENS", "Tirage I2C SDA"),
    "R18": part("Device", "R", "4.7k", R_FP, "SENS", "Tirage I2C SCL"),
    "R19": part("Device", "R", "0R", R_FP, "SENS",
                "Adresse accelero : 0R vers GND = 0x18, vers +3V3 = 0x19"),
    "J5":  part("Connector_Generic", "Conn_01x04", "I2C EXT",
                "Connector_JST:JST_SH_BM04B-SRSS-TB_1x04-1MP_P1.00mm_Vertical", "SENS",
                "Port I2C deporte (compatible Qwiic/STEMMA-QT)", "BM04B-SRSS-TB"),

    # ---------------- BLOC 7 : debug / mecanique ----------------
    "J6":  part("Connector_Generic", "Conn_01x06", "DEBUG",
                "Connector_PinHeader_1.27mm:PinHeader_1x06_P1.27mm_Vertical", "DBG",
                "UART0 + BOOT + EN (secours si USB natif indisponible)"),
    "TP1": part("Connector", "TestPoint", "+5V", "TestPoint:TestPoint_Pad_D1.0mm", "DBG", ""),
    "TP2": part("Connector", "TestPoint", "+3V3", "TestPoint:TestPoint_Pad_D1.0mm", "DBG", ""),
    "TP3": part("Connector", "TestPoint", "GND", "TestPoint:TestPoint_Pad_D1.0mm", "DBG", ""),
    "H1":  part("Mechanical", "MountingHole", "M2", "MountingHole:MountingHole_2.2mm_M2", "DBG", ""),
    "H2":  part("Mechanical", "MountingHole", "M2", "MountingHole:MountingHole_2.2mm_M2", "DBG", ""),
    "H3":  part("Mechanical", "MountingHole", "M2", "MountingHole:MountingHole_2.2mm_M2", "DBG", ""),
    "H4":  part("Mechanical", "MountingHole", "M2", "MountingHole:MountingHole_2.2mm_M2", "DBG", ""),
}

# --------------------------------------------------------------------------
# Symbole maison : lecteur microSD Molex 104031-0811
# pastilles 1-8 = contacts microSD, 9/10 = switch de detection, 11 = blindage
# --------------------------------------------------------------------------
CUSTOM_SYMBOLS = {
    "microSD_Molex_104031-0811": dict(
        desc="Lecteur microSD push-pull Molex 104031-0811 avec detection de carte",
        fp="Connector_Card:microSD_HC_Molex_104031-0811",
        pins=[  # (numero, nom, type, cote)  cote: L=gauche R=droite
            ("4", "VDD", "power_in", "L"),
            ("6", "VSS", "power_in", "L"),
            ("11", "SHIELD", "passive", "L"),
            ("5", "CLK", "input", "R"),
            ("3", "CMD", "bidirectional", "R"),
            ("7", "DAT0", "bidirectional", "R"),
            ("8", "DAT1", "bidirectional", "R"),
            ("1", "DAT2", "bidirectional", "R"),
            ("2", "CD/DAT3", "bidirectional", "R"),
            ("9", "DET_SW1", "passive", "R"),
            ("10", "DET_SW2", "passive", "R"),
        ],
    ),
}

# --------------------------------------------------------------------------
# NETLIST
# --------------------------------------------------------------------------
NETS = {
    # ---- alimentation ----
    "VBUS": [("J1", "A4"), ("J1", "B4"), ("J1", "A9"), ("J1", "B9"),
             ("F1", "1"), ("D1", "5")],
    "+5V": [("F1", "2"), ("C7", "1"), ("C1", "1"), ("C2", "1"),
            ("U1", "3"), ("R3", "1"), ("TP1", "1")],
    "VREG_EN": [("U1", "2"), ("R3", "2")],
    "SW_NODE": [("U1", "5"), ("L1", "1"), ("C3", "1")],
    "BST": [("U1", "6"), ("C3", "2")],
    "+3V3": [("L1", "2"), ("U1", "1"), ("C4", "1"), ("C5", "1"), ("C6", "1"),
             ("C8", "1"), ("C9", "1"), ("U2", "2"), ("R4", "1"), ("R5", "1"),
             ("J2", "2"), ("J2", "3"),
             ("J3", "4"), ("C11", "1"), ("C12", "1"),
             ("R7", "1"), ("R8", "1"), ("R9", "1"), ("R10", "1"), ("R11", "1"),
             ("R12", "1"), ("FB1", "1"),
             ("U4", "1"), ("U4", "11"), ("C15", "1"), ("C16", "1"), ("C17", "1"),
             ("R15", "1"), ("R16", "1"), ("R17", "1"), ("R18", "1"),
             ("U5", "1"), ("U5", "14"), ("U5", "8"), ("C18", "1"), ("C19", "1"),
             ("J5", "2"), ("J6", "1"), ("TP2", "1")],
    "VDD_AMP": [("FB1", "2"), ("U3", "7"), ("U3", "8"), ("C13", "1"), ("C14", "1")],
    "GND": [("J1", "A1"), ("J1", "A12"), ("J1", "B1"), ("J1", "B12"), ("J1", "S1"),
            ("D1", "2"), ("R1", "2"), ("R2", "2"),
            ("C1", "2"), ("C2", "2"), ("C7", "2"), ("U1", "4"),
            ("C4", "2"), ("C5", "2"), ("C6", "2"),
            ("U2", "1"), ("U2", "40"), ("U2", "41"),
            ("C8", "2"), ("C9", "2"), ("C10", "2"), ("SW1", "2"), ("SW2", "2"),
            ("J2", "1"), ("J2", "4"), ("J2", "11"),
            ("J3", "6"), ("J3", "11"), ("J3", "10"), ("C11", "2"), ("C12", "2"),
            ("U3", "3"), ("U3", "11"), ("U3", "15"), ("U3", "17"),
            ("C13", "2"), ("C14", "2"), ("R13", "2"), ("R14", "2"),
            ("U4", "2"), ("U4", "3"), ("U4", "4"), ("U4", "6"), ("U4", "12"),
            ("C15", "2"), ("C16", "2"), ("C17", "2"),
            ("U5", "5"), ("U5", "10"), ("U5", "12"), ("R19", "2"),
            ("C18", "2"), ("C19", "2"),
            ("J5", "1"), ("J6", "2"), ("TP3", "1")],

    # ---- USB ----
    "USB_DM": [("J1", "A7"), ("J1", "B7"), ("D1", "1"), ("D1", "6"), ("U2", "13")],
    "USB_DP": [("J1", "A6"), ("J1", "B6"), ("D1", "3"), ("D1", "4"), ("U2", "14")],
    "CC1": [("J1", "A5"), ("R1", "1")],
    "CC2": [("J1", "B5"), ("R2", "1")],

    # ---- controle MCU ----
    "EN": [("U2", "3"), ("R4", "2"), ("C10", "1"), ("SW1", "1"), ("J6", "6")],
    "BOOT": [("U2", "27"), ("R5", "2"), ("SW2", "1"), ("J6", "5")],
    "UART_TX": [("U2", "37"), ("J6", "3")],
    "UART_RX": [("U2", "36"), ("J6", "4")],

    # ---- ecran QSPI ----
    "LCD_SCK_MCU": [("U2", "20"), ("R6", "1")],                 # IO12
    "LCD_SCK": [("R6", "2"), ("J2", "5"), ("TP4", "1")],
    "LCD_D0": [("U2", "19"), ("J2", "6")],                      # IO11
    "LCD_D1": [("U2", "21"), ("J2", "7")],                      # IO13
    "LCD_D2": [("U2", "22"), ("J2", "8")],                      # IO14
    "LCD_D3": [("U2", "18"), ("J2", "9")],                      # IO10
    "LCD_CS": [("U2", "17"), ("J2", "10")],                     # IO9
    "LCD_RST": [("U2", "12"), ("J2", "12")],                    # IO8
    "LCD_TE": [("U2", "11"), ("J2", "13")],                     # IO18
    "LCD_PWR_EN": [("U2", "10"), ("J2", "14")],                 # IO17

    # ---- microSD ----
    "SD_CLK": [("U2", "32"), ("J3", "5")],                      # IO39
    "SD_CMD": [("U2", "31"), ("J3", "3"), ("R7", "2")],         # IO38
    "SD_D0": [("U2", "33"), ("J3", "7"), ("R8", "2")],          # IO40
    "SD_D1": [("U2", "34"), ("J3", "8"), ("R11", "2")],         # IO41
    "SD_D2": [("U2", "35"), ("J3", "1"), ("R9", "2")],          # IO42
    "SD_D3": [("U2", "23"), ("J3", "2"), ("R10", "2")],         # IO21
    "SD_DET": [("U2", "24"), ("J3", "9"), ("R12", "2")],        # IO47

    # ---- audio I2S ----
    "I2S_BCLK": [("U2", "5"), ("U3", "16")],                    # IO5
    "I2S_LRCLK": [("U2", "6"), ("U3", "14")],                   # IO6
    "I2S_DOUT": [("U2", "7"), ("U3", "1")],                     # IO7
    "AMP_EN": [("U2", "8"), ("U3", "4"), ("R13", "1")],         # IO15
    "AMP_GAIN": [("U3", "2"), ("R14", "1")],
    "SPK_P": [("U3", "9"), ("J4", "1")],
    "SPK_N": [("U3", "10"), ("J4", "2")],

    # ---- capteurs I2C ----
    "I2C_SDA": [("U2", "39"), ("U4", "9"), ("U5", "6"), ("R17", "2"), ("J5", "3")],
    "I2C_SCL": [("U2", "38"), ("U4", "10"), ("U5", "4"), ("R18", "2"), ("J5", "4")],
    "TOF_XSHUT": [("U2", "9"), ("U4", "5"), ("R15", "2")],      # IO16
    "TOF_INT": [("U2", "4"), ("U4", "7"), ("R16", "2")],        # IO4
    "ACC_INT1": [("U2", "25"), ("U5", "11")],                   # IO48
    "ACC_ADDR": [("U5", "7"), ("R19", "1")],
}

# Elements presents sur la carte mais qui ne se commandent pas : trous de
# fixation et points de test. Les empreintes KiCad portent deja le drapeau
# exclude_from_bom, le schema doit dire la meme chose sinon KiCad signale une
# divergence empreinte/symbole.
NO_BOM = {"H1", "H2", "H3", "H4", "TP1", "TP2", "TP3", "TP4"}

# Broches volontairement non connectees (drapeau no-connect au schema).
NO_CONNECT = [
    # GPIO35/36/37 : consommes par la PSRAM octale du N16R8 - INTERDIT d'usage
    ("U2", "28"), ("U2", "29"), ("U2", "30"),
    # broches de strapping laissees libres (IO45 = VDD_SPI, IO46 = log ROM)
    ("U2", "15"), ("U2", "16"), ("U2", "26"),
    # MAX98357A
    ("U3", "5"), ("U3", "6"), ("U3", "12"), ("U3", "13"),
    # VL53L1X
    ("U4", "8"),
    # USB-C : SBU1/SBU2 inutilises en USB 2.0 peripherique
    ("J1", "A8"), ("J1", "B8"),
    # LIS3DH
    ("U5", "2"), ("U5", "3"), ("U5", "9"), ("U5", "13"), ("U5", "15"), ("U5", "16"),
]

# Nets d'alimentation -> symbole power au lieu d'une etiquette texte.
POWER_NETS = {"GND": "power:GND", "+3V3": "power:+3V3", "+5V": "power:+5V"}

# --------------------------------------------------------------------------
# Placement PCB : ref -> (x, y, rotation, couche)
# Coordonnees absolues mm. Carte = 100..144 en X, 100..148 en Y.
# --------------------------------------------------------------------------
PCB_PLACE = {
    "J1": (124.00, 149.50, 0, "F.Cu"),
    "F1": (116.75, 147.50, 0, "F.Cu"),
    "D1": (132.85, 142.30, 0, "F.Cu"),
    "R1": (129.00, 139.00, 0, "F.Cu"),
    "R2": (131.50, 139.00, 0, "F.Cu"),
    "C7": (117.00, 143.50, 90, "F.Cu"),
    "U1": (109.50, 143.00, 0, "F.Cu"),
    "R3": (113.00, 139.75, 0, "F.Cu"),
    "C1": (114.00, 143.50, 90, "F.Cu"),
    "C2": (113.90, 147.00, 0, "F.Cu"),
    "C3": (109.50, 139.50, 0, "F.Cu"),
    "L1": (104.00, 142.90, 0, "F.Cu"),
    "C4": (101.30, 138.75, 90, "F.Cu"),
    "C5": (104.20, 139.00, 0, "F.Cu"),
    "C6": (101.50, 145.85, 0, "F.Cu"),
    "U2": (124.00, 126.50, 0, "F.Cu"),
    "C8": (113.50, 138.05, 0, "F.Cu"),
    "C9": (116.50, 137.50, 0, "F.Cu"),
    "R4": (133.95, 144.70, 0, "F.Cu"),
    "C10": (137.50, 145.35, 0, "F.Cu"),
    "R5": (140.50, 142.00, 0, "F.Cu"),
    "SW1": (134.50, 147.75, 0, "F.Cu"),
    "SW2": (139.50, 147.75, 0, "F.Cu"),
    "J2": (124.00, 110.50, 0, "F.Cu"),
    "R6": (136.50, 110.00, 0, "F.Cu"),
    "TP4": (140.00, 110.50, 0, "F.Cu"),
    "J3": (107.20, 124.00, 270, "F.Cu"),
    "R7": (101.50, 135.15, 0, "F.Cu"),
    "R8": (101.50, 136.35, 0, "F.Cu"),
    "R9": (104.50, 133.50, 0, "F.Cu"),
    "R10": (104.50, 135.00, 0, "F.Cu"),
    "R11": (107.50, 133.50, 0, "F.Cu"),
    "R12": (107.50, 135.00, 0, "F.Cu"),
    "C11": (102.00, 132.75, 90, "F.Cu"),
    "C12": (104.50, 131.55, 0, "F.Cu"),
    "FB1": (140.00, 116.50, 0, "F.Cu"),
    "U3": (140.50, 121.00, 0, "F.Cu"),
    "C13": (145.00, 118.00, 90, "F.Cu"),
    "C14": (145.00, 122.00, 90, "F.Cu"),
    "R13": (140.00, 126.00, 0, "F.Cu"),
    "R14": (140.00, 128.00, 0, "F.Cu"),
    "J4": (143.50, 132.00, 90, "F.Cu"),
    "U4": (128.00, 102.60, 0, "F.Cu"),
    "C15": (134.00, 103.00, 0, "F.Cu"),
    "C16": (131.00, 106.00, 0, "F.Cu"),
    "C17": (125.00, 106.00, 0, "F.Cu"),
    "R15": (122.00, 103.00, 0, "F.Cu"),
    "R16": (122.00, 105.00, 0, "F.Cu"),
    "U5": (112.00, 103.50, 0, "F.Cu"),
    "C18": (107.50, 102.50, 0, "F.Cu"),
    "C19": (107.50, 105.00, 0, "F.Cu"),
    "R17": (116.00, 106.50, 0, "F.Cu"),
    "R18": (119.00, 106.50, 0, "F.Cu"),
    "R19": (116.00, 103.00, 0, "F.Cu"),
    "J5": (104.00, 113.00, 270, "F.Cu"),
    "J6": (136.70, 137.15, 0, "F.Cu"),
    "TP1": (120.00, 139.00, 0, "F.Cu"),
    "TP2": (123.00, 139.00, 0, "F.Cu"),
    "TP3": (126.00, 139.00, 0, "F.Cu"),
    "H1": (103.00, 103.00, 0, "F.Cu"),
    "H2": (145.00, 103.00, 0, "F.Cu"),
    "H3": (103.00, 149.00, 0, "F.Cu"),
    "H4": (145.00, 149.00, 0, "F.Cu"),
}

# --------------------------------------------------------------------------
# Table d'affectation des GPIO (documentation + serigraphie)
# --------------------------------------------------------------------------
GPIO_MAP = [
    ("IO12", "20", "LCD_SCK_MCU", "Horloge QSPI, devient LCD_SCK apres R6"),
    ("IO11", "19", "LCD_D0",      "Donnee QSPI 0"),
    ("IO13", "21", "LCD_D1",      "Donnee QSPI 1"),
    ("IO14", "22", "LCD_D2",      "Donnee QSPI 2"),
    ("IO10", "18", "LCD_D3",      "Donnee QSPI 3"),
    ("IO9",  "17", "LCD_CS",      "Selection ecran"),
    ("IO8",  "12", "LCD_RST",     "Reset ecran"),
    ("IO18", "11", "LCD_TE",      "Tearing Effect - synchro anti-dechirure"),
    ("IO17", "10", "LCD_PWR_EN",  "Activation alimentation dalle"),
    ("IO39", "32", "SD_CLK",      "Horloge SDIO"),
    ("IO38", "31", "SD_CMD",      "Commande SDIO"),
    ("IO40", "33", "SD_D0",       "Donnee SDIO 0"),
    ("IO41", "34", "SD_D1",       "Donnee SDIO 1"),
    ("IO42", "35", "SD_D2",       "Donnee SDIO 2"),
    ("IO21", "23", "SD_D3",       "Donnee SDIO 3"),
    ("IO47", "24", "SD_DET",      "Detection de carte"),
    ("IO5",  "5",  "I2S_BCLK",    "Horloge bit I2S"),
    ("IO6",  "6",  "I2S_LRCLK",   "Horloge mot I2S"),
    ("IO7",  "7",  "I2S_DOUT",    "Donnee I2S"),
    ("IO15", "8",  "AMP_EN",      "Activation ampli (bas = eteint)"),
    ("IO1",  "39", "I2C_SDA",     "I2C donnee"),
    ("IO2",  "38", "I2C_SCL",     "I2C horloge"),
    ("IO16", "9",  "TOF_XSHUT",   "Reset du VL53L1X"),
    ("IO4",  "4",  "TOF_INT",     "Interruption ToF"),
    ("IO48", "25", "ACC_INT1",    "Interruption accelerometre"),
    ("IO19", "13", "USB_D-",      "USB natif"),
    ("IO20", "14", "USB_D+",      "USB natif"),
    ("IO43", "37", "UART_TX",     "Console de debug"),
    ("IO44", "36", "UART_RX",     "Console de debug"),
    ("IO0",  "27", "BOOT",        "Strapping - bouton BOOT"),
    ("IO35", "28", "-- INTERDIT", "PSRAM octale (N16R8)"),
    ("IO36", "29", "-- INTERDIT", "PSRAM octale (N16R8)"),
    ("IO37", "30", "-- INTERDIT", "PSRAM octale (N16R8)"),
    ("IO3",  "15", "libre",       "Strapping JTAG - laisse non connecte"),
    ("IO45", "26", "libre",       "Strapping VDD_SPI - laisse non connecte"),
    ("IO46", "16", "libre",       "Strapping log ROM - laisse non connecte"),
]

# Brochage du connecteur ecran J2 (documentation + serigraphie)
J2_PINOUT = [
    (1, "GND"), (2, "+3V3"), (3, "+3V3"), (4, "GND"),
    (5, "LCD_SCK"), (6, "LCD_D0"), (7, "LCD_D1"), (8, "LCD_D2"),
    (9, "LCD_D3"), (10, "LCD_CS"), (11, "GND"), (12, "LCD_RST"),
    (13, "LCD_TE"), (14, "LCD_PWR_EN"),
]
