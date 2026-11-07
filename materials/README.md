# Materials database schema

`materials.yaml` holds every material property used anywhere in the project.
`db.py` loads it, validates it, and converts everything to SI (temperatures
to K). The test suite fails if any entry breaks the rules below.

```yaml
schema_version: 1
materials:
  - id: firebrick_example          # unique, snake_case
    name: Dense firebrick, 30% Al2O3
    category: refractory_dense     # see CATEGORIES in db.py
    product:                       # omit only for generic reference data
      manufacturer: ...
      product_name: ...
      grade: ...
    suppliers:                     # optional until Phase 3
      - name: ...
        url: ...
        price: 12.5
        currency: RON
        per: piece                 # piece | m2 | kg | roll | ...
        date_checked: 2026-11-07
    properties:
      thermal_conductivity:
        unit: W/(m*K)              # as written on the datasheet; converted by pint
        data:                      # temperature-dependent: list of points (T_C in °C)
          - {T_C: 200, value: 0.90}
          - {T_C: 600, value: 1.00}
        confidence: DATASHEET      # DATASHEET | REFERENCE | ASSUMPTION
        uncertainty: {rel: 0.15}   # or {rel_low: 0.1, rel_high: 0.3}; required always
        source:
          title: Manufacturer X datasheet "Y", rev 3
          url: https://...         # url or citation required
          locator: table 2, p. 1   # page/table
          accessed: 2026-11-07
          file: sources/x_y_rev3.pdf   # optional local copy
      density:
        unit: g/cm**3
        value: 2.1                 # constant (temperature-independent) form
        confidence: DATASHEET
        uncertainty: {rel: 0.05}
        source: {...}
      max_service_temperature:
        unit: degC
        value: 1250
        ...
```

Rules enforced by `db.py`:
- Every property has `unit`, exactly one of `value` / `data`, `confidence`,
  `uncertainty` and `source` (`title`, `accessed`, and `url` or `citation`).
- `ASSUMPTION` entries also need `reasoning`.
- Units must convert to the canonical SI unit for that property.
  Thermal-expansion values per °C are written as `1/delta_degC`.
- `Property.at(T_K)` interpolates linearly within the datasheet range and
  raises outside it. Extrapolation is opt-in: pass `extrapolate=True`, and
  the caller must record the reason in the risks document.
