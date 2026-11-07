"""External natural convection (still air, the worst case for shell temperature).

Correlations: Churchill & Chu (1975), as given in Incropera, DeWitt, Bergman & Lavine,
Fundamentals of Heat and Mass Transfer, 7th ed.:
  vertical plate, all Ra (Eq. 9.26); long horizontal cylinder (Eq. 9.34);
  sphere, Churchill (1983) (Eq. 9.35); lower surface of a hot plate (Eq. 9.32, Nu = 0.52 Ra^1/5).
Air properties: CoolProp (Lemmon et al. pseudo-pure air), at the film temperature.
"""

from __future__ import annotations

import math

from CoolProp.CoolProp import PropsSI
from scipy.constants import g as G

P_ATM = 101325.0


def air(T_K: float) -> dict:
    T = max(T_K, 200.0)
    k = PropsSI("L", "T", T, "P", P_ATM, "Air")
    mu = PropsSI("V", "T", T, "P", P_ATM, "Air")
    rho = PropsSI("D", "T", T, "P", P_ATM, "Air")
    cp = PropsSI("C", "T", T, "P", P_ATM, "Air")
    return {"k": k, "nu": mu / rho, "alpha": k / (rho * cp), "Pr": mu * cp / k, "cp": cp, "rho": rho}


def rayleigh(Ts_K: float, Tinf_K: float, L_m: float) -> tuple[float, dict]:
    Tf = 0.5 * (Ts_K + Tinf_K)
    p = air(Tf)
    beta = 1.0 / Tf
    Ra = G * beta * abs(Ts_K - Tinf_K) * L_m**3 / (p["nu"] * p["alpha"])
    return Ra, p


def nu_vertical_plate(Ra: float, Pr: float) -> float:
    return (0.825 + 0.387 * Ra ** (1 / 6) / (1 + (0.492 / Pr) ** (9 / 16)) ** (8 / 27)) ** 2


def nu_horizontal_cylinder(Ra: float, Pr: float) -> float:
    return (0.60 + 0.387 * Ra ** (1 / 6) / (1 + (0.559 / Pr) ** (9 / 16)) ** (8 / 27)) ** 2


def nu_sphere(Ra: float, Pr: float) -> float:
    return 2 + 0.589 * Ra ** 0.25 / (1 + (0.469 / Pr) ** (9 / 16)) ** (4 / 9)


def nu_hot_plate_facing_down(Ra: float, Pr: float) -> float:
    return 0.52 * Ra ** 0.2


def h_natural(shape: str, L_m: float):
    """Return h(Ts) [W/(m2 K)] for a given shape and characteristic length (diameter for
    cylinder/sphere, height for vertical plate, area/perimeter for horizontal plate)."""
    nu_fn = {"vertical": nu_vertical_plate, "cylinder": nu_horizontal_cylinder, "sphere": nu_sphere,
             "down": nu_hot_plate_facing_down}[shape]

    def h(Ts_K: float, Tinf_K: float) -> float:
        if abs(Ts_K - Tinf_K) < 1e-6:
            Ts_K = Tinf_K + 1e-6
        Ra, p = rayleigh(Ts_K, Tinf_K, L_m)
        return nu_fn(Ra, p["Pr"]) * p["k"] / L_m

    return h
