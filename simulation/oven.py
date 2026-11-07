"""Coupled oven model: cavity (radiation network + well-stirred gas) + 1D wall stacks.

Surfaces: floor (cooking area), fire bed, door, vault (arch + walls, one isothermal surface).
- Fire bed: prescribed radiative output chi_r * Q; reradiating when the fire is out.
- Door: black at ambient when open; reradiating (adiabatic) when closed.
- Floor and vault: brick emissivity eps(T) from the DB; absorb irradiation G from the
  radiosity solve (lagged by one time step), emit implicitly, and exchange convection
  with the gas.
- Gas, door open: two-zone mouth flow. Ambient air enters low and sweeps the
  floor (cooling it); the hot upper layer gets (1 - chi_r) Q plus the floor's
  heat, convects to the vault, and leaves as enthalpy. Door closed: one still,
  well-mixed zone.
- Walls: verified 1D layered conduction (simulation/conduction.py). The vault is
  modelled as a cylinder (barrel) or sphere (dome) of the vault's inner area.
- Outside: still-air natural convection (worst case) + radiation to ambient.

Simplifications are listed in docs/reports/phase-2.md and docs/risks.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np
from scipy.constants import Stefan_Boltzmann as SIGMA

from simulation.conduction import BC, Layer, Stack
from simulation.convection import air, h_natural
from simulation.fire import FireParams
from simulation.radiation import ConvexCavity, solve_radiosity, view_factors

FIRE_BED_EPS = 0.9  # only used to report an implied fire-bed temperature (diagnostic)
_VF_CACHE: dict = {}


@dataclass
class OvenConfig:
    name: str
    cavity: ConvexCavity
    vault_layers: list[Layer]
    vault_geometry: str
    vault_r_inner_m: float
    vault_outer: tuple[str, float]        # (convection shape, characteristic length m)
    floor_layers: list[Layer]
    floor_outer: tuple[str, float]
    eps_brick: Callable[[float], float]
    eps_shell: float
    eps_floor_bottom: float
    T_amb_K: float = 283.15
    n_rays: int = 300_000


@dataclass
class OvenModel:
    cfg: OvenConfig
    fire: FireParams
    door_closed: bool = False
    t_s: float = 0.0
    M_wood_kg: float = 0.0
    log: list = field(default_factory=list)

    def __post_init__(self):
        key = (type(self.cfg.cavity).__name__, repr(self.cfg.cavity.__dict__ if hasattr(self.cfg.cavity, "__dict__") else ""), self.cfg.n_rays)
        if key not in _VF_CACHE:
            _VF_CACHE[key] = view_factors(self.cfg.cavity, self.cfg.n_rays)
        self.F, self.A = _VF_CACHE[key]
        Ta = self.cfg.T_amb_K
        self.vault = Stack(self.cfg.vault_layers, self.cfg.vault_geometry, self.cfg.vault_r_inner_m, T_init_K=Ta)
        self.floor = Stack(self.cfg.floor_layers, "planar", T_init_K=Ta)
        self.T_g = Ta
        self._h_v = h_natural(*self.cfg.vault_outer)
        self._h_f = h_natural(*self.cfg.floor_outer)

    # ------------------------------------------------------------------ cavity
    def _cavity(self, burn_kg_s: float) -> dict:
        Ta = self.cfg.T_amb_K
        Tf, Tv = self.floor.T_inner_K, self.vault.T_inner_K
        Q = self.fire.heat_release_W(burn_kg_s)
        eps = np.array([self.cfg.eps_brick(Tf), FIRE_BED_EPS, 1.0, self.cfg.eps_brick(Tv)])
        T = np.array([Tf, np.nan, Ta, Tv])
        q = np.array([np.nan, self.fire.chi_r * Q / self.A[1], np.nan, np.nan])
        if self.door_closed:
            T[2], q[2], eps[2] = np.nan, 0.0, 0.9
        r = solve_radiosity(self.F, self.A, eps, T, q)
        G = self.F @ r["J_W_m2"]
        m_g = 0.0 if self.door_closed else self.fire.gas_flow_kg_s(burn_kg_s)
        cp = air(0.5 * (self.T_g + Ta))["cp"]
        h = self.fire.h_in_W_m2K
        Af, Av = self.A[0], self.A[3]
        Q_gas = (1 - self.fire.chi_r) * Q
        if self.door_closed:
            # still, well-mixed gas
            T_floor_gas = T_g = (Q_gas + h * (Af * Tf + Av * Tv)) / (h * (Af + Av))
            Q_floor_air = 0.0
        else:
            # two-zone flow through the open mouth: ambient air enters low and sweeps the floor,
            # combustion products form a hot upper layer that sweeps the vault and leaves high.
            T_floor_gas = Ta
            Q_floor_air = h * Af * (Tf - Ta)  # heat picked up from the floor by inflowing air
            T_g = (Q_gas + Q_floor_air + h * Av * Tv + m_g * cp * Ta) / (h * Av + m_g * cp)
        return {"Q": Q, "G": G, "T_g": T_g, "T_floor_gas": T_floor_gas, "m_g": m_g, "cp": cp, "rad": r, "eps": eps}

    def _bcs(self, c: dict) -> tuple[BC, BC, BC, BC]:
        Ta, h = self.cfg.T_amb_K, self.fire.h_in_W_m2K
        Tf, Tv = self.floor.T_inner_K, self.vault.T_inner_K
        Gf, Gv = max(c["G"][0], 0.0), max(c["G"][3], 0.0)
        v_in = BC(h=h, T_inf_K=c["T_g"], eps=self.cfg.eps_brick(Tv), T_rad_K=(Gv / SIGMA) ** 0.25)
        f_in = BC(h=h, T_inf_K=c["T_floor_gas"], eps=self.cfg.eps_brick(Tf), T_rad_K=(Gf / SIGMA) ** 0.25)
        v_out = BC(h=lambda Ts: self._h_v(Ts, Ta), T_inf_K=Ta, eps=self.cfg.eps_shell, T_rad_K=Ta)
        f_out = BC(h=lambda Ts: self._h_f(Ts, Ta), T_inf_K=Ta, eps=self.cfg.eps_floor_bottom, T_rad_K=Ta)
        return v_in, v_out, f_in, f_out

    def _record(self, c, rv, rf, feed, burn):
        Ta = self.cfg.T_amb_K
        Av, Af = self.A[3], self.A[0]
        q_door = c["rad"]["q_W_m2"][2]
        rec = {
            "t_s": self.t_s, "feed_kg_h": feed * 3600, "burn_kg_h": burn * 3600, "Q_fire_W": c["Q"],
            "T_floor_C": self.floor.T_inner_K - 273.15, "T_vault_C": self.vault.T_inner_K - 273.15,
            "T_gas_C": c["T_g"] - 273.15, "T_shell_C": self.vault.T_outer_K - 273.15,
            "T_floor_bottom_C": self.floor.T_outer_K - 273.15,
            "Q_flue_W": c["m_g"] * c["cp"] * (c["T_g"] - Ta),
            "Q_door_rad_W": -q_door * self.A[2] if not self.door_closed else 0.0,
            "Q_walls_W": -(rv["q_out_W_m2"] * Av + rf["q_out_W_m2"] * Af),
            "T_fire_bed_C": c["rad"]["T_K"][1] - 273.15,
        }
        # interface temperature brick/insulation in the floor stack (base of first layer)
        n0 = self.cfg.floor_layers[0].n_cells
        rec["T_floor_brick_base_C"] = float(np.mean(self.floor.T[n0 - 1:n0 + 1])) - 273.15
        n1 = n0 + self.cfg.floor_layers[1].n_cells
        rec["T_concrete_top_C"] = float(np.mean(self.floor.T[n1 - 1:n1 + 1])) - 273.15 if len(self.cfg.floor_layers) > 2 else float("nan")
        return rec

    # ------------------------------------------------------------------ time stepping
    def step(self, dt_s: float, feed_kg_s: float) -> dict:
        burn = self.M_wood_kg / self.fire.tau_burn_s
        c = self._cavity(burn)
        v_in, v_out, f_in, f_out = self._bcs(c)
        rv = self.vault.step(dt_s, v_in, v_out)
        rf = self.floor.step(dt_s, f_in, f_out)
        self.T_g = c["T_g"]
        self.M_wood_kg += (feed_kg_s - burn) * dt_s
        self.t_s += dt_s
        rec = self._record(c, rv, rf, feed_kg_s, burn)
        self.log.append(rec)
        return rec

    def run(self, t_end_s: float, dt_s: float, feed: Callable[["OvenModel"], float], stop: Callable[[dict], bool] | None = None) -> list[dict]:
        out = []
        while self.t_s < t_end_s - 1e-9:
            rec = self.step(dt_s, feed(self))
            out.append(rec)
            if stop and stop(rec):
                break
        return out

    # ------------------------------------------------------------------ steady state
    def steady(self, feed_kg_h: float, relax: float = 0.6, tol_K: float = 0.01, max_iter: int = 400) -> dict:
        burn = feed_kg_h / 3600.0
        self.M_wood_kg = burn * self.fire.tau_burn_s
        for it in range(max_iter):
            Tf0, Tv0 = self.floor.T_inner_K, self.vault.T_inner_K
            c = self._cavity(burn)
            v_in, v_out, f_in, f_out = self._bcs(c)
            Tv_old, Tf_old = self.vault.T.copy(), self.floor.T.copy()
            rv = self.vault.step(None, v_in, v_out)
            rf = self.floor.step(None, f_in, f_out)
            self.vault.T = Tv_old + relax * (self.vault.T - Tv_old)
            self.floor.T = Tf_old + relax * (self.floor.T - Tf_old)
            self.vault._Ts = [Tv0 + relax * (rv["Ts_in_K"] - Tv0), self.vault._Ts[1]]
            self.floor._Ts = [Tf0 + relax * (rf["Ts_in_K"] - Tf0), self.floor._Ts[1]]
            self.T_g = c["T_g"]
            if max(abs(self.floor.T_inner_K - Tf0), abs(self.vault.T_inner_K - Tv0)) < tol_K and it > 5:
                break
        else:
            raise RuntimeError("steady state did not converge")
        c = self._cavity(burn)
        v_in, v_out, f_in, f_out = self._bcs(c)
        rv = self.vault.step(None, v_in, v_out)
        rf = self.floor.step(None, f_in, f_out)
        return self._record(c, rv, rf, burn, burn)
