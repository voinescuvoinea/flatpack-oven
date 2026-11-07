# Risks and unknowns

Running list. Every phase report reviews it. Status: open | mitigated | closed | accepted.

| ID | Risk / unknown | Why it matters | Mitigation / plan | Status |
|----|----------------|----------------|-------------------|--------|
| K-01 | No published oven measurement dataset may exist to validate the combined model | Predictions stay uncalibrated, so floor temperature and heat-up could be quite wrong | Search in Phase 1; the coupon test (Phase 1.5); calibrate in Phase 5; report results as ranges | open |
| K-02 | Fire heat input is uncertain (wood species, moisture, piece size, how the operator loads it) | It is the dominant input to every thermal prediction | Empirical heat-release model with literature ranges; log wood mass and moisture during tests | open |
| K-03 | Draft, flue flow and smoke spill at the door are not modelled with CFD | CO exposure at the door; heat lost up the flue | Proven door/flue proportions from existing designs; smoke behaviour checked at first firing | open |
| K-04 | Datasheets give "typical" values at only a few temperatures; local Romanian products may lack full datasheets | Rule 1 may force ASSUMPTION entries or a change of product | Prefer products with complete datasheets; uncertainty ranges; sensitivity analysis | open |
| K-05 | Cracking at module joints and from thermal shock, especially in the first firings | Durability, and loose fragments on a food surface | Expansion joints by design; slow curing schedule; thermal-stress estimate in Phase 2 | open |
| K-06 | Fixed outdoor install: water gets into porous refractory and fibre insulation; freeze/thaw in winter storage | Spalling, steam damage on fast firing, wet insulation stops insulating | Oven sits under a roof (R-E1), but humidity, condensation and splash remain; drying procedure (R-S7); build-site winter minimum from sourced data | open |
| K-07 | Steel shell outdoors: corrosion, differential expansion against the refractory, fasteners seizing or loosening | Structural life, gaps that lead to wet insulation | Material and fastener choice in Phase 1; slotted or floating joints | open |
| K-08 | Food safety of the cooking-floor material and any sealant near food | R-S6 | Choose floor material with documented food-contact suitability; no sealant on the cooking surface | open |
| K-09 | Fibre insulation handling during assembly (AES fibre is still an irritant) | Builder health | PPE and handling steps in the assembly instructions; encapsulated panels | open |
| K-10 | Budget: price changes, shipping heavy refractories, exchange rate | R-C1 | Prefer local Romanian sourcing; dated quotes; contingency line in the BOM | open |
| K-11 | Total oven mass is likely to be hundreds of kg (not yet computed) | Base design, tip-over, ground loading | Mass budget in Phase 1; user-built concrete base designed to our interface spec (R-I2) | open |
| K-12 | Door and flue cannot meet the 60 °C touch target | Burns | Zone, guard and label (R-S1) | accepted |
| K-13 | Claude cannot physically check fit, tolerances or workmanship | Assembly problems, gaps | Generous tolerances, a test-fit step, a go/no-go checklist before first firing | open |
| K-14 | No independent engineering review is arranged yet | Safety sign-off | Seek a reviewer (refractory/oven builder) before first firing | open |
| K-15 | Roof is a separate project: flue heat and sparks near roof structure | Fire spread to the roof | Publish flue position, temperatures and clearances to the roof task (R-I1) | open |
| K-16 | Concrete base under a hot floor: concrete degrades above its temperature limit, and trapped moisture can spall | Base cracking, oven settling | Under-floor insulation sized so the concrete stays below a sourced limit (R-I2) | open |
| K-17 | Superwool k is published only for 200 °C and above; the cold side of the insulation runs below that | Heat-loss and shell-temperature predictions | Use the 200 °C value below 200 °C (conservative, slightly overpredicts loss); flagged in the materials database | accepted |
| K-18 | Refarom brick thermal properties are proxies (Haasser H3), not measured for this product | Floor and dome temperature predictions | Wide uncertainty bands; sensitivity analysis in Phase 2; ask Refarom for a full datasheet. Coupon test declined (decision 0003), so first-firing data calibrates (Phase 5). | open |
| K-19 | A barrel vault distributes top heat differently from a round dome; no quantitative source found for Neapolitan performance | Concept B could bake less evenly on top | Phase 2 radiation model compares vault and dome view factors; mitigated by turning pizzas, as is normal practice | open |
| K-20 | No dense castable datasheet; castable price is an unverified snippet | Concept C mass, cost and cracking behaviour unknown | Request Refarom BR 40 A datasheet and quote before choosing C | open |
| K-21 | Steel sheet and laser-cutting prices unknown | Budget check for concepts A, B and C is incomplete | Local quotes in Phase 3; B is designed so it needs no laser cutting | open |
| K-22 | Contact-burn thresholds taken from a secondary summary of EN ISO 13732-1 | R-S1 verification | Buy EN ISO 13732-1 or CENELEC Guide 29 before Phase 3 | open |
| K-23 | Brick emissivity correlation valid from 400 °C up; held constant below | Heat-up phase radiation slightly off | Low sensitivity (Phase 2 OAT); measure in Phase 5 | accepted |
| K-24 | Model under-predicts early floor heating ~1.5–2× vs F22 (held-out feeds too) | Heat-up time and wood for heat-up are pessimistic | Reported as upper bounds; calibrate at first firing (Phase 4 plan targets this) | open |
| K-25 | Calibrated fire/flow parameters poorly identified (chi_r and F22 insulation at bounds) | Wood-rate prediction ±20 % | Sensitivity with ±30 %; measure mouth gas temperature and wood mass in Phase 5 | open |
| K-26 | 64 mm thin barrel arch: stability not yet checked | Arch could be unstable or crack | Thrust-line check (Phase 3): geometric safety factor 8.5, thrust line within middle third | closed |
| K-27 | Retention prediction assumes a perfectly sealed, insulating door | Over-optimistic retention | Not a requirement; insulated door design in Phase 3 | accepted |
| K-28 | Concrete under floor: with 125 mm CaSi, about 84 °C (10 °C amb.) to 104.5 °C (40 °C amb., steady long session); limit 100 °C is an ASSUMPTION | Base cracking or spalling over time | 5 CaSi layers (decision 0005); thermocouple on concrete at first firing; 6th layer if measured > 100 °C; verify limit from authorised EN 1992-1-2 | open |
| K-29 | Shell ≤ 60 °C at 40 °C ambient needs ≥ 125 mm equivalent insulation; Superwool-only would strain the budget | R-S1 vs R-C1 | Hybrid 50 mm Superwool + 100 mm ProRox: shell 59 °C at 40 °C ambient (Phase 3 check) | mitigated |
| K-30 | Floor recovery after a pizza (R-P5) not modelled | Unknown recovery time | Contact model in Phase 3 or measure in Phase 5 | open |
| K-31 | Front-wall piers beside the door arch are narrow (76–127 mm pieces) and take the door-arch thrust | Pier movement or cracking | Thin-joint mortar bonding, door-arch rise raised to 120 mm (lower thrust), thrust strips at springing; inspect during build | open |
| K-32 | Budget: 712 USD priced, 15 lines (ProRox, steel, sheet, hardware) still need quotes | R-C1 | Quotes before purchase; fallback substitutions listed in Phase 3 report | open |
| K-33 | Mortar consumption uses an ASSUMED 2 kg/L | Too little mortar bought | 30 % allowance; one extra bag is cheap | accepted |
| K-34 | CAD masses use the stainless density proxy for mild/galvanized steel | Steel mass ~2 % high | Negligible for design | accepted |
