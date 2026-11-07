"""Masonry-arch stability by thrust-line (limit) analysis, Heyman's safe theorem.

An arch of rigid voussoirs with no tensile strength is safe if a line of thrust in
equilibrium with the loads can be found lying inside the masonry. "Middle third"
means no joint opens. Geometric safety factor = actual thickness / minimum thickness
for which any thrust line still fits (centre-line and loads scale with thickness).

Verified against the classical result for a semicircular arch under self-weight,
t_min / R_centre ~= 0.107 (Milankovitch; Heyman 1969 gives 0.106 approximately).

Units SI: lengths m, forces N (per metre of barrel length).
"""

from __future__ import annotations

import math

import numpy as np


def voussoirs(R_c: float, t: float, half_angle: float, n: int, gamma_N_m3: float, q_ext_N_m2: float = 0.0):
    """Half arch from crown (phi=0) to springing (phi=half_angle), n voussoirs.
    Returns joint angles, weights W [N/m] and their centroid x [m] (x horizontal from the crown line).
    q_ext: extra vertical load per unit extrados arc length (insulation), applied at the extrados."""
    Ri, Re = R_c - t / 2, R_c + t / 2
    phi = np.linspace(0, half_angle, n + 1)
    W, X = [], []
    for a, b in zip(phi[:-1], phi[1:]):
        d = b - a
        m = 0.5 * (a + b)
        area = 0.5 * (Re**2 - Ri**2) * d
        rc = (2 / 3) * (Re**3 - Ri**3) / (Re**2 - Ri**2) * math.sin(d / 2) / (d / 2)
        w_self = gamma_N_m3 * area
        w_ext = q_ext_N_m2 * Re * d
        x_self, x_ext = rc * math.sin(m), Re * math.sin(m)
        W.append(w_self + w_ext)
        X.append((w_self * x_self + w_ext * x_ext) / (w_self + w_ext))
    return phi, np.array(W), np.array(X), Ri, Re


def thrust_radii(phi, W, X, H, r0):
    """Radius at which the thrust line crosses each joint (crown thrust H at radius r0)."""
    cumW = np.concatenate([[0.0], np.cumsum(W)])
    cumWX = np.concatenate([[0.0], np.cumsum(W * X)])
    return (r0 + cumWX / H) / (np.cos(phi) + np.sin(phi) * cumW / H)


def feasible(R_c, t, half_angle, gamma, q_ext=0.0, n=60, margin=0.0, nH=300, nr=61):
    """Search crown thrust H and crown position for a thrust line within [Ri + m t, Re - m t].
    Returns dict with feasibility, H range [N/m] and best (min max-|eccentricity|/t) solution."""
    phi, W, X, Ri, Re = voussoirs(R_c, t, half_angle, n, gamma, q_ext)
    Wt = W.sum()
    lo_b, hi_b = Ri + margin * t, Re - margin * t
    Hs = Wt * np.logspace(-2, 2, nH)
    best, Hok = None, []
    for r0 in np.linspace(lo_b, hi_b, nr):
        for H in Hs:
            r = thrust_radii(phi, W, X, H, r0)
            if np.all(r >= lo_b - 1e-12) and np.all(r <= hi_b + 1e-12):
                Hok.append(H)
                ecc = np.max(np.abs(r - R_c)) / t
                if best is None or ecc < best[0]:
                    best = (ecc, H, r0)
    if best is None:
        return {"feasible": False}
    return {"feasible": True, "H_min_N_m": min(Hok), "H_max_N_m": max(Hok), "best_ecc_over_t": best[0],
            "best_H_N_m": best[1], "half_weight_N_m": Wt}


def minimum_thickness(R_c, half_angle, gamma, q_ext=0.0, t_hi=None, tol=1e-4, **kw):
    """Smallest t (same centre-line radius) for which a thrust line fits inside the section."""
    lo, hi = 1e-4 * R_c, t_hi or 0.5 * R_c
    if not feasible(R_c, hi, half_angle, gamma, q_ext, **kw)["feasible"]:
        return float("nan")
    while hi - lo > tol * R_c:
        mid = 0.5 * (lo + hi)
        if feasible(R_c, mid, half_angle, gamma, q_ext, **kw)["feasible"]:
            hi = mid
        else:
            lo = mid
    return hi
