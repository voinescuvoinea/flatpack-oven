"""Materials database loader and validator.

All material properties used by the project come through this module. Values
are stored in ``materials.yaml`` in the units written on the source datasheet
and converted to SI here (temperatures to kelvin).
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pint
import yaml

UREG = pint.UnitRegistry()

DB_PATH = Path(__file__).with_name("materials.yaml")

#: Canonical SI unit for every allowed property name.
CANONICAL_UNITS: dict[str, str] = {
    "thermal_conductivity": "W/(m*K)",
    "density": "kg/m**3",
    "specific_heat": "J/(kg*K)",
    "emissivity": "dimensionless",
    "thermal_expansion": "1/K",
    "youngs_modulus": "Pa",
    "modulus_of_rupture": "Pa",
    "cold_crushing_strength": "Pa",
    "max_service_temperature": "K",
    "porosity": "dimensionless",
    "water_absorption": "dimensionless",
    "permanent_linear_change": "dimensionless",
    # fuel properties (category "fuel")
    "lower_heating_value": "J/kg",
    "moisture_content": "dimensionless",
    "combustion_efficiency": "dimensionless",
    "mass_fraction_C": "dimensionless",
    "mass_fraction_H": "dimensionless",
    "mass_fraction_O": "dimensionless",
    "mass_fraction_N": "dimensionless",
    "mass_fraction_S": "dimensionless",
}

CATEGORIES = {
    "refractory_dense",
    "refractory_insulating",
    "refractory_castable",
    "cooking_floor",
    "insulation",
    "structural_steel",
    "fastener",
    "sealant",
    "fuel",
    "other",
}

CONFIDENCE = {"DATASHEET", "REFERENCE", "ASSUMPTION"}

_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class MaterialsDBError(ValueError):
    """Raised when the database violates the schema or sourcing rules."""


@dataclass(frozen=True)
class Property:
    """One material property in SI units.

    Attributes:
        name: property name (key of CANONICAL_UNITS).
        unit_si: canonical SI unit string.
        values_si: property values in ``unit_si``; shape (1,) if constant.
        T_K: temperatures [K] matching ``values_si``, or None if constant.
        rel_low, rel_high: relative uncertainty below/above the nominal value [-].
        confidence: DATASHEET | REFERENCE | ASSUMPTION.
        source: source record as written in the YAML.
    """

    name: str
    unit_si: str
    values_si: np.ndarray
    T_K: np.ndarray | None
    rel_low: float
    rel_high: float
    confidence: str
    source: dict[str, Any]
    reasoning: str | None = None

    @property
    def is_constant(self) -> bool:
        return self.T_K is None

    def at(self, T_K: float | np.ndarray, *, extrapolate: bool = False) -> np.ndarray | float:
        """Nominal value at temperature ``T_K`` [K], in ``unit_si``.

        Linear interpolation between datasheet points. Outside the datasheet
        range this raises unless ``extrapolate=True`` (which holds the end value
        constant; the caller must record that assumption in docs/risks.md).
        """
        if self.T_K is None:
            out = np.full(np.shape(T_K), self.values_si[0], dtype=float)
            return float(out) if out.ndim == 0 else out
        T = np.asarray(T_K, dtype=float)
        lo, hi = self.T_K[0], self.T_K[-1]
        if not extrapolate and (np.any(T < lo - 1e-9) or np.any(T > hi + 1e-9)):
            raise MaterialsDBError(
                f"{self.name}: T={T} K outside sourced range [{lo:.2f}, {hi:.2f}] K; "
                "pass extrapolate=True only with a recorded assumption"
            )
        out = np.interp(T, self.T_K, self.values_si)
        return float(out) if out.ndim == 0 else out

    def bounds_at(self, T_K: float | np.ndarray, **kw) -> tuple[Any, Any]:
        """(low, high) values at ``T_K`` [K] from the recorded uncertainty, in ``unit_si``."""
        nominal = self.at(T_K, **kw)
        return nominal * (1.0 - self.rel_low), nominal * (1.0 + self.rel_high)


@dataclass(frozen=True)
class Material:
    id: str
    name: str
    category: str
    properties: dict[str, Property]
    product: dict[str, Any] = field(default_factory=dict)
    suppliers: list[dict[str, Any]] = field(default_factory=list)
    notes: str | None = None

    def __getitem__(self, prop: str) -> Property:
        try:
            return self.properties[prop]
        except KeyError:
            raise MaterialsDBError(f"material {self.id!r} has no sourced {prop!r}") from None


def _err(where: str, msg: str) -> MaterialsDBError:
    return MaterialsDBError(f"{where}: {msg}")


def _as_date(v: Any, where: str) -> dt.date:
    if isinstance(v, dt.date):
        return v
    try:
        return dt.date.fromisoformat(str(v))
    except ValueError:
        raise _err(where, f"expected ISO date, got {v!r}") from None


def _validate_source(src: Any, where: str) -> dict[str, Any]:
    if not isinstance(src, dict):
        raise _err(where, "source must be a mapping")
    if not src.get("title"):
        raise _err(where, "source.title is required")
    if not (src.get("url") or src.get("citation")):
        raise _err(where, "source needs url or citation")
    if "accessed" not in src:
        raise _err(where, "source.accessed (date) is required")
    _as_date(src["accessed"], f"{where}.source.accessed")
    return src


def _parse_uncertainty(u: Any, where: str) -> tuple[float, float]:
    if not isinstance(u, dict):
        raise _err(where, "uncertainty is required, e.g. {rel: 0.15}")
    if "rel" in u:
        lo = hi = float(u["rel"])
    elif "rel_low" in u and "rel_high" in u:
        lo, hi = float(u["rel_low"]), float(u["rel_high"])
    else:
        raise _err(where, "uncertainty needs rel, or rel_low and rel_high")
    if lo < 0 or hi < 0 or lo >= 1:
        raise _err(where, f"invalid uncertainty bounds ({lo}, {hi})")
    return lo, hi


def _convert(values: np.ndarray, unit: str, canonical: str, where: str) -> np.ndarray:
    try:
        q = UREG.Quantity(values, unit)
        return np.asarray(q.to(canonical).magnitude, dtype=float)
    except (pint.errors.DimensionalityError, pint.errors.UndefinedUnitError, pint.errors.OffsetUnitCalculusError) as e:
        raise _err(where, f"unit {unit!r} not convertible to {canonical!r}: {e}") from None


def _T_C_to_K(T_C: np.ndarray) -> np.ndarray:
    return np.asarray(UREG.Quantity(T_C, "degC").to("K").magnitude, dtype=float)


def _parse_property(name: str, raw: Any, where: str) -> Property:
    if name not in CANONICAL_UNITS:
        raise _err(where, f"unknown property {name!r}; allowed: {sorted(CANONICAL_UNITS)}")
    if not isinstance(raw, dict):
        raise _err(where, "property must be a mapping")
    unit = raw.get("unit")
    if not unit:
        raise _err(where, "unit is required")
    conf = raw.get("confidence")
    if conf not in CONFIDENCE:
        raise _err(where, f"confidence must be one of {sorted(CONFIDENCE)}")
    reasoning = raw.get("reasoning")
    if conf == "ASSUMPTION" and not reasoning:
        raise _err(where, "ASSUMPTION requires reasoning")
    rel_lo, rel_hi = _parse_uncertainty(raw.get("uncertainty"), where)
    source = _validate_source(raw.get("source"), where)

    has_value, has_data = "value" in raw, "data" in raw
    if has_value == has_data:
        raise _err(where, "exactly one of value / data is required")
    canonical = CANONICAL_UNITS[name]

    if has_value:
        vals = np.array([float(raw["value"])])
        T_K = None
    else:
        pts = raw["data"]
        if not isinstance(pts, list) or len(pts) < 2:
            raise _err(where, "data needs at least two {T_C, value} points")
        try:
            T_C = np.array([float(p["T_C"]) for p in pts])
            vals = np.array([float(p["value"]) for p in pts])
        except (KeyError, TypeError, ValueError):
            raise _err(where, "each data point needs numeric T_C and value") from None
        if np.any(np.diff(T_C) <= 0):
            raise _err(where, "data T_C must be strictly increasing")
        T_K = _T_C_to_K(T_C)

    if canonical == "K":
        vals_si = _T_C_to_K(vals) if unit in ("degC", "°C") else _convert(vals, unit, canonical, where)
    else:
        vals_si = _convert(vals, unit, canonical, where)

    return Property(
        name=name,
        unit_si=canonical,
        values_si=vals_si,
        T_K=T_K,
        rel_low=rel_lo,
        rel_high=rel_hi,
        confidence=conf,
        source=source,
        reasoning=reasoning,
    )


def _parse_material(raw: Any, idx: int) -> Material:
    where = f"materials[{idx}]"
    if not isinstance(raw, dict):
        raise _err(where, "must be a mapping")
    mid = raw.get("id")
    if not isinstance(mid, str) or not _ID_RE.match(mid):
        raise _err(where, f"id must be snake_case, got {mid!r}")
    where = f"material {mid!r}"
    if not raw.get("name"):
        raise _err(where, "name is required")
    if raw.get("category") not in CATEGORIES:
        raise _err(where, f"category must be one of {sorted(CATEGORIES)}")
    props_raw = raw.get("properties") or {}
    if not isinstance(props_raw, dict):
        raise _err(where, "properties must be a mapping")
    props = {k: _parse_property(k, v, f"{where}.{k}") for k, v in props_raw.items()}
    suppliers = raw.get("suppliers") or []
    for j, s in enumerate(suppliers):
        sw = f"{where}.suppliers[{j}]"
        for key in ("name", "price", "currency", "per", "date_checked"):
            if key not in s:
                raise _err(sw, f"{key} is required")
        _as_date(s["date_checked"], sw)
    return Material(
        id=mid,
        name=raw["name"],
        category=raw["category"],
        properties=props,
        product=raw.get("product") or {},
        suppliers=suppliers,
        notes=raw.get("notes"),
    )


def load(path: str | Path = DB_PATH) -> dict[str, Material]:
    """Load and validate the materials database. Returns {material_id: Material}."""
    with open(path, encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    if not isinstance(doc, dict) or doc.get("schema_version") != 1:
        raise MaterialsDBError(f"{path}: expected schema_version: 1")
    mats: dict[str, Material] = {}
    for i, raw in enumerate(doc.get("materials") or []):
        m = _parse_material(raw, i)
        if m.id in mats:
            raise MaterialsDBError(f"duplicate material id {m.id!r}")
        mats[m.id] = m
    return mats
