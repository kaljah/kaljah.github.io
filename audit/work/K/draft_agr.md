# BUG-XXX — AGR form throughput units MMscfd / Mcf/day / m³/yr are ignored by the server (read as MMscf/yr): CO2 365× low, 2.7× high, or 28,317× high

**Status:** Confirmed
**Severity:** Critical
**Category:** Calculation
**Discovered by:** Agent K (Frontend/UI)

## Location
- `new/client/src/components/scope1/AGRForm.jsx` (unit dropdown: MMscf/yr, MMscfd, Mcf/day, m³/yr → `agr_unit`)
- `new/client/src/components/Scope1Form.jsx` ≈lines 803-819 (every formData key incl. raw `agr_throughput`/`agr_unit` copied into `calc_inputs.agr`) and ≈lines 943-950 (client-side conversion to top-level `amount`, with an extra `/1000` for m³/yr)
- `new/server/calculations/dispatcher.py` AGR branch (≈line 1018) reads `agr_throughput` + `agr_unit` and calls `_normalize_volume(..., "mmscf")` (≈line 122), which only knows scf/mcf/m3/bbl and returns the value unchanged for "mmscf/day", "mcf/day", "m3/yr".

## Reproduction
1. UI (:5191) as admin → Emissions → Scope 1, Region = first facility, Process = Acid Gas Removal (AGR).
2. Gas Throughput = 28316800, unit "m³/yr" (= 1000 MMscf/yr), Inlet CO2 5 %, Outlet CO2 0.5 %; Calculate & Submit.
3. Same via API with equivalent throughputs in each unit (`audit/repro/BUG-<id>.py`).

## Input
1000 MMscf/yr expressed in each unit offered by the dropdown; CO2 5 % in, 0.5 % out.

## Expected
Hand calculation: 1000 MMscf × (5 − 0.5) % = 45 MMscf CO2 = 4.5e7 scf ÷ 379.5 scf/lbmol × 44.01 lb/lbmol × 0.4536 kg/lb ≈ **2,367 t CO2** — identical for every unit.

## Actual
| Input | CO2 (t) | totalCo2e (t) |
|---|---|---|
| 1000 MMscf/yr | 2,371.4 | 2,828.7 (correct) |
| 2.740 MMscfd | 6.5 | 7.7 (365× low) |
| 2,739.7 Mcf/day | 6,497.0 | 7,749.8 (2.74× high) |
| 28,316,847 m³/yr | 67,150,409 | 80,098,823 (28,317× high) |

Browser submission (record id 752 in audit/db/ui.db): request `amount: 1, unit: "MMscf"`, `calc_inputs.agr = {agr_throughput: 28316800, agr_unit: "m3/yr", ...}`; response/record `co2e_total = 80,436,130 t` for a 1000 MMscf/yr unit, and stored activity `amount = 1 MMscf` (client conversion divides m³ by 28,316.8 **and** by 1000; correct is ÷28,316.8 → 1000 MMscf).

## Evidence
Playwright capture `audit/work/K/t_agr.mjs` (POST body + 201 response above); API run `audit/work/K/agr2.py`; `_normalize_volume("28316800","m3/yr","mmscf")` returns 28316800.

## Root Cause
Client converts the throughput only into `amount`, but also forwards the raw throughput and unit string in `calc_inputs`; the dispatcher prefers `agr_throughput` and its `_normalize_volume` has no rate units (`/day`, `/yr`) and no `m3/yr`, falling through to "already MMscf". The client's m³/yr branch additionally has a spurious `/1000`.

## Impact
Any AGR record entered in three of the four offered units is wrong by 2.7× to 28,000×; a single m³/yr entry adds ~80 Mt CO2e to the inventory and is auto-Verified for admin. Stored activity amount is also 1000× wrong for m³/yr.

## Affected Components
Scope 1 AGR manual entry (Tier 3; AGR is only offered as Tier 3), dashboard/intensity/SBTi totals that include these records.

## Recommended Fix
Server: handle rate/annual units explicitly (`mmscf/day`×365, `mcf/day`×0.365, `m3/yr`/`m3`÷28,316.85 etc.) and reject unknown units instead of passing through. Client: send one canonical value (MMscf/yr) in both `amount` and `calc_inputs.agr.agr_throughput`, and remove the extra `/1000`.
