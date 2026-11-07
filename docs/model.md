# Thermal model: structure, verification, calibration, limits

Code: `simulation/`. Verification tests: `tests/`. Calibration: `validation/f22.py`.

## Structure
```
            wood feed ──► fire bed (first-order burn, tau) ──► Q = eta * LHV * burn rate
                               │ chi_r * Q (radiation)          │ (1 - chi_r) * Q
                               ▼                                ▼
   floor ◄──── gray-diffuse radiosity network (floor, fire, door, vault) ────► vault
     ▲  cold inflow air (door open)                hot upper gas layer ──► out through door/flue
     │                                                         │
   1D layered conduction stack                    1D layered conduction stack (cylinder/sphere)
   brick / CaSi / concrete                        brick / Superwool
     ▼                                                         ▼
   natural convection + radiation to ambient (still air = worst case for touch temperature)
```
- **Conduction** (`conduction.py`): finite volume, implicit, Picard iteration for
  k(T) and nonlinear boundary conditions. Exact log/1/r resistances for curved stacks.
- **Radiation** (`radiation.py`): Monte Carlo view factors (convex cavity, 3×10⁵
  rays per emitting surface) and the net-radiation method. Brick emissivity ε(T)
  from the IFRF correlation.
- **Gas, door open**: two-zone mouth flow. Ambient air sweeps the floor; the hot
  layer collects (1 − χr)Q plus the heat picked up from the floor, convects to the
  vault and leaves as enthalpy (flue loss). **Door closed**: one still zone.
- **Air properties**: CoolProp. Flue gas is treated as air for cp (high excess air).
- **External convection**: Churchill–Chu correlations (vertical plate, horizontal
  cylinder, sphere), and Nu = 0.52 Ra^0.2 for a hot plate facing down.

## Verification (rule 5): all automated, `uv run pytest`
| Check | Reference | Result |
|---|---|---|
| Steady composite wall | exact piecewise-linear profile | to 1e-6 K |
| Steady cylinder and sphere shells | exact flux | rel. 1e-9 |
| k(T) linear in T | Kirchhoff transform | rel. 2e-4 |
| Radiation boundary | exact root | 1e-6 K |
| Semi-infinite solid, step | erfc solution | < 1 K at 30 min |
| Slab with convection | exact eigen-series | < 0.3 K at 1 h |
| Transient energy conservation (stack) | bookkeeping | rel. 1e-6 |
| Parallel squares, coaxial disks view factors | closed forms | ±0.004 |
| Hemisphere area, floor-to-dome F = 1 | geometry | 1e-4 / 1e-3 |
| Two-surface radiosity | concentric-sphere formula | rel. 1e-10 |
| Coupled oven energy balance, steady / 2 h transient | bookkeeping | 0.2 % / 2 % |

## Calibration and validation against the published oven (Falciano et al. 2022, 2023)
- **Free parameters (5):**
  - χr, the radiated share of fire heat
  - excess-air ratio λ
  - in-cavity convection coefficient h
  - the published oven's unknown equivalent insulation, vault and floor
- **Targets:**
  - steady floor 453 ± 32 °C and vault 546 ± 53 °C at 3 kg/h
  - loss split: 46 % flue, 26 % walls
  - initial floor heating rate at 3 and 9 kg/h
- **Held out:** heating rate at 4.5 and 6 kg/h.
- Results are in `validation/f22_calibration.json` and summarised in `docs/reports/phase-2.md`.

## Known limitations (also in docs/risks.md)
1. **Early floor heating is under-predicted by about 2×** against the published
   heating-rate correlation, including at held-out feeds. Likely causes:
   - no direct ember-to-floor contact or sideways conduction under the fire
   - the published oven's floor material and pre-heating are unknown
   - only one well-stirred upper gas zone
   Consequence: **predicted heat-up times are pessimistic (upper bounds)**.
2. **Some parameters are poorly identified.** χr hits its upper bound of 0.6, and the
   published oven's insulation hits its lower bound. Sensitivity runs use
   ±30 % on these.
3. **The vault (arch + walls) is one isothermal surface.** The model gives no
   top-heat distribution, only the average. Barrel-versus-dome evenness (K-19)
   is not resolved by this model.
4. **Simplified fire.** No gas or soot radiation beyond χr; feed is continuous,
   not log by log; no wind or draft dependence.
5. **Concrete properties are an ASSUMPTION**; the shell uses the paint
   emissivity; Superwool k is extrapolated below 200 °C (held constant,
   conservative).
6. **The floor under the fire is not part of the floor conduction stack**
   (the fire bed is a radiating surface).
