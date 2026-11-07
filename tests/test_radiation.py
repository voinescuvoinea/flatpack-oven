"""Verification of view factors and the radiosity network against closed-form results."""

import math

import numpy as np
import pytest
from scipy.constants import Stefan_Boltzmann as SIGMA

from simulation import radiation as rad
from validation import analytical as an

N = 200_000


def test_box_parallel_squares():
    F, A = rad.view_factors(rad.BoxCavity(1.0, 1.0), N)
    ref = an.parallel_squares_view_factor(1.0, 1.0)  # 0.19982
    assert F[0, 1] == pytest.approx(ref, abs=0.004)
    assert F[1, 0] == pytest.approx(ref, abs=0.004)


def test_cylinder_coaxial_disks():
    F, A = rad.view_factors(rad.CylinderCavity(0.45, 0.40), N)
    assert F[0, 1] == pytest.approx(an.coaxial_disks_view_factor(0.45, 0.45, 0.40), abs=0.004)


def test_summation_and_reciprocity_barrel():
    cav = rad.BarrelVault(W=0.80, L=0.90, hw=0.15, rise=0.25, door_w=0.52, door_h=0.24, fire_d=0.27)
    F, A = rad.view_factors(cav, N)
    np.testing.assert_allclose(F.sum(axis=1), 1.0, atol=1e-9)
    assert np.all(F >= -1e-9)
    for i in range(3):
        assert A[i] * F[i, 3] == pytest.approx(A[3] * F[3, i], rel=1e-9)
    # floor and fire are coplanar: they cannot see each other
    assert F[0, 1] == 0.0 and F[1, 0] == 0.0


def test_hemisphere_dome_area_and_floor_view():
    cav = rad.DomeOven(R=0.45, hw=0.0, c=0.45, rd=1e-4, fire_frac=0.25)
    # hemisphere (2 pi R^2) + floor (pi R^2), minus the tiny chord cut
    assert cav.total_area() == pytest.approx(3 * math.pi * 0.45**2, rel=1e-4)
    F, A = rad.view_factors(cav, 50_000)
    assert F[0, 3] == pytest.approx(1.0, abs=1e-3)


def test_radiosity_concentric_spheres():
    r1, r2, e1, e2, T1, T2 = 0.3, 0.5, 0.8, 0.6, 900.0, 400.0
    A = np.array([4 * math.pi * r1**2, 4 * math.pi * r2**2])
    F = np.array([[0.0, 1.0], [A[0] / A[1], 1 - A[0] / A[1]]])
    out = rad.solve_radiosity(F, A, np.array([e1, e2]), np.array([T1, T2]), np.array([np.nan, np.nan]))
    q_ref = SIGMA * (T1**4 - T2**4) / (1 / e1 + (A[0] / A[1]) * (1 / e2 - 1))
    assert out["q_W_m2"][0] == pytest.approx(q_ref, rel=1e-10)
    assert A @ out["q_W_m2"] == pytest.approx(0.0, abs=1e-6)


def test_radiosity_prescribed_flux_source():
    # source with fixed output inside a black isothermal sphere: all power must be absorbed by the sphere
    A = np.array([0.1, 2.0])
    F = np.array([[0.0, 1.0], [0.05, 0.95]])
    out = rad.solve_radiosity(F, A, np.array([0.9, 1.0]), np.array([np.nan, 500.0]), np.array([20000.0, np.nan]))
    assert out["q_W_m2"][1] * A[1] == pytest.approx(-20000.0 * 0.1, rel=1e-10)
    assert out["T_K"][0] > 500.0
