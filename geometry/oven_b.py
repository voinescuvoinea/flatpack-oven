"""Parametric CadQuery model of oven B (firebrick barrel vault in a bolted steel frame).

All dimensions are named parameters in millimetres (CadQuery convention).
Coordinates: x across the span (0 = centre line), y depth (0 = inner face of the front
end wall gasket line / front of the floor field), z up (0 = top of the user's concrete base).

Every physical part is generated as a numbered solid with a material id from the
materials DB, so masses and the BOM come from the model, not from hand counts.

Run: uv run python -m geometry.oven_b   -> exports to geometry/out/
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import cached_property

import cadquery as cq

from simulation.expansion import arch_arc_length, rise_for_arc_length


@dataclass(frozen=True)
class Params:
    # standard fireclay brick (Refarom 65 SA)
    bL: float = 230.0
    bW: float = 114.0
    bT: float = 64.0
    # floor field: bricks laid flat, long side along y, staggered columns
    floor_cols: int = 7
    floor_rows: int = 4
    floor_gap: float = 5.0          # floating floor: fibre-filled gap to walls (expansion)
    # floor insulation (CaSi CS-270 boards)
    casi_layers: int = 5           # 125 mm: keeps the concrete base cooler in long sessions (decision 0005)
    casi_t: float = 25.0
    casi_margin: float = 50.0       # boards extend 50 mm beyond the brickwork
    # side walls: bricks standing on end on the CaSi
    wall_h: float = 230.0
    # vault: bricks laid flat, 8 courses (crown ~360 mm above floor), V-joints filled with refractory mortar
    arch_courses: int = 8
    arch_joint_in: float = 2.0      # joint thickness at the intrados
    # end walls: bricks laid flat in courses, 114 thick
    end_t: float = 114.0
    end_gasket: float = 5.0         # fibre gasket between vault/floor and end walls
    course_h: float = 66.0          # 64 brick + 2 joint
    # door (front wall opening), small segmental brick arch on top
    door_w: float = 520.0
    door_h: float = 240.0           # above the cooking floor
    door_arch_rise: float = 120.0   # segmental door arch of half bricks (lower thrust than a flat arch)
    # insulation on vault, side walls and end walls
    sw_t: float = 50.0              # Superwool Plus, 2 x 25 mm (hot side)
    rw_t: float = 100.0             # ProRox WM 960ES (cold side, mesh outwards)
    # steel
    shell_t: float = 0.5            # pre-painted flat roofing sheet over the barrel
    panel_t: float = 1.0            # end panels
    ang: float = 50.0               # L50x50x5 angles (skewbacks, buckstays)
    ang_t: float = 5.0
    thrust_strip_h: float = 64.0    # CaSi thrust strip (boards on edge) through the insulation at springing level
    rod_d: float = 12.0             # M12 tie rods
    flue_d: float = 150.0
    hood_depth: float = 220.0

    # ---------------- derived geometry ----------------
    @property
    def span(self) -> float:
        return self.floor_cols * self.bW + 2 * self.floor_gap

    @property
    def length(self) -> float:
        return self.floor_rows * self.bL

    @property
    def z_casi_top(self) -> float:
        return self.casi_layers * self.casi_t

    @property
    def z_floor(self) -> float:
        return self.z_casi_top + self.bT

    @property
    def z_spring(self) -> float:
        return self.z_casi_top + self.wall_h

    @cached_property
    def arch(self) -> dict:
        arc = self.arch_courses * self.bW + (self.arch_courses - 1) * self.arch_joint_in
        f = rise_for_arc_length(self.span / 1000, arc / 1000) * 1000
        R = (self.span**2 / 4 + f**2) / (2 * f)
        half = math.asin(self.span / (2 * R))
        return {"rise": f, "R_i": R, "R_e": R + self.bT, "half_angle": half, "z_c": self.z_spring + f - R,
                "crown_above_floor": self.z_spring + f - self.z_floor, "arc_in": arc}

    @property
    def x_wall_out(self) -> float:
        return self.span / 2 + self.bT

    @property
    def y_back_out(self) -> float:
        return self.length + self.end_gasket + self.end_t

    @property
    def y_front_out(self) -> float:
        return -(self.end_gasket + self.end_t)

    @property
    def ins_t(self) -> float:
        return self.sw_t + self.rw_t


@dataclass
class Part:
    pid: str
    name: str
    family: str
    material: str | None
    solid: cq.Workplane
    note: str = ""

    @property
    def volume_m3(self) -> float:
        return self.solid.val().Volume() * 1e-9


@dataclass
class OvenB:
    p: Params = field(default_factory=Params)
    parts: list[Part] = field(default_factory=list)

    def add(self, pid, name, family, material, solid, note=""):
        self.parts.append(Part(pid, name, family, material, solid, note))

    # ------------------------------------------------------------------ build
    def build(self) -> "OvenB":
        self._floor_insulation()
        self._floor()
        self._side_walls()
        self._skewbacks()
        self._vault()
        self._end_walls()
        self._insulation()
        self._steel()
        return self

    def _box(self, dx, dy, dz, x, y, z):
        """Axis-aligned box with its min corner at (x, y, z)."""
        return cq.Workplane("XY").box(dx, dy, dz, centered=False).translate((x, y, z))

    def _floor_insulation(self):
        p = self.p
        w = 2 * (p.x_wall_out + p.casi_margin)
        y0 = p.y_front_out - p.casi_margin
        d = p.y_back_out - p.y_front_out + 2 * p.casi_margin
        for i in range(p.casi_layers):
            self.add(f"I-{i+1}", f"Floor insulation layer {i+1} (CaSi 25 mm, cut from 1200x600 boards)", "floor insulation",
                     "casi_board_cs270", self._box(w, d, p.casi_t, -w / 2, y0, i * p.casi_t))

    def _floor(self):
        p = self.p
        x0 = -p.floor_cols * p.bW / 2
        n = 0
        for c in range(p.floor_cols):
            x = x0 + c * p.bW
            # odd columns start with a half brick so cross-joints do not line up
            pieces = [p.bL] * p.floor_rows if c % 2 == 0 else [p.bL / 2] + [p.bL] * (p.floor_rows - 1) + [p.bL / 2]
            y = 0.0
            for L in pieces:
                n += 1
                half = "half brick" if L < p.bL else "brick"
                self.add(f"F-{n:02d}", f"Floor {half} col {c+1}", "floor bricks", "refarom_65sa_brick",
                         self._box(p.bW, L, p.bT, x, y, p.z_casi_top), note="cut" if L < p.bL else "")
                y += L

    def _side_walls(self):
        p = self.p
        n_per = round(p.length / p.bW)
        pitch = p.length / n_per
        for side, sx in (("L", -1), ("R", 1)):
            for i in range(n_per):
                x = sx * p.span / 2 if sx > 0 else -p.span / 2 - p.bT
                self.add(f"W{side}-{i+1}", f"Side wall {side} brick {i+1} (on end)", "side wall bricks", "refarom_65sa_brick",
                         self._box(p.bT, p.bW, p.wall_h, x, i * pitch, p.z_casi_top))

    def _skewbacks(self):
        """Skewback: a brick cut so its inner face lies on the springing radial plane."""
        p, a = self.p, self.p.arch
        ang = a["half_angle"]  # radial plane at springing is tilted by `ang` from vertical
        for side, sx in (("L", -1), ("R", 1)):
            for i in range(p.floor_rows):
                # profile in the x-z plane (right side), then mirrored for the left side
                xi, zi = p.span / 2, p.z_spring
                xe, ze = xi + p.bT * math.sin(ang), zi + p.bT * math.cos(ang)
                outer = p.span / 2 + p.bT  # skewback brick sits on the wall, flush with its outer face
                pts = [(xi, zi), (outer, zi), (outer, ze), (xe, ze)]
                if sx < 0:
                    pts = [(-x, z) for x, z in pts][::-1]
                prof = cq.Workplane("XZ").polyline(pts).close().extrude(-p.bL).translate((0, i * p.bL, 0))
                self.add(f"S{side}-{i+1}", f"Skewback {side} {i+1} (brick cut to springing angle)", "skewback bricks",
                         "refarom_65sa_brick", prof, note="cut")

    def _vault(self):
        p, a = self.p, self.p.arch
        Ri, half = a["R_i"], a["half_angle"]
        dphi_b = p.bW / Ri
        dphi_j = p.arch_joint_in / Ri
        total = p.arch_courses * dphi_b + (p.arch_courses - 1) * dphi_j
        phi = -total / 2 + dphi_b / 2
        n = 0
        for k in range(p.arch_courses):
            pieces = [p.bL] * p.floor_rows if k % 2 == 0 else [p.bL / 2] + [p.bL] * (p.floor_rows - 1) + [p.bL / 2]
            y = 0.0
            for L in pieces:
                n += 1
                b = (cq.Workplane("XY").box(p.bW, L, p.bT, centered=(True, False, False))
                     .translate((0, y, Ri))
                     .rotate((0, 0, 0), (0, 1, 0), math.degrees(phi))
                     .translate((0, 0, a["z_c"])))
                self.add(f"A{k+1}-{n:02d}", f"Vault course {k+1} {'half brick' if L < p.bL else 'brick'}", "vault bricks",
                         "refarom_65sa_brick", b, note="cut" if L < p.bL else "")
                y += L
            phi += dphi_b + dphi_j

    def _arc_pts(self, w, Re, n=24):
        """Points on the extrados-type circle (centre z_c, radius Re) from x=+w over the top to x=-w."""
        zc = self.p.arch["z_c"]
        if Re <= w or zc + math.sqrt(Re**2 - w**2) < self.p.z_spring - 1e-6:
            raise ValueError("profile circle must meet the wall line above the springing")
        th0 = math.acos(w / Re)
        return [(Re * math.cos(th0 + (math.pi - 2 * th0) * i / n), zc + Re * math.sin(th0 + (math.pi - 2 * th0) * i / n)) for i in range(n + 1)]

    def _end_wall_outline(self, y0, y1):
        """Solid of one end wall: rectangle up to springing + segment up to the vault extrados."""
        p, a = self.p, self.p.arch
        w = p.x_wall_out
        Re = a["R_e"]
        z_top_c = a["z_c"] + Re
        pts = [(-w, p.z_casi_top), (w, p.z_casi_top)] + self._arc_pts(w, Re)
        prof = cq.Workplane("XZ").polyline(pts).close().extrude(-(y1 - y0)).translate((0, y0, 0))
        return prof, z_top_c

    def _end_walls(self):
        p, a = self.p, self.p.arch
        back, _ = self._end_wall_outline(p.length + p.end_gasket, p.y_back_out)
        self.add("E-B", "Back end wall (bricks laid flat in courses, top course cut to the vault profile)", "end wall bricks",
                 "refarom_65sa_brick", back, note="brick assembly; see cut list")
        front, _ = self._end_wall_outline(p.y_front_out, -p.end_gasket)
        # door opening: rectangle + segmental arch
        dw, dh, fr = p.door_w, p.door_h, p.door_arch_rise
        Rd = (dw**2 / 4 + fr**2) / (2 * fr)
        zc = p.z_floor + dh - Rd
        self._door_opening = (dw, dh, fr, Rd, zc)
        opening = self._door_cut(p.y_front_out - 1, p.end_t + 2, 0.0)
        self.add("E-F", "Front end wall with door opening (bricks laid flat; door arch of half bricks)", "end wall bricks",
                 "refarom_65sa_brick", front.cut(opening), note="brick assembly; see cut list")
        self._door_opening = (dw, dh, fr, Rd, zc)

    def _insulation(self):
        """Vault + side-wall insulation as two shells; end walls covered by flat blankets."""
        p, a = self.p, self.p.arch
        L0, L1 = p.y_front_out, p.y_back_out
        for pid, name, mat, r0, t in (("V-SW", "Vault+side insulation, Superwool Plus 2 x 25 mm", "superwool_plus_blanket_128", 0.0, p.sw_t),
                                     ("V-RW", "Vault+side insulation, ProRox WM 960ES 100 mm (mesh outside)", "prorox_wm960es", p.sw_t, p.rw_t)):
            outer = self._envelope(r0 + t, L0, L1)
            inner = self._envelope(r0, L0, L1)
            self.add(pid, name, "vault insulation", mat, outer.cut(inner))
        for side, y0 in (("front", L0 - p.ins_t), ("back", L1)):
            for pid_s, mat, t, off in (("SW", "superwool_plus_blanket_128", p.sw_t, 0.0), ("RW", "prorox_wm960es", p.rw_t, p.sw_t)):
                prof, _ = self._end_wall_outline(0, 1)
                # end cover = end-wall outline grown by the vault insulation thickness, as a flat blanket
                yy = (y0 + (p.ins_t - off - t) if side == "front" else y0 + off)
                blk = self._envelope(p.ins_t, yy, yy + t, end_cap=True)
                if side == "front":
                    blk = blk.cut(self._door_cut(yy - 1, t + 2, 30))
                self.add(f"E{pid_s}-{side[0].upper()}", f"End insulation {side}, {'Superwool 50 mm' if pid_s == 'SW' else 'ProRox 100 mm'}",
                         "end insulation", mat, blk)

    def _envelope(self, grow, y0, y1, end_cap=False):
        """Solid bounded by the oven's outer brick profile grown by `grow` mm, extruded y0..y1."""
        p, a = self.p, self.p.arch
        w = p.x_wall_out + grow
        Re = a["R_e"] + grow
        pts = [(-w, 0.0), (w, 0.0)] + self._arc_pts(w, Re)
        return cq.Workplane("XZ").polyline(pts).close().extrude(-(y1 - y0)).translate((0, y0, 0))

    def _steel(self):
        """All structural steel sits OUTSIDE the shell (cool). The arch thrust reaches it through
        continuous CaSi thrust strips that replace the insulation at springing level."""
        p, a = self.p, self.p.arch
        L0, L1 = p.y_front_out - p.ins_t, p.y_back_out + p.ins_t
        shell = self._envelope(p.ins_t + p.shell_t, L0, L1).cut(self._envelope(p.ins_t, L0 - 1, L1 + 1))
        self.add("P-SH", "Outer shell, pre-painted steel roofing sheet 0.5 mm, bent over the insulation", "shell", "stainless_1_4301_sheet",
                 shell, note="steel density proxy")
        for side, y in (("F", L0 - p.panel_t), ("B", L1)):
            panel = self._envelope(p.ins_t + p.shell_t, y, y + p.panel_t)
            if side == "F":
                panel = panel.cut(self._door_cut(y - 1, p.panel_t + 2, 30))
            self.add(f"P-E{side}", f"End panel {'front' if side == 'F' else 'back'}, steel 1 mm (DXF)", "shell", "stainless_1_4301_sheet", panel)

        def L_angle(length):
            prof = cq.Workplane("XZ").polyline([(0, 0), (p.ang, 0), (p.ang, p.ang_t), (p.ang_t, p.ang_t), (p.ang_t, p.ang), (0, p.ang)]).close()
            return prof.extrude(-length)

        x_out = p.x_wall_out + p.ins_t + p.shell_t  # outer face of the shell at the sides
        for side, sx in (("L", -1), ("R", 1)):
            x0 = p.x_wall_out if sx > 0 else -p.x_wall_out - p.ins_t
            strip = self._box(p.ins_t, p.y_back_out - p.y_front_out, p.thrust_strip_h, x0, p.y_front_out, p.z_spring)
            self.add(f"KS-{side}", f"Thrust strip {side}: CaSi boards on edge, 150 x 64 mm, full depth (carries arch thrust through the insulation)",
                     "thrust strips", "casi_board_cs270", strip)
            ang = L_angle(L1 - L0 + 2 * p.ang)
            if sx < 0:
                ang = ang.mirror("YZ")
            self.add(f"K-{side}", f"Skewback rail {side}, L50x50x5 outside the shell, bears on the thrust strip", "frame",
                     "stainless_1_4301_sheet", ang.translate((sx * x_out, L0 - p.ang, p.z_spring)), note="mild steel S235, painted")
        z_top = a["z_c"] + a["R_e"] + p.ins_t + p.shell_t + 2 * p.ang
        for side, sx in (("L", -1), ("R", 1)):
            for end, y in (("F", L0 - p.ang), ("B", L1)):
                post = L_angle(z_top).rotate((0, 0, 0), (1, 0, 0), 90).translate((x_out, y, 0))
                if sx < 0:
                    post = post.mirror("YZ")
                self.add(f"B-{side}{end}", f"Buckstay {side}{end}, L50x50x5, foot cleat anchored to base (2 x M12)", "frame",
                         "stainless_1_4301_sheet", post, note="mild steel S235, painted")
        for end, y in (("F", L0 - p.ang / 2), ("B", L1 + p.ang / 2)):
            half = x_out + p.ang + 80
            rod = cq.Workplane("YZ").circle(p.rod_d / 2).extrude(2 * half).translate((-half, y, z_top - p.ang / 2))
            self.add(f"T-{end}", f"Tie rod {end}, M12 threaded rod over the shell, disc-spring stack one end", "frame",
                     "stainless_1_4301_sheet", rod, note="zinc-plated OK (cool side)")
        dw, dh, fr, Rd, zc = self._door_opening
        y_face = L0 - p.panel_t
        door = self._box(dw + 40, 50, dh + 30, -(dw + 40) / 2, y_face - p.hood_depth - 50, p.z_floor - 5).faces(">Y").shell(-1.0)
        self.add("D-1", "Door, 1 mm steel box filled with Superwool, wooden handles (retention/curing only)", "door and flue",
                 "stainless_1_4301_sheet", door, note="steel shell mass only")
        hood = self._box(dw + 80, p.hood_depth, 200, -(dw + 80) / 2, y_face - p.hood_depth, p.z_floor + dh - 40).faces("<Z").shell(-2.0)
        hood = hood.cut(cq.Workplane("XY").circle(p.flue_d / 2).extrude(400).translate((0, y_face - p.hood_depth / 2, p.z_floor + dh)))
        self.add("H-1", "Flue hood (vestibule) over the mouth, 2 mm black steel (DXF)", "door and flue", "stainless_1_4301_sheet", hood)
        pipe = (cq.Workplane("XY").circle(p.flue_d / 2).circle(p.flue_d / 2 - 1.5).extrude(1000)
                .translate((0, y_face - p.hood_depth / 2, p.z_floor + dh + 160)))
        self.add("H-2", "Flue pipe Ø150 x 1000 mm, black steel stove pipe (not galvanized)", "door and flue", "stainless_1_4301_sheet", pipe)

    def _door_cut(self, y, depth, margin):
        """Prism of the door opening (rectangle + segmental arch) grown by `margin`, at y..y+depth."""
        p = self.p
        dw, dh, fr, Rd, zc = self._door_opening
        w2 = dw / 2 + margin
        R = Rd + margin
        th0 = math.asin(min(w2 / R, 1.0))
        pts = [(-w2, p.z_floor - margin), (w2, p.z_floor - margin)]
        pts += [(R * math.sin(th0 - 2 * th0 * i / 16), zc + R * math.cos(th0 - 2 * th0 * i / 16)) for i in range(17)]
        return cq.Workplane("XZ").polyline(pts).close().extrude(-depth).translate((0, y, 0))

    # ------------------------------------------------------------------ outputs
    def assembly(self) -> cq.Assembly:
        colors = {"floor bricks": (0.80, 0.55, 0.35), "vault bricks": (0.75, 0.45, 0.30), "side wall bricks": (0.70, 0.45, 0.30),
                  "skewback bricks": (0.6, 0.35, 0.25), "end wall bricks": (0.72, 0.5, 0.35), "floor insulation": (0.95, 0.95, 0.92),
                  "vault insulation": (0.9, 0.9, 0.6), "end insulation": (0.9, 0.9, 0.6), "shell": (0.25, 0.25, 0.28),
                  "frame": (0.15, 0.15, 0.15), "door and flue": (0.2, 0.2, 0.2)}
        asm = cq.Assembly(name="oven_b")
        for pt in self.parts:
            asm.add(pt.solid, name=pt.pid, color=cq.Color(*colors.get(pt.family, (0.5, 0.5, 0.5)), 1.0))
        return asm


def summary(p: Params) -> dict:
    a = p.arch
    return {
        "internal_span_mm": p.span, "internal_length_mm": p.length,
        "floor_field_mm": [p.floor_cols * p.bW, p.length], "cooking_floor_height_above_base_mm": p.z_floor,
        "springing_above_floor_mm": p.z_spring - p.z_floor, "arch_rise_mm": a["rise"], "arch_R_i_mm": a["R_i"],
        "arch_half_angle_deg": math.degrees(a["half_angle"]), "crown_above_floor_mm": a["crown_above_floor"],
        "door_w_x_h_mm": [p.door_w, p.door_h],
        "outer_width_mm": 2 * (p.x_wall_out + p.ins_t + p.shell_t), "outer_depth_mm": p.y_back_out - p.y_front_out + 2 * p.ins_t,
        "outer_height_above_base_mm": a["z_c"] + a["R_e"] + p.ins_t + p.shell_t,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(summary(Params()), indent=1))
