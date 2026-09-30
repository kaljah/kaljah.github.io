# BUG-XXX — Uncertainty dashboard applies max(u_CO2, u_CH4, u_N2O) to each record's total CO2e instead of CO2e-weighting the per-gas uncertainties

**Status:** Confirmed
**Severity:** High
**Category:** Uncertainty
**Discovered by:** Agent G (Uncertainty Auditor)

## Location
`new/server/routes/dashboard.py` `_query_uncertainty.get_ef_uncertainty()` (~L2433-2446): `valid_u = [u_co2,u_ch4,u_n2o]` → `return max(valid_u)`. The result is applied to `co2e_total`.

## Reproduction
1. As admin, POST one `stationary_combustion` / Natural Gas / 12000 m3 / factor_source=default record for year 2043.
2. GET `/api/dashboard/uncertainty?year=2043`.
Script: `audit/repro/<ID>.py`.

## Input
The stored record uncertainties (1σ) are CO2 0.0559, CH4 0.1118 and N2O 0.1118. CO2 makes up 99.897 % of the record's CO2e.

## Expected
Weight the per-gas uncertainty by each gas's CO2e contribution. Activity data (±10 % @95 %) is common to all gases. The EFs are CO2 ±5 %, CH4 ±20 % and N2O ±20 % (95 %). Hand calculation: U95 = 2·√((0.05·E)² + Σ(u_EF,g·E_g)²)/E = **±11.18 %**.

## Actual
The dashboard shows **±22.36 %**. This is 2× the expected value: the CH4 value of 0.1118 was applied to 100 % of the CO2e. Each top contributor is also labelled ±22.4 %.

## Evidence
The repro prints the expected and actual values. In the snapshot DB, 110 rows store (0.05, 0.20, 0.20). For those rows the CO2-dominated CO2e is assigned a 1σ of 0.20 instead of about 0.05, which is a 4× overstatement.

## Root Cause
The gases are aggregated without CO2e weighting. The docstring says "use max of those (conservative)". That is not IPCC Approach 1 propagation.

## Impact
Category and inventory uncertainty are overstated by 2 to 4× for every combustion and flaring category whose CH4 and N2O uncertainty exceeds its CO2 uncertainty. This is almost all of them. Categories are pushed into the "medium"/"high" level and the tier breakdown is distorted, because tier classification uses the same inflated `u`. The same inflated number appears on the Uncertainty page, in its CSV export and in the PDF report.

## Affected Components
`/api/dashboard/uncertainty` (JSON + CSV), `UncertaintyAssessment.jsx` (badge, levels, tier cards), `ModernReportGenerator.js`.

## Recommended Fix
Per record: u_rec = √((u_AD·E)² + Σ_g (u_EF,g · GWP_g · m_g)²) / E. At minimum use Σ_g u_g·E_g,CO2e combined in quadrature, not the max. This requires the per-gas CO2e amounts, which are already stored as co2/ch4/n2o_emissions.
