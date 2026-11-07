# Design principles, sourcing and site data (Phase 1)

Accessed 2026-11-07 unless noted. Strength of sources: [P] peer-reviewed,
[D] manufacturer datasheet, [S] standard or official guidance, [F] builder forum
or vendor blog (practice, not engineering proof).

## 1. Oven geometry: what the evidence says
| Topic | Finding | Source |
|---|---|---|
| Measured Neapolitan oven | Ø 90 cm floor; 20 cm cylindrical wall plus 20 cm elliptical vault (crown ≈ 40 cm); mouth 44 × 22 cm; ~10 cm firebrick walls/floor; fire takes ~¼ of floor | [P] F22 (see 01-published-oven-data.md) |
| Dome height | Low domes favour pizza: they heat up faster and run hotter. High domes hold heat and suit roasting. Rules of thumb vary: crown ≈ ⅓ of floor diameter, or "~30 cm regardless of diameter" | [F] Forno Bravo forum; [F] Forno Bravo Pompeii plans |
| Door height | "Door = 63 % of interior height" is widely repeated but disputed. Forno Bravo's own low-vault table gives 69–71 %; F22 is 55 % (22/40) | [F]; [P] F22 |
| Floor material | Neapolitan ovens traditionally use biscotto di Sorrento, claimed lower k (< 0.6 W/mK) than dense firebrick (~1–1.3), to avoid burnt bases at 450–480 °C. The F22 firebrick floor bakes fine at 439–453 °C (pizza base ~100 °C at 80 s) | [F] forum (no datasheet); [P] F22/F23b |
| Heat into the pizza | 73 % radiation and 15 % convection from the vault, 12 % conduction from the floor (water-tray proxy) | [P] F23a |
| Where heat goes (steady) | 46 % up the flue, 26 % through the insulated walls, the rest stored or into the food | [P] F23a |
| Pizza standard | AVPN: Ø ≤ 35 cm, bake 60–90 s | [S] AVPN Disciplinare 2022 |

**Implications for us**
- A **Ø 0.90 m floor** (the F22 size) fits a 45 cm pizza beside a fire taking ¼
  of the floor, leaving ~9 cm margin all round (computed in
  `geometry/concepts.py`). Matching the published oven also lets Phase 2
  validate against it directly.
- **Door: ~52 cm wide × ~24 cm high (proposal).** A 45 cm pizza on a peel needs
  more width than F22's 44 cm. A bigger opening loses more heat, so Phase 2 sizes it.
- **Crown ≈ 40 cm**, as in F22.
- **Floor: Refarom fireclay brick, first choice.** It is local, cheap, and works
  in the published oven. Biscotto has no datasheet and no EU price found, so it
  stays an upgrade option if bases burn.

## 2. Materials found (details and sources in `materials/materials.yaml`)
| Role | Product | Price (date 2026-11-07) | Data quality |
|---|---|---|---|
| Floor / hot face | Refarom 65 SA fireclay brick 230×114×64 (made in Brașov, RO), Hornbach | 5.74 RON/pc | Max temp, porosity, strength [D]; k, ρ, cp, α by proxy (Haasser H3 [D]) |
| Floor insulation | CaSi board CS-270, 1200×600×25, Hornbach | 94.00 RON/sheet | k(T), ρ, max temp [D] |
| Dome insulation | Morgan Superwool Plus blanket 128 kg/m³ (AES, not classified carcinogenic in EU) | €139.95 / 25 mm roll 4.46 m² (EU online, density label to confirm) | k(T) 200–1000 °C, ρ [D] |
| Sealant | Fermit stove sealant 1000 °C, 310 ml, Hornbach | 37.52 RON | max temp only |
| Castable (concept C) | none with a datasheet yet. Refarom BR 40 A via Romstal (datasheet blocked); Solargil 1300 °C (FR) | €57.48 / 25 kg (snippet, unverified) | density ASSUMPTION |
| Steel sheet | 1.4301 density from stockist | no public price | quote needed |

Not found or not usable:
- No Romanian stockist for bio-soluble blanket
- No public steel sheet prices
- No 30 % alumina dense brick with complete datasheet. Incropera Table A.3
  could not be checked online, so it was not used.

## 3. Laser cutting (local)
Shops offering stainless laser cutting exist in Romania (e.g. Profinox), but
none publish prices. **Decision (R-F6): design so that laser cutting is
optional.** Concept B needs none: angle iron, rods and flat sheet can be cut
with an angle grinder. If concept A is chosen, Phase 3 sends DXFs for real
quotes, with grinder-cut fallbacks.

## 4. Site and safety values
| Item | Value | Source | Use |
|---|---|---|---|
| Build-site record low | −35.3 °C (Jan; extremes 1901–present) | [S] NOAA / Romanian National Institute of Statistics climate data for the nearest station (station withheld at the owner's request; accessed 2026-11-07) | R-E2 winter survival (unfired, dry) |
| Build-site Jan mean daily minimum | −3.0 °C (1991–2020) | same | typical freeze/thaw cycling |
| Manual handling | 25 kg (men) / 16 kg (women) at knuckle-to-elbow height, close to body | [S] HSE INDG143 rev4, Fig. 1 (`materials/sources/hse_indg143_manual_handling.pdf`) | R-F2 confirmed |
| Contact burn thresholds, bare metal | ≈70 °C at 1 s, ≈51 °C at 1 min, ≈43 °C prolonged (indicative) | [F] secondary summary of EN ISO 13732-1; the standard itself is paywalled | R-S1: our 60 °C target is fine for brief touches. Handles need lower temperatures or insulating grips. Buy the standard (or CENELEC Guide 29) before Phase 3. |
| Concrete base temperature limit | **ASSUMPTION ≤ 100 °C** at the concrete surface | EN 1992-1-2 Table 3.1 strength factors (not verified online); moisture in concrete is an additional concern | R-I2: verify from the standard in Phase 2. Floor insulation is sized to keep well below this. |
| Exchange rate | 1 EUR = 5.3403 RON = 1.1165 USD (2026-11-06) | [S] ECB reference rates | R-C1 budget = 1000 USD ≈ 4783 RON |
