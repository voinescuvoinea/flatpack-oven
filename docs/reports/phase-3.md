# Phase 3 report: Detailed design

Date: 2026-11-07. Status: **approved 2026-11-07** (decision 0005). R-F1 amended, floor insulation raised to 125 mm, quote requests drafted.

## 1. What was produced
| Deliverable | Where | How it is generated |
|---|---|---|
| Parametric CAD (119 numbered parts) | `geometry/oven_b.py` → `geometry/out/oven_b.step` | CadQuery; every dimension a named parameter in `Params` |
| Views | `geometry/out/*.svg` | from the CAD model |
| Bill of materials | `bom/bom.md`, `bom/bom.csv` | from CAD volumes, course tables and DB prices (`bom/build_bom.py`) |
| Cut list | `bom/cut_list.md` | course-by-course brick layout (`geometry/end_walls.py`) |
| 1:1 DXF templates (9) | `bom/dxf/` | former rib, skewback, both end walls, end panels, shell sheet, door, hood |
| Interface specs for base and roof | `docs/interfaces.md` | from CAD (mass, footprint, anchors, flue) |
| Arch stability check | `geometry/arch_statics.py` | thrust-line method, verified on the semicircle benchmark |
| As-designed thermal re-check | `docs/reports/phase-3-thermal-check.json` | Phase 2 model on the CAD geometry |

Tests: 51 passing, including CAD validity and geometric consistency, the
statics benchmark, and BOM traceability.

![oven](../../geometry/out/oven_b_iso.svg)
![bricks](../../geometry/out/oven_b_bricks_iso.svg)

## 2. The design in brief
- **Floor:** 28 bricks laid flat, 798 × 920 mm, staggered. It floats on
  4 × 25 mm CaSi with a 5 mm fibre-filled gap all round.
- **Vault:**
  - **8 courses** of bricks laid flat (64 mm thick), span 808 mm, rise 193 mm,
    crown **359 mm** above the floor
  - joints 2 mm at the inside face, opening to a mortar-filled V at the back
  - built over a reusable 3-rib plywood former
- **Walls:**
  - side walls: bricks standing on end
  - skewbacks: 8 bricks cut to 51°
  - end walls: 114 mm, bricks laid flat in staggered courses, top course cut to the vault curve
- **Door:** 520 mm wide, 240 mm high. Its top is a segmental arch of
  9 half-bricks with a 120 mm rise. The door is 67 % of the crown height,
  typical for low pizza domes.
- **Insulation:** 50 mm Superwool (hot side) + 100 mm ProRox WM 960ES (cold side, mesh outwards) over the vault, sides and ends.
- **Frame: all steel outside the shell (cool side).** The arch thrust passes
  through continuous CaSi thrust strips to L50×50×5 rails, then 4 buckstays
  anchored to the base, then 2 M12 tie rods over the top with disc-spring
  stacks. Springs and zinc-plated parts stay cool, and there are no hot
  steel thermal bridges.
- **Shell:** pre-painted 0.5 mm roofing sheet bent over the barrel, with 1 mm end panels.
- **Front:** steel hood in front of the mouth with a Ø150 stove pipe;
  insulated steel door for curing and retention.
- **Overall:** about 1.44 × 1.86 m on the base. Shell top 738 mm above the base.
  **Mass 594 kg** (bricks 425 kg); the heaviest part is one brick, about 3.4 kg.

## 3. Checks
### Arch stability (closes K-26)
- The solver was first checked on the classical semicircle, giving
  t_min/R = 0.109 against the literature's 0.107.
- On our arch (64 mm, half-angle 51°, own weight + insulation + sheet):
  - **geometric safety factor 8.5**; a thrust line still fits at 7.5 mm thickness
  - the thrust line **can stay inside the middle third**, so no joint opens
  - horizontal thrust 0.63–0.80 kN per metre, about **0.35 kN per tie rod**
- The 64 mm vault is structurally comfortable.

### As-designed thermal re-check (Phase 2 model, CAD geometry)
| | 10 °C ambient | 40 °C ambient | −5 °C ambient |
|---|---|---|---|
| Wood to hold the floor at 450 °C (steady) | **1.5 kg/h** | 1.4 | 1.5 |
| Vault | 531 °C | 527 | 533 |
| Shell (still air, long session) | 33 °C | **59 °C** ✓ R-S1 | 20 °C |
| Superwool/ProRox interface (limit 660 °C) | 373 °C ✓ | 376 °C ✓ | 373 °C |
| Concrete top (steady, long session) | 93 °C | **113 °C** ⚠ | 84 °C |
| Heat-up to 430 °C floor at 9 kg/h (pessimistic) | 114 min | – | 119 min |
| Heat-up at 6 kg/h (pessimistic) | 182 min | – | 191 min |

Where the heat goes at the 450 °C hold: flue 53 %, door radiation 37 %, walls 10 %.

Compared with Phase 2, the smaller arched door and the hybrid insulation cut
holding wood from 1.8 to 1.5 kg/h. The shell meets 60 °C even in the worst case.

### Thermal expansion provisions (from Phase 2)
| Movement | Size | Provision in the design |
|---|---|---|
| Arch span | 3–4 mm | tie rods with 12 disc springs each, about 8 mm travel |
| Floor | 3–3.5 mm | floating floor, 5 mm fibre gaps |
| Barrel length | 3–5 mm | 5 mm fibre gaskets at both end walls |

## 4. Budget (R-C1, about 1000 USD)
- **Priced: 712 USD.**
  - 150 bricks: $180
  - 10 CaSi boards: $197
  - 2 Superwool rolls: $313
  - mortar and sealant: $23
- **15 lines still need quotes:**
  - ProRox mat (4.4 m²)
  - 6.9 m of L50×50×5 (25 kg)
  - 3 m of M12 rod, 24 disc springs, anchors and fasteners
  - 3.3 m² of roofing sheet and 1.4 m² of 1 mm sheet
  - 2 mm hood sheet, stove pipe and cap, paint
  - plywood for the former
  - Superwool gasket strips
- **Honest reading:** about $290 remains for those lines. The steel items are
  ordinary hardware-store goods; **ProRox is the uncertain one.**
- **If quotes overshoot, in order of preference:**
  1. Do the rock-wool layer in two layers (50 + 50 mm).
  2. Ask the Superwool seller for 25 mm offcuts for the gaskets.
  3. Swap ProRox for one more Superwool roll plus a 50 mm local stone-wool slab
     rated for the interface temperature. The model can re-check any
     replacement in minutes.

## 5. Requirement amendments proposed (need your approval)
- **R-F1 (no masonry skills).** The design needs three small wet jobs:
  - filling the pre-formed V-joints of the vault with mortar
  - the door arch
  - thin-joint mortar in the front wall, which carries the door arch thrust

  Everything else is dry-placed, numbered and pre-cut. Proposed wording:
  *"No bricklaying skill: numbered, pre-cut bricks placed dry on templates and
  a former; the only wet work is filling marked joints with ready-mixed
  refractory mortar."*
- **R-I2 (concrete).** In long sessions on hot days, the concrete under the
  floor can exceed the assumed 100 °C limit (113 °C).
  - Option A: add a 5th CaSi layer (about $40).
  - Option B: keep 4 layers, and put a thermocouple on the concrete at first
    firing (Phase 4 plan).

  **Recommendation: A**, cheap insurance.

## 6. Open items carried to Phase 4
- Assembly instructions, the curing and first-firing schedule, and the measurement plan
- **Floor recovery after a pizza (R-P5, K-30)**: still not modelled. It goes
  into the measurement plan.
- **Hardware details** (disc-spring size, anchor type) are chosen once quotes
  show what is in stock locally.
- **Front-wall piers beside the door arch** are narrow (76–127 mm pieces in
  courses 3–5). They are mortar-bonded and restrained by the thrust strips;
  check during assembly (K-31).

## Decisions needed
- **D1.** Approve the R-F1 wording above?
- **D2.** Concrete: Option A (5th CaSi layer, recommended) or B?
- **D3.** Gather quotes now (I can draft a short Romanian quote-request text for each supplier), or go straight to Phase 4?

## Addendum (after approval, decision 0005)
- Floor insulation raised to **5 × 25 mm CaSi (125 mm)**.
  - Concrete top, steady long session: **84 °C** at 10 °C ambient (was 93), **104.5 °C** at 40 °C ambient (was 113), 74 °C at −5 °C.
  - Holding wood: 1.3–1.5 kg/h.
  - Cooking floor 25 mm higher (base top + 189 mm).
  - Oven mass 606 kg.
- The hot-day long-session case is still slightly above the *assumed* 100 °C limit. A 6th layer
  would cost about $20–40, but it is not added yet: the limit is unverified, and a thermocouple
  on the concrete at first firing (Phase 4 plan) decides.
- Priced subtotal **752 USD**. Quote requests in Romanian: `bom/quote_requests_ro.md`.
