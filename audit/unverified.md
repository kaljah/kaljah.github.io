# Unverified Values, Factors, and Assumptions Register

**Auditor Instruction**: In strict compliance with ABSOLUTE RULE #1, any emission factor, constant, formula parameter, or default value that could NOT be traced to a specific published equation/table in the *API Compendium 2021*, the *GHG Protocol*, *IPCC Guidelines*, or the user's Excel golden cases (`/reference/comprehensive_golden_cases.xlsx`) is cataloged here as **UNVERIFIED** for manual engineering verification.

---

## 1. Unverified Factors and Constants Inventory

| Item ID | Code File & Line | Parameter / Constant | App Value | Purported Source | Reason Unverified / Action Required |
| :--- | :--- | :--- | :---: | :--- | :--- |
| **UNV-01** | `emission_factors_chapter7_onshore.py:142` | Gas Header Fugitive Rate | `0.0450 kg/hr/node` | Internal Sonatrach Field Survey (2018) | Not found in API Compendium Table 7-11 or EPA Table W-1A. User must confirm whether this was derived from field-specific LDAR measurements. |
| **UNV-02** | `routes/scope2.py:412` | Algeria Residual Grid Mix Factor | `0.4500 kg CO2e/kWh` | Regional Grid Default | No official Sonelgaz or CREG residual mix certification is cited in `/reference/`. Must verify against official Sonelgaz 2024 annual sustainability report. |
| **UNV-03** | `calculations/vented_mud.py:78` | Drilling Mud Gas Desorption Curve | Polynomial $f(P, T)$ | Operator Empirical Equation | Compendium Table 6-7 specifies fixed gas-oil ratio (GOR) degassing ranges. The polynomial function has no provenance citation in the code comments. |
| **UNV-04** | `routes/reports_cbam.py:88` | CBAM Embedded Direct Emissions Benchmark | `1.85 tCO2e/t H2` | EU CBAM Draft Annex IV (2023) | Derived from EU draft transitional rules. User must verify whether updated 2026 definitive CBAM benchmark values are required. |
| **UNV-05** | `calculations/flare_defaults.py:65` | Crosswind Flare Efficiency Decay | $0.98 \times (1 - 0.015 W)$ | Experimental wind-tunnel report | Not specified in API Compendium Section 5.1.2 (which assumes constant 98% destruction efficiency unless pilot is snuffed). |
| **UNV-06** | `calculations/indirect.py:90` | Default Steam Boiler Efficiency | `0.80 (80%)` | Code comment: "EPA Hub Table 7" | EPA GHG Emission Factors Hub uses 80% as nominal boiler efficiency. Not in API Compendium (which utilizes 82% in Exhibit 8.3). |
| **UNV-07** | `calculations/indirect.py:91` | Default Steam Transmission Loss | `0.00 (0%)` | Code comment: "Default 0%" | Compendium Exhibit 8.3 assumes 10% line loss. App defaults to 0% if unspecified by user, potentially undercounting upstream fuel burn by ~10%. |
| **UNV-08** | `calculations/fugitive_other.py:112` | Refrigerant HFC-134a 20-yr GWP | `3,790` | IPCC AR5 | AR5 Chapter 8 Table 8.A.1 cites 3,710 for HFC-134a (20-yr horizon) without climate-carbon feedbacks, or 3,790 with feedbacks. The code does not document the feedback basis. |

---

## 2. Methodology Gap Notes

1. **Offshore Flaring Wind-Loss**:
   - Section 5.1.2 of the API Compendium assumes standard flares operate at 98% destruction efficiency $\eta_d$ and 96.5% combustion efficiency $\eta_c$. Any wind-speed decay parameter should be documented with a reference to the specific flare manufacturer test curve or field testing protocol.
2. **Boiler Efficiency Defaults**:
   - The discrepancy between the app's default (80%) and the Compendium Exhibit 8.3 example (82% boiler, 10% transmission loss) should be formalized in the application's configuration options so verifiers can clearly see the methodology selected.
