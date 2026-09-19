# Calculation Logic Audit — Full Read-Only Review
> Date: 2026-04-23 | Mode: READ-ONLY — no changes made  
> Files read: constants.py, units.py, base.py, combustion.py, vented.py, fugitive.py, midstream.py, dispatcher.py, legacy_engine.py, emissions.py, scope2.py, scope3.py, dashboard.py, models.py, electricity_factors.py

---

## Summary Table

| # | Severity | File | Issue |
|---|---|---|---|
| C1 | 🔴 CRITICAL | `constants.py` | `GWP_DEFAULT_GWP` comment says "AR5" but values are AR4 (CH4=25, N2O=298). `DEFAULT_GWP` correctly points to AR5, but the named dict is misleading and could cause confusion if used directly. |
| C2 | 🔴 CRITICAL | `legacy_engine.py:602` | `is_specific` branch divides by 1000 twice — once in the totalCo2e formula and then again on each gas value. Result: CO2e is `(em['co2'] + em['ch4']*GWP + em['n2o']*GWP) / 1000`, then each gas is divided by 1000 again, making the *stored* gas values 1,000× too small while totalCo2e is only 1,000× too small of the already-wrong sum. |
| C3 | 🔴 CRITICAL | `legacy_engine.py:614` | `em['ch4'] = (v / gwp_dict['CH4']) / 1000.0` — when process has `factor_data.type`, the stored `ch4_emissions` is back-calculated from the total by dividing by GWP (28) then by 1000 again. This is not a valid CH4 mass — it's an intensity unit. The correct value should come directly from the factor. |
| C4 | 🔴 CRITICAL | `scope3.py:162` | Scope 3 bulk import: `co2e = (amt * ef) / 1000`. The division by 1000 only makes sense if `ef` is in `g CO2e/unit` or the `amt` is in a sub-unit. If `ef` is already in `kg CO2e/unit` (which is the standard for Scope 3), then co2e is already in kg and should just be `amt * ef / 1000` to get tonnes — this is correct only if EF is kg/unit. But if EF is in `t CO2e/unit` (common for large-volume Category 11), then dividing by 1000 is wrong by 1000×. No unit validation or comment exists. |
| C5 | 🔴 CRITICAL | `combustion.py:38` | `"l_to_gal"` key used in `CONVERSIONS.get("l_to_gal", 0.264172)` — this key does **not exist** in `units.py`'s `CONVERSIONS` dict. The fallback `0.264172` is used instead. This is technically correct numerically (1 liter = 0.264172 gal), but the `CONVERSIONS.get()` is silently using the default rather than the registered constant. If anyone ever adds a wrong `l_to_gal` to CONVERSIONS, it would silently override the correct default. |
| C6 | 🔴 CRITICAL | `dispatcher.py:115` | Completions: `flare_eff = float(... or 0)` then passed as `control_efficiency=flare_eff / 100.0` to `CompletionFlowbackCalculator.calculate()`. BUT in the legacy engine fallback at `legacy_engine.py:377`, the same efficiency is passed as `eff_pct / 100.0` to `ghg_calc.calculate_completions(dur, rate, eff_pct / 100.0)`. If `compute_emissions` is called and falls back through the API dispatcher (which calls `CompletionFlowbackCalculator`), the efficiency is divided by 100 correctly. BUT if the legacy engine tier-3 path is hit, and `eff_pct` already comes in as a percentage string like `95`, it is divided by 100 to get 0.95 — which is correct. However the dispatcher at line 119 passes `control_efficiency=flare_eff / 100.0` while `CompletionFlowbackCalculator.calculate()` expects a decimal fraction already. If `flare_eff` is 95 (percent), this gives 0.95 — correct. BUT: if the user enters 0.95 (already a fraction), the `/100` produces 0.0095, removing 99% of control. No unit guard exists. |
| M1 | 🟡 MEDIUM | `dashboard.py:568` | `GAS_TO_BOE = 0.178` comment says "API 2021 approx: 5.615 Mcf/bbl → 0.178 BOE/Mcf". The actual standard is **5.8 Mcf/BOE** (IEA/API 2009, widely used), giving 0.172 BOE/Mcf. The 5.615 figure comes from energy equivalence (1 BOE = 5.8 MMBtu, 1 Mcf NG = ~1.03 MMBtu → 5.615 Mcf/BOE). Using 0.178 vs 0.172 is a ~3.5% difference in gas BOE. **Not wrong per se** (there are multiple standards), but should be documented. |
| M2 | 🟡 MEDIUM | `vented.py:105` | `LiquidsUnloadingCalculator` pressure equation: `v_std = v_tubing * (pressure / 14.7)`. `pressure` is labeled as `psia` in the inputs dict but the user typically enters wellhead pressure in **psig**. If the user enters 100 psig, the correct absolute pressure is 114.7 psia, but the code uses 100/14.7 = 6.8×, producing ~15% underestimate instead of using (100+14.7)/14.7 = 7.8×. The dispatcher passes `pressure=float(flat_inputs.get('pressure', 100.0))` with no psig→psia conversion. |
| M3 | 🟡 MEDIUM | `legacy_engine.py:448` | Pneumatic intermittent: `ch4_kg = (annual_scf * 0.0423 * ch4_content) / 2.20462`. `0.0423` is lb/scf CH4 density. Dividing by 2.20462 converts lb→kg. This is correct. However the factor `13.5 scf/year/device` (line 445) is multiplied by `count` (line 445) but the variable is `annual_scf = 13.5 * count`, not per device × count of actuations. The comment says "13.5 scf/year/device" which is correct, but the API 2021 Table 6-7 default for intermittent pneumatics is **13.5 scf/actuation**, not per year. If there are multiple actuations per year, the result is too low. |
| M4 | 🟡 MEDIUM | `legacy_engine.py:502` | Dehydrator: `ch4_kg = (annual_scf * 0.0423) / 2.20462`. This should be `0.0423 * 0.453592 = 0.01918 kg/scf`. But `0.0423 / 2.20462 = 0.01919 kg/scf`. Numerically nearly identical — this is fine. However: the factor `37.85 scf CH4/gal TEG` (line 499) is from a 1970s GLYCalc default and is much higher than the API 2021 Table 6-5 value of **~3-5 scf/gal**. The `midstream.py:DehydratorCalculator` correctly uses 3.0. There is an inconsistency: the legacy engine uses 37.85 while the dispatcher uses 3.0. Which path is actually called depends on whether `factor_source == 'specific'` is set. |
| M5 | 🟡 MEDIUM | `units.py:96-97` | `convert()` function: if the key is not found AND the reverse key is also not found, it raises `ValueError`. But `calculate_co2e()` on line 64-66 uses `CONVERSIONS["gwp_ch4"]` and `CONVERSIONS["gwp_n2o"]` — these ARE in the dict. But `calculate_co2e` signature is `(co2=0, ch4=0, n2o=0)` — it does NOT use `GWP_AR5`/`DEFAULT_GWP` directly. It uses `CONVERSIONS["gwp_ch4"]` which is set to `DEFAULT_GWP['CH4']` = 28. This is **correct**. ✓ |
| M6 | 🟡 MEDIUM | `scope2.py:189` | `co2e = (kwh * ef) / 1000`. `GRID_FACTORS` unit is `"kg CO2e/kWh"`. So: `co2e = kwh * (kg/kWh) = kg` → `/ 1000 = tonnes`. This is **correct** numerically. ✓ (BUG-4 from previous session was a false alarm.) |
| M7 | 🟡 MEDIUM | `dashboard.py:586` | Gas BOE conversion when unit is `m3`: `gas *= 0.035315` — comment says "1 m3 ~ 35.315 scf → 0.035315 Mcf". Then multiplied by `GAS_TO_BOE = 0.178`. Result: 1 m3 gas → 0.006286 BOE. The correct value is 1 m3 ≈ 35.315 scf = 0.035315 Mcf → × 0.178 = 0.00629 BOE. This is correct. ✓ |
| M8 | 🟡 MEDIUM | `legacy_engine.py:97-98` | In `convert_factor_to_kg()`: `'mcf': 0.0353147` and `'mscf': 0.0353147`. The conversion table represents "how many m3 per unit". 1 Mcf = 1000 scf = 28.317 m3, so the correct `mcf` conversion should be `28.3168`, not `0.0353147`. This dict appears to be the **denominator normalization** (m3 per factor-denominator-unit), so the intent is: if factor is per Mcf, convert to per m3 by dividing by 28.317 → i.e., multiply by 1/28.317 = 0.0353. The table stores the inverse (per-m3 factor), so 1/28.317 = 0.0353147. This is correct when used as `val * (f / a)`. ✓ |
| L1 | 🟢 LOW | `combustion.py:34-36` | Dead code: `normalized_quantity = fuel_quantity * 1000000.0 * 35.3147 / 1000.0` is immediately overwritten by `normalized_quantity = fuel_quantity * 1000000.0` on the next line. The first assignment (lines 34-35) is unreachable. |
| L2 | 🟢 LOW | `legacy_engine.py:394-395` | `if process == 'fugitive':` block reads `f = calc_inputs.get('fugitive') or {}` and also `count = float(f.get('count') or amount or 0)`. But the dispatcher already routes `"fugitive"` to `EquipmentFugitiveCalculator` which needs `equipment_count` and `ef`. The legacy path and the API path are now duplicated. The legacy path will win only when the dispatcher returns zero (no matching calc). Low risk but confusing. |
| L3 | 🟢 LOW | `constants.py:2` | Comment says "AR5 GWP Values" but `GWP_DEFAULT_GWP` contains AR4 values (CH4=25, N2O=298). This is a misleading comment — not a calculation error since `DEFAULT_GWP` correctly points to `GWP_AR5`. The named dict `GWP_DEFAULT_GWP` is never used anywhere in the codebase (only `DEFAULT_GWP` is). Safe to ignore but confusing. |

---

## Critical Findings (Require Action)

### C1 — `constants.py` misleading dict name (low impact)
`GWP_DEFAULT_GWP = { 'CH4': 25 }` is named "DEFAULT" but contains AR4 values. It is **never referenced** in any file — only `DEFAULT_GWP` (= `GWP_AR5`) is imported. Risk: a future developer uses `GWP_DEFAULT_GWP` by mistake and gets AR4 instead of AR5.

### C2 — `legacy_engine.py:602-606` double division by 1000 in `is_specific` path
```python
em['totalCo2e'] = (em['co2'] + (em['ch4'] * gwp_dict['CH4']) + (em['n2o'] * gwp_dict['N2O'])) / 1000.0
em['co2'] /= 1000.0   # Already in kg, divides again
em['ch4'] /= 1000.0
em['n2o'] /= 1000.0
```
At this point `em['co2']` is in **kg** (from `amount * factor_kg`). Dividing by 1000 gives tonnes — correct. But `totalCo2e` is computed BEFORE the `/=` operations using the kg values, then divided by 1000. This means totalCo2e = `(kg_co2 + kg_ch4*28 + kg_n2o*265) / 1000` = tonnes — which is also correct **IF** `em['co2']` etc. are in kg at the time of the formula.

**Wait — re-reading carefully:** The totalCo2e formula uses `em['co2']` etc. which are in kg at that point → dividing by 1000 gives tonnes ✓. Then the gas values are divided by 1000 individually → tonnes ✓. So this is **actually correct**. The `totalCo2e` uses kg values before conversion; the `/1000` on that formula makes it tonnes.

**UPDATED: C2 is a FALSE ALARM.** ✓

### C3 — `legacy_engine.py:614` back-calculation of CH4 from total is incorrect
```python
v = ghg_calc.calculate_default_kg(amount, unit, hhv, factor_data, 'total')
em['totalCo2e'] = v / 1000.0
em['ch4'] = (v / gwp_dict['CH4']) / 1000.0  # BUG
```
`v` is total CO2e in **kg**. Dividing by `GWP_CH4 (28)` gives `kg / 28`, which is **not a valid CH4 mass**. This only makes sense if the entire emission is methane (100% CH4). For mixed-gas or combustion sources, this produces a wrong CH4 value. The correct approach: if only a `total` factor is available, CH4 should be 0 or computed from the gas composition. This path is hit when `factor_data.get('type')` exists — i.e., equipment-type factors.

**This is a real bug — the stored `ch4_emissions` for equipment-type factors is wrong.**

### C4 — `scope3.py:162` ambiguous EF units in bulk import
`co2e = (amt * ef) / 1000` — if `ef` is in `t CO2e/unit` (common for Category 11 crude oil use, e.g., 0.43 tCO2e/bbl), then multiplying by amount (bbl) gives tonnes, and dividing by 1000 gives kt — **wrong by 1000×**. This affects any Scope 3 bulk import where the user provides EF in tonnes rather than kg. No unit validation exists.

### C5 — `combustion.py:38` missing CONVERSIONS key  
`CONVERSIONS.get("l_to_gal", 0.264172)` — the key `l_to_gal` does not exist in `units.py`. The fallback 0.264172 is numerically correct (1 L = 0.264172 US gal). Functionally harmless but is a latent bug — if the key is ever added with a different value, behavior changes silently.

### C6 — Pressure unit ambiguity in LiquidsUnloading (M2 re-classified)
`v_std = v_tubing * (pressure / 14.7)` assumes **psia**. User inputs wellhead pressure typically in **psig**. A user entering 500 psig gets 500/14.7 = 34× instead of the correct (500+14.7)/14.7 = 35× — a 3% underestimate. Minor but systematic.

---

## What Is Correct ✓

| Check | Result |
|---|---|
| GWP values used throughout (AR5: CH4=28, N2O=265) | ✓ Correct |
| BOE conversion gas factor (0.178 BOE/Mcf) | ✓ Acceptable (documented API standard) |
| Scope 2 co2e formula: `(kwh * ef_kg_kwh) / 1000` = tonnes | ✓ Correct |
| `calculate_co2e()` uses AR5 GWPs via CONVERSIONS dict | ✓ Correct |
| Scope 1 `co2e_total` stored as tonnes | ✓ Confirmed |
| Intensity = (S1+S2) / BOE after today's fix | ✓ Fixed and correct |
| Flaring dual-efficiency model (η_c, η_d) | ✓ Correct approach |
| Dehydrator dispatcher uses 3 scf/gal | ✓ Conservative, defensible |
| Unit conversion dict denominators in `convert_factor_to_kg` | ✓ Correct (inverse convention) |
| Scope 3 `is_specific` path totalCo2e formula | ✓ Correct |

---

## Recommended Fix Priority

| Priority | Item | Effort |
|---|---|---|
| 🔴 Fix Now | C3 — ch4 back-calc from total wrong | 2 lines |
| 🔴 Fix Now | C4 — S3 bulk import EF unit ambiguity | Add unit check + comment |
| 🟡 Fix Soon | M2/C6 — Pressure psig vs psia in unloading | Add psig→psia conversion |
| 🟡 Fix Soon | M3 — Pneumatic intermittent: scf/actuation vs scf/yr | Clarify or multiply by actuations |
| 🟡 Fix Soon | M4 — Dehydrator EF inconsistency (37.85 legacy vs 3.0 dispatcher) | Remove legacy dehy path |
| 🟢 Low | L1 — Dead code in combustion.py | Remove 1 line |
| 🟢 Low | C1/L3 — `GWP_DEFAULT_GWP` misleading name | Rename or remove |
| 🟢 Low | C5 — Missing `l_to_gal` key in CONVERSIONS | Add to dict |
