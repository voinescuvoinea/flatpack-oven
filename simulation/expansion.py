"""Thermal expansion of the brick vault and floor, and what the joints and frame must absorb.

Free thermal strain eps = alpha * dT, with alpha from the materials DB (proxy, +/-20 %).
No stress values are computed because the brick's Young's modulus is not sourced.
The design rule is therefore to ALLOW the movement (floating floor, sprung tie rods,
dry joints) rather than restrain it and rely on unknown strength.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.optimize import brentq


def arch_arc_length(span_m: float, rise_m: float) -> float:
    R = (span_m**2 / 4 + rise_m**2) / (2 * rise_m)
    return R * 2 * math.asin(span_m / (2 * R))


def rise_for_arc_length(span_m: float, arc_m: float) -> float:
    """Rise of a circular segmental arch with given span and arc length (rise < span/2)."""
    return brentq(lambda f: arch_arc_length(span_m, f) - arc_m, 1e-6, span_m / 2 - 1e-9)


def arch_movement(span_m: float, rise_m: float, t_m: float, alpha_per_K: float, dT_mean_K: float) -> dict:
    """Mid-thickness arch line heated uniformly by dT_mean.
    - free: span and rise both grow by alpha*dT (geometric similarity) -> span growth the frame must allow
    - span held fixed by the frame: the extra arch length lifts the crown instead."""
    s_mid = span_m + t_m  # mid-thickness span approx (springing at mid-thickness)
    f_mid = rise_m + t_m / 2
    strain = alpha_per_K * dT_mean_K
    arc = arch_arc_length(s_mid, f_mid)
    f_fixed = rise_for_arc_length(s_mid, arc * (1 + strain))
    return {
        "strain": strain,
        "span_growth_free_mm": s_mid * strain * 1e3,
        "crown_lift_free_mm": f_mid * strain * 1e3,
        "crown_lift_if_span_fixed_mm": (f_fixed - f_mid) * 1e3,
    }


def linear_growth_mm(length_m: float, alpha_per_K: float, dT_K: float) -> float:
    return length_m * alpha_per_K * dT_K * 1e3


def through_thickness_mismatch(alpha_per_K: float, T_hot_K: float, T_cold_K: float) -> float:
    """Difference in free strain between hot and cold faces (drives bowing / face cracking)."""
    return alpha_per_K * (T_hot_K - T_cold_K)


def mean_temperature_rise(T_cells_K: np.ndarray, vol: np.ndarray, T_ref_K: float) -> float:
    return float(np.sum((T_cells_K - T_ref_K) * vol) / np.sum(vol))
