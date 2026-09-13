# Numerical Methods & Mathematical Logic Remediation Plan

Application of drop-in verified mathematical fixes for all 8 findings identified during the exhaustive numerical audit of calculation logic, data transformations, and mathematical invariants.

---

## Scope of Changes

### 1. Unit & Dimensional Precision (`new/server/calculations/units.py`)
- **Mscf / Mcf / MMscf Invariant Registry**: Expand `CONVERSIONS` with bidirectional definitions for `mscf_to_m3`, `m3_to_mscf`, `mcf_to_m3`, `m3_to_mcf`, `mmscf_to_scf`, `scf_to_mmscf`, and align high-precision physical constants ($0.028316846592\text{ m}^3/\text{scf}$) to prevent round-trip drift.

### 2. Conservation of Mass in Midstream Dehydration (`new/server/calculations/midstream.py`)
- **Dehydrator Combustion $\text{CO}_2$ Product**: When regenerator still vent or flash tank stream is routed to thermal destruction (`flare`, `combustor`, `thermal_oxidizer`), compute the stoichiometric conversion of oxidized methane to carbon dioxide:
  $$\text{CO}_{2,\text{combusted}} = \text{CH}_{4,\text{combusted}} \times \left(\frac{44.01}{16.04}\right)$$
- Propagate Tier-aware uncertainty for generated $\text{CO}_2$, update `total_co2e`, and return `co2=co2_res`.

### 3. Dashboard KPI Normalization & Boundary Invariants (`new/server/routes/dashboard.py`)
- **Gas Production Normalization**: In `_query_intensity_stats`, add explicit branch for `g_unit == "mmscf"` scaling `gas *= 1000.0` (Mscf) and `gas_m3 = gas * 28316.8` ($\text{m}^3$), eliminating $1,000\times$ BOE deficit and artificial intensity spikes.
- **Flaring Volume Normalization**: In `_query_intensity_stats`, add `elif unit == "mmscf": qty *= 28316.8` ($\text{m}^3$), eliminating $28,316.8\times$ under-reporting of flaring volume.
- **IEEE 754 Floating-Point Regularization**: Round `methane_loss_rate_pct` and `flaring_rate_pct` to 4 decimal places to prevent $\epsilon \approx 10^{-16}$ float drift triggering false positive regulatory warnings.
- **Segment-Aware OGMP Target Status**: In `pathway_status` and `ogmp_target_status`, replace hardcoded `0.20` with segment-specific `ogmp_target` ($0.20\%$ upstream, $0.05\%$ midstream).
- **SBTi Zero-Actual Preservation**: In `get_sbti_trajectory`, preserve valid reporting periods where actual emissions reached $0.0\text{ tCO}_2\text{e}$ by testing candidate year membership rather than filtering `v > 0`.

### 4. Reconciliation Domain Edge-Case Safety (`new/server/routes/data.py` & `new/server/routes/satellite.py`)
- **Non-Detection Variance Suppression**: When `bottom_up > 0` but `top_down == 0.0` (baseline/non-detection), set `variance_pct = None` and `variance_flag = False` to prevent spurious $-100.0\%$ failure flags.

---

## Verification Plan

### Automated Tests
- Run `pytest tests/ -v` to ensure zero regression across all existing 105 tests.
- Add regression tests in `tests/test_audit_remediation.py` specifically targeting:
  - `mmscf` gas production and flaring volume scaling in intensity stats.
  - Midstream dehydrator stoichiometric $\text{CO}_2$ combustion output.
  - Midstream $0.05\%$ OGMP compliance classification.
  - Non-detection top-down zero survey variance behavior.
  - SBTi trajectory selection with zero actuals.
  - High-precision unit conversions (`mscf_to_m3`, `m3_to_mscf`).

### Frontend Production Build
- Run `npm run build` in `new/client` to verify seamless client-side compilation.
