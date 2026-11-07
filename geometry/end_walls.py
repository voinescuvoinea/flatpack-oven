"""Course-by-course layout of the two end walls (bricks laid flat, 230 along x, 114 deep, 64 high).

For each course: which x-segments are brick (outside the door opening and door arch),
how many full bricks, which cut pieces (length) and whether the top edge must follow
a curve (vault extrados, door-arch extrados) - cut with a grinder against a 1:1 template.
Odd courses are offset by half a brick so vertical joints do not line up.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from geometry.oven_b import Params


@dataclass
class Piece:
    length_mm: float
    curved_top: bool
    kind: str  # "full", "cut", "curve"


def _profile_half_width(p: Params, z: float) -> float:
    """Half width of the end-wall outline at height z (rectangle + vault extrados circle)."""
    a = p.arch
    w = p.x_wall_out
    dz = z - a["z_c"]
    if dz >= a["R_e"]:
        return 0.0
    circ = math.sqrt(a["R_e"] ** 2 - dz**2)
    return min(w, circ)


def door_geometry(p: Params) -> dict:
    fr, dw = p.door_arch_rise, p.door_w
    Rd = (dw**2 / 4 + fr**2) / (2 * fr)
    vous_radial = p.bL / 2  # half bricks, 115 mm radial
    th = math.asin(dw / 2 / Rd)
    arc = 2 * th * Rd
    n_v = max(3, round((arc + 2) / (p.bT + 2)))
    return {"Rd": Rd, "zc": p.z_floor + p.door_h - Rd, "z_spring": p.z_floor + p.door_h - fr, "half_angle": th,
            "n_voussoirs": n_v, "joint_in_mm": (arc - n_v * p.bT) / (n_v - 1), "radial": vous_radial}


def _door_block_half_width(p: Params, z: float, d: dict) -> float:
    """Half width of the region taken by the door opening + door arch ring at height z (0 if none)."""
    if z < p.z_floor - 1e-6:
        return 0.0
    Ro = d["Rd"] + d["radial"]
    if z <= d["z_spring"]:
        return p.door_w / 2  # below the door-arch springing only the opening itself
    dz = z - d["zc"]
    if dz >= Ro:
        return 0.0
    return math.sqrt(Ro**2 - dz**2)


def courses(p: Params, front: bool) -> list[dict]:
    d = door_geometry(p)
    out = []
    z = p.z_casi_top
    k = 0
    while True:
        z_top = z + p.bT
        hw_bot, hw_top = _profile_half_width(p, z), _profile_half_width(p, z_top)
        if hw_bot <= 1.0:
            break
        segs = []
        if front:
            hb = max(_door_block_half_width(p, z + 1e-3, d), _door_block_half_width(p, z_top - 1e-3, d))
            if hb > 0:
                segs = [(-hw_bot, -hb), (hb, hw_bot)]
            else:
                segs = [(-hw_bot, hw_bot)]
        else:
            segs = [(-hw_bot, hw_bot)]
        curved = hw_top < hw_bot - 0.5
        pieces: list[Piece] = []
        for x0, x1 in segs:
            L = x1 - x0
            if L <= 5:
                continue
            pieces += _lay_course(L, p.bL, stagger=bool(k % 2), curved=curved)
        bricks = sum(1.0 if pc.length_mm > p.bL / 2 + 1 else 0.5 for pc in pieces)
        out.append({"course": k + 1, "z_bottom_mm": z, "z_top_mm": z_top, "segments_mm": segs, "pieces": pieces, "bricks": bricks})
        z += p.course_h
        k += 1
    return out


def door_arch_bricks(p: Params) -> float:
    return door_geometry(p)["n_voussoirs"] / 2  # half bricks


MIN_PIECE_MM = 50.0


def _lay_course(L: float, bL: float, stagger: bool, curved: bool) -> list[Piece]:
    """Symmetric layout of one course segment of length L. Even courses: full bricks centred,
    equal end cuts (no piece < MIN_PIECE_MM). Odd courses: joints shifted by half a brick.
    An end piece up to 20 mm longer than a brick is laid as a full brick with wider joints."""
    if L <= bL + 20:
        return [Piece(min(L, bL), curved, "full" if L >= bL - 2 and not curved else ("curve" if curved else "cut"))]
    n = int(L // bL)
    e = (L - n * bL) / 2
    if e < MIN_PIECE_MM:
        n -= 1
        e += bL / 2
    joints = [e + k * bL for k in range(n + 1)]
    if stagger:
        joints = [j + bL / 2 for j in joints] + [joints[0] - bL / 2]
    joints = sorted(j for j in joints if MIN_PIECE_MM <= j <= L - MIN_PIECE_MM)
    edges = [0.0] + joints + [L]
    out = []
    for a, b in zip(edges[:-1], edges[1:]):
        seg = b - a
        is_end = a == 0.0 or b == L
        if seg >= bL - 2:
            out.append(Piece(bL, curved and is_end, "curve" if curved and is_end else "full"))
            if seg > bL + 20:
                out.append(Piece(seg - bL, curved and is_end, "curve" if curved and is_end else "cut"))
        else:
            out.append(Piece(seg, curved and is_end, "curve" if curved and is_end else "cut"))
    return out
