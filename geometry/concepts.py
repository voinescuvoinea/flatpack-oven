"""Phase 1 concept-level estimates: floor fit, areas, masses, part counts, known costs.

Indicative only. Thermal performance is Phase 2. Geometry in metres here (concept
level, no CAD yet). Material data come only from materials.db. Design parameters
(dimensions, layer thicknesses) are proposals and are listed as such in the output.

Run:  uv run python -m geometry.concepts
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from scipy.optimize import brentq

from materials import db

# --- exchange rates: ECB reference rates published 2026-11-06 --------------------------
EUR_PER_EUR = 1.0
RON_PER_EUR = 5.3403
USD_PER_EUR = 1.1165
FX_SOURCE = "ECB euro foreign exchange reference rates, 2026-11-06"


def to_usd(amount: float, currency: str) -> float:
    eur = {"EUR": amount, "RON": amount / RON_PER_EUR, "USD": amount / USD_PER_EUR}[currency]
    return eur * USD_PER_EUR


# --- geometry helpers (each one has an analytical test) ---------------------------------
def segment_depth_for_area_fraction(R_m: float, fraction: float) -> float:
    """Depth b [m] (sagitta) of a circular segment of a circle radius R_m holding `fraction` of its area."""
    if not 0.0 < fraction < 1.0:
        raise ValueError("fraction must be in (0, 1)")
    # segment area / circle area = (theta - sin theta) / (2 pi), theta = central angle
    theta = brentq(lambda th: (th - math.sin(th)) / (2 * math.pi) - fraction, 1e-9, 2 * math.pi)
    return R_m * (1.0 - math.cos(theta / 2.0))


def clear_circle_diameter_beside_fire(R_m: float, fire_depth_m: float) -> float:
    """Largest circle [m diameter] that fits in a round floor of radius R_m when a segment of
    depth fire_depth_m (measured from the wall) is taken by the fire.

    The circle touches the chord and the far wall: r = R - b/2, so D = 2R - b.
    """
    if not 0.0 <= fire_depth_m <= 2 * R_m:
        raise ValueError("fire depth out of range")
    return 2.0 * R_m - fire_depth_m


def oblate_hemispheroid_area(a_m: float, c_m: float) -> float:
    """Curved area [m2] of half an oblate spheroid, equatorial radius a_m, polar half-axis c_m <= a_m."""
    if c_m > a_m:
        raise ValueError("oblate only (c <= a)")
    if math.isclose(c_m, a_m):
        return 2.0 * math.pi * a_m**2
    e = math.sqrt(1.0 - (c_m / a_m) ** 2)
    full = 2.0 * math.pi * a_m**2 * (1.0 + (1.0 - e**2) / e * math.atanh(e))
    return full / 2.0


def segmental_arch(span_m: float, rise_m: float) -> tuple[float, float]:
    """(radius [m], central angle [rad]) of a circular segmental arch with given span and rise."""
    R = (span_m**2 / 4.0 + rise_m**2) / (2.0 * rise_m)
    theta = 2.0 * math.asin(span_m / (2.0 * R))
    if rise_m > R:  # more than a semicircle
        theta = 2.0 * math.pi - theta
    return R, theta


def circular_segment_area(R_m: float, theta_rad: float) -> float:
    return R_m**2 / 2.0 * (theta_rad - math.sin(theta_rad))


# --- concept definitions -----------------------------------------------------------------
@dataclass
class Item:
    name: str
    material: str | None  # materials.db id, or None for unpriced/unsourced hardware
    mass_kg: float = 0.0
    qty: float = 0.0
    unit: str = ""
    cost_usd: float | None = None  # None = no sourced price yet
    hot_face: bool = False  # counted in the stored-heat indicator


@dataclass
class Concept:
    key: str
    title: str
    summary: str
    params: dict
    items: list[Item] = field(default_factory=list)
    parts: dict = field(default_factory=dict)  # part family -> (count, max mass kg)


def _price(mat: db.Material, qty: float) -> float:
    s = mat.suppliers[0]
    return to_usd(qty * float(s["price"]), s["currency"])


def build(mats: dict[str, db.Material]) -> list[Concept]:
    brick = mats["refarom_65sa_brick"]
    rho_brick = brick["density"].at(300.0)
    v_brick = 0.230 * 0.114 * 0.064
    m_brick = rho_brick * v_brick
    sw = mats["superwool_plus_blanket_128"]
    casi = mats["casi_board_cs270"]
    rho_sw, rho_casi = sw["density"].at(300.0), casi["density"].at(300.0)
    rho_steel = mats["stainless_1_4301_sheet"]["density"].at(300.0)
    rho_cast = mats["dense_castable_generic"]["density"].at(300.0)
    sealant = mats["fermit_stove_sealant"]

    common = dict(
        pizza_D_m=0.45, door_w_m=0.52, door_h_m=0.24, t_floor_brick_m=0.064,
        t_floor_casi_m=0.050, t_dome_sw_m=0.075, t_shell_m=0.001,
    )
    concepts: list[Concept] = []

    def floor_items(area_m2: float, perim_m: float) -> list[Item]:
        n = math.ceil(area_m2 / (0.230 * 0.114))
        casi_area = 2 * area_m2 * 1.15  # 2 x 25 mm layers, 15 % allowance for the wider insulated footprint
        sheets = math.ceil(casi_area / 0.72)
        return [
            Item("floor bricks (laid flat, 64 mm)", brick.id, n * m_brick, n, "pcs", _price(brick, n), hot_face=True),
            Item("floor insulation CaSi 2x25 mm", casi.id, casi_area / 2 * 0.050 * rho_casi, sheets, "sheets", _price(casi, sheets)),
        ]

    def dome_insulation(area_m2: float) -> Item:
        rolls = math.ceil(area_m2 * 3 / 4.46)  # 3 layers x 25 mm
        return Item("dome insulation Superwool 3x25 mm", sw.id, area_m2 * 0.075 * rho_sw, rolls, "rolls", _price(sw, rolls))

    # ---- A: steel-lined low dome --------------------------------------------------------
    R, hw, c = 0.45, 0.20, 0.20
    a_in = 2 * math.pi * R * hw + oblate_hemispheroid_area(R, c)
    t_liner = 0.0015
    Ro = R + 0.075
    a_out = 2 * math.pi * Ro * hw + oblate_hemispheroid_area(Ro, c + 0.075)
    A = Concept(
        "A", "Steel-lined low dome",
        "Bolted stainless gores form a low dome over a firebrick floor; fibre insulation; painted steel outer shell. Like commercial portable ovens, scaled up.",
        dict(common, floor="round D 0.90 m", wall_h_m=hw, vault_rise_m=c, liner_t_m=t_liner),
    )
    A.items += floor_items(math.pi * R**2, 2 * math.pi * R)
    A.items += [
        Item("inner liner, stainless 1.5 mm (8 gores + crown + door arch)", "stainless_1_4301_sheet", a_in * t_liner * rho_steel * 1.15, a_in * 1.15, "m2", None),
        dome_insulation(a_out),
        Item("outer shell, steel 1 mm, painted", "stainless_1_4301_sheet", a_out * 1.1 * 0.001 * rho_steel, a_out * 1.1, "m2", None),
        Item("laser cutting + bending of liner/shell", None, 0, 1, "job", None),
        Item("refractory sealant", sealant.id, 0, 2, "cartridges", _price(sealant, 2)),
        Item("door, flue pipe, fasteners (A2 stainless)", None, 0, 1, "lot", None),
    ]
    A.parts = {"floor bricks": (A.items[0].qty, m_brick), "liner gores": (10, A.items[2].mass_kg / 10), "shell panels": (10, A.items[4].mass_kg / 10)}
    concepts.append(A)

    # ---- B: firebrick barrel vault in a steel frame ---------------------------------------
    W, L, hw_b, rise = 0.80, 0.90, 0.15, 0.25
    t = 0.114
    Rv, th = segmental_arch(W, rise)
    arch_vol = (Rv + t / 2) * th * t * L
    side_vol = 2 * hw_b * L * t
    end_area = W * hw_b + circular_segment_area(Rv, th)
    door_area = common["door_w_m"] * common["door_h_m"]
    end_vol = (2 * end_area - door_area) * t
    vault_vol = arch_vol + side_vol + end_vol
    n_vault = math.ceil(vault_vol / v_brick)
    a_out_b = (Rv + t) * th * L + 2 * (hw_b + t) * L + 2 * end_area
    B = Concept(
        "B", "Firebrick barrel vault (sprung arch in a steel frame)",
        "Local fireclay bricks dry-fitted on a reusable former, held by a bolted angle-iron frame with tie rods (kiln practice); fibre insulation; light outer shell.",
        dict(common, floor="rect 0.80 x 0.90 m, fire along back wall", wall_h_m=hw_b, vault_rise_m=rise, brick_t_m=t,
             arch_radius_m=round(Rv, 3), arch_angle_deg=round(math.degrees(th), 1)),
    )
    B.items += floor_items(W * L, 2 * (W + L))
    B.items += [
        Item("vault + walls, bricks (114 mm thick)", brick.id, n_vault * m_brick, n_vault, "pcs", _price(brick, n_vault), hot_face=True),
        dome_insulation(a_out_b),
        Item("steel frame: angle buckstays + M12 tie rods", None, 0, 1, "lot", None),
        Item("outer shell, steel 1 mm or cement board", "stainless_1_4301_sheet", a_out_b * 1.1 * 0.001 * rho_steel, a_out_b * 1.1, "m2", None),
        Item("refractory sealant / mortar for arch joints", sealant.id, 0, 4, "cartridges", _price(sealant, 4)),
        Item("door, flue pipe, fasteners", None, 0, 1, "lot", None),
    ]
    B.parts = {"floor bricks": (B.items[0].qty, m_brick), "vault bricks": (n_vault, m_brick), "frame members": (12, None)}
    concepts.append(B)

    # ---- C: cast refractory segment dome ------------------------------------------------
    t_c = 0.08
    Rm = R + t_c / 2
    a_mid = 2 * math.pi * Rm * hw + oblate_hemispheroid_area(Rm, c + t_c / 2)
    m_cast = a_mid * t_c * rho_cast
    bags = math.ceil(m_cast * 1.1 / 25)
    eur_bag = float(mats["dense_castable_generic"].suppliers[0]["price"])
    Ro_c = R + t_c
    a_out_c = 2 * math.pi * Ro_c * hw + oblate_hemispheroid_area(Ro_c, c + t_c)
    C = Concept(
        "C", "Cast refractory segment dome (home-cast in reusable moulds)",
        "8 dome segments + crown cast from dense castable in moulds (the commercial modular-kit approach); fibre insulation; outer shell or render.",
        dict(common, floor="round D 0.90 m", wall_h_m=hw, vault_rise_m=c, shell_t_m=t_c, segments=9),
    )
    C.items += floor_items(math.pi * R**2, 2 * math.pi * R)
    C.items += [
        Item("dome segments, dense castable 80 mm", "dense_castable_generic", m_cast, bags, "bags 25 kg", to_usd(bags * eur_bag, "EUR"), hot_face=True),
        Item("moulds (plywood/EPS), reinforcement needles", None, 0, 1, "lot", None),
        dome_insulation(a_out_c),
        Item("outer shell, steel 1 mm or render on mesh", "stainless_1_4301_sheet", a_out_c * 1.1 * 0.001 * rho_steel, a_out_c * 1.1, "m2", None),
        Item("refractory sealant for segment joints", sealant.id, 0, 3, "cartridges", _price(sealant, 3)),
        Item("door, flue pipe, fasteners", None, 0, 1, "lot", None),
    ]
    C.parts = {"floor bricks": (C.items[0].qty, m_brick), "dome segments": (9, m_cast / 9)}
    concepts.append(C)
    return concepts


def stored_heat_MJ(concept: Concept, mats: dict[str, db.Material], T_op_C: float = 450.0, T_amb_C: float = 10.0) -> float:
    """Upper-bound heat [MJ] to bring all hot-face refractory to T_op (uniform), using sourced cp."""
    E = 0.0
    for it in concept.items:
        if it.hot_face and it.material:
            prop = mats[it.material].properties.get("specific_heat")
            cp = prop.at(300.0) if prop else mats["refarom_65sa_brick"]["specific_heat"].at(300.0)
            E += it.mass_kg * cp * (T_op_C - T_amb_C)
    return E / 1e6


def report() -> str:
    mats = db.load()
    concepts = build(mats)
    wood = mats["oak_firewood_f22"]
    lhv = wood["lower_heating_value"].at(300.0)
    eta = wood["combustion_efficiency"].at(300.0)

    R = 0.45
    b = segment_depth_for_area_fraction(R, 0.25)
    D_clear = clear_circle_diameter_beside_fire(R, b)
    out = [
        "# Concept estimates (generated by `geometry/concepts.py`, do not edit by hand)",
        "",
        f"Exchange rates: {FX_SOURCE}: 1 EUR = {RON_PER_EUR} RON = {USD_PER_EUR} USD.",
        "",
        "## Floor fit (round floor, fire taking 1/4 of the floor as in Falciano et al. 2022)",
        f"- Ø 0.90 m floor: fire segment depth {b*100:.1f} cm; largest clear circle beside it {D_clear*100:.1f} cm,",
        f"  so a 45 cm pizza gets a {(D_clear-0.45)/2*100:.1f} cm margin all round.",
        "",
        "## Comparison",
        "",
        "| | A | B | C |",
        "|---|---|---|---|",
    ]
    rows: dict[str, list[str]] = {k: [] for k in [
        "Concept", "Refractory mass (kg)", "Total estimated mass (kg)", "Heaviest single part (kg)", "Part count (approx.)",
        "Stored heat at 450 °C, upper bound (MJ)", "…as wood at F22 LHV and η (kg)",
        "Priced items (USD)", "Unpriced items"]}
    for c in concepts:
        refr = sum(i.mass_kg for i in c.items if i.hot_face)
        total = sum(i.mass_kg for i in c.items)
        heaviest = max((m for _, m in c.parts.values() if m), default=0)
        nparts = sum(int(n) for n, _ in c.parts.values())
        E = stored_heat_MJ(c, mats)
        priced = sum(i.cost_usd for i in c.items if i.cost_usd is not None)
        unpriced = [i.name.split(",")[0] for i in c.items if i.cost_usd is None]
        rows["Concept"].append(c.title)
        rows["Refractory mass (kg)"].append(f"{refr:.0f}")
        rows["Total estimated mass (kg)"].append(f"{total:.0f} + hardware")
        rows["Heaviest single part (kg)"].append(f"{heaviest:.1f}")
        rows["Part count (approx.)"].append(f"~{nparts} + fasteners")
        rows["Stored heat at 450 °C, upper bound (MJ)"].append(f"{E:.0f}")
        rows["…as wood at F22 LHV and η (kg)"].append(f"{E*1e6/(lhv*eta):.1f}")
        rows["Priced items (USD)"].append(f"{priced:.0f}")
        rows["Unpriced items"].append("; ".join(unpriced))
    for k, v in rows.items():
        out.append(f"| {k} | " + " | ".join(v) + " |")
    out += ["", "## Line items", ""]
    for c in concepts:
        out += [f"### {c.key}. {c.title}", "", c.summary, "", f"Design parameters (proposals): `{c.params}`", "",
                "| Item | Qty | Mass (kg) | Cost (USD) |", "|---|---|---|---|"]
        for i in c.items:
            cost = f"{i.cost_usd:.0f}" if i.cost_usd is not None else "quote needed"
            out.append(f"| {i.name} | {i.qty:.1f} {i.unit} | {i.mass_kg:.1f} | {cost} |")
        out.append("")
    out += [
        "## Notes on method",
        "- Masses use mid-surface area x thickness x sourced density. Steel uses the 1.4301 density for all sheet.",
        "- Stored heat assumes all hot-face refractory sits uniformly at 450 °C. That is an upper bound for",
        "  comparing concepts, not a heat-up prediction (Phase 2). Steel is not counted (cp not yet sourced).",
        "- 'Quote needed' items have no sourced price yet. They are listed, not guessed.",
    ]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    print(report(), end="")
