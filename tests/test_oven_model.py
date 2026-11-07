"""Consistency checks on the coupled oven model (energy conservation, sane limits)."""

import pytest

from simulation.configs import oven_b_config
from simulation.fire import FireParams
from simulation.oven import OvenModel


@pytest.fixture(scope="module")
def fp():
    return FireParams.from_db(chi_r=0.3, excess_air=2.0, h_in=15.0)


def test_steady_energy_balance(fp):
    r = OvenModel(oven_b_config(vault_t_m=0.064, ins_t_m=0.1), fp).steady(3.0)
    assert r["Q_flue_W"] + r["Q_door_rad_W"] + r["Q_walls_W"] == pytest.approx(r["Q_fire_W"], rel=2e-3)


def test_transient_energy_balance(fp):
    m = OvenModel(oven_b_config(vault_t_m=0.064, ins_t_m=0.1), fp)
    Ta = m.cfg.T_amb_K
    E0 = m.vault.heat_content_J(Ta) * m.A[3] + m.floor.heat_content_J(Ta) * m.A[0]
    dt, E_fire, E_loss = 10.0, 0.0, 0.0
    for _ in range(720):  # 2 h at 6 kg/h
        r = m.step(dt, 6.0 / 3600)
        E_fire += r["Q_fire_W"] * dt
        E_loss += (r["Q_flue_W"] + r["Q_door_rad_W"] + r["Q_walls_W"]) * dt
    dE = m.vault.heat_content_J(Ta) * m.A[3] + m.floor.heat_content_J(Ta) * m.A[0] - E0
    # radiation is lagged by one step, so the balance closes only approximately
    assert dE + E_loss == pytest.approx(E_fire, rel=0.02)


def test_cooling_with_door_closed_is_monotonic(fp):
    m = OvenModel(oven_b_config(vault_t_m=0.064, ins_t_m=0.1), fp)
    m.run(3600, 30, lambda _: 6.0 / 3600)
    m.door_closed = True
    m.M_wood_kg = 0.0
    log = m.run(m.t_s + 4 * 3600, 60, lambda _: 0.0)
    T = [r["T_vault_C"] for r in log[5:]]
    assert all(b <= a + 1e-6 for a, b in zip(T, T[1:]))
