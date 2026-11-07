# Project brief: Flat-pack wood-fired oven, designed and simulated with Claude Code

Status: v1, 2026-11-07. User answers to the draft are folded into requirements/requirements.yaml.

## Context
I want to build a real, physical prototype of a wood-fired oven that is designed,
engineered, and simulated by Claude. The goal is to show that AI can take a
real-world physical product from requirements to a design that can be built and
checked. It must work in reality: real materials that can be bought, real physics,
and honest uncertainty. I (or someone like me) will actually build and fire it.

Claude's output does not replace review by a qualified person. Before the first
firing, the design and the safety analysis should be checked by someone with
refractory or mechanical-engineering experience, if possible.

## Requirements
Single source of truth: `requirements/requirements.yaml` (IDs, values, status,
verification method). Summary of what the user decided on 2026-11-07:
- One large pizza (size to confirm); performance matters more than commercial polish
- Budget about 1000 USD; built in Romania, sourced in Romania/EU
- Parts movable by a few people; fixed, permanent outdoor installation
- Any normal workshop tools; Claude decides on laser cutting and refractory
  sealants, with justification
- Not used below -5 °C, but it stays outdoors through winter

## How we work
The non-negotiable rules are in `CLAUDE.md` (loaded every session).

## Phase 0: Setup
- `git init`; Python 3.12; `uv` with a lockfile so versions are pinned (done; see decision 0001)
- Dependencies (pinned): cadquery, numpy, scipy, matplotlib, pyyaml, ezdxf,
  pytest (add pint if useful). Confirm CadQuery installs and runs on this
  machine before going further.
- Layout and conventions: see `CLAUDE.md`
- Before writing physics code: list questions for me, plus any requirements
  that conflict with each other or with physics (e.g. thermal mass vs part
  weight vs heat-up time vs budget)
- STOP.

## Phase 1: Research and concept
- Research proven designs (Neapolitan dome, barrel vault, modular commercial
  kits, portable steel-shell ovens) and summarise the engineering principles:
  dome geometry, door-to-dome height ratio, floor thermal mass vs heat-up time,
  insulation layering, flue placement and sizing, and how heat reaches the
  floor (cavity radiation from fire and dome vs conduction)
- Build the materials database: refractories (firebrick, castable, refractory
  panels, cordierite), insulation (AES blanket, calcium silicate board,
  vermiculite/perlite), shell (steel grades, stainless vs mild), and fasteners
  rated for heat. For each: sourced properties, prices, availability.
- Propose 2–3 concepts that fit the flat-pack constraint. Compare: total and
  per-part mass, cost against budget, expected performance, part count and
  assembly effort, durability risks (especially cracking at module joints).
- Requirements conflicts found, and proposed amendments
- STOP.

## Phase 1.5 (recommended): Material coupon test
- Before buying everything: buy a small set of the chosen floor and dome
  materials plus 2–3 thermocouples. Fire one module or joint in a small fire.
- Purpose: check real material behaviour, the joint concept, and the
  measurement setup cheaply. This gives first calibration data.
- STOP.

## Phase 2: Physics model (for the chosen concept)
- 1D, then 2D (axisymmetric where it fits), transient conduction through the
  layered walls and floor, with radiation and convection boundaries. Verified
  against analytical solutions.
- Cavity model: a radiation network linking fire, dome, floor, and door
  opening, plus heat lost with flue gas. This is the part that predicts floor
  and dome temperatures.
- Fire as an empirically grounded heat input: wood burn rate × heating value
  corrected for moisture content, with a split between radiated and convected
  heat. All parameters come from literature, with ranges.
- If a published oven measurement dataset can be found, validate the combined
  model against it. If not, state clearly that the model is uncalibrated until
  Phase 5.
- Predict (as ranges): heat-up time, steady floor and dome temperatures, outer
  shell temperature, underside and base temperature, heat retention after the
  fire dies, wood consumption
- Sensitivity analysis: which parameters and uncertain material values matter most
- Thermal stresses and expansion: refractory module joints, steel shell vs
  inner refractory, fastener temperatures. Propose joint designs that allow
  expansion.
- STOP.

## Phase 3: Detailed design
- Full parametric CadQuery model; every dimension is a named parameter
- Check the mass of every part against R-F2, and the total cost against R-C1
- Exports: STEP, DXF for laser-cut parts (with bend allowances if bent), PDF
  drawings
- Bill of materials (product, supplier, quantity, price, date checked) and cut lists
- Requirements traceability matrix: each requirement ID → how it is met → how
  it will be verified
- STOP.

## Phase 4: Build and validation plan
- IKEA-style assembly instructions: numbered parts, step by step, diagrams
  generated from the CAD model
- Curing and first-firing procedure (slow initial drying of refractories),
  plus a go/no-go checklist before the first full firing
- Measurement plan: thermocouple type and positions (floor centre and edge at
  the surface and at depth, dome crown inner face, between insulation layers,
  outer shell, base or underside, flue gas), logger and sampling rate, wood mass
  and moisture log, ambient temperature and wind. CSV format agreed in advance
  so the data can be fed straight into the model.
- Final risks and unknowns list
- STOP.

## Phase 5: Build, measure, calibrate
- I build and fire the oven and log data
- Claude compares measurements with predictions, fits the uncertain
  parameters, updates the model, and writes up lessons learned and a list of
  revisions for v2
