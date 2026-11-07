# Phase 0 report: Setup

Date: 2026-11-07. Status: **approved by user 2026-11-07**.

## Done
- Project scaffold, laid out as in `CLAUDE.md`. Python 3.12 environment managed
  by `uv`, with exact pins and `uv.lock` (decision 0001). CadQuery 2.8.0 installs
  and runs on this machine.
- `CLAUDE.md`: rules, conventions, layout, commands, status.
- `docs/brief.md`: context and phase plan (Phases 0–5, including the optional 1.5 coupon test).
- `requirements/requirements.yaml`: 26 requirements with IDs, status and
  verification method. 16 confirmed, 5 proposed, 5 open.
- `materials/`: database schema, plus a loader/validator that enforces
  sourcing, uncertainty, units and no silent extrapolation. The database itself
  is empty on purpose, because no values are entered before Phase 1 research.
- `docs/risks.md`: 14 initial risks and unknowns.
- Tests: 17 passing (`uv run pytest`), covering materials-DB validation and
  unit conversion, and the structure of the requirements file.
- `git init` done. Nothing committed yet (see Q7).

## Tensions between requirements (and with physics)
1. **Large floor vs heat-up time vs wood vs budget.** With the fire burning
   beside the pizza, the internal floor must be much wider than the pizza.
   Floor area, and with it floor mass, grows with the square of the floor size.
   That raises heat-up energy, wood use and cost together. Phase 1 will derive
   the floor size from the pizza diameter instead of guessing.
2. **Thermal mass: pizza vs bread.** Pizza-only favours a thin, low-mass dome
   (fast heat-up). Baking on retained heat favours a heavy dome and floor (slow
   heat-up). This is the biggest concept driver after floor size (Q2).
3. **"No masonry" vs the best-performing designs.** The classic
   high-performance ovens are masonry or cast domes. Flat-pack substitutes
   include dry-fitted precast refractory segments, bolted refractory panels,
   and a steel inner liner with insulation. Each trades performance, mass,
   cracking risk and cost differently. Phase 1 compares 2–3 of them.
4. **Fixed outdoors + freeze/thaw + porous refractory + fibre insulation.**
   Keeping the insulation and refractory dry becomes a structural requirement,
   not an accessory. Wet insulation stops insulating, and trapped water damages
   refractory through freezing and through steam on fast firing. How much
   weatherproofing the shell needs depends on Q4.
5. **Winter storage below -5 °C.** You said it won't be *used* below -5 °C,
   but a fixed oven sits outdoors through the whole winter. Freeze/thaw design
   needs the local minimum (Q5).
6. **60 °C touch target.** This cannot be met at the door mouth and the flue.
   Those areas will be zoned, guarded and labelled (R-S1, K-12).
7. **Budget vs shipping.** Refractories are heavy, so EU shipping can cost as
   much as the material. Romanian local sourcing is likely essential (K-10).

## Questions for you
- **Q1 Pizza size.** "One really big pizza": what diameter? The working default
  is 40 cm. Other options: 45 cm, 50 cm+.
- **Q2 Use.** Pizza only, or also bread, roasts or slow cooking on the heat that
  remains after the fire?
- **Q3 Base.** Should the design include its own stand (steel frame, costs part
  of the budget)? Or will it sit on something you have or will build
  (concrete-block plinth, masonry table, wooden table)? If so, what?
- **Q4 Weather.** Will the oven be under a roof or shelter? Or must the shell be
  fully rainproof by itself?
- **Q5 Location.** Which county or city? This gives the winter minimum,
  local suppliers and nearby laser-cutting shops.
- **Q6 Proposed defaults.** Approve or change:
  - R-P2 heat-up ≤ 90 min
  - R-F2 ≤ 25 kg for one-person parts, ≤ 100 kg absolute
  - R-E3 operating ambient -5…+40 °C, nominal 10 °C
  - R-C1 measurement kit costed as a separate line
- **Q7 Git.** May I commit to git at checkpoints (end of each step and
  phase)? The repo is initialised but nothing is committed.

## User answers (2026-11-07) and resulting changes
| Q | Answer | Requirement change |
|---|--------|--------------------|
| Q1 | 45 cm pizza | R-P4 confirmed at 45 cm |
| Q2 | Neapolitan pizza only | New R-P0 (optimise for Neapolitan). R-P6 retained heat dropped as a goal. Tension 2 resolved in favour of low mass and fast heat-up. |
| Q3 | User-built concrete base, may be part of the structure, not in budget | R-F4 confirmed. New R-I2 base interface. R-C1 excludes the base. |
| Q4 | Roof is a separate project | R-E1: oven under a roof, no direct rain on the shell. New R-I1 roof interface. R-C1 excludes the roof. |
| Q5 | Build site in Romania (location withheld) | R-E2: winter minimum to be sourced from climate data in Phase 1 |
| Q6 | Defaults approved | R-P2, R-F2, R-E3 confirmed |
| Q7 | Create repo, commit, push | Private GitHub repo created |

Still proposed (targets set in Phase 1): R-P1a wood consumption, R-P5 floor recovery time.

## Next (Phase 1, after approval)
Research proven designs. Fill the materials database with specific products
available in Romania/EU (datasheets saved). Check laser-cutting access and
cost. Derive the floor size from Q1. Then present 2–3 flat-pack concepts with a
comparison of mass, cost, performance and risks.
