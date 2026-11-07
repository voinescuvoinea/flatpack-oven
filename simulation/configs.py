"""Oven configurations: the published validation oven (F22) and our concept B."""

from __future__ import annotations

from materials import db
from simulation.conduction import Layer
from simulation.oven import OvenConfig
from simulation.radiation import BarrelVault, DomeOven


def _eps(mats, scale=1.0):
    p = mats["refarom_65sa_brick"]["emissivity"]
    return lambda T: min(float(p.at(T, extrapolate=True)) * scale, 1.0)


def f22_config(t_ins_m: float, mats=None, T_amb_C: float = 36.4, t_ins_floor_m: float | None = None, **scales) -> OvenConfig:
    """Falciano et al. (2022) pilot oven. Insulation is unknown in the paper: an
    equivalent thickness t_ins_m of our insulation materials is calibrated."""
    mats = mats or db.load()
    brick, sw, casi, conc = (mats[k] for k in ("refarom_65sa_brick", "superwool_plus_blanket_128", "casi_board_cs270", "concrete_base_generic"))
    R = 0.45
    return OvenConfig(
        name="F22 pilot oven",
        cavity=DomeOven(R=R, hw=0.20, c=0.20, rd=0.22, fire_frac=0.25),
        vault_layers=[Layer.from_material(brick, 0.10, 10, **_s(scales, "brick")), Layer.from_material(sw, t_ins_m, 8, **_s(scales, "sw"))],
        vault_geometry="sphere", vault_r_inner_m=R,
        vault_outer=("sphere", 2 * (R + 0.10 + t_ins_m)),
        floor_layers=[Layer.from_material(brick, 0.10, 10, **_s(scales, "brick")), Layer.from_material(casi, t_ins_floor_m or t_ins_m, 8, **_s(scales, "casi")),
                      Layer.from_material(conc, 0.15, 6, **_s(scales, "conc"))],
        floor_outer=("down", 0.25),
        eps_brick=_eps(mats, scales.get("eps_brick", 1.0)),
        eps_shell=0.92, eps_floor_bottom=0.97, T_amb_K=T_amb_C + 273.15,
    )


def oven_b_config(vault_t_m: float = 0.114, ins_t_m: float = 0.075, floor_casi_t_m: float = 0.050,
                  T_amb_C: float = 10.0, mats=None, outer_ins_t_m: float = 0.0, **scales) -> OvenConfig:
    """Concept B: 0.80 x 0.90 m floor, 0.15 m walls, 0.25 m segmental arch rise, 0.52 x 0.24 m door,
    fire along the back wall (0.27 m strip), 64 mm floor brick on CaSi on a 0.15 m concrete slab."""
    mats = mats or db.load()
    brick, sw, casi, conc = (mats[k] for k in ("refarom_65sa_brick", "superwool_plus_blanket_128", "casi_board_cs270", "concrete_base_generic"))
    cav = BarrelVault(W=0.80, L=0.90, hw=0.15, rise=0.25, door_w=0.52, door_h=0.24, fire_d=0.27)
    n_v = max(6, int(round(vault_t_m / 0.01)))
    return OvenConfig(
        name=f"Oven B (vault {vault_t_m*1000:.0f} mm, insulation {ins_t_m*1000:.0f} mm)",
        cavity=cav,
        vault_layers=[Layer.from_material(brick, vault_t_m, n_v, **_s(scales, "brick")), Layer.from_material(sw, ins_t_m, 8, **_s(scales, "sw"))]
        + ([Layer.from_material(mats["prorox_wm960es"], outer_ins_t_m, 8, **_s(scales, "rw"))] if outer_ins_t_m > 0 else []),
        vault_geometry="cylinder", vault_r_inner_m=cav.R,
        vault_outer=("cylinder", 2 * (cav.R + vault_t_m + ins_t_m + outer_ins_t_m)),
        floor_layers=[Layer.from_material(brick, 0.064, 8, **_s(scales, "brick")), Layer.from_material(casi, floor_casi_t_m, 6, **_s(scales, "casi")),
                      Layer.from_material(conc, 0.15, 6, **_s(scales, "conc"))],
        floor_outer=("down", 0.27),
        eps_brick=_eps(mats, scales.get("eps_brick", 1.0)),
        eps_shell=mats["shell_heat_resistant_paint"]["emissivity"].at(300.0) * scales.get("eps_shell", 1.0),
        eps_floor_bottom=mats["concrete_base_generic"]["emissivity"].at(300.0),
        T_amb_K=T_amb_C + 273.15,
    )


def _s(scales: dict, prefix: str) -> dict:
    """Map e.g. brick_k=1.2 -> k_scale=1.2 for the layer of that material."""
    out = {}
    for key in ("k", "rho", "cp"):
        v = scales.get(f"{prefix}_{key}")
        if v is not None:
            out[f"{key}_scale"] = v
    return out


def oven_b_as_designed(p=None, T_amb_C: float = 10.0, mats=None, **scales) -> OvenConfig:
    """Concept B with the Phase 3 CAD geometry (geometry/oven_b.Params), hybrid vault insulation
    and 100 mm CaSi under the floor. The arched door is represented by a rectangle of equal area."""
    import math as _m
    from geometry.oven_b import Params
    from geometry.end_walls import door_geometry
    p = p or Params()
    a = p.arch
    d = door_geometry(p)
    seg = d["Rd"] ** 2 / 2 * (2 * d["half_angle"] - _m.sin(2 * d["half_angle"]))
    door_area = p.door_w * (p.door_h - p.door_arch_rise) + seg  # mm2
    mats = mats or db.load()
    cfg = oven_b_config(vault_t_m=p.bT / 1000, ins_t_m=p.sw_t / 1000, outer_ins_t_m=p.rw_t / 1000,
                        floor_casi_t_m=p.casi_layers * p.casi_t / 1000, T_amb_C=T_amb_C, mats=mats, **scales)
    cfg.cavity = BarrelVault(W=p.span / 1000, L=p.length / 1000, hw=(p.z_spring - p.z_floor) / 1000, rise=a["rise"] / 1000,
                             door_w=p.door_w / 1000, door_h=door_area / p.door_w / 1000, fire_d=0.27)
    cfg.vault_r_inner_m = a["R_i"] / 1000
    cfg.vault_outer = ("cylinder", 2 * (a["R_e"] + p.ins_t) / 1000)
    cfg.name = "Oven B as designed (Phase 3)"
    return cfg
