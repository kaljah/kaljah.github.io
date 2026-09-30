# BUG-XXX — Tier 1 combustion applies the catalog HHV in the wrong basis when the activity unit is mass or the other phase (diesel/crude per tonne ×3.6, natural gas per tonne ÷40, ethane per scf ×39)

**Status:** Confirmed
**Severity:** High
**Category:** Calculation
**Discovered by:** Agent C (Tier / Factor Auditor)

## Location
- `new/server/calculations/combustion.py` `convert_factor_to_kg_per_unit()`, lines ~84-135 (the `kg/MMBtu` branch).
  - `is_solid_fuel` is set true for any mass activity unit (`a_unit in [tonne, kg, lb ...]`). The fuel's HHV is then read as kBtu/short ton, even for diesel (138000 Btu/gal) or natural gas (1020 Btu/scf).
  - For volume units, liquid/gas is decided by keyword. "propane" and "ethane" are not in the liquid list, so gal-basis HHVs are multiplied by scf (35.3147 per m3).
- `new/server/emission_factors_api2021.py`: `Ethane` is typed `gases`, yet its `hhv` 69600 is Btu/gal.
- The client allows the combination. `CombustionForm.jsx` offers every unit (m3, scf, gal, bbl, L, kg, ton, tonne) for every fuel. In `Scope1Form.jsx`, `convertActivityData()` has no kg/tonne↔gal or scf↔gal pair, so the unit is sent unchanged.

## Reproduction
1. `python audit/repro/BUG-<ID>.py` (own db). It POSTs Tier 1 (`factor_source=default`) combustion records to `/api/emissions/`.

## Input
| Fuel | Quantity |
|---|---|
| Diesel (No. 2 Fuel Oil) | 1 tonne |
| Crude Oil | 1 tonne |
| Natural Gas | 1 tonne |
| Ethane | 1000 scf |
| Propane (Liquid) | 1 m3 (API/bulk path; the UI converts m3→gal for this fuel) |

## Expected (t CO2, independent)
- Diesel 1 t ≈ 3.17 (IPCC 2006 cross-check: 43.0 TJ/Gg × 74,100 kg/TJ = 3.19).
- Crude 1 t ≈ 3.10 (IPCC: 42.3 × 73,300).
- Natural gas 1 t ≈ 2.4–2.7.
- Ethane gas 1000 scf ≈ 1.77 MMBtu × 59.6 = 0.105.
- Propane liquid 1 m3 = 264.17 gal × 0.0915 × 62.88 = 1.52.

## Actual
| Case | Actual (t CO2) | Ratio to expected |
|---|---|---|
| Diesel | 11.25 | 3.55× |
| Crude | 11.34 | 3.66× |
| Natural gas | 0.0597 | 0.025× |
| Ethane | 4.148 | 39.5× (identical to 1000 gal) |
| Propane (Liquid) | 0.203 | 0.13× |

All cases return HTTP 201, with calc_method "Stationary Combustion" and no warning.

## Evidence
Repro output: every case is flagged WRONG. Diesel 1 tonne gives 11.2507 t. 138000/1000 = 138 MMBtu/short ton × 1.10231 × 73.96 kg/MMBtu = 11.25 t. This confirms that the Btu/gal HHV is used as kBtu/short ton.

## Root Cause
The catalog HHV carries no unit. Its basis is implied by `baseUnit` (gal, scf or ton). The converter infers the basis from the activity unit, and from fuel-name keywords, instead of from the factor's basis. It has no density bridge between volume-basis HHV and mass activity.

## Impact
Tier 1 combustion totals are wrong by 3.5× to 40× whenever a liquid or gaseous fuel is reported in kg or tonnes. Mass reporting is common outside the US. The same applies to ethane reported in scf, and to liquid propane in m3 or L via bulk upload/API.

## Affected Components
- Manual Scope 1 entry, bulk upload and recalculation.
- The same function is used for Tier 2 custom factors with kg/MMBtu units.

## Recommended Fix
- Store the HHV unit explicitly (Btu/gal, Btu/scf, MMBtu/short ton).
- Convert activity to the HHV basis using density when crossing mass↔volume, or reject units incompatible with the fuel's basis.
- Fix `Ethane` to a liquid basis, or add a gaseous HHV.
