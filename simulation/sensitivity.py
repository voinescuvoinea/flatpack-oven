"""One-at-a-time sensitivity of the key predictions to uncertain inputs.

Material ranges come from the materials DB uncertainty fields; fire/cavity
parameter ranges come from the calibration (or +/-30 % where the calibration does
not constrain them). Outputs:
  wood_kg_h  - steady feed holding the floor at 450 C (nominal 10 C ambient)
  heatup_min - time to 430 C floor at 6 kg/h from cold (10 C)
  shell_C    - steady shell temperature at 40 C ambient at the 450 C-floor feed

Run: uv run python -m simulation.sensitivity
"""

from __future__ import annotations

import json
from pathlib import Path

from materials import db
from simulation.configs import oven_b_config
from simulation.oven import OvenModel
from simulation.scenarios import CAL_PATH, calibrated, steady_feed_for_floor

OUT = Path(__file__).resolve().parents[1] / "docs" / "reports" / "phase-2-sensitivity.json"
BASE = {"vault_t_m": 0.064, "ins_t_m": 0.100}


def ranges(mats) -> dict:
    b = mats["refarom_65sa_brick"]
    sw = mats["superwool_plus_blanket_128"]
    ca = mats["casi_board_cs270"]
    co = mats["concrete_base_generic"]
    sh = mats["shell_heat_resistant_paint"]
    cal = json.loads(CAL_PATH.read_text())
    p, se = cal["params"], cal["param_std_err"]

    def band(prop):
        return (1 - prop.rel_low, 1 + prop.rel_high)

    def cal_band(name, lo_lim, hi_lim):
        v, s = p[name], se.get(name, float("nan"))
        if not (s == s) or s > 0.3 * v:  # NaN or poorly constrained -> +/-30 %
            s = 0.3 * v
        return (max(v - s, lo_lim), min(v + s, hi_lim))

    return {
        "brick_k": ("cfg", band(b["thermal_conductivity"])),
        "brick_rho": ("cfg", band(b["density"])),
        "brick_cp": ("cfg", band(b["specific_heat"])),
        "eps_brick": ("cfg", band(b["emissivity"])),
        "sw_k": ("cfg", band(sw["thermal_conductivity"])),
        "casi_k": ("cfg", band(ca["thermal_conductivity"])),
        "conc_k": ("cfg", band(co["thermal_conductivity"])),
        "eps_shell": ("cfg", band(sh["emissivity"])),
        "chi_r": ("fire", cal_band("chi_r", 0.05, 0.6)),
        "excess_air": ("fire", cal_band("excess_air", 1.2, 6.0)),
        "h_in_W_m2K": ("fire", cal_band("h_in_W_m2K", 2.0, 60.0)),
        "tau_burn_s": ("fire", (450.0, 1800.0)),
    }


def evaluate(mats, cfg_scales: dict, fire_over: dict) -> dict:
    fp = calibrated(mats, **fire_over)
    kw = dict(BASE, **cfg_scales)
    wood, _ = steady_feed_for_floor(kw, fp, 450.0, mats)
    m = OvenModel(oven_b_config(mats=mats, **kw), fp)
    log = m.run(6 * 3600, 30.0, lambda _: 6.0 / 3600, stop=lambda r: r["T_floor_C"] >= 430.0)
    heat = log[-1]["t_s"] / 60 if log[-1]["T_floor_C"] >= 430 else float("inf")
    kw40 = dict(kw, T_amb_C=40.0)
    _, r40 = steady_feed_for_floor(kw40, fp, 450.0, mats)
    return {"wood_kg_h": wood, "heatup_min": heat, "shell_C": r40["T_shell_C"]}


def main():
    mats = db.load()
    base = evaluate(mats, {}, {})
    rows = []
    for name, (kind, (lo, hi)) in ranges(mats).items():
        res = {}
        for tag, val in (("low", lo), ("high", hi)):
            cfg, fire = ({name: val}, {}) if kind == "cfg" else ({}, {name: val})
            res[tag] = evaluate(mats, cfg, fire)
        rows.append({"param": name, "low": lo, "high": hi, **{f"{o}_{t}": res[t][o] for t in ("low", "high") for o in base}})
        print(rows[-1], flush=True)
    OUT.write_text(json.dumps({"base": base, "rows": rows}, indent=1))


if __name__ == "__main__":
    main()
