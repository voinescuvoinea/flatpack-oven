"""Checks on the parametric CAD model, end-wall layout and BOM generation."""

import math

import pytest

from geometry import end_walls as ew
from geometry.oven_b import OvenB, Params
from simulation.expansion import arch_arc_length


@pytest.fixture(scope="module")
def ov():
    return OvenB(Params()).build()


def test_all_solids_valid_and_ids_unique(ov):
    ids = [pt.pid for pt in ov.parts]
    assert len(ids) == len(set(ids))
    assert all(pt.solid.val().isValid() for pt in ov.parts)


def test_arch_geometry_consistent():
    p = Params()
    a = p.arch
    # arc length of the intrados equals the bricks plus joints
    assert arch_arc_length(p.span, a["rise"]) == pytest.approx(a["arc_in"], rel=1e-9)
    # springing points lie on the intrados circle
    assert math.hypot(p.span / 2, p.z_spring - a["z_c"]) == pytest.approx(a["R_i"], rel=1e-9)


def test_floor_field_fills_floor_exactly(ov):
    p = Params()
    area = sum(pt.volume_m3 for pt in ov.parts if pt.family == "floor bricks") / (p.bT / 1000)
    assert area == pytest.approx(p.floor_cols * p.bW * p.length * 1e-6, rel=1e-9)


def test_vault_bricks_do_not_overlap_and_close_the_arch(ov):
    p = Params()
    vol = sum(pt.volume_m3 for pt in ov.parts if pt.family == "vault bricks")
    assert vol == pytest.approx(p.arch_courses * p.bW * p.bT * p.length * 1e-9, rel=1e-9)


def test_end_wall_courses_cover_the_outline():
    p = Params()
    for front in (False, True):
        for c in ew.courses(p, front):
            seg_len = sum(b - a for a, b in c["segments_mm"])
            assert sum(pc.length_mm for pc in c["pieces"]) == pytest.approx(seg_len, abs=25)  # <= joint slack
            assert all(pc.length_mm >= ew.MIN_PIECE_MM - 1e-6 for pc in c["pieces"])


def test_bom_priced_lines_trace_to_db():
    from bom.build_bom import build
    p, ov, rows, priced = build()
    for g, item, q, u, c, src, note in rows:
        if c != "QUOTE":
            assert src, item
    assert priced > 0
