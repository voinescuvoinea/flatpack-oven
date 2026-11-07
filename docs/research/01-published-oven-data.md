# Published measurements of a traditional Neapolitan wood-fired oven

Accessed 2026-11-07. This is the main candidate validation dataset (risk K-01).
All three papers come from one group (University of Naples Federico II) and the
same pilot oven.

## [F22] Falciano, Masi & Moresi (2022)
"Performance characterization of a traditional wood-fired pizza oven."
*J. Food Sci.* 87(9):4107–4118. doi:10.1111/1750-3841.16268. Open access:
https://pmc.ncbi.nlm.nih.gov/articles/PMC9804529/

Oven (pilot scale, firebrick):
- Chamber: cylinder Ø 90 cm × 20 cm high, topped by an oblate ellipsoidal vault
  20 cm high. Interior crown height is therefore about 40 cm (our inference
  from the two 20 cm figures; the paper gives no total).
- Mouth: semicircular, 44 cm wide × 22 cm high
- Walls and floor about 10 cm thick. The paper does not report insulation or
  flue dimensions.
- The fire takes about ¼ of the floor area.

Fuel: seasoned oak logs, 600 ± 200 g, 250 ± 20 mm long, Ø 40 ± 10 mm.
Moisture 5.67 ± 0.17 % (wet basis). Calculated HHV ≈ 18.19 MJ/kg,
LHV ≈ 16.66 MJ/kg. Ambient during tests 36.4 ± 4.8 °C.

Results:
- Start-up of a new oven: days 1–4 at 3 kg/h for 1, 2, 4 and ~8 h
  (a curing schedule we can reuse)
- Pseudo-steady state at 3 kg/h after 4–6 h: vault 546 ± 53 °C, floor 453 ± 32 °C
- Initial floor heating rate: dT_FL/dt|0 = (49 ± 2)·Q_fw (°C/h, Q_fw in kg/h), r² = 0.99
- Maximum floor temperature: T_FL,max = (165 ± 11)·Q_fw − (10.6 ± 1.3)·Q_fw² (°C), r² = 0.99.
  It levels off at 629 ± 43 °C at 9 kg/h.
- Floor temperature rises roughly linearly for t ≤ 70 min
- Flue gas: T_FG = 8.6·Q_fw + 57.7, v_FG = 0.19·Q_fw + 1.5 (units as in the paper)
- Combustion efficiency 87 ± 3 % at 3 kg/h, falling to 79 ± 4 % at 9 kg/h
- Efficiency into food (water trays, pizzas) ≈ 13–15 %
- Floor during baking tests: 439 ± 8 °C. Bake time 60–90 s.

## [F23a] Falciano, Masi & Moresi (2023)
"Semiempirical modeling of a traditional wood-fired pizza oven in
quasi-steady-state operating conditions." *J. Food Sci.* 88(5):2036–2052.
doi:10.1111/1750-3841.16532 (PMID 36951313). We have only the abstract: the
full text blocks automated download. **The user could download it manually
into materials/sources/.**
- At quasi-steady state, flue-gas loss is 46 % and loss through the insulated
  chamber is 26 % of the firewood energy
- Enthalpy accumulation in the firebrick chamber ≈ 3.4 kW
- Vault-to-floor exchange is modelled as radiation plus convection
- Heat into a pizza-sized water tray: 73 % radiation and 15 % convection from
  the vault, 12 % conduction from the floor

## [F23b] Falciano, Moresi & Masi (2023)
"Phenomenology of Neapolitan Pizza Baking in a Traditional Wood-Fired Oven."
*Foods* 12(4):890. doi:10.3390/foods12040890. PMC9957212.
- Floor during baking: 439 ± 3 °C (quasi-steady). The floor under a pizza cools
  quadratically with time, more for heavier pizzas.
- Bake 60–90 s. Pizza bottom about 100 °C at 80 s.

## Pizza standard
- AVPN Disciplinare 2022: finished diameter ≤ 35 cm, dough ball 200–280 g,
  https://www.pizzanapoletana.org/public/pdf/Disciplinare_AVPN_2022_en.pdf.
  Our 45 cm pizza is oversized (R-P4).
- STG "Pizza Napoletana" (as reported via secondary sources; not yet checked
  against the official text): floor about 485 °C, vault about 430 °C, bake 60–90 s.
  Other sources swap the floor and vault figures. Our R-P1 range of 400–480 °C
  is consistent with the measured 439–453 °C.

## Use in this project
- **Model validation (Phase 2):** reproduce F22's T_FL,max(Q_fw) curve and
  heating rate for its geometry before applying the model to ours. Report the
  error, and note the confounders: unknown insulation and a 36 °C ambient.
- **Design point:** about 3 kg/h of dry hardwood holds a 90 cm Neapolitan oven
  near 450 °C floor. That gives a first estimate for R-P1a.
- **Heat budget:** F23a's 46/26 split shows wall loss is a quarter of fuel
  energy even in an insulated oven, so insulation matters. The flue loss is
  mostly unavoidable.
