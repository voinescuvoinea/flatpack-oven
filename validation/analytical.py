"""Closed-form reference solutions used to verify the solvers (standard heat-transfer results)."""

from __future__ import annotations

import math

import numpy as np
from scipy.optimize import brentq
from scipy.special import erf


def semi_infinite_step(x_m, t_s, alpha_m2_s, T_i_K, T_s_K):
    """Semi-infinite solid, surface stepped from T_i to T_s at t = 0."""
    return T_s_K + (T_i_K - T_s_K) * erf(np.asarray(x_m) / (2.0 * math.sqrt(alpha_m2_s * t_s)))


def slab_convection_series(x_m, t_s, L_m, k, alpha, h, T_i_K, T_inf_K, n_terms=60):
    """Plane wall 0<=x<=L, adiabatic at x=0, convection h to T_inf at x=L, uniform T_i at t=0.
    Exact eigen-series: theta = sum C_n exp(-zeta_n^2 Fo) cos(zeta_n x/L), zeta tan zeta = Bi."""
    Bi = h * L_m / k
    Fo = alpha * t_s / L_m**2
    theta = np.zeros_like(np.asarray(x_m, dtype=float))
    for n in range(n_terms):
        lo, hi = n * math.pi + 1e-12, n * math.pi + math.pi / 2 - 1e-12
        z = brentq(lambda z: z * math.tan(z) - Bi, lo, hi)
        C = 4 * math.sin(z) / (2 * z + math.sin(2 * z))
        theta = theta + C * math.exp(-z * z * Fo) * np.cos(z * np.asarray(x_m) / L_m)
    return T_inf_K + (T_i_K - T_inf_K) * theta


def cylinder_shell_flux_per_inner_area(r1, r2, k, T1, T2):
    return k * (T1 - T2) / (r1 * math.log(r2 / r1))


def sphere_shell_flux_per_inner_area(r1, r2, k, T1, T2):
    return k * (T1 - T2) / (r1**2 * (1 / r1 - 1 / r2))


def linear_k_slab_flux(L, k0, beta, T1, T2):
    """Steady slab with k = k0 + beta*T (Kirchhoff transform): q = (1/L) * integral_T2^T1 k dT."""
    return (k0 * (T1 - T2) + 0.5 * beta * (T1**2 - T2**2)) / L


def parallel_squares_view_factor(a, d):
    """Two directly opposed parallel squares of side a, distance d (standard closed form)."""
    X = Y = a / d
    A = math.log(math.sqrt((1 + X * X) * (1 + Y * Y) / (1 + X * X + Y * Y)))
    B = X * math.sqrt(1 + Y * Y) * math.atan(X / math.sqrt(1 + Y * Y))
    C = Y * math.sqrt(1 + X * X) * math.atan(Y / math.sqrt(1 + X * X))
    D = X * math.atan(X) + Y * math.atan(Y)
    return 2.0 / (math.pi * X * Y) * (A + B + C - D)


def coaxial_disks_view_factor(r1, r2, d):
    """Disk radius r1 to coaxial parallel disk radius r2 at distance d."""
    R1, R2 = r1 / d, r2 / d
    S = 1 + (1 + R2**2) / R1**2
    return 0.5 * (S - math.sqrt(S * S - 4 * (R2 / R1) ** 2))
