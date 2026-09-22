# Phase 49 — Human Review Required

> Audit Date: 2026-09-20  
> Platform: GHG Accounting / MRV Platform  
> Status: These items CANNOT be resolved by automated testing alone  

---

## Introduction

The following items require review by qualified domain experts — GHG methodology specialists, O&G operations engineers, regulatory compliance officers, or IT security auditors — before the platform can be considered production-certified.

Automation has identified these questions. It has NOT invented answers.

---

## HR-01: N2O Default Emission Factor for Flaring

**Category**: Methodology Ambiguity  
**Severity**: MEDIUM  
**Automated finding**: Inconsistency between `FlaringCalculator` (default ef_n2o = 0.0) and `_split_vented_and_flared()` (default ef_n2o = 0.0001 kg/MMBtu).  

**Question for expert**: What is the correct default N2O emission factor for flaring when no site-specific measurement is available?  
- API Compendium 2021 Table 5-3 should be consulted
- Regulatory frameworks (e.g., Alberta AER D007, EPA 40 CFR Part 98 Subpart W) may specify different defaults
- The two defaults must be harmonized to one standard value

**Impact if wrong**: Systematic under- or over-reporting of N2O from flaring  
**Action required**: Confirm correct API 2021 N2O default and update both code paths

---

## HR-02: Mobile vs. Stationary Combustion Boundary

**Category**: Scope Classification  
**Severity**: MEDIUM  
**Automated finding**: Both `mobile_combustion` and `stationary_combustion` route to the same `CombustionCalculator`. No methodological distinction is made at the calculation level.

**Question for expert**: 
1. Are company-owned mobile sources always Scope 1?
2. Are contractor-owned mobile sources Scope 3 Category 4?
3. Does the platform correctly handle the boundary between operated vs. non-operated assets?
4. Does the `process_type` field alone adequately capture this distinction for regulatory reporting?

**Impact**: Incorrect scope assignment leads to materially incorrect inventory categorization  
**Action required**: Define and document organizational boundary rules for mobile sources

---

## HR-03: OGMP 2.0 Level Assignment Methodology

**Category**: OGMP Interpretation  
**Severity**: MEDIUM  
**Automated finding**: `services/ogmp.py` implements level assignment based on measurement type codes. The mapping from survey_type → OGMP level is a business rule.

**Question for expert**:
1. Does the current survey_type → level mapping match OGMP 2.0 framework v2.5 requirements?
2. Is "Satellite (Sentinel-5P/MethaneSAT)" correctly mapped to Level 4 or Level 5?
3. Are the reconciliation thresholds (default 20%) aligned with OGMP 2.0 guidance?
4. Does the platform handle the OGMP reporting year cutoff correctly?

**Impact**: Incorrect OGMP level reporting misrepresents methane management performance  
**Action required**: Review `services/ogmp.py` against OGMP 2.0 Technical Guidance documentation

---

## HR-04: Scope 3 Category Completeness

**Category**: Scope 3 Methodology  
**Severity**: MEDIUM  
**Automated finding**: Scope 3 supports 15 categories in the UI, but only spend-EEIO and physical activity methods are tested in the golden dataset. Category 15 (investments) has no reference implementation.

**Question for expert**:
1. Are all 15 GHG Protocol Scope 3 categories required for reporting?
2. Which categories are material for oil & gas operations?
3. Is the Category 11 (Use of sold products) calculation correct for natural gas?
4. Is Category 3 (Fuel and energy-related activities) double-counting risk managed?

**Impact**: Missing or incorrect Scope 3 categories lead to underreporting of value chain emissions  
**Action required**: Scope 3 category completeness audit by emissions inventory specialist

---

## HR-05: Uncertainty GWP Interaction

**Category**: Methodology Ambiguity  
**Severity**: LOW-MEDIUM  
**Automated finding**: Uncertainty is propagated per-gas (CO2, CH4, N2O individually) using SRSS, then GWP conversion is applied. The question is whether GWP itself has uncertainty and whether that should be propagated.

**Question for expert**:
1. Should GWP uncertainty (e.g., AR5 CH4 GWP = 28 ± 11%) be included in total CO2e uncertainty?
2. ISO 14064-1:2018 §7.5 — does the organization's uncertainty methodology comply?
3. Is the current implementation adequate for third-party verification?

**Impact**: Under-reporting of total CO2e uncertainty could affect confidence intervals on regulatory reports  
**Action required**: Review with ISO 14064-1 qualified verifier

---

## HR-06: Custom Emission Factor Validation Boundary

**Category**: Emission Factor Policy  
**Severity**: MEDIUM  
**Automated finding**: Custom factors can override default API Compendium 2021 factors. The system allows any numeric value to be stored as a custom factor with no validation against published ranges.

**Question for expert**:
1. Should there be bounds-checking on custom factors relative to API Compendium 2021 default ranges?
2. What approval workflow (if any) should be required before custom factors are used in production calculations?
3. Should custom factors require a documented measurement methodology reference?
4. How should historical calculations be handled when a custom factor is updated?

**Impact**: An incorrect custom factor (e.g., wrong units, wrong gas) will produce systematically incorrect emissions without automated detection  
**Action required**: Define custom factor governance policy; consider implementing plausibility bounds

---

## HR-07: CSRF Protection Architecture

**Category**: Security Architecture  
**Severity**: MEDIUM  
**Automated finding**: The entire auth blueprint (`/api/auth/*`) is exempt from CSRF protection. This is due to the cross-origin architecture (GitHub Pages frontend + Render backend), where the SPA cannot share CSRF tokens via traditional cookie paths.

**Question for security architect**:
1. Is `SameSite=None` + `Secure` + HTTPS sufficient CSRF mitigation for the cross-origin SPA architecture?
2. Should the application implement a custom CSRF token mechanism (e.g., double-submit cookie pattern) that works cross-origin?
3. Is the current threat model documented and accepted by the security team?
4. Does this architecture comply with the organization's security policy?

**Impact**: Cross-site request forgery attacks on login/register are theoretically possible from malicious sites, though mitigated by SameSite=None requiring HTTPS  
**Action required**: Security architecture review and documented risk acceptance or mitigation

---

## HR-08: Production Database and Backup Procedure

**Category**: Data Integrity / Operations  
**Severity**: HIGH  
**Automated finding**: The platform uses SQLite (2.3 GB live database). No backup procedure, retention policy, or restore testing was found in the repository.

**Question for operations team**:
1. What is the backup schedule for `ghg_app.db`?
2. Has a restore ever been tested in an isolated environment?
3. Is the WAL journal (`ghg_app.db-wal`, currently 233 MB) regularly checkpointed?
4. For PostgreSQL deployments — what is the backup and point-in-time recovery configuration?
5. Is the 4.1 GB `import_debug.log` intentionally preserved? If so, what is the retention policy?
6. Should the application migrate to PostgreSQL for production to support proper backup, replication, and connection pooling?

**Impact**: Data loss of a 2.3 GB SQLite database with no tested restore procedure is catastrophic for regulatory compliance and audit trail integrity  
**Action required**: Immediate backup procedure implementation and restore testing

---

## HR-09: Regulatory Reporting Standard Compliance

**Category**: Compliance  
**Severity**: HIGH (context-dependent)  
**Automated finding**: The platform implements API Compendium 2021 for oil & gas calculations and OGMP 2.0. Actual regulatory reporting may require alignment with specific national regulations.

**Question for compliance team**:
1. Which regulatory framework governs the primary reporting jurisdiction (Algeria ONHYD? EU ETS? SEC climate disclosure?)?
2. Does the API 2021 methodology align with the jurisdiction's accepted calculation methods?
3. Are the IPCC AR5 GWP values (used as default) acceptable to the primary regulator, or does the regulator require AR4 or AR6?
4. Is third-party verification required, and does the current implementation produce verification-ready documentation?

**Impact**: Using a methodology not accepted by the regulatory authority makes the entire inventory invalid  
**Action required**: Regulatory compliance review by in-country legal/compliance counsel

---

## HR-10: Golden Dataset External Validation

**Category**: Calculation Correctness Assurance  
**Severity**: MEDIUM  
**Automated finding**: The 25 golden test cases in `validation/golden_dataset/golden_cases.json` have expected values that appear to have been independently derived (not from the production calculator). However, there is no documented cross-reference to published worked examples from API, EPA, or IPCC.

**Question for methodology expert**:
1. Have the golden case expected values been verified against published example calculations (e.g., API Compendium 2021 worked examples, EPA GHG Reporting Rule examples)?
2. If not, can they be? At least 2–3 calculations per methodology type should be traceable to an authoritative external source.
3. Are the tolerances (e.g., 1e-4 relative) appropriate for regulatory precision requirements?

**Impact**: If golden cases are internally derived rather than externally referenced, they provide circular validation rather than independent verification  
**Action required**: External validation of at least representative golden cases against published authoritative examples

---

## Summary Table

| ID | Topic | Domain Expert Required | Severity | Blocking Production? |
|---|---|---|---|---|
| HR-01 | N2O flaring default factor | GHG Methodology Specialist | MEDIUM | Yes |
| HR-02 | Mobile combustion scope boundary | GHG/Operations Expert | MEDIUM | Yes |
| HR-03 | OGMP 2.0 level methodology | OGMP Specialist | MEDIUM | Yes |
| HR-04 | Scope 3 category completeness | Emissions Inventory Expert | MEDIUM | Yes |
| HR-05 | GWP uncertainty in CO2e | ISO 14064-1 Verifier | LOW-MEDIUM | No |
| HR-06 | Custom factor governance | GHG Manager / Policy | MEDIUM | No |
| HR-07 | CSRF cross-origin architecture | Security Architect | MEDIUM | Yes |
| HR-08 | Database backup/restore | Operations / DBA | HIGH | **CRITICAL** |
| HR-09 | Regulatory reporting alignment | Compliance Counsel | HIGH | **CRITICAL** |
| HR-10 | Golden dataset external validation | GHG Methodology Specialist | MEDIUM | No |

---

*Document generated: 2026-09-20 | Status: COMPLETE*  
*This document must be reviewed by qualified human experts. Automation cannot substitute for expert judgment on these items.*
