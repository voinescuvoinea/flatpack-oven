"""Phase 3 re-check of the Phase 2 predictions on the as-designed geometry.

Run: uv run python -m simulation.as_designed   -> docs/reports/phase-3-thermal-check.json
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.optimize import brentq

from materials import db
from simulation.configs import oven_b_as_designed
from simulation.oven import OvenModel
from simulation.scenarios import calibrated

OUT = Path(__file__).resolve().parents[1] / "docs" / "reports" / "phase-3-thermal-check.json"


def main():
    mats = db.load()
    fp = calibrated(mats)
    res = {}
    for Ta in (10.0, 40.0, -5.0):
        f = lambda feed: OvenModel(oven_b_as_designed(T_amb_C=Ta, mats=mats), fp).steady(feed)["T_floor_C"] - 450.0
        feed = brentq(f, 0.3, 20.0, xtol=0.01)
        m = OvenModel(oven_b_as_designed(T_amb_C=Ta, mats=mats), fp)
        r = m.steady(feed)
        n0 = m.cfg.vault_layers[0].n_cells + m.cfg.vault_layers[1].n_cells
        res[f"steady_{Ta:+.0f}C"] = {"feed_kg_h": feed, **{k: float(r[k]) for k in ("T_floor_C", "T_vault_C", "T_shell_C", "T_concrete_top_C",
                                     "T_floor_bottom_C", "Q_flue_W", "Q_door_rad_W", "Q_walls_W", "Q_fire_W")},
                                     "T_sw_rw_interface_C": float(0.5 * (m.vault.T[n0 - 1] + m.vault.T[n0]) - 273.15)}
        print(Ta, {k: round(v, 1) for k, v in res[f"steady_{Ta:+.0f}C"].items()}, flush=True)
    for feed in (6.0, 9.0):
        for Ta in (10.0, -5.0):
            m = OvenModel(oven_b_as_designed(T_amb_C=Ta, mats=mats), fp)
            log = m.run(6 * 3600, 30.0, lambda _: feed / 3600, stop=lambda r: r["T_floor_C"] >= 430.0)
            res[f"heatup_{feed:g}kgh_{Ta:+.0f}C"] = {"t_min": log[-1]["t_s"] / 60, "wood_kg": feed * log[-1]["t_s"] / 3600,
                                                     "T_vault_at_ready_C": log[-1]["T_vault_C"]}
            print(feed, Ta, res[f"heatup_{feed:g}kgh_{Ta:+.0f}C"], flush=True)
    OUT.write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
