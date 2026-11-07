"""1D transient heat conduction through layered walls.

Finite volume, cell-centred, fully implicit (backward Euler) in time, with Picard
iteration for temperature-dependent k(T), rho*cp(T) and nonlinear boundary
conditions (convection + radiation). Planar, cylindrical and spherical geometry.
Exact log/inverse-radius resistances are used inside each cell.

All quantities are SI, temperatures in kelvin. Fluxes and heat capacities are
per unit INNER surface area (the surface at x = 0), so curved and planar stacks
share one convention. x runs from the inner (hot) face outwards.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np
from scipy.constants import Stefan_Boltzmann as SIGMA
from scipy.linalg import solve_banded

from materials import db

PropFn = Callable[[np.ndarray], np.ndarray]  # T_K -> value

#: Material properties that were evaluated outside their sourced range (see docs/risks.md K-17, K-23).
EXTRAPOLATED: set[str] = set()


def _prop_fn(mat: db.Material, name: str, scale: float, extrapolate: bool) -> PropFn:
    prop = mat[name]
    if prop.is_constant:
        v = float(prop.values_si[0]) * scale
        return lambda T: np.full(np.shape(T), v)
    lo, hi = prop.T_K[0], prop.T_K[-1]

    def f(T):
        T = np.asarray(T, dtype=float)
        if extrapolate and (np.any(T < lo) or np.any(T > hi)):
            EXTRAPOLATED.add(f"{mat.id}.{name}")
        return np.asarray(prop.at(T, extrapolate=extrapolate)) * scale

    return f


@dataclass
class Layer:
    """One homogeneous layer. k [W/(m K)] and rho_cp [J/(m3 K)] are functions of T [K]."""

    name: str
    thickness_m: float
    k: PropFn
    rho_cp: PropFn
    n_cells: int = 8

    @classmethod
    def from_material(
        cls, mat: db.Material, thickness_m: float, n_cells: int = 8, *,
        k_scale: float = 1.0, rho_scale: float = 1.0, cp_scale: float = 1.0, extrapolate: bool = True,
    ) -> "Layer":
        k = _prop_fn(mat, "thermal_conductivity", k_scale, extrapolate)
        rho = _prop_fn(mat, "density", rho_scale, extrapolate)
        cp = _prop_fn(mat, "specific_heat", cp_scale, extrapolate)
        return cls(mat.id, thickness_m, k, lambda T: rho(T) * cp(T), n_cells)

    @classmethod
    def constant(cls, name: str, thickness_m: float, k: float, rho_cp: float, n_cells: int = 8) -> "Layer":
        return cls(name, thickness_m, lambda T: np.full(np.shape(T), k), lambda T: np.full(np.shape(T), rho_cp), n_cells)


@dataclass
class BC:
    """Boundary condition. Heat flux INTO the body per unit area of that surface [W/m2]:

        q(Ts) = q_W_m2 + h(Ts) * (T_inf_K - Ts) + eps * sigma * (T_rad_K**4 - Ts**4)

    or a fixed surface temperature if T_fixed_K is set. h may be a float or a function h(Ts) [W/(m2 K)].
    """

    T_fixed_K: float | None = None
    q_W_m2: float = 0.0
    h: float | Callable[[float], float] = 0.0
    T_inf_K: float = 293.15
    eps: float = 0.0
    T_rad_K: float = 293.15

    def linearised(self, Ts: float) -> tuple[float, float]:
        """(a, b) with q(T) ~= a - b*T near T = Ts."""
        h = self.h(Ts) if callable(self.h) else self.h
        r = self.eps * SIGMA
        a = self.q_W_m2 + h * self.T_inf_K + r * (self.T_rad_K**4 - Ts**4) + 4 * r * Ts**4
        b = h + 4 * r * Ts**3
        return a, b

    def flux(self, Ts: float) -> float:
        h = self.h(Ts) if callable(self.h) else self.h
        return self.q_W_m2 + h * (self.T_inf_K - Ts) + self.eps * SIGMA * (self.T_rad_K**4 - Ts**4)


@dataclass
class Stack:
    """Layered wall. geometry: 'planar' | 'cylinder' | 'sphere'; r_inner_m required if curved."""

    layers: list[Layer]
    geometry: str = "planar"
    r_inner_m: float | None = None
    T_init_K: float = 293.15
    T: np.ndarray = field(init=False)

    def __post_init__(self):
        if self.geometry not in ("planar", "cylinder", "sphere"):
            raise ValueError(self.geometry)
        if self.geometry != "planar" and not self.r_inner_m:
            raise ValueError("curved stack needs r_inner_m")
        xf, owner = [0.0], []
        for li, L in enumerate(self.layers):
            dx = L.thickness_m / L.n_cells
            for _ in range(L.n_cells):
                xf.append(xf[-1] + dx)
                owner.append(li)
        self.x_faces = np.array(xf)
        self.x_cells = 0.5 * (self.x_faces[:-1] + self.x_faces[1:])
        self.owner = np.array(owner)
        self.n = len(owner)
        self.T = np.full(self.n, float(self.T_init_K))
        r0 = self.r_inner_m or 1.0
        rf = r0 + self.x_faces
        if self.geometry == "planar":
            self.vol = np.diff(self.x_faces)
            self.area_out = 1.0
        elif self.geometry == "cylinder":
            self.vol = (rf[1:] ** 2 - rf[:-1] ** 2) / (2 * r0)
            self.area_out = rf[-1] / r0
        else:
            self.vol = (rf[1:] ** 3 - rf[:-1] ** 3) / (3 * r0**2)
            self.area_out = (rf[-1] / r0) ** 2
        self._Ts = [float(self.T_init_K), float(self.T_init_K)]

    # resistance per unit inner area between positions x1 < x2 with conductivity k
    def _R(self, x1: float, x2: float, k: float) -> float:
        if self.geometry == "planar":
            return (x2 - x1) / k
        r0 = self.r_inner_m
        r1, r2 = r0 + x1, r0 + x2
        if self.geometry == "cylinder":
            return r0 * np.log(r2 / r1) / k
        return r0**2 * (1.0 / r1 - 1.0 / r2) / k

    def _k_cells(self, T: np.ndarray) -> np.ndarray:
        k = np.empty(self.n)
        for li, L in enumerate(self.layers):
            m = self.owner == li
            k[m] = L.k(T[m])
        return k

    def _C_cells(self, T: np.ndarray) -> np.ndarray:
        c = np.empty(self.n)
        for li, L in enumerate(self.layers):
            m = self.owner == li
            c[m] = L.rho_cp(T[m])
        return c * self.vol

    @property
    def total_thickness_m(self) -> float:
        return float(self.x_faces[-1])

    @property
    def T_inner_K(self) -> float:
        return self._Ts[0]

    @property
    def T_outer_K(self) -> float:
        return self._Ts[1]

    def heat_content_J(self, T_ref_K: float) -> float:
        """Sensible heat above T_ref [J per m2 of inner area], using rho*cp at cell temperature."""
        return float(np.sum(self._C_cells(self.T) * (self.T - T_ref_K)))

    def step(self, dt_s: float | None, bc_in: BC, bc_out: BC, *, tol_K: float = 1e-6, max_iter: int = 50) -> dict:
        """Advance by dt_s (None = steady state). Returns boundary fluxes into the body
        [W per m2 of inner area] and surface temperatures [K]."""
        T_old = self.T.copy()
        T = self.T.copy()
        Ts_in, Ts_out = self._Ts
        for _ in range(max_iter):
            k = self._k_cells(T)
            C = self._C_cells(T) if dt_s else np.zeros(self.n)
            # interior face conductances
            G = np.empty(self.n - 1)
            for i in range(self.n - 1):
                xf = self.x_faces[i + 1]
                G[i] = 1.0 / (self._R(self.x_cells[i], xf, k[i]) + self._R(xf, self.x_cells[i + 1], k[i + 1]))
            G_in = 1.0 / self._R(0.0, self.x_cells[0], k[0])
            G_out = 1.0 / self._R(self.x_cells[-1], self.x_faces[-1], k[-1])
            diag = (C / dt_s if dt_s else np.zeros(self.n)).copy()
            rhs = (C / dt_s * T_old if dt_s else np.zeros(self.n)).copy()
            upper = np.zeros(self.n)
            lower = np.zeros(self.n)
            diag[:-1] += G
            diag[1:] += G
            upper[1:] = -G
            lower[:-1] = -G
            coeffs = []
            for idx, bc, Gb, A, Ts in ((0, bc_in, G_in, 1.0, Ts_in), (self.n - 1, bc_out, G_out, self.area_out, Ts_out)):
                if bc.T_fixed_K is not None:
                    c0, c1 = Gb * bc.T_fixed_K, Gb
                else:
                    a, b = bc.linearised(Ts)
                    c0, c1 = Gb * A * a / (Gb + A * b), Gb * A * b / (Gb + A * b)
                diag[idx] += c1
                rhs[idx] += c0
                coeffs.append((Gb, A, bc))
            ab = np.vstack([upper, diag, lower])
            T_new = solve_banded((1, 1), ab, rhs)
            # update surface temperatures
            Ts_new = []
            for (Gb, A, bc), Tc in zip(coeffs, (T_new[0], T_new[-1])):
                if bc.T_fixed_K is not None:
                    Ts_new.append(bc.T_fixed_K)
                else:
                    a, b = bc.linearised((Ts_in, Ts_out)[len(Ts_new)])
                    Ts_new.append((Gb * Tc + A * a) / (Gb + A * b))
            change = max(np.max(np.abs(T_new - T)), abs(Ts_new[0] - Ts_in), abs(Ts_new[1] - Ts_out))
            T, (Ts_in, Ts_out) = T_new, Ts_new
            if change < tol_K:
                break
        else:
            raise RuntimeError("conduction Picard iteration did not converge")
        self.T, self._Ts = T, [Ts_in, Ts_out]
        q_in = G_in * (Ts_in - T[0])  # into the body at inner face, per m2 inner area
        q_out = G_out * (Ts_out - T[-1])  # into the body at outer face, per m2 inner area
        return {"q_in_W_m2": q_in, "q_out_W_m2": q_out, "Ts_in_K": Ts_in, "Ts_out_K": Ts_out}
