"""Verification of the 1D conduction solver against closed-form solutions (rule 5)."""

import math

import numpy as np
import pytest
from scipy.constants import Stefan_Boltzmann as SIGMA
from scipy.optimize import brentq

from simulation.conduction import BC, Layer, Stack
from validation import analytical as an


def test_steady_composite_planar_wall():
    L1, k1, L2, k2 = 0.1, 1.2, 0.05, 0.08
    s = Stack([Layer.constant("a", L1, k1, 2e6, 10), Layer.constant("b", L2, k2, 2e5, 10)])
    r = s.step(None, BC(T_fixed_K=773.15), BC(T_fixed_K=293.15))
    q = 480.0 / (L1 / k1 + L2 / k2)
    assert r["q_in_W_m2"] == pytest.approx(q, rel=1e-9)
    assert -r["q_out_W_m2"] == pytest.approx(q, rel=1e-9)
    # exact piecewise-linear profile at every cell centre
    x = s.x_cells
    T_exact = np.where(x < L1, 773.15 - q * x / k1, 773.15 - q * L1 / k1 - q * (x - L1) / k2)
    np.testing.assert_allclose(s.T, T_exact, atol=1e-6)


@pytest.mark.parametrize("geom, ref", [("cylinder", an.cylinder_shell_flux_per_inner_area), ("sphere", an.sphere_shell_flux_per_inner_area)])
def test_steady_curved_shells(geom, ref):
    r1, t, k = 0.445, 0.114, 1.2
    s = Stack([Layer.constant("a", t, k, 2e6, 6)], geometry=geom, r_inner_m=r1)
    r = s.step(None, BC(T_fixed_K=800.0), BC(T_fixed_K=300.0))
    assert r["q_in_W_m2"] == pytest.approx(ref(r1, r1 + t, k, 800.0, 300.0), rel=1e-9)


def test_steady_linear_k_kirchhoff():
    k0, beta, L = 0.05, 2e-4, 0.075
    lay = Layer("lin", L, lambda T: k0 + beta * np.asarray(T), lambda T: np.full(np.shape(T), 1e5), 40)
    s = Stack([lay])
    r = s.step(None, BC(T_fixed_K=900.0), BC(T_fixed_K=300.0))
    assert r["q_in_W_m2"] == pytest.approx(an.linear_k_slab_flux(L, k0, beta, 900.0, 300.0), rel=2e-4)


def test_steady_radiation_boundary():
    L, k, eps, T1, Tinf = 0.05, 0.1, 0.9, 700.0, 300.0
    s = Stack([Layer.constant("a", L, k, 1e5, 20)])
    r = s.step(None, BC(T_fixed_K=T1), BC(eps=eps, T_rad_K=Tinf))
    T2 = brentq(lambda T2: k * (T1 - T2) / L - eps * SIGMA * (T2**4 - Tinf**4), Tinf, T1)
    assert r["Ts_out_K"] == pytest.approx(T2, abs=1e-6)


def test_transient_semi_infinite():
    k, rho_cp = 1.2, 2050 * 1060
    alpha = k / rho_cp
    s = Stack([Layer.constant("a", 0.5, k, rho_cp, 200)], T_init_K=293.15)
    dt, t_end = 5.0, 1800.0
    for _ in range(int(t_end / dt)):
        s.step(dt, BC(T_fixed_K=773.15), BC(q_W_m2=0.0))
    ref = an.semi_infinite_step(s.x_cells, t_end, alpha, 293.15, 773.15)
    assert np.max(np.abs(s.T - ref)) < 1.0  # K, backward Euler with dt=5 s


def test_transient_slab_convection_series():
    L, k, rho_cp, h = 0.064, 1.2, 2.17e6, 25.0
    alpha = k / rho_cp
    # inner face (x=0) adiabatic, outer face convective -> mirror of the series solution
    s = Stack([Layer.constant("a", L, k, rho_cp, 64)], T_init_K=773.15)
    dt, t_end = 2.0, 3600.0
    for _ in range(int(t_end / dt)):
        s.step(dt, BC(q_W_m2=0.0), BC(h=h, T_inf_K=293.15))
    ref = an.slab_convection_series(s.x_cells, t_end, L, k, alpha, h, 773.15, 293.15)
    assert np.max(np.abs(s.T - ref)) < 0.3


def test_energy_conservation_transient():
    s = Stack([Layer.constant("a", 0.1, 1.0, 2e6, 20), Layer.constant("b", 0.05, 0.1, 1e5, 10)], T_init_K=300.0)
    E0 = s.heat_content_J(300.0)
    E_in = 0.0
    dt = 10.0
    for _ in range(360):
        r = s.step(dt, BC(q_W_m2=5000.0), BC(h=10.0, T_inf_K=300.0))
        E_in += (r["q_in_W_m2"] + r["q_out_W_m2"]) * dt
    assert s.heat_content_J(300.0) - E0 == pytest.approx(E_in, rel=1e-6)
