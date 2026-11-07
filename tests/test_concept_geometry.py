"""Analytical checks for the concept geometry helpers."""

import math

import pytest

from geometry import concepts as g


def test_half_area_segment_is_the_semicircle():
    assert g.segment_depth_for_area_fraction(0.45, 0.5) == pytest.approx(0.45, rel=1e-9)


def test_segment_area_fraction_roundtrip():
    R = 0.45
    b = g.segment_depth_for_area_fraction(R, 0.25)
    theta = 2 * math.acos(1 - b / R)
    assert g.circular_segment_area(R, theta) / (math.pi * R**2) == pytest.approx(0.25, rel=1e-9)


def test_clear_circle_touches_chord_and_wall():
    # no fire -> full floor; fire to the centre -> half-diameter circle
    assert g.clear_circle_diameter_beside_fire(0.45, 0.0) == pytest.approx(0.90)
    assert g.clear_circle_diameter_beside_fire(0.45, 0.45) == pytest.approx(0.45)


def test_oblate_hemispheroid_limits():
    a = 0.45
    assert g.oblate_hemispheroid_area(a, a) == pytest.approx(2 * math.pi * a**2)
    assert g.oblate_hemispheroid_area(a, a * (1 - 1e-6)) == pytest.approx(2 * math.pi * a**2, rel=1e-5)
    # flat limit -> disc area
    assert g.oblate_hemispheroid_area(a, 1e-6) == pytest.approx(math.pi * a**2, rel=1e-4)


def test_segmental_arch_semicircle_and_rise():
    R, th = g.segmental_arch(0.80, 0.40)
    assert R == pytest.approx(0.40) and th == pytest.approx(math.pi)
    R, th = g.segmental_arch(0.80, 0.25)
    assert R - math.sqrt(R**2 - 0.40**2) == pytest.approx(0.25)


def test_report_runs_and_prices_are_sourced():
    text = g.report()
    assert "quote needed" in text  # unpriced items are flagged, not invented
    for c in g.build(g.db.load()):
        for it in c.items:
            if it.cost_usd is not None:
                assert it.material, f"{it.name}: priced item must trace to a materials-db supplier"
