"""Build the interactive project page from the project's own data.

Collects: CAD model (as an embedded glTF), part list, requirements, materials DB, BOM,
risks, decisions, calibration, sensitivity, as-designed check and the precomputed
sweeps (explorer/sweeps.py), then fills explorer/template.html.

Run: uv run python -m explorer.build
  -> explorer/index.html            standalone page (open in any browser)
  -> explorer/out/oven_explorer.html  same page as a fragment, for publishing as an Artifact
"""

from __future__ import annotations

import base64
import json
import math
import re
import tempfile
from pathlib import Path

import yaml

from bom.build_bom import build as build_bom
from geometry import arch_statics as st
from geometry import end_walls as ew
from geometry.interfaces import masses
from geometry.oven_b import OvenB, Params, summary
from materials import db

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).parent
DISPLAY = {  # property -> (label, display unit, factor from SI, offset)
    "thermal_conductivity": ("Thermal conductivity", "W/(m·K)", 1.0, 0.0),
    "density": ("Density", "kg/m³", 1.0, 0.0),
    "specific_heat": ("Specific heat", "kJ/(kg·K)", 1e-3, 0.0),
    "emissivity": ("Emissivity", "–", 1.0, 0.0),
    "thermal_expansion": ("Thermal expansion", "10⁻⁶/K", 1e6, 0.0),
    "max_service_temperature": ("Max service temperature", "°C", 1.0, -273.15),
    "porosity": ("Apparent porosity", "–", 1.0, 0.0),
    "cold_crushing_strength": ("Cold crushing strength", "MPa", 1e-6, 0.0),
    "permanent_linear_change": ("Shrinkage after heating", "–", 1.0, 0.0),
    "lower_heating_value": ("Lower heating value", "MJ/kg", 1e-6, 0.0),
    "moisture_content": ("Moisture content", "–", 1.0, 0.0),
    "combustion_efficiency": ("Combustion efficiency", "–", 1.0, 0.0),
}


def _materials(mats):
    out = []
    for m in mats.values():
        props = []
        for name, pr in m.properties.items():
            if name.startswith("mass_fraction"):
                continue
            label, unit, f, off = DISPLAY.get(name, (name, pr.unit_si, 1.0, 0.0))
            item = {"name": label, "unit": unit, "confidence": pr.confidence, "rel_low": pr.rel_low, "rel_high": pr.rel_high,
                    "source": {k: str(v) for k, v in pr.source.items() if k in ("title", "url", "locator", "accessed", "citation")},
                    "reasoning": pr.reasoning}
            if pr.is_constant:
                item["value"] = float(pr.values_si[0]) * f + off
            else:
                item["data"] = [[float(T) - 273.15, float(v) * f + off] for T, v in zip(pr.T_K, pr.values_si)]
            props.append(item)
        sup = [{k: str(v) for k, v in s.items()} for s in m.suppliers]
        out.append({"id": m.id, "name": m.name, "category": m.category, "notes": (m.notes or "").strip(), "suppliers": sup, "props": props})
    return out


def _risks():
    rows = []
    for line in (ROOT / "docs" / "risks.md").read_text().splitlines():
        if line.startswith("| K-"):
            c = [x.strip() for x in line.strip().strip("|").split("|")]
            rows.append({"id": c[0], "risk": c[1], "why": c[2], "mitigation": c[3], "status": c[4]})
    return rows


def _decisions():
    out = []
    for f in sorted((ROOT / "docs" / "decisions").glob("*.md")):
        first = f.read_text().splitlines()[0].lstrip("# ").strip()
        out.append(first)
    return out


def _arch_statics(p, mats):
    a = p.arch
    rho = mats["refarom_65sa_brick"]["density"].at(300.0)
    q = (p.sw_t / 1000 * mats["superwool_plus_blanket_128"]["density"].at(300.0)
         + p.rw_t / 1000 * mats["prorox_wm960es"]["density"].at(300.0) + 4.0) * 9.81
    Rc, t = (a["R_i"] + p.bT / 2) / 1000, p.bT / 1000
    r = st.feasible(Rc, t, a["half_angle"], rho * 9.81, q, n=60, nH=250, nr=51)
    rm = st.feasible(Rc, t, a["half_angle"], rho * 9.81, q, n=60, nH=250, nr=51, margin=1 / 3)
    tmin = st.minimum_thickness(Rc, a["half_angle"], rho * 9.81, q, n=60, nH=250, nr=51)
    return {"safety_factor": t / tmin, "t_min_mm": tmin * 1000, "middle_third": rm["feasible"],
            "H_range_N_m": [rm.get("H_min_N_m"), rm.get("H_max_N_m")], "half_weight_N_m": r["half_weight_N_m"]}


def _courses(p):
    out = {}
    for front in (False, True):
        out["front" if front else "back"] = [
            {"course": c["course"], "z0": c["z_bottom_mm"], "z1": c["z_top_mm"], "segments": c["segments_mm"],
             "pieces": [{"len": pc.length_mm, "kind": pc.kind} for pc in c["pieces"]], "bricks": c["bricks"]}
            for c in ew.courses(p, front)]
    return out


def collect() -> tuple[dict, str]:
    p = Params()
    mats = db.load()
    ov = OvenB(p).build()
    fam_mass = masses(ov, mats)
    parts = []
    for pt in ov.parts:
        rho = mats[pt.material]["density"].at(300.0)
        parts.append({"id": pt.pid, "name": pt.name, "family": pt.family, "material": pt.material,
                      "mass_kg": pt.volume_m3 * rho, "note": pt.note})
    with tempfile.TemporaryDirectory() as td:
        glb = Path(td) / "oven.glb"
        ov.assembly().export(str(glb), "GLTF", tolerance=0.5, angularTolerance=0.3)
        glb_b64 = base64.b64encode(glb.read_bytes()).decode()
    _, _, bom_rows, priced = build_bom()
    reqs = yaml.safe_load((ROOT / "requirements" / "requirements.yaml").read_text())["requirements"]
    rep = lambda f: json.loads((ROOT / f).read_text()) if (ROOT / f).exists() else None
    a = p.arch
    d = ew.door_geometry(p)
    data = {
        "summary": {**summary(p), "mass_kg": sum(fam_mass.values()), "brick_mass_kg": sum(v for k, v in fam_mass.items() if "brick" in k),
                    "n_parts": len(parts)},
        "geometry": {k: getattr(p, k) for k in ("bL", "bW", "bT", "floor_cols", "floor_rows", "floor_gap", "casi_layers", "casi_t", "wall_h",
                                                 "arch_courses", "arch_joint_in", "end_t", "end_gasket", "door_w", "door_h", "door_arch_rise",
                                                 "sw_t", "rw_t", "shell_t", "ang", "thrust_strip_h", "flue_d")}
        | {"span": p.span, "length": p.length, "z_casi_top": p.z_casi_top, "z_floor": p.z_floor, "z_spring": p.z_spring,
           "x_wall_out": p.x_wall_out, "R_i": a["R_i"], "R_e": a["R_e"], "z_c": a["z_c"], "rise": a["rise"], "half_angle": a["half_angle"],
           "door": {k: float(v) for k, v in d.items()}},
        "parts": parts,
        "family_mass": fam_mass,
        "courses": _courses(p),
        "statics": _arch_statics(p, mats),
        "requirements": reqs,
        "risks": _risks(),
        "decisions": _decisions(),
        "materials": _materials(mats),
        "bom": {"rows": [dict(zip(["group", "item", "qty", "unit", "cost_usd", "price_source", "note"], r)) for r in bom_rows],
                "priced_usd": priced, "budget_usd": 1000.0},
        "calibration": rep("validation/f22_calibration.json"),
        "sensitivity": rep("docs/reports/phase-2-sensitivity.json"),
        "as_designed": rep("docs/reports/phase-3-thermal-check.json"),
        "sweeps": rep("explorer/data/sweeps.json"),
        "phases": [
            {"n": 0, "name": "Setup", "status": "done", "what": "Requirements, rules, project structure"},
            {"n": 1, "name": "Research & concept", "status": "done", "what": "Published oven data, sourced materials, 3 concepts, concept B chosen"},
            {"n": 2, "name": "Physics model", "status": "done", "what": "Verified heat model, calibrated on a published oven, predictions"},
            {"n": 3, "name": "Detailed design", "status": "done", "what": "Parametric CAD, parts list, cut list, templates, arch statics"},
            {"n": 4, "name": "Build & validation plan", "status": "next", "what": "Assembly steps, curing and first firing, measurement plan"},
            {"n": 5, "name": "Build, measure, calibrate", "status": "later", "what": "Fire the oven, compare with the model, lessons for v2"},
        ],
    }
    return data, glb_b64


def render(data: dict, glb_b64: str) -> tuple[str, str]:
    tpl = (HERE / "template.html").read_text()
    head, body = tpl.split("<!--BODY-->", 1)
    head = head.replace("<!--HEAD-->", "")
    js = json.dumps(data, default=float, separators=(",", ":")).replace("</", "<\\/")
    body = body.replace("__DATA_JSON__", js).replace("__GLB_B64__", glb_b64)
    full = ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
            + head + "</head>\n<body>\n" + body + "\n</body>\n</html>\n")
    fragment = head + body
    return full, fragment


def main():
    data, glb = collect()
    full, frag = render(data, glb)
    (HERE / "index.html").write_text(full)
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "oven_explorer.html").write_text(frag)
    print(f"index.html {len(full)/1e6:.2f} MB; sweeps {'present' if data['sweeps'] else 'MISSING (run explorer.sweeps)'}")


if __name__ == "__main__":
    main()
