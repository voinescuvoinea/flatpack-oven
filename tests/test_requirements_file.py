"""Structural checks on requirements/requirements.yaml."""

from pathlib import Path

import yaml

REQ = Path(__file__).resolve().parents[1] / "requirements" / "requirements.yaml"
STATUS = {"confirmed", "proposed", "open"}
VERIFICATION = {"analysis", "test", "inspection", "demonstration"}


def _reqs():
    return yaml.safe_load(REQ.read_text(encoding="utf-8"))["requirements"]


def test_ids_unique_and_well_formed():
    ids = [r["id"] for r in _reqs()]
    assert len(ids) == len(set(ids))
    assert all(i.startswith("R-") for i in ids)


def test_each_requirement_complete():
    for r in _reqs():
        assert r.get("title") and r.get("text"), r["id"]
        assert r["status"] in STATUS, r["id"]
        assert r["verification"] and set(r["verification"]) <= VERIFICATION, r["id"]


def test_non_confirmed_requirements_explain_themselves():
    for r in _reqs():
        if r["status"] == "proposed" and "values" in r:
            assert r.get("notes"), f"{r['id']}: proposed numeric values need a note on their origin"
