"""Cavity radiation: Monte Carlo view factors for convex cavities + gray-diffuse radiosity network.

Cavities are convex, so a ray leaving a surface into the interior hits exactly one
boundary point. That point is found by bisection on an inside() test. Rays are
emitted only from planar surfaces (floor, fire bed, door). The view factors from
the single curved "vault" surface follow from reciprocity and summation.

Coordinates: x across, y depth (front/door side at low y), z up. Metres.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.constants import Stefan_Boltzmann as SIGMA
from scipy.integrate import quad


# ----------------------------------------------------------------------------- cavities
class ConvexCavity:
    names: list[str]          # surface names; the last one is the curved remainder ("vault")
    emitters: list[str]       # planar surfaces we shoot rays from
    size_m: float             # bounding length for ray marching

    def inside(self, p: np.ndarray) -> np.ndarray: ...
    def classify(self, p: np.ndarray) -> np.ndarray: ...
    def sample(self, name: str, n: int, rng) -> tuple[np.ndarray, np.ndarray]: ...
    def area(self, name: str) -> float: ...
    def total_area(self) -> float: ...


def _cosine_dirs(normals: np.ndarray, rng) -> np.ndarray:
    n = normals.shape[0]
    u1, u2 = rng.random(n), rng.random(n)
    r, phi = np.sqrt(u1), 2 * math.pi * u2
    local = np.stack([r * np.cos(phi), r * np.sin(phi), np.sqrt(1 - u1)], axis=1)
    # orthonormal basis around each normal
    a = np.where(np.abs(normals[:, :1]) < 0.9, np.array([[1.0, 0, 0]]), np.array([[0, 1.0, 0]]))
    t1 = np.cross(normals, a)
    t1 /= np.linalg.norm(t1, axis=1, keepdims=True)
    t2 = np.cross(normals, t1)
    return local[:, :1] * t1 + local[:, 1:2] * t2 + local[:, 2:] * normals


def view_factors(cav: ConvexCavity, n_rays: int = 200_000, seed: int = 1) -> tuple[np.ndarray, np.ndarray]:
    """Return (F, A): F[i, j] view factor from surface i to j, A[i] areas [m2], ordered as cav.names."""
    rng = np.random.default_rng(seed)
    names = cav.names
    N = len(names)
    A = np.array([cav.area(nm) if nm != names[-1] else 0.0 for nm in names])
    A[-1] = cav.total_area() - A[:-1].sum()
    F = np.zeros((N, N))
    for nm in cav.emitters:
        i = names.index(nm)
        p0, nrm = cav.sample(nm, n_rays, rng)
        d = _cosine_dirs(nrm, rng)
        start = p0 + 1e-9 * nrm
        lo, hi = np.zeros(n_rays), np.full(n_rays, 2.5 * cav.size_m)
        for _ in range(48):
            mid = 0.5 * (lo + hi)
            ins = cav.inside(start + mid[:, None] * d)
            lo = np.where(ins, mid, lo)
            hi = np.where(ins, hi, mid)
        hit = start + hi[:, None] * d
        j = cav.classify(hit)
        F[i] = np.bincount(j, minlength=N) / n_rays
    # curved remainder by reciprocity and summation
    v = N - 1
    for j in range(N - 1):
        F[v, j] = A[j] * F[j, v] / A[v]
    F[v, v] = 1.0 - F[v, :v].sum()
    return F, A


class BoxCavity(ConvexCavity):
    """Test cavity: a x a x d box; emitter = bottom; surfaces: bottom, top, sides(remainder)."""

    def __init__(self, a, d):
        self.a, self.d, self.size_m = a, d, math.sqrt(2 * a * a + d * d)
        self.names, self.emitters = ["bottom", "top", "sides"], ["bottom", "top"]

    def inside(self, p):
        h = self.a / 2
        return (np.abs(p[:, 0]) < h) & (np.abs(p[:, 1]) < h) & (p[:, 2] > 0) & (p[:, 2] < self.d)

    def classify(self, p):
        e = 1e-7
        return np.where(p[:, 2] < e, 0, np.where(p[:, 2] > self.d - e, 1, 2))

    def sample(self, name, n, rng):
        xy = (rng.random((n, 2)) - 0.5) * self.a
        z = np.zeros((n, 1)) if name == "bottom" else np.full((n, 1), self.d)
        nz = 1.0 if name == "bottom" else -1.0
        return np.hstack([xy, z]), np.tile([0, 0, nz], (n, 1)).astype(float)

    def area(self, name):
        return self.a**2

    def total_area(self):
        return 2 * self.a**2 + 4 * self.a * self.d


class CylinderCavity(ConvexCavity):
    """Test cavity: vertical cylinder radius r, height d; bottom, top, wall(remainder)."""

    def __init__(self, r, d):
        self.r, self.d, self.size_m = r, d, math.hypot(2 * r, d)
        self.names, self.emitters = ["bottom", "top", "wall"], ["bottom", "top"]

    def inside(self, p):
        return (p[:, 0] ** 2 + p[:, 1] ** 2 < self.r**2) & (p[:, 2] > 0) & (p[:, 2] < self.d)

    def classify(self, p):
        e = 1e-7
        return np.where(p[:, 2] < e, 0, np.where(p[:, 2] > self.d - e, 1, 2))

    def sample(self, name, n, rng):
        rr, ph = self.r * np.sqrt(rng.random(n)), 2 * math.pi * rng.random(n)
        z = np.zeros(n) if name == "bottom" else np.full(n, self.d)
        nz = 1.0 if name == "bottom" else -1.0
        return np.stack([rr * np.cos(ph), rr * np.sin(ph), z], 1), np.tile([0, 0, nz], (n, 1)).astype(float)

    def area(self, name):
        return math.pi * self.r**2

    def total_area(self):
        return 2 * math.pi * self.r**2 + 2 * math.pi * self.r * self.d


@dataclass
class BarrelVault(ConvexCavity):
    """Rectangular floor W (x) by L (y); side walls hw; segmental arch of rise `rise` over the span.
    Door (w x h rectangle) centred in the front wall y=0. Fire bed = back strip of depth fire_d."""

    W: float
    L: float
    hw: float
    rise: float
    door_w: float
    door_h: float
    fire_d: float

    def __post_init__(self):
        s = self.W
        self.R = (s * s / 4 + self.rise**2) / (2 * self.rise)
        self.zc = self.hw + self.rise - self.R
        self.theta = 2 * math.asin(s / (2 * self.R))
        self.names = ["floor", "fire", "door", "vault"]
        self.emitters = ["floor", "fire", "door"]
        self.size_m = math.sqrt(self.W**2 + self.L**2 + (self.hw + self.rise) ** 2)

    def inside(self, p):
        x, y, z = p[:, 0], p[:, 1], p[:, 2]
        box = (np.abs(x) < self.W / 2) & (y > 0) & (y < self.L) & (z > 0)
        arch = (z <= self.hw) | (x * x + (z - self.zc) ** 2 < self.R**2)
        return box & arch

    def classify(self, p):
        e = 1e-7
        x, y, z = p[:, 0], p[:, 1], p[:, 2]
        out = np.full(len(p), 3)
        floor = z < e
        out[floor & (y < self.L - self.fire_d)] = 0
        out[floor & (y >= self.L - self.fire_d)] = 1
        door = (y < e) & (np.abs(x) <= self.door_w / 2) & (z <= self.door_h) & ~floor
        out[door] = 2
        return out

    def sample(self, name, n, rng):
        if name == "floor":
            p = np.stack([(rng.random(n) - 0.5) * self.W, rng.random(n) * (self.L - self.fire_d), np.zeros(n)], 1)
            nrm = [0, 0, 1.0]
        elif name == "fire":
            p = np.stack([(rng.random(n) - 0.5) * self.W, self.L - self.fire_d * rng.random(n), np.zeros(n)], 1)
            nrm = [0, 0, 1.0]
        else:
            p = np.stack([(rng.random(n) - 0.5) * self.door_w, np.zeros(n), rng.random(n) * self.door_h], 1)
            nrm = [0, 1.0, 0]
        return p, np.tile(nrm, (n, 1))

    def end_wall_area(self) -> float:
        return self.W * self.hw + self.R**2 / 2 * (self.theta - math.sin(self.theta))

    def area(self, name):
        return {"floor": self.W * (self.L - self.fire_d), "fire": self.W * self.fire_d, "door": self.door_w * self.door_h}[name]

    def total_area(self):
        return self.W * self.L + 2 * self.hw * self.L + self.R * self.theta * self.L + 2 * self.end_wall_area()


@dataclass
class DomeOven(ConvexCavity):
    """Falciano et al. (2022) pilot-oven shape: cylinder radius R, wall height hw, oblate
    half-spheroid of height c on top. The semicircular mouth (radius rd) is taken as planar,
    in the chord plane y = -y0 where the chord width equals the mouth width. The fire bed is
    the back circular segment holding `fire_frac` of the full floor area."""

    R: float
    hw: float
    c: float
    rd: float
    fire_frac: float

    def __post_init__(self):
        self.y0 = math.sqrt(self.R**2 - self.rd**2)
        th = _solve_theta(self.fire_frac)
        self.fire_y = self.R * math.cos(th / 2)  # fire where y > fire_y
        self.names = ["floor", "fire", "door", "vault"]
        self.emitters = ["floor", "fire", "door"]
        self.size_m = 2 * self.R + self.hw + self.c

    def _r_of_z(self, z):
        z = np.asarray(z, dtype=float)
        top = np.clip(1 - ((z - self.hw) / self.c) ** 2, 0, None)
        return np.where(z <= self.hw, self.R, self.R * np.sqrt(top))

    def inside(self, p):
        x, y, z = p[:, 0], p[:, 1], p[:, 2]
        return (z > 0) & (z < self.hw + self.c) & (x * x + y * y < self._r_of_z(z) ** 2) & (y > -self.y0)

    def classify(self, p):
        e = 1e-7
        x, y, z = p[:, 0], p[:, 1], p[:, 2]
        out = np.full(len(p), 3)
        floor = z < e
        out[floor & (y <= self.fire_y)] = 0
        out[floor & (y > self.fire_y)] = 1
        out[(np.abs(y + self.y0) < e) & (x * x + z * z <= self.rd**2) & ~floor] = 2
        return out

    def _floor_points(self, n, rng, fire: bool):
        pts = []
        while sum(len(q) for q in pts) < n:
            q = (rng.random((2 * n, 2)) - 0.5) * 2 * self.R
            ok = (q[:, 0] ** 2 + q[:, 1] ** 2 < self.R**2) & (q[:, 1] > -self.y0)
            ok &= (q[:, 1] > self.fire_y) if fire else (q[:, 1] <= self.fire_y)
            pts.append(q[ok])
        q = np.vstack(pts)[:n]
        return np.hstack([q, np.zeros((n, 1))])

    def sample(self, name, n, rng):
        if name in ("floor", "fire"):
            return self._floor_points(n, rng, name == "fire"), np.tile([0, 0, 1.0], (n, 1))
        rr, ph = self.rd * np.sqrt(rng.random(n)), math.pi * rng.random(n)
        p = np.stack([rr * np.cos(ph), np.full(n, -self.y0), rr * np.sin(ph)], 1)
        return p, np.tile([0, 1.0, 0], (n, 1))

    def _floor_area_total(self):
        # circle minus the front segment cut at y = -y0
        d = self.y0
        seg = self.R**2 * math.acos(d / self.R) - d * math.sqrt(self.R**2 - d * d)
        return math.pi * self.R**2 - seg

    def area(self, name):
        fire = self.fire_frac * math.pi * self.R**2
        return {"fire": fire, "floor": self._floor_area_total() - fire, "door": math.pi * self.rd**2 / 2}[name]

    def total_area(self):
        a = math.asin(self.y0 / self.R)
        wall = self.R * (math.pi + 2 * a) * self.hw
        # spheroid part with y > -y0: integrate over z the arc length kept times slant factor
        def ring(z):
            r = float(self._r_of_z(z))
            if r <= 0:
                return 0.0
            dr = -self.R * (z - self.hw) / (self.c**2 * math.sqrt(max(1 - ((z - self.hw) / self.c) ** 2, 1e-15)))
            keep = 2 * math.pi if r <= self.y0 else (math.pi + 2 * math.asin(self.y0 / r))
            return keep * r * math.sqrt(1 + dr * dr)
        cap, _ = quad(ring, self.hw, self.hw + self.c, limit=200)
        # planar front face (chord plane) inside the profile
        def width(z):
            r = float(self._r_of_z(z))
            return 2 * math.sqrt(r * r - self.y0**2) if r > self.y0 else 0.0
        z_top = self.hw + self.c * math.sqrt(max(1 - (self.y0 / self.R) ** 2, 0))
        front, _ = quad(width, 0, z_top, limit=200)
        return self._floor_area_total() + wall + cap + front


def _solve_theta(frac: float) -> float:
    from scipy.optimize import brentq
    return brentq(lambda th: (th - math.sin(th)) / (2 * math.pi) - frac, 1e-9, 2 * math.pi)


# ----------------------------------------------------------------------------- radiosity
def solve_radiosity(F: np.ndarray, A: np.ndarray, eps: np.ndarray, T_K: np.ndarray, q_fixed: np.ndarray) -> dict:
    """Gray diffuse enclosure. For each surface give either T_K[i] (with q_fixed[i] = nan) or a
    prescribed net outgoing flux q_fixed[i] [W/m2] (with T_K[i] = nan).
    Returns net outgoing flux q [W/m2], radiosity J, and the implied temperature of prescribed-flux surfaces."""
    N = len(A)
    M = np.zeros((N, N))
    b = np.zeros(N)
    for i in range(N):
        if np.isnan(q_fixed[i]):
            M[i, i] = 1.0
            M[i] -= (1 - eps[i]) * F[i]
            b[i] = eps[i] * SIGMA * T_K[i] ** 4
        else:
            M[i, i] = 1.0
            M[i] -= F[i]
            b[i] = q_fixed[i]
    J = np.linalg.solve(M, b)
    G = F @ J  # irradiation
    q = J - G
    T_out = T_K.copy()
    for i in range(N):
        if not np.isnan(q_fixed[i]):
            # emissive power from J = eps*Eb + (1-eps)*G
            Eb = (J[i] - (1 - eps[i]) * G[i]) / eps[i]
            T_out[i] = (max(Eb, 0.0) / SIGMA) ** 0.25
    return {"q_W_m2": q, "J_W_m2": J, "T_K": T_out}
