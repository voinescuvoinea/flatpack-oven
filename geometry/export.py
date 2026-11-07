"""Export oven B: STEP assembly, SVG views, and 1:1 DXF templates for cutting.

Run: uv run python -m geometry.export   -> geometry/out/ (STEP, SVG), bom/dxf/ (DXF)
"""

from __future__ import annotations

import math
from pathlib import Path

import cadquery as cq
import ezdxf

from geometry import end_walls as ew
from geometry.oven_b import OvenB, Params

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "geometry" / "out"
DXF = ROOT / "bom" / "dxf"


def _doc(title: str):
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    msp = doc.modelspace()
    for name, color in (("CUT", 1), ("MARK", 3), ("HOLES", 5), ("TEXT", 7)):
        doc.layers.add(name, color=color)
    return doc, msp


def _label(msp, text, x, y, h=12):
    msp.add_text(text, height=h, dxfattribs={"layer": "TEXT"}).set_placement((x, y))


def _arc_poly(cx, cz, R, a0, a1, n=48):
    return [(cx + R * math.cos(a0 + (a1 - a0) * i / n), cz + R * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def former_rib(p: Params):
    """Plywood former rib: top = vault intrados minus 3 mm (room to strike the former), flat base 100 mm below springing."""
    a = p.arch
    doc, msp = _doc("former")
    R = a["R_i"] - 3
    h = a["half_angle"]
    top = _arc_poly(0, a["z_c"] - p.z_spring, R, math.pi / 2 + h, math.pi / 2 - h)
    base = -100.0
    pts = [(top[0][0], base)] + top + [(top[-1][0], base)]
    msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "CUT"})
    msp.add_line((-p.span / 2, 0), (p.span / 2, 0), dxfattribs={"layer": "MARK"})
    _label(msp, f"FORMER RIB - 3 off, 18 mm plywood. Line = springing level. Intrados R {a['R_i']:.0f} mm minus 3 mm.", -p.span / 2, base - 40)
    doc.saveas(DXF / "former_rib.dxf")


def skewback_template(p: Params):
    a = p.arch
    doc, msp = _doc("skewback")
    ang = a["half_angle"]
    xe, ze = p.bT * math.sin(ang), p.bT * math.cos(ang)
    pts = [(0, 0), (p.bT, 0), (p.bT, ze), (xe, ze)]
    msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "CUT"})
    msp.add_lwpolyline([(0, 0), (p.bT, 0), (p.bT, p.bW), (0, p.bW)], close=True, dxfattribs={"layer": "MARK"})
    _label(msp, f"SKEWBACK - end view of the brick (64 x 114 outline). Cut along the {math.degrees(ang):.1f} deg face. 8 off.", 0, -30, 6)
    doc.saveas(DXF / "skewback_template.dxf")


def end_wall(p: Params, front: bool):
    a = p.arch
    doc, msp = _doc("end wall")
    w = p.x_wall_out
    outline = [(-w, p.z_casi_top), (w, p.z_casi_top)]
    th0 = math.acos(w / a["R_e"])
    outline += _arc_poly(0, a["z_c"], a["R_e"], th0, math.pi - th0)
    msp.add_lwpolyline(outline, close=True, dxfattribs={"layer": "CUT"})
    msp.add_lwpolyline(_arc_poly(0, a["z_c"], a["R_i"], math.pi / 2 - a["half_angle"], math.pi / 2 + a["half_angle"]),
                       dxfattribs={"layer": "MARK"})  # vault intrados for reference
    for c in ew.courses(p, front):
        for (x0, x1) in c["segments_mm"]:
            msp.add_line((x0, c["z_bottom_mm"]), (x1, c["z_bottom_mm"]), dxfattribs={"layer": "MARK"})
            x = x0
            for pc in c["pieces"]:
                x += pc.length_mm
                if x < x1 - 1:
                    msp.add_line((x, c["z_bottom_mm"]), (x, c["z_top_mm"]), dxfattribs={"layer": "MARK"})
        _label(msp, f"C{c['course']}", w + 20, c["z_bottom_mm"] + 20)
    if front:
        d = ew.door_geometry(p)
        msp.add_lwpolyline([(-p.door_w / 2, p.z_floor), (-p.door_w / 2, d["z_spring"])], dxfattribs={"layer": "CUT"})
        msp.add_lwpolyline([(p.door_w / 2, p.z_floor), (p.door_w / 2, d["z_spring"])], dxfattribs={"layer": "CUT"})
        for R in (d["Rd"], d["Rd"] + d["radial"]):
            msp.add_lwpolyline(_arc_poly(0, d["zc"], R, math.pi / 2 - d["half_angle"], math.pi / 2 + d["half_angle"]), dxfattribs={"layer": "CUT"})
        for i in range(d["n_voussoirs"] + 1):
            t = math.pi / 2 - d["half_angle"] + 2 * d["half_angle"] * i / d["n_voussoirs"]
            msp.add_line((d["Rd"] * math.cos(t), d["zc"] + d["Rd"] * math.sin(t)),
                         ((d["Rd"] + d["radial"]) * math.cos(t), d["zc"] + (d["Rd"] + d["radial"]) * math.sin(t)), dxfattribs={"layer": "MARK"})
        msp.add_line((-p.door_w / 2, p.z_floor), (p.door_w / 2, p.z_floor), dxfattribs={"layer": "MARK"})
    _label(msp, f"{'FRONT' if front else 'BACK'} END WALL - elevation seen from outside, 1:1. Red = cut lines, green = joints/course lines. "
                f"z = mm above concrete base.", -w, p.z_casi_top - 40, 10)
    doc.saveas(DXF / f"end_wall_{'front' if front else 'back'}.dxf")


def _envelope_pts(p: Params, grow: float):
    a = p.arch
    w = p.x_wall_out + grow
    Re = a["R_e"] + grow
    th0 = math.acos(w / Re)
    return [(-w, 0.0), (w, 0.0)] + _arc_poly(0, a["z_c"], Re, th0, math.pi - th0)


def end_panels(p: Params):
    grow = p.ins_t + p.shell_t
    for front in (True, False):
        doc, msp = _doc("panel")
        pts = _envelope_pts(p, grow)
        msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "CUT"})
        # 20 mm return flange marking + fixing holes every ~150 mm along the curved/side edge, 25 mm in
        inner = _envelope_pts(p, grow - 25)
        perim = inner[2:] + [inner[0]]
        for (x0, z0), (x1, z1) in zip([inner[1]] + perim[:-1], perim):
            seg = math.hypot(x1 - x0, z1 - z0)
            n = max(1, int(seg // 150))
            for i in range(n):
                t = (i + 0.5) / n
                msp.add_circle((x0 + t * (x1 - x0), z0 + t * (z1 - z0)), 3.25, dxfattribs={"layer": "HOLES"})
        if front:
            d = ew.door_geometry(p)
            m = 30
            Rm = d["Rd"] + m
            th = math.asin(min((p.door_w / 2 + m) / Rm, 1.0))
            hole = [(-(p.door_w / 2 + m), p.z_floor - m), (p.door_w / 2 + m, p.z_floor - m)]
            hole += _arc_poly(0, d["zc"], Rm, math.pi / 2 - th, math.pi / 2 + th)
            msp.add_lwpolyline(hole, close=True, dxfattribs={"layer": "CUT"})
        _label(msp, f"END PANEL {'FRONT' if front else 'BACK'} - steel 1 mm, holes 6.5 mm for M6 / self-drilling screws. z = mm above base.",
               pts[0][0], -40, 10)
        doc.saveas(DXF / f"end_panel_{'front' if front else 'back'}.dxf")


def shell_sheet(p: Params):
    a = p.arch
    grow = p.ins_t
    w = p.x_wall_out + grow
    Re = a["R_e"] + grow
    th0 = math.acos(w / Re)
    z_side = a["z_c"] + Re * math.sin(th0)
    developed = 2 * z_side + Re * (math.pi - 2 * th0)
    length = p.y_back_out - p.y_front_out + 2 * p.ins_t
    doc, msp = _doc("shell")
    msp.add_lwpolyline([(0, 0), (developed, 0), (developed, length), (0, length)], close=True, dxfattribs={"layer": "CUT"})
    for xb in (z_side, developed - z_side):
        msp.add_line((xb, 0), (xb, length), dxfattribs={"layer": "MARK"})
    _label(msp, f"SHELL - pre-painted sheet 0.5 mm, developed {developed:.0f} x {length:.0f} mm (may be 2-3 strips with 50 mm overlaps). "
                "Green = start of curve.", 0, -40, 15)
    doc.saveas(DXF / "shell_sheet.dxf")
    return developed, length


def door_and_hood(p: Params):
    doc, msp = _doc("door")
    W, H = p.door_w + 40, p.door_h + 30
    msp.add_lwpolyline([(0, 0), (W, 0), (W, H), (0, H)], close=True, dxfattribs={"layer": "CUT"})
    for x in (W * 0.25, W * 0.75):
        msp.add_circle((x, H * 0.6), 4.25, dxfattribs={"layer": "HOLES"})
    _label(msp, "DOOR FRONT PLATE - 1 mm steel, folded into a 50 mm deep box, filled with Superwool. Handle holes 8.5 mm.", 0, -30, 10)
    doc.saveas(DXF / "door_front.dxf")
    doc, msp = _doc("hood")
    Wh, D, Hh = p.door_w + 80, p.hood_depth, 200
    x = 0
    for name, (a_, b_) in (("TOP (with flue hole)", (Wh, D)), ("FRONT", (Wh, Hh)), ("SIDE L", (D, Hh)), ("SIDE R", (D, Hh))):
        msp.add_lwpolyline([(x, 0), (x + a_, 0), (x + a_, b_), (x, b_)], close=True, dxfattribs={"layer": "CUT"})
        if name.startswith("TOP"):
            msp.add_circle((x + a_ / 2, b_ / 2), p.flue_d / 2, dxfattribs={"layer": "CUT"})
        _label(msp, name, x, -25, 10)
        x += a_ + 40
    _label(msp, "FLUE HOOD - 2 mm black steel (not galvanized). Bolt together with 20 mm folded flanges; Ø150 collar for stove pipe.", 0, -60, 10)
    doc.saveas(DXF / "hood_parts.dxf")


def views(ov: OvenB):
    OUT.mkdir(parents=True, exist_ok=True)
    asm = ov.assembly()
    asm.save(str(OUT / "oven_b.step"))
    opts = {"width": 900, "height": 650, "marginLeft": 20, "marginTop": 20, "showAxes": False, "strokeWidth": 0.4, "showHidden": False}

    def svg(parts, name, d):
        # CadQuery's SVG image 'up' is reversed for these directions: rotate 180 deg about the view axis (no mirroring)
        comp = cq.Compound.makeCompound([pt.solid.val() for pt in parts]).rotate((0, 0, 0), d, 180)
        cq.exporters.export(comp, str(OUT / name), opt=dict(opts, projectionDir=d))

    svg(ov.parts, "oven_b_iso.svg", (1.0, -1.2, 0.8))
    svg(ov.parts, "oven_b_front.svg", (0.0, -1.0, 0.0))
    svg([pt for pt in ov.parts if "brick" in pt.family or pt.family in ("floor insulation", "thrust strips")], "oven_b_bricks_iso.svg", (1.0, -1.2, 0.8))
    svg([pt for pt in ov.parts if pt.family in ("floor bricks", "side wall bricks", "skewback bricks", "floor insulation")],
        "oven_b_floor_iso.svg", (1.0, -1.2, 0.8))


def main():
    DXF.mkdir(parents=True, exist_ok=True)
    p = Params()
    ov = OvenB(p).build()
    former_rib(p)
    skewback_template(p)
    end_wall(p, False)
    end_wall(p, True)
    end_panels(p)
    dev = shell_sheet(p)
    door_and_hood(p)
    views(ov)
    print("shell developed x length mm:", [round(v) for v in dev])


if __name__ == "__main__":
    main()
