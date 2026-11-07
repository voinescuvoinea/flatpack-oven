import math

import pytest

from geometry import arch_statics as st


def test_semicircular_arch_minimum_thickness_benchmark():
    # Classical result: t_min / R ~= 0.107 for a full semicircle under self-weight
    t = st.minimum_thickness(1.0, math.pi / 2, gamma=1.0, n=90, nH=400, nr=81)
    assert 0.100 < t < 0.112


def test_thick_flat_segment_is_safe_and_thin_semicircle_is_not():
    assert st.feasible(1.0, 0.2, math.radians(60), 1.0)["feasible"]
    assert not st.feasible(1.0, 0.05, math.pi / 2, 1.0)["feasible"]
