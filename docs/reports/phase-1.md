# Phase 1 report: Research and concept

Date: 2026-11-07. Status: **approved 2026-11-07**: concept B, no coupon test, geometry proposals accepted (decisions 0002, 0003).

## What was done
- **Found a validation dataset (K-01).** Three peer-reviewed papers (Falciano,
  Masi & Moresi 2022–2023, University of Naples) measure a Ø 90 cm Neapolitan
  firebrick oven. They give floor and vault temperatures against wood feed rate,
  heating rates, the heat-loss split (46 % flue, 26 % walls), and the share of
  heat reaching the pizza by each route (73 % radiation from the vault).
  Summary in `docs/research/01-published-oven-data.md`.
- **Researched design principles and site data**: dome and door proportions,
  floor material, build-site climate, manual-handling limits, contact-burn limits,
  and the concrete temperature limit. See `docs/research/02-design-principles-and-site.md`.
- **Materials database, 7 entries.** Every value has a source; datasheets are
  saved in `materials/sources/`. Proxy values are marked ASSUMPTION with
  reasons and wide uncertainty bands. The validator rejected one bad entry of
  mine, which shows the guard rails work.
- **Concept estimator** `geometry/concepts.py` (with analytical tests),
  generating `docs/concepts/estimates.md`. Nothing in it is a guessed price:
  unpriced items are marked "quote needed".
- Tests: 23 passing.

## Key design numbers (proposals, apply to any concept)
| Parameter | Proposal | Basis |
|---|---|---|
| Internal floor | Ø 0.90 m (B: 0.80 × 0.90 m) | 45 cm pizza + 9 cm margin beside a fire taking ¼ of the floor (computed). Same size as the published oven, so the model can be validated against it directly. |
| Crown height | ~0.40 m | Published oven; low dome favours pizza |
| Door | ~0.52 m wide × ~0.24 m high | A 45 cm pizza needs more width than the published 44 cm door; Phase 2 sizes it against heat loss |
| Floor | Refarom 64 mm fireclay brick on 2 × 25 mm CaSi board | Local, cheap, and firebrick works in the published oven |
| Dome insulation | 3 × 25 mm Superwool Plus (bio-soluble) | R-S5; thickness set in Phase 2 against the 60 °C shell target |

## The three concepts
All three share the floor, insulation, door and flue approach. They differ in
how the dome is made.

### A. Steel-lined low dome
Bolted stainless gores (laser-cut) form the dome, wrapped in fibre insulation
and a painted steel shell. This is the construction of commercial portable
ovens, scaled up.
- **Strengths:** lightest (refractory ≈ 86 kg, all floor) and fastest to heat,
  storing about ⅙ of B's heat. Truly flat-pack, and every part is light.
- **Weaknesses:** the steel sits at 550 °C+ with flame contact, so oxidation,
  distortion and expansion at bolted joints are real risks. This oven is
  physically unlike the published one, so validation is weaker. The cost
  depends on stainless sheet plus laser cutting and bending, none of it priced
  yet, and that is likely its largest cost line.

### B. Firebrick barrel vault (recommended)
Local Refarom bricks are fitted dry into a segmental arch (span 0.80 m, rise
0.25 m) over a reusable plywood former. A bolted angle-iron frame with tie
rods holds the arch, as in kiln building, with no mortar beyond thin sealant
joints. Fibre insulation and a light outer shell go on top.
- **Strengths:**
  - It is closest to the published oven (firebrick, ~10–11 cm walls,
    similar size), so the Phase 2 model can be checked against real data.
  - Cheapest materials: about $574 is priced so far, including all bricks and
    insulation. The steel frame needs only angle iron, rods and a grinder, with
    no laser cutting.
  - The heaviest part is a 3.4 kg brick. Very robust and repairable: a cracked
    brick is a 6-lei swap.
- **Weaknesses:**
  - Heavy (≈ 490 kg refractory), so more wood and slower heat-up. From the
    published heating rates, 90 min (R-P2) needs roughly 6 kg/h of wood, which
    is marginal. Phase 2 will test a thinner 64 mm vault (bricks laid flat) to
    halve the mass.
  - Setting the arch over a former takes care (numbered courses help).
  - A barrel spreads top heat less evenly than a round dome (K-19), so
    pizzas need turning.

### C. Cast refractory segment dome
Nine segments are home-cast from dense castable in reusable moulds, as in
commercial modular kits. This suits you, since you can cast.
- **Strengths:** the ideal low-dome shape and the fewest parts (~34). It
  resembles the published oven.
- **Weaknesses:**
  - No castable datasheet yet, and the only price found (an unverified French
    one) puts refractory alone at ~$1260, over budget.
  - Segments weigh ~32 kg each.
  - Cracking at segment joints, and curing quality depends on home casting.
  - It needs mould-making.

### Side by side (from `docs/concepts/estimates.md`)
| | A Steel dome | B Brick vault | C Cast segments |
|---|---|---|---|
| Refractory mass | 86 kg | 492 kg | 376 kg |
| Heaviest part | 3.4 kg | 3.4 kg | 32 kg |
| Heat stored at 450 °C (upper bound), as wood | 2.8 kg | 15.8 kg | 12.1 kg |
| Priced so far | $417 | $574 | $1259 |
| Still unpriced | stainless liner, shell, laser and bending (largest), door | angle frame, shell, door | moulds, shell, door |
| Laser cutting needed | yes | no | no |
| Matches the validation oven | weakly | closely | closely (wall), unknown material |
| Main risk | hot steel distortion and joints | heat-up time, arch build | castable data, cost, joint cracks |

A faceted dome of flat brick tiles in a steel skeleton was also considered and
dropped: it has many joints and leak paths, and the steel/brick expansion
mismatch at every tile.

## Recommendation
**Concept B, with a thin-vault variant studied in Phase 2.** It is the only
concept that combines local materials with a clear budget margin, simple
grinder-only fabrication, and a published dataset close enough to validate
the model against. That last point matters for the project's goal of honest,
verified predictions. Its weakness, mass and heat-up time, is exactly what
Phase 2 is built to quantify and reduce.

A would be my choice only if fast heat-up matters more to you than proven
behaviour. C should wait until a castable datasheet and a real price exist.

## Requirement updates (all within approved scope)
- R-E2: build-site climate values added (record low −35.3 °C, January mean minimum −3.0 °C)
- R-F2: HSE source confirmed (25 kg; parts over 16 kg get a label)
- R-I2: concrete limit ≤ 100 °C, recorded as an ASSUMPTION to verify in Phase 2
- R-P1a: first anchor of about 3 kg/h from the published oven
- R-F6, decided: laser cutting is optional, and concept B avoids it

## Things you could do to help (optional, a few minutes each)
1. **Email Refarom** (import@refarom.ro, Brașov) for the full datasheet of the
   65 SA brick (thermal conductivity, density, specific heat) and the BR 40 A
   castable. This replaces proxy values with real ones (K-18, K-20).
2. **Download one paper in a browser.** Falciano et al. 2023, "Semiempirical
   modeling of a traditional wood-fired pizza oven", J. Food Sci.
   88(5):2036–2052, doi:10.1111/1750-3841.16532. It is open access, but the
   site blocks automated downloads. Drop the PDF into `materials/sources/`;
   it holds the full model and parameters for Phase 2 validation.
3. **Check stock at your local Hornbach** for the Refarom brick and the
   CaSi board (the listings showed Domnești stock).

## Decisions needed from you
- **D1. Concept:** A, B (recommended) or C?
- **D2. Phase 1.5 coupon test** (recommended for B): buy ~20 bricks, one CaSi
  sheet and a K-type thermocouple kit, and fire a small test to check brick
  behaviour and calibrate one material. Yes or no?
- **D3. Geometry proposals:** accept Ø 0.90 m floor (B: 0.80 × 0.90 m),
  ~0.40 m crown and a ~0.52 × 0.24 m door as the Phase 2 starting point?
