import math

import pytest

from simulation import expansion as ex


def test_semicircle_arc_length():
    assert ex.arch_arc_length(0.8, 0.4 - 1e-12) == pytest.approx(math.pi * 0.4, rel=1e-6)


def test_rise_inverse():
    s, f = 0.914, 0.307
    assert ex.rise_for_arc_length(s, ex.arch_arc_length(s, f)) == pytest.approx(f, rel=1e-9)


def test_free_growth_is_similar_scaling():
    r = ex.arch_movement(0.80, 0.25, 0.114, 7.5e-6, 400.0)
    assert r["span_growth_free_mm"] == pytest.approx((0.80 + 0.114) * 7.5e-6 * 400 * 1e3)
    # holding the span forces a larger crown lift than free similar growth
    assert r["crown_lift_if_span_fixed_mm"] > r["crown_lift_free_mm"]
