# Full Codebase Bug Audit

> Audit date: 2026-04-23 | Status: **7 bugs fixed this session**, **9 remaining bugs below**

---

## Already Fixed This Session

| # | File | Bug | Fix |
|---|---|---|---|
| F1 | `models.py` | `MitigationProject` missing `facility` relationship → 500 on batch-all | Added `db.relationship('Facility')` |
| F2 | `Reports.jsx` | `reportYear` defaulted to 2026 → blank PDFs (no data for 2026 in DB) | Sync `reportYear` to `filterRes.data.years[0]` on load |
| F3 | `Reports.jsx` | `division` filter not sent to `/emissions` API params | Added `division` to params |
| F4 | `Reports.jsx` | `division` missing from `useEffect` deps | Added to dep array |
| F5 | `ModernReportGenerator.js` | Array `regionId` serialized as `[object Array]` in query string | Skip `facility_id` param when array; filter client-side |
| F6 | `ModernReportGenerator.js` | `ch4_intensity * 1000 * boe` — double x1000 on already-kg/BOE value | Removed the x1000 |
| F7 | `dashboard.py` `get_intensity_stats` | Scope 3 Cat 11 added to intensity numerator → 10x inflation (5379 vs correct 110) | Moved S3 to separate `s3_map`, excluded from `co2_intensity` |

---

## Critical Bugs (Data-Affecting)

### BUG-1 — `emissions.py` update_emission(): recalculate block always runs
**Lines:** 458-479  
**Impact:** The `if data.get('recalculate'):` block only sets `factor_data`, but `compute_emissions()` runs unconditionally outside the if. Every PUT request (even a simple status change) overwrites stored emission values with a fresh recalculation.

```python
if data.get('recalculate'):
    fuel_key = data.get('fuel_type') or record.fuel_type
    factor_data = API_FACTORS.get(fuel_key, {})
gwp_dict = resolve_gwp_dict(user)   # outside if!
try:
    calculated_em, method = compute_emissions(...)  # always runs!
```

**Fix:** Move `gwp_dict`, the `try` block, and all field assignments inside the `if data.get('recalculate'):` block.

---

### BUG-2 — `emissions.py` import_emissions(): file handle leak
**Lines:** 554-556  
**Impact:** `log_file = open('import_debug.log', 'a')` is opened at the top of the function. It is only closed in the early-return unauthorized path. Every normal execution path (including mid-import exceptions) leaks the file handle, eventually exhausting OS file descriptors.

**Fix:** Wrap in `with open(...) as log_file:` or add `finally: log_file.close()`.

---

### BUG-3 — `dashboard.py` get_categorical_breakdown(): Scope 3 inflates region totals
**Lines:** 502-504  
**Impact:** Same class of bug as the intensity fix (F7). Scope 3 Cat 11 (use of sold products) is added to each region's total in the doughnut/bar charts, making them ~5-10x too large. The categorical breakdown is used to drive the dashboard charts.

```python
for r in scope3_results:
    output_map[key] = output_map.get(key, 0) + float(r.total_emissions or 0)  # inflates!
```

**Fix:** Remove S3 from `output_map`, or add a separate `scope3` key so the frontend can display it in a separate section.

---

### BUG-4 — `scope2.py` bulk_import_scope2(): units ambiguity in co2e formula
**Lines:** 189  
**Impact:** `co2e = (kwh * ef) / 1000` — this is correct only if `ef` is in kg CO2e/kWh. If `GRID_FACTORS` stores `ef` in t CO2e/MWh (which is the international standard), then the formula should be `co2e = (kwh / 1000) * ef`. These produce the same numeric result only if 1 kg/kWh == 1 t/MWh, which is true. However, if any grid factor is stored in kg/MWh instead, the result will be off by 1000x.

**Fix:** Verify `electricity_factors.py` units and add a comment confirming the formula is correct for that unit.

---

## Medium Bugs (UX / Logic)

### BUG-5 — `dashboard.py` get_uncertainty_analysis(): no facility/activity/division filter
**Lines:** 747-751  
**Impact:** Uncertainty widget always shows full-fleet numbers regardless of the current dashboard filter. When filtered to a single facility, the uncertainty values are meaningless.

```python
s1_emissions = Emission.query.filter_by(year=year).filter(Emission.status != 'Draft').all()
# No facility_id, activity, or division filter
```

**Fix:** Read `facilityId`, `activity`, `division` from `request.args` and apply them to the queries.

---

### BUG-6 — `emissions.py` add_emission(): goal notification checks Scope 1 only
**Lines:** 323  
**Impact:** Goal threshold notification fires based only on Scope 1 total, not total GHG (S1+S2+S3). Goals are set as total GHG targets, so the alert threshold is wrong.

```python
total_emissions = db.session.query(func.sum(Emission.co2e_total)) \
    .filter(Emission.year == current_year).scalar() or 0  # Scope 1 only!
```

**Fix:** Add Scope 2 and Scope 3 totals for the same year and sum them.

---

### BUG-7 — `emissions.py` add_emission(): debug print() statements in production
**Lines:** 211-239  
**Impact:** 6 `print(f"DEBUG ...")` calls run on every emission addition, logging raw user input (fuel type, quantities, emission factors) to stdout unfiltered. Performance hit + potential data exposure.

**Fix:** Remove all `DEBUG -` print statements or replace with `app.logger.debug(...)`.

---

### BUG-8 — `ModernReportGenerator.js` fetchAllReportData(): scope detection uses fragile heuristic fallback
**Impact:** When `r.scope` is null/undefined (legacy records), the code falls back to `process_type` string matching. Records with process types like "Stationary Combustion - Natural Gas Electricity" match the Scope 2 heuristic (contains "electricity") even though they are Scope 1. This creates wrong scope labels in Annex A.

**Fix:** Trust the `scope` field from the API (which is always set on seeded/new data). Only apply the heuristic if `r.scope` is explicitly null AND the record predates a known cutoff date.

---

## Low Priority

### BUG-9 — `ModernReportGenerator.js` Annex A didDrawPage: drawFooter receives wrong arg
**Impact:** `drawFooter(hookData.pageNumber)` — but `drawFooter()` ignores its argument and always calls `doc.internal.getNumberOfPages()` internally. The footer renders correctly but the parameter is silently ignored, which is confusing. If `drawFooter` is ever refactored to use the parameter, the Annex A pages will show wrong page numbers.

**Fix:** Either make `drawFooter` accept and use a `pageNumber` parameter, or remove the unused argument.
