"""Tests for the materials database loader/validator.

The fixture below uses SYNTHETIC numbers chosen to make the arithmetic easy to
check. They are not material data and must never be copied into materials.yaml.
"""

import textwrap

import numpy as np
import pytest

from materials import db

SRC = "{title: synthetic test fixture, citation: none, accessed: 2026-11-07}"

FIXTURE = f"""
schema_version: 1
materials:
  - id: test_brick
    name: Synthetic test brick
    category: refractory_dense
    properties:
      thermal_conductivity:
        unit: W/(m*K)
        data:
          - {{T_C: 0, value: 1.0}}
          - {{T_C: 100, value: 2.0}}
        confidence: DATASHEET
        uncertainty: {{rel: 0.1}}
        source: {SRC}
      density:
        unit: g/cm**3
        value: 2.0
        confidence: DATASHEET
        uncertainty: {{rel_low: 0.05, rel_high: 0.10}}
        source: {SRC}
      max_service_temperature:
        unit: degC
        value: 1000
        confidence: DATASHEET
        uncertainty: {{rel: 0.0}}
        source: {SRC}
      thermal_expansion:
        unit: 1/delta_degC
        value: 5.0e-6
        confidence: ASSUMPTION
        reasoning: synthetic
        uncertainty: {{rel: 0.5}}
        source: {SRC}
"""


def _write(tmp_path, text):
    p = tmp_path / "m.yaml"
    p.write_text(textwrap.dedent(text), encoding="utf-8")
    return p


@pytest.fixture
def mats(tmp_path):
    return db.load(_write(tmp_path, FIXTURE))


def test_real_database_validates():
    db.load()  # the committed materials.yaml must always pass validation


def test_unit_conversion_to_si(mats):
    b = mats["test_brick"]
    assert b["density"].at(300.0) == pytest.approx(2000.0)  # g/cm3 -> kg/m3
    assert b["max_service_temperature"].values_si[0] == pytest.approx(1273.15)  # degC -> K
    assert b["thermal_expansion"].values_si[0] == pytest.approx(5.0e-6)  # per degC == per K


def test_temperature_dependent_interpolation(mats):
    k = mats["test_brick"]["thermal_conductivity"]
    assert k.T_K[0] == pytest.approx(273.15)
    assert k.at(273.15 + 50.0) == pytest.approx(1.5)
    np.testing.assert_allclose(k.at(np.array([273.15, 373.15])), [1.0, 2.0])


def test_no_silent_extrapolation(mats):
    k = mats["test_brick"]["thermal_conductivity"]
    with pytest.raises(db.MaterialsDBError, match="outside sourced range"):
        k.at(273.15 + 500.0)
    assert k.at(273.15 + 500.0, extrapolate=True) == pytest.approx(2.0)


def test_uncertainty_bounds(mats):
    lo, hi = mats["test_brick"]["density"].bounds_at(300.0)
    assert (lo, hi) == (pytest.approx(1900.0), pytest.approx(2200.0))


def test_missing_property_raises(mats):
    with pytest.raises(db.MaterialsDBError, match="no sourced"):
        mats["test_brick"]["specific_heat"]


@pytest.mark.parametrize(
    "old, new, msg",
    [
        ("source: " + SRC, "source: {title: x, accessed: 2026-11-07}", "url or citation"),
        ("reasoning: synthetic", "reasoning: ''", "ASSUMPTION requires reasoning"),
        ("uncertainty: {rel: 0.1}", "", "uncertainty is required"),
        ("unit: g/cm**3", "unit: W/(m*K)", "not convertible"),
        ("density:", "colour:", "unknown property"),
        ("category: refractory_dense", "category: magic", "category"),
        ("{T_C: 100, value: 2.0}", "{T_C: 0, value: 2.0}", "strictly increasing"),
    ],
)
def test_validation_rejects(tmp_path, old, new, msg):
    assert old in FIXTURE
    bad = FIXTURE.replace(old, new, 1)
    with pytest.raises(db.MaterialsDBError, match=msg):
        db.load(_write(tmp_path, bad))


def test_duplicate_ids_rejected(tmp_path):
    body = FIXTURE.split("materials:\n", 1)[1]
    with pytest.raises(db.MaterialsDBError, match="duplicate"):
        db.load(_write(tmp_path, FIXTURE + body))
