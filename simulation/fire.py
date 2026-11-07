"""Empirically grounded fire model (no combustion CFD).

- Wood is fed at a scheduled rate and burns from a first-order inventory
  (dM/dt = feed - M/tau). Heat release Q = eta_comb * LHV * burn rate,
  with eta_comb and LHV from Falciano et al. (2022), via the materials DB.
- A fraction chi_r of Q leaves the fire bed as radiation (flame + embers).
  The rest heats a well-stirred hot gas zone.
- Gas mass flow = burning wood x (1 + lambda * stoichiometric air), with the
  stoichiometric air computed from the wood's elemental composition. Flue gas is
  treated as air for cp (high excess air; recorded assumption).
chi_r, lambda and the in-cavity convection coefficient are CALIBRATED against
the published oven (validation/f22.py), not assumed.
"""

from __future__ import annotations

from dataclasses import dataclass

from materials import db

# IUPAC standard atomic weights [kg/kmol]; O2 mass fraction of dry air from its mole fraction 0.2095
M_C, M_H, M_O, M_S = 12.011, 1.008, 15.999, 32.06
Y_O2_AIR = 0.2095 * (2 * M_O) / 28.965


def stoich_air_per_kg_dry(wood: db.Material) -> float:
    """kg dry air per kg dry wood for complete combustion."""
    f = {e: wood[f"mass_fraction_{e}"].at(300.0) for e in "CHOS"}
    # C + O2 -> CO2; 2H + 1/2 O2 -> H2O (O2 per kg H = M_O / (2 M_H)); S + O2 -> SO2; minus O in fuel
    o2 =f["C"] * (2 * M_O) / M_C + f["H"] * M_O / (2 * M_H) + f["S"] * (2 * M_O) / M_S - f["O"]
    return o2 / Y_O2_AIR


@dataclass
class FireParams:
    chi_r: float           # radiative fraction of heat release [-]
    excess_air: float      # lambda, air / stoichiometric air [-]
    h_in_W_m2K: float      # gas-to-surface convection inside the cavity
    tau_burn_s: float      # inventory burn-out time constant
    eta_comb: float
    lhv_J_kg: float
    moisture: float        # wet-basis mass fraction
    afr_st: float          # kg air / kg dry wood

    @classmethod
    def from_db(cls, chi_r, excess_air, h_in, tau_burn_s=900.0, wood_id="oak_firewood_f22", mats=None):
        mats = mats or db.load()
        w = mats[wood_id]
        return cls(chi_r, excess_air, h_in, tau_burn_s, w["combustion_efficiency"].at(300.0),
                   w["lower_heating_value"].at(300.0), w["moisture_content"].at(300.0), stoich_air_per_kg_dry(w))

    def heat_release_W(self, burn_kg_s: float) -> float:
        return self.eta_comb * self.lhv_J_kg * burn_kg_s

    def gas_flow_kg_s(self, burn_kg_s: float) -> float:
        dry = burn_kg_s * (1 - self.moisture)
        return burn_kg_s + dry * self.excess_air * self.afr_st
