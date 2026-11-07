"""Phase 2 predictions for concept B, using the F22-calibrated fire/cavity parameters.

Run: uv run python -m simulation.scenarios   (writes docs/reports/phase-2-results.json)
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.optimize import brentq

from materials import db
from simulation.configs import oven_b_config
from simulation.fire import FireParams
from simulation.oven import OvenModel

CAL_PATH = Path(__file__).resolve().parents[1] / "validation" / "f22_calibration.json"
OUT = Path(__file__).resolve().parents[1] / "docs" / "reports" / "phase-2-results.json"


def calibrated(mats=None, **override) -> FireParams:
    p = json.loads(CAL_PATH.read_text())["params"]
    return FireParams.from_db(override.get("chi_r", p["chi_r"]), override.get("excess_air", p["excess_air"]),
                              override.get("h_in_W_m2K", p["h_in_W_m2K"]), tau_burn_s=override.get("tau_burn_s", 900.0), mats=mats)


def steady_feed_for_floor(cfg_kw: dict, fp: FireParams, T_set_C: float = 450.0, mats=None) -> tuple[float, dict]:
    def f(feed):
        return OvenModel(oven_b_config(mats=mats, **cfg_kw), fp).steady(feed)["T_floor_C"] - T_set_C
    feed = brentq(f, 0.3, 20.0, xtol=0.01)
    return feed, OvenModel(oven_b_config(mats=mats, **cfg_kw), fp).steady(feed)


def session(cfg_kw: dict, fp: FireParams, heat_feed_kg_h: float, T_set_C: float = 450.0, T_ready_C: float = 430.0,
            hold_min: float = 60.0, retention_h: float = 10.0, dt_s: float = 30.0, mats=None, feed_ss_kg_h: float | None = None) -> dict:
    """Heat up at a fixed feed until the floor reaches T_ready, hold the floor near T_set for hold_min
    with a proportional feed controller, then stop feeding, close the door and watch it cool."""
    m = OvenModel(oven_b_config(mats=mats, **cfg_kw), fp)
    heat = m.run(6 * 3600, dt_s, lambda _: heat_feed_kg_h / 3600, stop=lambda r: r["T_floor_C"] >= T_ready_C)
    reached = heat[-1]["T_floor_C"] >= T_ready_C
    t_heat_min = heat[-1]["t_s"] / 60
    wood_heat = heat_feed_kg_h * t_heat_min / 60
    if feed_ss_kg_h is None:
        feed_ss_kg_h, _ = steady_feed_for_floor(cfg_kw, fp, T_set_C, mats)
    Kp = 0.05  # kg/h per K
    t0 = m.t_s
    hold = m.run(t0 + hold_min * 60, dt_s,
                 lambda mod: float(np.clip(feed_ss_kg_h + Kp * (T_set_C - mod.floor.T_inner_K + 273.15), 0, 12)) / 3600)
    m.door_closed = True
    t1 = m.t_s
    cool = m.run(t1 + retention_h * 3600, 60.0, lambda _: 0.0)
    T_floor_cool = np.array([r["T_floor_C"] for r in cool])
    t_cool_h = (np.array([r["t_s"] for r in cool]) - t1) / 3600

    def t_below(T):
        idx = np.nonzero(T_floor_cool < T)[0]
        return float(t_cool_h[idx[0]]) if len(idx) else float("nan")

    allrec = heat + hold + cool
    return {
        "heat_feed_kg_h": heat_feed_kg_h, "reached_ready": bool(reached),
        "t_heatup_min": t_heat_min, "wood_heatup_kg": wood_heat,
        "hold_feed_mean_kg_h": float(np.mean([r["feed_kg_h"] for r in hold])),
        "hold_floor_min_C": float(min(r["T_floor_C"] for r in hold)), "hold_floor_max_C": float(max(r["T_floor_C"] for r in hold)),
        "hold_vault_mean_C": float(np.mean([r["T_vault_C"] for r in hold])),
        "shell_max_C": float(max(r["T_shell_C"] for r in allrec)),
        "concrete_top_max_C": float(max(r["T_concrete_top_C"] for r in allrec)),
        "retention_h_to_300C": t_below(300.0), "retention_h_to_200C": t_below(200.0),
        "floor_C_after_8h_closed": float(np.interp(8.0, t_cool_h, T_floor_cool)),
        "timeline": [{k: round(float(r[k]), 2) for k in ("t_s", "feed_kg_h", "T_floor_C", "T_vault_C", "T_gas_C", "T_shell_C", "T_concrete_top_C")}
                     for r in allrec[:: max(1, len(allrec) // 400)]],
    }


def shell_check(cfg_kw: dict, fp: FireParams, ins_list=(0.050, 0.075, 0.100, 0.125, 0.150), T_amb_C=40.0, T_set_C=450.0, mats=None) -> list[dict]:
    """Steady state (long session upper bound) at a hot ambient: shell and concrete temperatures vs insulation."""
    out = []
    for t in ins_list:
        kw = dict(cfg_kw, ins_t_m=t, T_amb_C=T_amb_C)
        feed, r = steady_feed_for_floor(kw, fp, T_set_C, mats)
        out.append({"ins_mm": t * 1000, "feed_kg_h": feed, "T_shell_C": r["T_shell_C"], "T_concrete_top_C": r["T_concrete_top_C"],
                    "T_floor_bottom_C": r["T_floor_bottom_C"], "T_vault_C": r["T_vault_C"],
                    "walls_W": r["Q_walls_W"], "flue_W": r["Q_flue_W"], "door_W": r["Q_door_rad_W"]})
    return out


def main():
    mats = db.load()
    fp = calibrated(mats)
    res = {"calibration": json.loads(CAL_PATH.read_text())}
    res["variants"] = {}
    for vt in (0.114, 0.064):
        kw = {"vault_t_m": vt, "ins_t_m": 0.100}
        feed_ss, ss = steady_feed_for_floor(kw, fp, 450.0, mats)
        v = {"steady_feed_for_450C_kg_h": feed_ss, "steady": {k: float(ss[k]) for k in ("T_floor_C", "T_vault_C", "T_gas_C", "T_shell_C", "T_concrete_top_C", "Q_flue_W", "Q_door_rad_W", "Q_walls_W", "Q_fire_W")}}
        v["sessions"] = {str(f): session(kw, fp, f, mats=mats, feed_ss_kg_h=feed_ss) for f in (6.0, 9.0)}
        res["variants"][f"vault_{int(vt*1000)}mm"] = v
        print(vt, {k: (round(x, 2) if isinstance(x, float) else x) for k, x in v["sessions"]["6.0"].items() if k != "timeline"}, flush=True)
    res["shell_check_40C"] = shell_check({"vault_t_m": 0.064}, fp, mats=mats)
    OUT.write_text(json.dumps(res, indent=1))
    return res


if __name__ == "__main__":
    main()
