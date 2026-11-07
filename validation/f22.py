"""Calibrate and validate the oven model against Falciano, Masi & Moresi (2022, 2023).

Calibration targets (quasi-steady at 3 kg/h, ambient 36.4 C):
  floor 453 +/- 32 C, vault 546 +/- 53 C           [F22]
  flue-gas loss 46 %, insulated-chamber loss 26 % of firewood energy  [F23a]
  (F23a gives no uncertainty for the split; +/- 5 percentage points ASSUMED for weighting)
  initial floor heating rate at 3 and 9 kg/h: dT/dt = (49 +/- 2) * Q_fw [C/h]  [F22 Eq. 8]
  (Eq. 8 is a fit; +/- 15 % ASSUMED on each point for weighting)
Free parameters: chi_r, excess air, in-cavity h, and the F22 oven's (unknown) equivalent
insulation thickness under the vault and under the floor.

Held-out check (not used in calibration): heating rate at 4.5 and 6 kg/h.

Run: uv run python -m validation.f22
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

from materials import db
from simulation.configs import f22_config
from simulation.fire import FireParams
from simulation.oven import OvenModel

TARGETS = {"T_floor_C": (453.0, 32.0), "T_vault_C": (546.0, 53.0), "flue_frac": (0.46, 0.05), "walls_frac": (0.26, 0.05)}
NAMES = ["chi_r", "excess_air", "h_in_W_m2K", "t_ins_m", "t_ins_floor_m"]
X0 = np.array([0.3, 2.0, 15.0, 0.05, 0.05])
LB = np.array([0.05, 1.2, 2.0, 0.01, 0.005])
UB = np.array([0.60, 6.0, 60.0, 0.25, 0.25])
RATE_CAL = (3.0, 9.0)
RATE_HOLDOUT = (4.5, 6.0)
DT_RATE_S = 60.0
OUT = Path(__file__).with_name("f22_calibration.json")


def _model(x, mats):
    chi, lam, h, t, tf = x
    return OvenModel(f22_config(t, mats, t_ins_floor_m=tf), FireParams.from_db(chi, lam, h, mats=mats))


def floor_rate(x, Q, mats, t_fit_min=70.0, dt_s=DT_RATE_S):
    m = _model(x, mats)
    log = m.run(t_fit_min * 60, dt_s, lambda mod: Q / 3600)
    t_h = np.array([r["t_s"] for r in log]) / 3600
    return float(np.polyfit(t_h, np.array([r["T_floor_C"] for r in log]), 1)[0])


def steady_f22(x, mats=None, feed_kg_h=3.0):
    m = _model(x, mats)
    r = m.steady(feed_kg_h)
    r["flue_frac"] = r["Q_flue_W"] / r["Q_fire_W"]
    r["walls_frac"] = r["Q_walls_W"] / r["Q_fire_W"]
    r["door_frac"] = r["Q_door_rad_W"] / r["Q_fire_W"]
    return r


def residuals(x, mats):
    r = steady_f22(x, mats)
    res = [(r[k] - v) / s for k, (v, s) in TARGETS.items()]
    res += [(floor_rate(x, Q, mats) - 49.0 * Q) / (0.15 * 49.0 * Q) for Q in RATE_CAL]
    return np.array(res)


def calibrate(mats=None) -> dict:
    mats = mats or db.load()
    sol = least_squares(residuals, X0, bounds=(LB, UB), args=(mats,), diff_step=1e-2, x_scale=X0, xtol=1e-6)
    r = steady_f22(sol.x, mats)
    # parameter standard errors from the Jacobian (residuals are already normalised by target uncertainty)
    J = sol.jac
    try:
        cov = np.linalg.inv(J.T @ J)
        se = np.sqrt(np.diag(cov))
    except np.linalg.LinAlgError:
        se = np.full(len(sol.x), np.nan)
    return {
        "params": dict(zip(NAMES, map(float, sol.x))),
        "param_std_err": dict(zip(NAMES, map(float, se))),
        "fit": {k: float(r[k]) for k in ("T_floor_C", "T_vault_C", "flue_frac", "walls_frac", "door_frac", "T_gas_C", "T_fire_bed_C")},
        "targets": {k: list(v) for k, v in TARGETS.items()},
        "normalised_residuals": list(map(float, sol.fun)),
        "status": sol.message,
    }


def initial_heating_rates(params: dict, feeds=(3.0, 4.5, 6.0, 9.0), mats=None) -> dict:
    """Floor surface heating rate over the first 70 min from cold (F22 Eq. 8), dt = 20 s."""
    mats = mats or db.load()
    x = [params[k] for k in NAMES]
    return {Q: {"model_C_per_h": floor_rate(x, Q, mats, dt_s=20.0), "measured_C_per_h": 49.0 * Q,
                "used_in_calibration": Q in RATE_CAL} for Q in feeds}


if __name__ == "__main__":
    cal = calibrate()
    cal["validation_heating_rate"] = initial_heating_rates(cal["params"])
    OUT.write_text(json.dumps(cal, indent=2))
    print(json.dumps(cal, indent=2))
