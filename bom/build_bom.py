"""Bill of materials for oven B, generated from the CAD model, the end-wall course tables and the
materials DB (prices). Nothing is priced unless the DB has a dated supplier price; everything else
is listed with quantity and marked QUOTE.

Run: uv run python -m bom.build_bom   -> bom/bom.csv, bom/bom.md, bom/cut_list.md
"""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path

from geometry import end_walls as ew
from geometry.concepts import FX_SOURCE, to_usd
from geometry.oven_b import OvenB, Params
from materials import db

HERE = Path(__file__).parent
SPARE_BRICKS = 0.10          # allowance for breakage / mis-cuts (design allowance)
CUT_WASTE_BOARD = 0.15       # allowance for board / blanket cutting waste (design allowance)
MORTAR_KG_PER_L = 2.0        # ASSUMPTION: wet-mixed fireclay mortar, ~2 kg dry powder per litre of joint
MORTAR_WASTE = 0.30          # allowance


def _price(mats, mid, qty):
    s = mats[mid].suppliers[0]
    return to_usd(qty * float(s["price"]), s["currency"]), f'{s["name"]}: {s["price"]} {s["currency"]}/{s["per"]} ({s["date_checked"]})'


def vault_mortar_litres(p: Params) -> float:
    a = p.arch
    Ri, Re = a["R_i"], a["R_e"]
    pitch = (p.bW + p.arch_joint_in) / Ri
    g_out = pitch * Re - p.bW
    per_joint = 0.5 * (p.arch_joint_in + g_out) * p.bT * p.length  # mm3
    return (p.arch_courses - 1 + 2) * per_joint * 1e-6  # + 2 skewback joints


def door_arch_mortar_litres(p: Params) -> float:
    d = ew.door_geometry(p)
    pitch = (p.bT + d["joint_in_mm"]) / d["Rd"]
    g_out = pitch * (d["Rd"] + d["radial"]) - p.bT
    return (d["n_voussoirs"] - 1) * 0.5 * (d["joint_in_mm"] + g_out) * d["radial"] * p.end_t * 1e-6


def build():
    p = Params()
    mats = db.load()
    ov = OvenB(p).build()
    parts = {pt.pid: pt for pt in ov.parts}
    rows = []

    def add(group, item, qty, unit, mat=None, priced_qty=None, note=""):
        if mat and mats[mat].suppliers and priced_qty is not None:
            usd, src = _price(mats, mat, priced_qty)
            rows.append([group, item, round(qty, 2), unit, round(usd, 2), src, note])
        else:
            rows.append([group, item, round(qty, 2), unit, "QUOTE", "", note])

    # ---- bricks
    fam = defaultdict(float)
    for pt in ov.parts:
        if pt.material == "refarom_65sa_brick" and pt.family not in ("end wall bricks",):
            fam[pt.family] += 0.5 if "half" in pt.name else 1.0
    back = sum(c["bricks"] for c in ew.courses(p, False))
    front = sum(c["bricks"] for c in ew.courses(p, True))
    door = ew.door_arch_bricks(p)
    n_bricks = sum(fam.values()) + back + front + door
    n_buy = math.ceil(n_bricks * (1 + SPARE_BRICKS))
    detail = ", ".join(f"{k} {v:g}" for k, v in fam.items()) + f", back wall {back:g}, front wall {front:g}, door arch {door:g}"
    add("Refractory", "Fireclay brick Refarom 65 SA 230x114x64", n_buy, "pcs", "refarom_65sa_brick", n_buy,
        f"{n_bricks:g} in the model ({detail}) + {SPARE_BRICKS:.0%} spares")
    mortar_l = vault_mortar_litres(p) + door_arch_mortar_litres(p) + 0.04 * parts["E-F"].volume_m3 * 1000
    bags = math.ceil(mortar_l * MORTAR_KG_PER_L * (1 + MORTAR_WASTE) / 25)
    add("Refractory", "Helios refractory mortar MC-29A, 25 kg", bags, "bags", "helios_refractory_mortar_mc29a", bags,
        f"V-joints of vault ({vault_mortar_litres(p):.1f} L) and door arch ({door_arch_mortar_litres(p):.1f} L), front-wall joints; "
        f"{MORTAR_KG_PER_L} kg/L is an ASSUMPTION")
    add("Refractory", "Fermit stove sealant 310 ml (hood-to-front-wall joint)", 2, "cartridges", "fermit_stove_sealant", 2)
    # ---- insulation
    casi_v = sum(pt.volume_m3 for pt in ov.parts if pt.material == "casi_board_cs270")
    sheets = math.ceil(casi_v / (1.2 * 0.6 * 0.025) * (1 + CUT_WASTE_BOARD))
    add("Insulation", "CaSi board CS-270 1200x600x25", sheets, "sheets", "casi_board_cs270", sheets,
        f"floor {p.casi_layers} layers + thrust strips = {casi_v*1000:.0f} L + {CUT_WASTE_BOARD:.0%} waste")
    sw_v = sum(pt.volume_m3 for pt in ov.parts if pt.material == "superwool_plus_blanket_128")
    sw_m2 = sw_v / 0.025 * (1 + CUT_WASTE_BOARD)
    rolls = math.ceil(sw_m2 / 4.46)
    add("Insulation", "Superwool Plus blanket 128 kg/m3, 25 mm, roll 7.32 x 0.61 m", rolls, "rolls", "superwool_plus_blanket_128", rolls,
        f"{sw_m2:.1f} m2 of 25 mm (2 layers on vault, sides, ends)")
    rw_v = sum(pt.volume_m3 for pt in ov.parts if pt.material == "prorox_wm960es")
    add("Insulation", "ROCKWOOL ProRox WM 960ES wired mat, 100 mm (or 2 x 50 mm)", rw_v / 0.1 * (1 + CUT_WASTE_BOARD), "m2", None, None,
        "outer layer; mesh side outwards")
    gasket = (2 * (p.floor_cols * p.bW + p.length) * p.bT + 2 * p.arch["arc_in"] * p.bT + 4 * p.wall_h * p.bT) * 1e-6
    add("Insulation", "Superwool 6 mm blanket/paper strips for 5 mm expansion gaskets", gasket * 1.3, "m2", None, None,
        "floor perimeter, vault-to-end-wall and side-wall-to-end-wall joints")
    # ---- steel
    def steel_kg(pids):
        rho = mats["stainless_1_4301_sheet"]["density"].at(300.0)
        return sum(parts[i].volume_m3 for i in pids) * rho
    ang_len = sum(parts[i].solid.val().BoundingBox().ylen if i.startswith("K-") else parts[i].solid.val().BoundingBox().zlen
                  for i in ("K-L", "K-R", "B-LF", "B-LB", "B-RF", "B-RB")) / 1000
    add("Steel frame", "Angle L50x50x5 S235 (2 skewback rails + 4 buckstays), cut list in cut_list.md", ang_len + 4 * 0.10, "m",
        note=f"{steel_kg(['K-L','K-R','B-LF','B-LB','B-RF','B-RB']):.0f} kg incl. 4 x 100 mm foot cleats")
    add("Steel frame", "Threaded rod M12 (tie rods)", 2 * parts["T-F"].solid.val().BoundingBox().xlen / 1000, "m", note="zinc-plated OK (outside shell)")
    add("Steel frame", "Disc springs DIN 2093 for M12 (Di 12.2 mm), stacked in series for >= 8 mm travel", 2 * 12, "pcs",
        note="arch thrust ~0.35 kN per rod; choose spring size for ~0.4 kN preload at mid-travel")
    add("Steel frame", "M12 nuts + large washers; M10 bolts for rail-to-buckstay joints", 1, "set")
    add("Steel frame", "M12 anchors for buckstay foot cleats (chemical or expansion)", 8, "pcs", note="positions in base interface drawing")
    add("Shell", "Pre-painted flat steel roofing sheet 0.5 mm (barrel shell)", parts["P-SH"].volume_m3 / 0.0005, "m2",
        note="paint emissivity ~0.92; no aluminium-look paint (low emissivity)")
    add("Shell", "Steel sheet 1 mm for end panels (DXF)", (parts["P-EF"].volume_m3 + parts["P-EB"].volume_m3) / 0.001, "m2")
    add("Shell", "Self-drilling screws with EPDM washers for shell", 60, "pcs")
    add("Door & flue", "Steel sheet 1 mm for door box + Superwool offcut filling, 2 wooden handles", 1, "set",
        note=f"{steel_kg(['D-1']):.1f} kg steel")
    add("Door & flue", "Black steel sheet 2 mm for flue hood (DXF), NOT galvanized", parts["H-1"].volume_m3 / 0.002, "m2",
        note=f"{steel_kg(['H-1']):.1f} kg")
    add("Door & flue", "Stove pipe Ø150 black steel 1 m + rain cap (roof interface R-I1)", 1, "set")
    add("Finishes", "Heat-resistant paint (frame, hood, pipe)", 1, "set")
    add("Temporary", "Arch former: 18 mm plywood (3 ribs from DXF) + slats + wedges", 1, "set", note="reusable for repairs")

    priced = sum(r[4] for r in rows if r[4] != "QUOTE")
    return p, ov, rows, priced


def cut_list(p: Params, ov) -> str:
    a = p.arch
    lines = ["# Cut list - oven B (generated by `bom/build_bom.py`)", "",
             "Grinder with a diamond disc for bricks (wet or with dust extraction, FFP3 mask). Saw or knife for boards and blankets.", "",
             "## Bricks", "",
             f"- Floor: {p.floor_cols} columns x {p.floor_rows} rows laid flat (long side front-to-back). "
             f"Columns 2, 4, 6 start and end with a half brick (115 mm): 3 bricks cut in half.",
             f"- Side walls: {2*round(p.length/p.bW)} bricks standing on end, no cuts.",
             f"- Skewbacks: 8 bricks, each cut lengthwise so one face lies at {math.degrees(a['half_angle']):.1f}° from vertical "
             f"(template `dxf/skewback_template.dxf`).",
             f"- Vault: {p.arch_courses} courses, bricks laid flat. Courses 2, 4, 6, 8 start and end with a half brick: 4 bricks cut in half. "
             f"Joints: {p.arch_joint_in:.0f} mm at the intrados, opening to "
             f"{(p.bW + p.arch_joint_in) / a['R_i'] * a['R_e'] - p.bW:.1f} mm at the back (fill with mortar).",
             ]
    d = ew.door_geometry(p)
    lines.append(f"- Door arch: {d['n_voussoirs']} half bricks (115 mm long) on edge, radius {d['Rd']:.0f} mm, rise {p.door_arch_rise:.0f} mm.")
    for front in (False, True):
        lines += ["", f"### {'Front' if front else 'Back'} end wall: courses (bricks laid flat, 114 mm deep)", "",
                  "| Course | z bottom (mm above base) | Pieces left to right (mm; * = top follows the curve, cut to template) | Bricks |", "|---|---|---|---|"]
        for c in ew.courses(p, front):
            pcs = " · ".join(f"{pc.length_mm:.0f}{'*' if pc.curved_top else ''}" for pc in c["pieces"])
            lines.append(f"| {c['course']} | {c['z_bottom_mm']:.0f} | {pcs} | {c['bricks']:g} |")
    lines += ["", "## Boards (CaSi 1200 x 600 x 25)", "",
              f"- Floor insulation: {p.casi_layers} layers, each {2*(p.x_wall_out+p.casi_margin):.0f} x {p.y_back_out-p.y_front_out+2*p.casi_margin:.0f} mm "
              "(2 boards + strip per layer; stagger the seams between layers).",
              f"- Thrust strips: 2 off, {p.y_back_out-p.y_front_out:.0f} mm long, {p.ins_t:.0f} mm (6 boards) wide x {p.thrust_strip_h:.0f} mm high: "
              "boards cut into 64 mm strips and stood on edge.",
              "", "## Steel (S235 angle L50x50x5)", ""]
    for pid in ("K-L", "K-R", "B-LF", "B-LB", "B-RF", "B-RB"):
        pt = next(x for x in ov.parts if x.pid == pid)
        bb = pt.solid.val().BoundingBox()
        L = bb.ylen if pid.startswith("K-") else bb.zlen
        lines.append(f"- {pid}: {pt.name.split(',')[0]} - {L:.0f} mm")
    lines.append("- 4 foot cleats, 100 mm each; drill per base interface drawing.")
    lines += ["", "## DXF files (`bom/dxf/`)", "",
              "former_rib (3 off, 18 mm plywood), skewback_template, end_wall_back, end_wall_front (1:1 templates with course lines), "
              "end_panel_front, end_panel_back, shell_sheet (developed), door_front, hood_parts."]
    return "\n".join(lines) + "\n"


def main():
    p, ov, rows, priced = build()
    with open(HERE / "bom.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["group", "item", "qty", "unit", "cost_usd", "price_source", "note"])
        w.writerows(rows)
    n_quote = sum(1 for r in rows if r[4] == "QUOTE")
    md = ["# Bill of materials - oven B (generated by `bom/build_bom.py`, do not edit by hand)", "",
          f"Prices converted with {FX_SOURCE}. 'QUOTE' = no sourced price yet (never guessed).", "",
          "| Group | Item | Qty | Unit | USD | Note |", "|---|---|---|---|---|---|"]
    for g, it, q, u, c, src, note in rows:
        md.append(f"| {g} | {it} | {q:g} | {u} | {c if c == 'QUOTE' else f'{c:.0f}'} | {note} |")
    md += ["", f"**Priced subtotal: {priced:.0f} USD** of the ~1000 USD budget (R-C1). {n_quote} lines still need quotes.", "",
           "Excluded by scope: concrete base (R-F4), roof (R-E1), measurement kit (separate line, Phase 4)."]
    (HERE / "bom.md").write_text("\n".join(md) + "\n")
    (HERE / "cut_list.md").write_text(cut_list(p, ov))
    print("\n".join(md))


if __name__ == "__main__":
    main()
