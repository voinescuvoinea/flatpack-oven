"""Precompute model sweeps for the interactive page (steady and heat-up runs on the as-designed oven).

Run: uv run python -m explorer.sweeps   (~5-8 min) -> explorer/data/sweeps.json
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from scipy.optimize import brentq

from geometry.oven_b import Params
from materials import db
from simulation.configs import oven_b_as_designed
from simulation.oven import OvenModel
from simulation.scenarios import calibrated

OUT = Path(__file__).with_name("data") / "sweeps.json"


def steady_at(p, Ta, T_set, mats, fp):
    f = lambda feed: OvenModel(oven_b_as_designed(p, T_amb_C=Ta, mats=mats), fp).steady(feed)["T_floor_C"] - T_set
    feed = brentq(f, 0.2, 25.0, xtol=0.01)
    r = OvenModel(oven_b_as_designed(p, T_amb_C=Ta, mats=mats), fp).steady(feed)
    return {"feed_kg_h": feed, **{k: float(r[k]) for k in ("T_floor_C", "T_vault_C", "T_gas_C", "T_shell_C", "T_concrete_top_C",
                                                            "Q_flue_W", "Q_door_rad_W", "Q_walls_W", "Q_fire_W")}}


def main():
    mats = db.load()
    fp = calibrated(mats)
    base = Params()
    out = {"insulation": [], "setpoint": [], "heatup": []}
    for rw in (50.0, 75.0, 100.0, 125.0, 150.0):
        for Ta in (-5.0, 10.0, 25.0, 40.0):
            r = steady_at(replace(base, rw_t=rw), Ta, 450.0, mats, fp)
            out["insulation"].append({"rw_mm": rw, "T_amb_C": Ta, **r})
            print("ins", rw, Ta, round(r["T_shell_C"], 1), round(r["feed_kg_h"], 2), flush=True)
    for T_set in (400.0, 430.0, 450.0, 480.0):
        r = steady_at(base, 10.0, T_set, mats, fp)
        out["setpoint"].append({"T_set_C": T_set, **r})
        print("set", T_set, round(r["feed_kg_h"], 2), flush=True)
    for feed in (4.0, 6.0, 8.0, 10.0, 12.0):
        m = OvenModel(oven_b_as_designed(base, T_amb_C=10.0, mats=mats), fp)
        log = m.run(8 * 3600, 30.0, lambda _: feed / 3600, stop=lambda r: r["T_floor_C"] >= 430.0)
        ok = bool(log[-1]["T_floor_C"] >= 430.0)
        out["heatup"].append({"feed_kg_h": feed, "reached": ok, "t_min": log[-1]["t_s"] / 60, "wood_kg": feed * log[-1]["t_s"] / 3600,
                              "curve": [{"t_min": r["t_s"] / 60, "floor": round(r["T_floor_C"], 1), "vault": round(r["T_vault_C"], 1)}
                                        for r in log[::4]]})
        print("heat", feed, round(log[-1]["t_s"] / 60), flush=True)
    OUT.write_text(json.dumps(out, default=lambda o: o.item() if hasattr(o, "item") else str(o)))


if __name__ == "__main__":
    main()
