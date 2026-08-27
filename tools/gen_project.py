"""Genere les fichiers de projet KiCad : cube.kicad_pro, cube.kicad_sym,
sym-lib-table, fp-lib-table."""
import json
import os

import sexpr
import design as D
import gen_sch
from sexpr import Sym

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(os.path.dirname(HERE), "hw")

# --------------------------------------------------------------------------
# Classes de nets : le QSPI et l'alimentation ont des contraintes propres
# --------------------------------------------------------------------------
NETCLASSES = [
    dict(name="Default", clearance=0.13, track_width=0.15,
         via_diameter=0.5, via_drill=0.3, uvia_diameter=0.3, uvia_drill=0.2,
         diff_pair_width=0.2, diff_pair_gap=0.25, pcb_color="rgba(0, 0, 0, 0.000)",
         wire_width=6, bus_width=12, schematic_color="rgba(0, 0, 0, 0.000)",
         line_style=0, priority=2147483647),
    dict(name="POWER", clearance=0.13, track_width=0.5,
         via_diameter=0.7, via_drill=0.35, uvia_diameter=0.3, uvia_drill=0.2,
         diff_pair_width=0.2, diff_pair_gap=0.25, pcb_color="rgba(200, 52, 52, 0.400)",
         wire_width=6, bus_width=12, schematic_color="rgba(0, 0, 0, 0.000)",
         line_style=0, priority=1),
    dict(name="QSPI", clearance=0.13, track_width=0.15,
         via_diameter=0.5, via_drill=0.3, uvia_diameter=0.3, uvia_drill=0.2,
         diff_pair_width=0.2, diff_pair_gap=0.25, pcb_color="rgba(72, 148, 255, 0.400)",
         wire_width=6, bus_width=12, schematic_color="rgba(0, 0, 0, 0.000)",
         line_style=0, priority=0),
    dict(name="USB", clearance=0.13, track_width=0.15,
         via_diameter=0.5, via_drill=0.3, uvia_diameter=0.3, uvia_drill=0.2,
         diff_pair_width=0.25, diff_pair_gap=0.2, pcb_color="rgba(0, 200, 0, 0.400)",
         wire_width=6, bus_width=12, schematic_color="rgba(0, 0, 0, 0.000)",
         line_style=0, priority=0),
]

NET_ASSIGN = {}
for _n in ("+3V3", "+5V", "GND", "VBUS", "VDD_AMP", "SW_NODE", "BST"):
    NET_ASSIGN[_n] = "POWER"
for _n in ("LCD_SCK", "LCD_SCK_MCU", "LCD_D0", "LCD_D1", "LCD_D2", "LCD_D3",
           "LCD_CS", "LCD_TE",
           "SD_CLK", "SD_CMD", "SD_D0", "SD_D1", "SD_D2", "SD_D3"):
    NET_ASSIGN[_n] = "QSPI"
for _n in ("USB_DP", "USB_DM"):
    NET_ASSIGN[_n] = "USB"


def kicad_pro():
    return {
        "board": {
            "3dviewports": [], "design_settings": {
                "defaults": {
                    "board_outline_line_width": 0.05,
                    "copper_line_width": 0.2,
                    "copper_text_size_h": 1.0, "copper_text_size_v": 1.0,
                    "copper_text_thickness": 0.15,
                    "other_line_width": 0.1,
                    "silk_line_width": 0.1,
                    "silk_text_size_h": 0.8, "silk_text_size_v": 0.8,
                    "silk_text_thickness": 0.12,
                },
                "diff_pair_dimensions": [], "drc_exclusions": [],
                "rules": {
                    "max_error": 0.005,
                    "min_clearance": 0.13,
                    "min_copper_edge_clearance": 0.3,
                    "min_hole_clearance": 0.25,
                    "min_hole_to_hole": 0.2,
                    "min_microvia_diameter": 0.2,
                    "min_microvia_drill": 0.1,
                    "min_resolved_spokes": 1,
                    "min_silk_clearance": 0.0,
                    "min_text_height": 0.8,
                    "min_text_thickness": 0.08,
                    "min_through_hole_diameter": 0.2,
                    "min_track_width": 0.127,
                    "min_via_annular_width": 0.1,
                    "min_via_diameter": 0.4,
                },
                "track_widths": [0.0, 0.2, 0.3, 0.6, 1.0],
                "via_dimensions": [{"diameter": 0.0, "drill": 0.0},
                                   {"diameter": 0.5, "drill": 0.3},
                                   {"diameter": 0.7, "drill": 0.35}],
                "zones_allow_external_fillets": False,
            },
            "layer_presets": [], "viewports": [],
        },
        "boards": [],
        "cvpcb": {"equivalence_files": []},
        "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
        "meta": {"filename": "cube.kicad_pro", "version": 3},
        "net_settings": {
            "classes": NETCLASSES,
            "meta": {"version": 4},
            "net_colors": None,
            "netclass_assignments": NET_ASSIGN,
            "netclass_patterns": [],
        },
        "pcbnew": {
            "last_paths": {"gencad": "", "idf": "", "netlist": "",
                           "plot": "", "pos_files": "", "specctra_dsn": "",
                           "step": "", "svg": "", "vrml": ""},
            "page_layout_descr_file": "",
        },
        "schematic": {
            "annotate_start_num": 0,
            "bom_fmt_presets": [], "bom_fmt_settings": {},
            "bom_presets": [], "bom_settings": {},
            "connection_grid_size": 50.0,
            "drawing": {
                "dashed_lines_dash_length_ratio": 12.0,
                "dashed_lines_gap_length_ratio": 3.0,
                "default_line_thickness": 6.0,
                "default_text_size": 50.0,
                "field_names": [],
                "intersheets_ref_own_page": False,
                "intersheets_ref_prefix": "",
                "intersheets_ref_short": False,
                "intersheets_ref_show": False,
                "intersheets_ref_suffix": "",
                "junction_size_choice": 3,
                "label_size_ratio": 0.375,
                "operating_point_overlay_i_precision": 3,
                "operating_point_overlay_i_range": "~A",
                "operating_point_overlay_v_precision": 3,
                "operating_point_overlay_v_range": "~V",
                "overbar_offset_ratio": 1.23,
                "pin_symbol_size": 25.0,
                "text_offset_ratio": 0.15,
            },
            "legacy_lib_dir": "", "legacy_lib_list": [],
            "meta": {"version": 1},
            "net_format_name": "",
            "page_layout_descr_file": "",
            "plot_directory": "",
            "spice_current_sheet_as_root": False,
            "spice_external_command": 'spice "%I"',
            "spice_model_current_sheet_as_root": True,
            "spice_save_all_currents": False,
            "spice_save_all_dissipations": False,
            "spice_save_all_voltages": False,
            "subpart_first_id": 65,
            "subpart_id_separator": 0,
        },
        "sheets": [["00000000-0000-0000-0000-000000000000", "Root"]],
        "text_variables": {},
    }


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # ---- cube.kicad_pro ----
    pro = kicad_pro()
    pro["sheets"] = [[gen_sch.uid("root-sheet"), "Root"]]
    with open(os.path.join(OUT_DIR, "cube.kicad_pro"), "w", encoding="utf-8") as fh:
        json.dump(pro, fh, indent=2)

    # ---- cube.kicad_sym : symboles maison ----
    lib = [Sym("kicad_symbol_lib"),
           [Sym("version"), Sym("20241209")],
           [Sym("generator"), "kicad_symbol_editor"],
           [Sym("generator_version"), "9.0"]]
    for name, spec in D.CUSTOM_SYMBOLS.items():
        lib.append(gen_sch.build_custom_symbol(name, spec))
    with open(os.path.join(OUT_DIR, "cube.kicad_sym"), "w", encoding="utf-8") as fh:
        fh.write(sexpr.dump(lib) + "\n")

    # ---- tables de librairies locales ----
    with open(os.path.join(OUT_DIR, "sym-lib-table"), "w", encoding="utf-8") as fh:
        fh.write('(sym_lib_table\n  (version 7)\n'
                 '  (lib (name "cube")(type "KiCad")'
                 '(uri "${KIPRJMOD}/cube.kicad_sym")(options "")'
                 '(descr "Symboles specifiques au projet CUBE"))\n)\n')
    with open(os.path.join(OUT_DIR, "fp-lib-table"), "w", encoding="utf-8") as fh:
        fh.write('(fp_lib_table\n  (version 7)\n)\n')

    for f in ("cube.kicad_pro", "cube.kicad_sym", "sym-lib-table", "fp-lib-table"):
        print("ecrit hw/%s" % f)


if __name__ == "__main__":
    main()
