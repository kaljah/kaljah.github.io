# Scope 1 bulk import: 100,000-row audit (2026-10-01)

**Scope.** 100,000 unique Scope 1 rows covering Tier 1, 2 and 3, every process and every unit the importer takes. The file was imported twice, each time into a fresh database:
- through the backend HTTP API (login, CSRF token, `POST /api/emissions/upload/start`);
- through the real UI (headless Chromium, Scope 1 › Bulk Import (Wizard)).

The results were then checked in the database, in the UI table and in the table's data feed.

**Code base.** Branch `ccr-b93733a1-u3m8s8` at commit `714e97e4` (§1–§5: the findings as found). **All findings were then fixed; see §6 for the fixes and the re-run of the same 100,000 rows.**

## 1. Summary

| | Result |
|---|---|
| File of 100,000 rows | **Refused as a whole** (cap of 50,000 rows per file), on both paths. It was then imported as two files of 50,000. |
| Rows saved / refused | 83,147 saved, 16,853 refused with a reason. API and UI give the same result. |
| API vs UI database | **Identical.** All 83,147 records match in every stored value (same total: 677,259,560.45 tCO₂e). |
| UI table vs database | 1,693 rendered rows (150 pages and 193 targeted searches) match within display precision. The full table feed (83,147 records) matches exactly. |
| Independent oracle (Tier 1/2 factors, stoichiometry, vented gas) | 46,788 rows checked. 45,398 pass. The **1,390 failures are all one defect (F1)**. |
| Unit-equivalence groups (same physical activity in different units) | 20,366 groups. 19,376 pass. The **990 failures are all from F3, F4 and F5**. |
| Rows that must be refused | 13,752. 13,343 refused, **409 silently accepted (F3, F4)**. |
| Ambiguous inputs that should be refused | 2,314. **1,667 silently accepted (F6 to F10)**. |
| Unit spellings verified correct | 113 activity-unit spellings by the oracle and 207 (column, unit) pairs by equivalence. |

What works:
- Tier 1 and Tier 2 unit conversion is correct for every supported spelling of:
  - energy (MMBtu, GJ, MJ, kJ, TJ, Btu, kBtu, kWh, MWh, therm);
  - gas volume (scf, Mscf/Mcf, MMscf/MMcf, kscf, Sm³, Nm³, m³, ksm3, mmsm3, cf, ft3);
  - liquid volume (gal, bbl, kbbl, Mbbl, MMbbl, L, m³);
  - mass (g, kg, tonne, t, lb, short ton, long ton);
  - counts and days.
- 0 oracle failures in 13 Tier 1/2 families (35,968 rows). This includes the HHV bases (Btu/scf, Btu/gal, kBtu/short ton), all 24 custom-factor unit shapes and well-year proration.
- Tier 3 flaring, blowdown, completions, unloading, AGR, stoichiometry, glycol dehydrators and fugitives are unit-invariant across every T/P/volume/rate unit they accept.
- Validation is good: negative or non-numeric quantities, missing units, bare "ton", unknown units, processes and factors, Scope 2 processes, invalid dates, factor/process mismatches and cross-dimension units are refused with clear reasons.

What does not work: 10 calculation or validation defects that change stored emissions (F1 to F10), plus 9 UI, import-flow and usability issues (F11 to F19).

## 2. Method

* **Dataset** (`audit/scope1_100k/data/scope1_audit_100k.csv`, 22 MB, 89 columns):
  - Built by `gen.py`. It is deterministic (seed 20261001) and regenerates the same file (MD5 `619b5c5c…`).
  - Every row is unique. The `source_ref` and `equipment_id` are unique, and the data cells are unique even ignoring those two IDs (both asserted).
  - "Other data" also varies:
    - 12 facilities (apostrophes, accents, upper/lower case, padding);
    - 5 date formats;
    - process keys and labels;
    - 23 spellings of the tier;
    - plain, scientific and thousands-separated numbers.
* **Families.** 31 families:
  - Tier 1: 42,000 rows;
  - Tier 2: 22,000;
  - Tier 3: 31,000;
  - invalid or ambiguous rows: 5,000.

  Per-family results are in §5.
* **Three kinds of expectation** (`data/expected.jsonl.gz`, one line per row):
  1. **Oracle.** Expected CO₂/CH₄/N₂O are computed with an independent unit table (NIST and API Compendium constants). Only catalog factor *values* are read from the app. Tolerance is 1e-4 relative.
  2. **Metamorphic group.** Rows describe the same physical activity in different units or spellings, at a known scale k. Emissions divided by k must be equal (spread ≤ 1e-4). This is how the Tier 3 engineering methods were tested without re-implementing them.
  3. **Must refuse / ambiguous.** The row should be refused, and the reason class is recorded.
* **Runs.** Each run used a fresh SQLite database with an admin user, 12 facilities and 24 custom factors (`harness.py`), on the real Flask app (`serve.py`):
  - API run: `api_upload.py` (port 5001).
  - UI run: `ui_upload.mjs` against the Vite dev server and the backend on 5000. It used the wizard with *Both Tiers — Auto Detect*, all processes, auto-mapped columns and no overwrite.
* **Checks.**
  - `check.py`: database vs expectations, and field fidelity (period, facility, quantity, unit, status, factor_source, equipment, CO₂e = CO₂ + 28·CH₄ + 265·N₂O).
  - `ui_table.mjs` and `ui_compare.py`: UI table vs database.
  - `probes.py`: a two-row reproduction of every finding.

## 3. Findings

Severity:
- **High** — wrong emissions stored silently, at scale.
- **Medium** — wrong emissions or metadata in specific cases, or a misleading result.
- **Low** — clean refusal or usability issue.

### F1 · High · Tier 3 combustion with a site HHV and no gas analysis stores **CO₂ = 0**

**Evidence.**
- 1,390 of 1,390 rows (`T3_COMB` "HHV × catalog factor" rows) have CO₂ = 0. Stored total is 17,604 tCO₂e against 401,737 expected.
- Probe P01: 1,000 Mscf of natural gas, HHV 1,020, CE 99.5 % → CO₂ 0.000 t, CO₂e 0.056 t. The same gas at Tier 1 gives 54.1 t (ratio 0.001).
- UI screenshot `06_ui_T3_combustion_CO2_zero.png`: 198,768 Sm³ of natural gas, CO₂ 0.000 t; expected 362.1 t.

**Root cause.**
- `dispatcher._composition()` (`calculations/dispatcher.py:331`) always returns `c1 = 0.0`.
- `CombustionCalculator` (`calculations/combustion.py:275`) tests `"c1" in comps and comps["c1"] not in [None, "", "-"]`. That is true for `0.0`, so the carbon balance runs on zero carbon and overwrites the factor-based CO₂.
- The guard added for "Tier 3 browser test #10" lets this path through precisely because the catalog factor counts as a "measured factor".

**Reach.** The manual form takes the same path: Tier 3 "Fuel analysis" with a base factor and no gas analysis.

**Fix.** Run the carbon balance only when the composition contains carbon (`any(comps[cN] > 0)`).

### F2 · Medium · Tier 3 combustion of **Coke Oven Gas** is refused

**Evidence.** 427 rows were refused with "Activity unit 'mscf' needs the fuel density to use a heating value tabulated per short_ton" (probe P02).

**Root cause.**
- The Tier 3 branch passes `fuel_type = flat_inputs["fuel_type"]` (`dispatcher.py:918`), which is the fuel *name*.
- `fuel_basis()` then keyword-matches "coke" as a solid.
- The Tier 1 branch uses the catalog `type` (`gases`) and works.

**Fix.** Use `emission_factors["type"]` and `factor_hhv_unit()` in the Tier 3 branch, as Tier 1 does.

### F3 · High · Tier 3 tank throughput: every unit except m3, gal and L is read as **bbl**

**Evidence.**
- `kbbl` and `Mbbl` rows are 1,000× low: 454 rows, 354 groups failed (screenshot 07, probe P03).
- Non-volume units are accepted as bbl: tonne, kg, MMBtu and scf (201 rows that must be refused; probe P04: 5,000 tonne → 148 tCO₂e).

**Root cause.** The `else: throughput_bbl = raw_throughput  # bbl` fallback (`dispatcher.py:1567`).

**Fix.** Use `units.unit_dimension` and refuse anything that is not a liquid volume.

### F4 · High · Tier 3 pneumatic bleed rate: only the exact string `m3` is converted

**Evidence.**
- `M3`, `m³`, `Sm3` and `m3/hr` are read as scf, so emissions are 35.3× low: 651 rows, 484 groups failed (screenshot 08, probe P05).
- `lb/hr`, `kg/hr` and nonsense units are accepted as scf (208 rows that must be refused; probe P06).

**Root cause.** `flat_inputs.get("pneu_bleed_unit", "scf") == "m3"` (`dispatcher.py:1633`).

**Fix.** Parse with `parse_volume_rate` and refuse unknown or non-volume units.

### F5 · High · Tier 3 associated-gas vent rate in **Mcf/day** is read as scf/h

**Evidence.** 152 rows and 152 groups are 41.7× low (0.024; screenshot 09, probe P07: 24 Mcf/day stored as 24 scf/h). Any unlisted rate unit falls through the same way.

**Root cause.** `else: rate_scfh = r_val` (`calculations/vented.py:2462`).

**Fix.** Use `parse_volume_rate` and refuse unknown units.

### F6 · Medium · `Mt` / `MT` / `mt` accepted as a metric tonne

**Evidence.** 202 rows accepted (probe P08: "1 Mt" of coal = 1 tonne). "Mt" is the SI symbol for a megatonne, so this is a silent 10⁶ error.

**Root cause.** `units.py:245` (`"mt": 1000.0`) after lower-casing.

**Fix.** Refuse `Mt`/`mt` as ambiguous (keep `MT`, if you decide it means metric ton, case-sensitively).

### F7 · Medium · Unknown pressure / temperature units are silently assumed psig / °C

**Evidence.**
- 199 rows with `kg/cm2`, `inHg`, `mmHg` or `torr`, and 206 rows with `centigrade`, `deg` or `Celsius degrees`, were all accepted.
- Probe P09: 10 kg/cm² read as 10 psig. Emissions came out at 17 % of the correctly converted reference (0.174×).

**Root cause.** The fallbacks in `to_psia` (`units.py:148`) and `to_kelvin` (`units.py:96`).

**Fix.** Raise `UnitError` on unknown units, as the volume parser already does.

### F8 · Medium · A quantity cell that carries a unit ("928 m3") is accepted with the unit column's unit

**Evidence.** 194 rows (probe P11: "928 m3" with `unit=scf` booked as 928 scf).

**Root cause.** `_clean_float` strips trailing units (`background_processor.py:143`).

**Fix.** Refuse the row when the trailing unit differs from the unit column, or refuse any trailing unit text.

### F9 · Medium · Contradicting unit columns: `tank_unit` silently wins over `unit`

**Evidence.** 200 rows (probe P12: `unit=bbl`, `tank_unit=m3`, so 1,000 bbl is booked as 1,000 m³, 6.3×). The stored record says "1,000 bbl".

**Fix.** Refuse the row when the two disagree. `agr_unit`, `blowdown_unit` and `vent_volume_unit` follow the same "method unit wins" lookup (not tested here).

### F10 · Medium · Unloading: the unit silently changes the factor

**Evidence.** 666 rows. Probe P13: "≤10 events/yr", 10 **wells** → 66.2 t (booked with the non-plunger per-well-year factor). The same with 10 events → 115.4 t (screenshot 10).
- A per-event factor with unit `wells` is replaced by the per-well-year factor.
- A per-well-year factor with `events` is replaced by a per-event factor.
- Any other count word (devices, components, completions, pcs, sources, each) is treated as wells.
- The stored record still shows the factor the user chose.

**Fix.** Refuse a count unit that does not match the factor basis.

### F11 · Medium · Tier 3 `hhv_unit` is ignored in the bulk import

**Evidence.** Probe P14: `hhv=37.99`, `hhv_unit=MJ/m3` (= 1,020 Btu/scf) is read as 37.99 Btu/scf. N₂O is 27× low, and so is CH₄ when there is no composition.
- The form converts the unit in the browser (`Scope1Form.jsx:1493-1540`).
- The CSV template documents `hhv` in Btu/scf or Btu/gal only, but the column is accepted and silently ignored.

**Fix.** Convert or refuse `hhv_unit` on the server.

### F12 · Medium · Metadata columns overwritten by method inputs (both paths)

* **Activity.** 1,638 records store the activity-table key (e.g. `wt_gas`) as the business **Activity**.
  - The wizard maps the *Activity* field to the `activity_key` column (substring match; screenshot 02, `ui_wizard_column_mapping.json`).
  - The server mapping does the same (`background_processor.py:1116`, whole-word "activity").
* **Region.** 1,186 records store the unloading basin ("Gulf Coast", "Appalachia" …) as the organisational **Region**, because the same CSV column name `region` is the template's region label and the Tier 2 unloading input (`background_processor.py:2553`). Dashboards grouped by region are affected.

**Fix.**
- Exact-match mapping for metadata fields.
- Rename the unloading input (e.g. `unload_region`).

### F13 · Medium · UI "Export CSV" silently exports 5,000 of 83,147 records

**Evidence.**
- The button requests `limit=all`, and the server caps it at 5,000 (`routes/emissions.py:124`). The toast reads "Exported 5000 records". The comment in the code claims it exports "every matching record".
- The export also has no facility/region column.
- Its Process column shows raw keys (`tank_flashing`).

**Fix.** Use the server-side `/api/emissions/export` stream, or page through the records.

### F14 · Low/Medium · Scope 1 table can show a different page than the pager

**Evidence.**
- Every page or filter change fires **two** identical requests, because `loadEntries()` is called from the effects at `Scope1Form.jsx:166` and `:525`.
- There is no stale-response guard.
- In 150 pages read through the UI, page 94 (another run: pages 100–104) displayed the previous page's rows while the pager showed the next number. 10 rows appeared twice and 10 were never shown.

**Fix.** Drop the duplicate effect, and cancel or ignore stale responses (AbortController or request id).

### F15 · Low · A file over 50,000 rows is refused only after ~80–90 s of processing

**Evidence.** API 79 s, UI 88 s (screenshot 01). No rows are saved, so the refusal itself is correct.

**Root cause.** The row count is already known before the loop (`total_rows`), but the check runs inside it (`background_processor.py:796`).

**Fix.** Refuse at `upload/start`.

### F16 · Low · Inconsistent unit vocabularies between methods (clean refusals)

Valid spellings accepted elsewhere are refused here, each with a clear message:

| Rows | Input | Refused spellings | Example |
|---|---|---|---|
| 937 | Tier 2 AGV oil rate | `bbl/d`, `bpd`, `gal/day` (`bbl/day` works) | |
| 364 | vented gas / dehydrator vent volume | `Nm3` (accepted by every other gas method) | P18 |
| 244 | activity tables | `barrels`, `gallons` | P17 |
| 306 | fugitive leak rate | `kg/day`, `g/hr`, `Mcf/day` | |
| 141 | Tier 3 composition method | `MMcf`, `kscf` (accepted at Tier 1) | |
| 391 | drilling | hours | |

### F17 · Low · Thousands separators accepted in `quantity` but not in method columns

**Evidence.** 53 rows. `vent_volume "12,345.6"` is refused with the misleading "Tier 3 requires either measured vent rate … or total measured vent volume" (P16).

**Fix.** Parse every numeric column with `_clean_float`.

### F18 · Low · Bulk import cannot do Tier 2 "catalog factor + site HHV/density"

**Evidence.** The form offers this Tier 2 mode. The import refuses it with "Custom factor 'Natural Gas' not found" (P15).

**Note.** The UI wizard has no Tier 2 card; only the "Force Custom Factors" select.

### F19 · Low · Other observations

* **Null quantity.** 3,154 engineered records (completions rate × duration, AGV vent rate, fugitive measurement / OGI) are stored with a null quantity, so the table shows "-".
* **Header auto-mapping.** The server maps `operating_hours` → `pneu_hours`, `blowdown_pressure` → `unload_press` and `blowdown_events` → `unload_freq` by whole-word match (`background_processor.py:1154-1158`). No stored value changed in this run, but it is a latent risk.
* **Unloading frequency bands.** Tier 2 unloading picks the Table 6-10 frequency band from the record's event count, without a well count.
* **Modal overlap.** The wizard modal's title is hidden under the top bar at 1600×1000.

## 4. Tooling and reproduction

All tooling is in `audit/scope1_100k/`:

| File | Role |
|---|---|
| `gen.py` | Builds the dataset and expectations (`data/`; part files are written alongside) |
| `harness.py`, `serve.py` | Isolated seeded DB; real Flask server |
| `api_upload.py` | HTTP upload with login, CSRF, status polling and error-CSV download |
| `ui_upload.mjs`, `ui_table.mjs` | Chromium through the wizard and the table (run from `new/client`) |
| `check.py`, `ui_compare.py` | Database vs expectations; UI table and feed vs database |
| `probes.py` | P01–P18 minimal reproductions → `results/probes_result.json` |

```bash
python audit/scope1_100k/gen.py --out /tmp/s1                         # 100k + part1/part2 + expected.jsonl
python audit/scope1_100k/serve.py /tmp/api.db 5001 &                  # fresh seeded server
python audit/scope1_100k/api_upload.py http://127.0.0.1:5001 /tmp/out /tmp/s1/scope1_audit_part1.csv /tmp/s1/scope1_audit_part2.csv
python audit/scope1_100k/check.py --db /tmp/api.db --expected /tmp/s1/expected.jsonl --csv /tmp/s1/scope1_audit_100k.csv --report /tmp/r.json
python audit/scope1_100k/probes.py                                    # 18 probes, ~1 s
# UI: backend on :5000 (serve.py), `npx vite` in new/client, then from new/client:
ADMIN_EMAIL=audit.admin@ghg.test ADMIN_PASSWORD='Audit-Passw0rd!2026' OUT_DIR=/tmp/ui node ../../audit/scope1_100k/ui_upload.mjs /tmp/s1/scope1_audit_part1.csv
```

Results are in `audit/scope1_100k/results/`:
- check summaries: API and UI are identical;
- the full UI check, gzipped;
- UI table vs DB;
- upload job outcomes;
- the UI column mapping;
- 10 screenshots.

## 5. Per-family results (UI run; the API run is identical)

| Family | Rows | Saved | Refused | Oracle checked / failed | Groups checked / failed | Unexpected refusals | Should-refuse accepted |
|---|---|---|---|---|---|---|---|
| T1_COMB | 16,000 | 8,824 | 7,176¹ | 8,824 / 0 | 2,474 / 0 | 0 | 0 |
| T1_MOBILE | 2,000 | 1,061 | 939¹ | 1,061 / 0 | 304 / 0 | 0 | 0 |
| T1_FLARE | 4,000 | 4,000 | 0 | 4,000 / 0 | 800 / 0 | 0 | 0 |
| T1_VENT | 1,500 | 1,500 | 0 | 1,500 / 0 | 300 / 0 | 0 | 0 |
| T1_AGV | 2,500 | 2,500 | 0 | 2,500 / 0 | 500 / 0 | 0 | 0 |
| T1_COMPL | 1,500 | 1,500 | 0 | 1,500 / 0 | – | 0 | 0 |
| T1_UNLOAD | 2,000 | 2,000 | 0 | 1,334 / 0 | 667 / 0 | 0 | 0 (666 ambiguous accepted, F10) |
| T1_CHEM | 3,000 | 3,000 | 0 | 3,000 / 0 | 600 / 0 | 0 | 0 |
| T1_DRILL | 1,000 | 609 | 391 | 609 / 0 | 233 / 0 | 0² | 0 |
| T1_COMPONENT | 4,000 | 4,000 | 0 | 4,000 / 0 | 1,333 / 0 | 0 | 0 |
| T1_ACTIVITY | 3,500 | 3,256 | 244 | – | 1,109 / 0 | 244 (F16) | 0 |
| T1_TANK | 1,000 | 1,000 | 0 | 1,000 / 0 | 200 / 0 | 0 | 0 |
| T2_CF | 16,000 | 13,715 | 2,285¹ | 13,715 / 0 | 2,005 / 0 | 0 | 0 |
| T2_COMPL | 1,500 | 1,500 | 0 | – | 500 / 0 | 0 | 0 |
| T2_UNLOAD | 1,500 | 1,500 | 0 | – | 750 / 0 | 0 | 0 |
| T2_AGV | 1,500 | 563 | 937 | – | 182 / 0 | 937 (F16) | 0 |
| T2_FUG | 1,500 | 1,500 | 0 | – | 750 / 0 | 0 | 0 |
| T3_COMB | 6,000 | 5,432 | 568 | 1,390 / **1,390** (F1) | 1,390 / 0 | 568 (427 F2, 141 F16) | 0 |
| T3_FLARE | 3,500 | 3,500 | 0 | – | 700 / 0 | 0 | 0 |
| T3_COMPL | 2,500 | 2,500 | 0 | – | 714 / 0 | 0 | 0 |
| T3_UNLOAD | 2,000 | 2,000 | 0 | – | 667 / 0 | 0 | 0 |
| T3_BLOW | 3,000 | 3,000 | 0 | – | 600 / 0 | 0 | 0 |
| T3_TANK | 2,500 | 2,500 | 0 | – | 500 / **354** (F3) | 0 | 0 |
| T3_PNEU | 2,000 | 2,000 | 0 | – | 500 / **484** (F4) | 0 | 0 |
| T3_AGR | 2,000 | 2,000 | 0 | – | 500 / 0 | 0 | 0 |
| T3_DEHY | 1,500 | 1,281 | 219 | – | 375 / 0 | 219 (F16) | 0 |
| T3_FUG | 2,000 | 1,694 | 306 | – | 666 / 0 | 306 (F16) | 0 |
| T3_STOICH | 1,500 | 1,500 | 0 | 1,500 / 0 | 300 / 0 | 0 | 0 |
| T3_AGV | 1,500 | 1,447 | 53 | – | 497 / **152** (F5) | 53 (F17) | 0 |
| T3_VENTGAS | 1,000 | 855 | 145 | 855 / 0 | 250 / 0 | 145 (F16) | 0 |
| NEG | 5,000 | 1,410 | 3,590 | – | – | 0 | **409** (F3, F4) + 1,001 ambiguous accepted (F6–F9) |

¹ Expected refusals: physical units of the wrong phase or dimension for the fuel (e.g. gas fuel in gallons, coal in m³), or a custom factor applied to the wrong dimension. All were refused with clear reasons.
² Drilling activity given in hours is refused ("drilling days"). The audit accepts either a conversion or a refusal here.

## 6. Fixes and re-run (2026-10-01)

Every finding is fixed. One more defect found while fixing F5 is also fixed (F20).

### 6.1 Fixes

| ID | Fix | Where |
|---|---|---|
| F1 | The carbon balance runs only when the gas analysis contains hydrocarbons. Without one, CO₂ comes from the factor and the site HHV. | `calculations/combustion.py` |
| F2 | Tier 3 takes the HHV basis from the catalog factor (type, `hhv_unit`), as Tier 1 does. The density is passed through as well. | `calculations/dispatcher.py` |
| F3 | Tank throughput goes through the shared unit table (kbbl, Mbbl, gal, L, m³ …). Gas volumes, masses, energies and unknown units are refused. | `dispatcher._liquid_bbl` |
| F4 | The bleed rate goes through the shared volume-rate parser (`scf`, `scf/hr`, `m3`, `m³`, `Sm3`, `m3/hr`, `scfm` …). Mass rates and unknown units are refused. | `units.volume_rate_m3_per_hour`, dispatcher |
| F5 | The vent rate goes through the same parser (`Mcf/day`, `MMscfd`, `m3/h` …). Unknown rate or duration units are refused. | `calculations/vented.py` |
| F20 | **New:** the Tier 3 associated-gas venting time defaulted to *days* in the dispatcher (24× high for files without `duration_unit`). It now defaults to hours, as the form and calculator do. | dispatcher |
| F6 | `Mt` / `MT` / `mt` is refused as ambiguous: "write 'tonne'". This applies to manual, bulk and JSON import. | `services/scope1_calc.validate_activity` |
| F7 | Unknown temperature or pressure units raise an error. `mmHg`, `torr`, `inHg` (absolute) and `centigrade` were added. `kg/cm2` (gauge or absolute?) and "deg" are refused. | `calculations/units.py` |
| F8 | A unit written inside the quantity cell must match the unit column, or the row is refused. | `background_processor._process_row` |
| F9 | Contradicting `unit` / `tank_unit` (also `blowdown_unit` and `agr_unit` when the volume is the record quantity) are refused. Two representations of the same activity are still accepted, e.g. the form's converted bbl at top level plus m³ in `calc_inputs`, as in stored records. The tank form now sends the converted bbl in both places. | `dispatcher._method_unit`, `legacy_engine`, `Scope1Form.jsx` |
| F10 | Unloading: a per-event factor needs `events`, a per-well-year factor needs `wells`, and other count words are refused. | dispatcher |
| F11 | `hhv_unit` (MJ/m3, kcal/m3, Btu/gal, MJ/kg, GJ/…) is converted on the server at Tier 1, 2 and 3. Unknown units are refused. | `combustion.user_hhv` |
| F12 | Generic words (`activity`, `region`, `hours`, `pressure`, `events`, `gor` …) map only an identical header, on both the server and the client. For unloading and associated-gas rows, `region` is the basin and the record keeps the facility region. | `background_processor`, `utils/importMapping.js` |
| F13 | Export CSV pages through every matching record (5,000 per request). Region / Facility was added, and Group and the process label are fixed. | `Scope1Form.jsx` |
| F14 | One request per page or filter change; a stale response is ignored. | `Scope1Form.jsx` |
| F15 | CSV rows are counted before processing; a file over 50,000 rows is refused immediately. | `background_processor` |
| F16 | Shared vocabularies: `bbl/d`, `bpd`, `gal/day`; GOR units parsed (unknown refused, it was read as scf/bbl); `Nm3`, `MMcf`, `kscf` in every gas method; `barrels`, `gallons`, `litre` in the activity tables; leak rates in g/hr, kg/day, Mcf/day …; drilling time in hours converted to days. The Tier 1 associated-gas oil unit no longer falls back to bbl. | units, vented, vented_gas, activity_factors, fugitive_onshore, dispatcher |
| F17 | "12,345.6" in any column of a comma CSV is read as 12345.6. | `background_processor` |
| F18 | Tier 2 "catalog fuel + site HHV / density" is accepted in bulk. The wizard has a Tier 2 card, and templates take `tier=2`. | `background_processor`, wizard, `routes/emissions.py` |
| F19 | Engineered records store the activity the method used: flowback scf, vented scf, leakers, measured hours. The wizard modal sits above the top bar. Server header aliases were removed (F12). | `services/scope1_calc.apply_result`, CSS |

**Tests.**
- 53 regression tests in `new/server/tests/test_s1k_bulk_100k_audit_2026_10_01.py`.
- 2 in `new/client/src/__tests__/importMapping.test.js`.

Results:
- Backend: 2,082 passed, 1 skipped. `test_performance.py` needs `pytest-benchmark`, which is not installed here; it errors the same way before the fixes.
- validation: 128 passed.
- vitest: 40 passed.
- ESLint: 0 errors.
- `npm run build`: OK.

### 6.2 Re-run of the same 100,000 rows

The dataset is unchanged: it regenerates byte-identical, MD5 `619b5c5c…`. Expectations changed only where a refused spelling is now supported (`litre`, `centigrade`, `mmHg`/`torr`/`inHg` → "either").

| | Before | After |
|---|---|---|
| 100k file | refused after 79 s (API) / 88 s (UI) | refused up front: 3.3 s (API) / ~10 s (UI, including navigation) |
| Saved / refused | 83,147 / 16,853 | 84,351 / 15,649 |
| API vs UI database | identical | identical, including the stored payload |
| Oracle checks | 45,398 / 46,788 pass | **47,434 / 47,434 pass** |
| Unit-equivalence groups | 19,376 / 20,366 pass | **20,830 / 20,830 pass** |
| Must-refuse rows accepted | 409 | **0** |
| Ambiguous rows accepted | 1,667 | **0** (1,897 / 1,897 refused) |
| Valid rows refused | 2,472 (F2, F16, F17) | **0** |
| Engineered records without quantity | 3,154 | **0** |
| Activity / region metadata overwritten | 1,638 / 1,186 | **0 / 0** |
| UI Export CSV | 5,000 of 83,147 | **84,351 of 84,351** |
| UI table, 150 pages | 1 page showed the previous page (10 duplicate rows) | **0** |
| UI table vs DB / table feed vs DB | 0 mismatches | **0 / 0 mismatches** (1,640 rendered rows; 84,351 feed records) |

Evidence is in `audit/scope1_100k/results/rerun_after_fixes/`:
- check summaries for the API and UI runs;
- UI table vs DB;
- upload jobs and the Export CSV count;
- screenshots, including the record from F1, now at 362.123 tCO₂ (the oracle gives 362.12 t; it was 0.000).

All 18 probes (`probes.py`) now give the expected outcome (`results/probes_result.json`).

