# Flat-pack wood-fired oven

A real oven that will be built and fired, designed and simulated end to end in
this repo. The full brief and phase plan are in `docs/brief.md`. The
requirements are in `requirements/requirements.yaml`, and that file is the
single source of truth for them.

## Status
- Phase 3 approved 2026-11-07 (decision 0005). Next: **Phase 4 (assembly, curing, measurement plan)**. Waiting on supplier quotes (`bom/quote_requests_ro.md`).
- Update this line at every phase gate.

## Non-negotiable rules
1. **No invented numbers.** Every material property comes from a manufacturer
   datasheet or an established engineering reference, recorded in
   `materials/materials.yaml` with source, locator, access date, confidence
   (DATASHEET / REFERENCE / ASSUMPTION) and an uncertainty range. ASSUMPTION
   entries need written reasoning. Prefer the exact product we plan to buy.
   Save datasheet PDFs in `materials/sources/` when the licence allows.
2. **Physics code gets material properties only through `materials.db`.** No
   hard-coded material constants. Physical constants (Stefan–Boltzmann etc.)
   come from `scipy.constants`.
3. **Temperature-dependent properties** where they matter. Never extrapolate
   past the datasheet temperature range without an explicit, recorded
   ASSUMPTION.
4. **SI units.** Kelvin internally (always, where radiation is involved). °C is
   fine in reports and in the YAML data, which the loader converts.
5. **Verify before trusting.** Every solver is checked against an analytical
   solution or a published case, as a pytest test, before it is used on the oven.
6. **Results are ranges.** Propagate the uncertainty of inputs and properties.
7. **Keep `docs/risks.md` current.** Combustion and smoke use simplified,
   empirically grounded models, not CFD, unless the user decides otherwise.
8. **Safety is a design requirement**: burns, CO, fire spread, structural
   failure, cracking, fibre exposure, food contact.
9. **Decisions** go in `docs/decisions/NNNN-title.md` (context, options,
   decision, why).
10. **Phase gates.** At the end of each phase, write `docs/reports/phase-N.md`
    (results, open questions, proposed requirement amendments), update Status
    above, then STOP and wait for approval.
11. **Requirements never change silently.** Propose an amendment, get user
    approval, then edit the YAML and record the change in the phase report.

## Conventions
- Variable names carry units: `T_K`, `T_C`, `k_W_mK`, `rho_kg_m3`,
  `cp_J_kgK`, `t_s`, `L_m`, `q_W_m2`, `m_kg`. Every public function's
  docstring lists units for its arguments and return values.
- CAD is CadQuery, parametric. Every dimension is a named parameter, in
  millimetres inside `geometry/` (the CadQuery convention), converted at the
  boundary to the simulation, which works in metres.
- Prices are recorded in their original currency with a check date, and
  converted to USD for the budget at a dated exchange rate.

## Layout
```
requirements/   requirements.yaml (IDs, status, verification method)
materials/      materials.yaml (sourced properties, prices), db.py (loader/validator), sources/ (datasheets)
geometry/       CadQuery parametric models
simulation/     thermal models (conduction, cavity radiation, fire input)
validation/     analytical / published reference cases used by the tests
bom/            bill of materials, cut lists, DXF
assembly/       assembly instructions and diagrams
docs/           brief.md, risks.md, decisions/, reports/
tests/          pytest
```

## Commands
- `~/.local/bin/uv run pytest`: run all tests (they must pass before a phase gate)
- `uv run python -m validation.f22`: recalibrate model on the published oven (~5 min)
- `uv run python -m simulation.scenarios` / `-m simulation.sensitivity`: Phase 2 predictions (~3 / ~12 min)
- `uv run python -m geometry.export` (STEP/SVG/DXF), `-m bom.build_bom` (BOM + cut list), `-m geometry.interfaces`, `-m simulation.as_designed` (~3 min)
- CAD parameters live in `geometry/oven_b.Params`; regenerate BOM/DXF/interfaces after any change
- `~/.local/bin/uv run python <script>`: run anything in the project env
- `~/.local/bin/uv add <pkg>==<ver>`: add a dependency. Always pin exactly; `uv.lock` is committed.
- No system `python3-venv`. The environment is managed by uv in `.venv/`.

## User context
- Builder is in Romania. Has normal workshop tools. No experience with
  refractories or sealants, so Claude proposes and justifies those choices.
- Standing preference: always choose the best-performing option (decision 0005); ask only for scope, safety or big budget changes.
- Performance matters more than commercial polish. It is a fixed, one-off
  installation in Romania. Neapolitan pizza only (45 cm).
- Out of scope: the concrete base (user builds it) and the roof (separate
  project). We only publish interface requirements for them (R-I1, R-I2).
- Git: commit at checkpoints and push to `origin` (private GitHub repo).
