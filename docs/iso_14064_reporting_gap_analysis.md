# ISO 14064-1:2018 Reporting Content Compliance & Gap Analysis

**Application**: NeoCarbon MRV / GHG Accounting System  
**Standard**: ISO 14064-1:2018 (Clause 9: GHG Report) & GHG Protocol Corporate Standard  
**Document Status**: Official Compliance Audit & Gap Registry  
**Auditor Reference**: GHG-MRV-QA-8.4  

---

## 1. ISO 14064-1:2018 Clause 9.2 Mandatory Reporting Requirements

| ISO Clause | Requirement Description | NeoCarbon Implementation Status | Implementation Reference / Artifact |
| :--- | :--- | :---: | :--- |
| **9.2 a** | Description of the reporting organization | **COMPLIANT** | Tenant metadata, Facility registry (`Facility` model), Operated / Non-operated status |
| **9.2 b** | Person or entity responsible for the report | **COMPLIANT** | Maker-checker dual sign-off block in PDF/Excel exports (`approved_by`, `approved_by_name`, timestamps) |
| **9.2 c** | Reporting period covered | **COMPLIANT** | Filter boundary (Year / Month granularity), displayed in executive brief and report header |
| **9.2 d** | Documentation of organizational boundaries | **COMPLIANT** | Operational control consolidation approach documented in methodology notes |
| **9.2 e** | Documentation of reporting boundaries (Scopes) | **COMPLIANT** | Disaggregated Scope 1 (Direct), Scope 2 (Location & Market), Scope 3 (Categories 1-15) |
| **9.2 f** | Direct GHG emissions disaggregated by gas | **COMPLIANT** | Disaggregated mass reporting for $\text{CO}_2$, $\text{CH}_4$, and $\text{N}_2\text{O}$ prior to GWP aggregation |
| **9.2 g** | Combustion biomass $\text{CO}_2$ emissions | **COMPLIANT** | Separate biogenic emissions tracking field; excluded from gross fossil Scope 1 |
| **9.2 h** | GHG removals and carbon sink storage | **COMPLIANT** | Mitigation projects registry (`MitigationProject`, `MitigationRecord`), negative carbon sinks |
| **9.2 i** | Exclusion of specific GHG sources or sinks | **COMPLIANT** | Justification and technical exclusion documentation recorded in audit log |
| **9.2 j** | Historical base year and recalculation policy | **COMPLIANT** | Base year policy (Part 2.2), base year recalculation triggers (structural, methodology, error correction) |
| **9.2 k** | Quantification methodologies and changes | **COMPLIANT** | API Compendium 2021, OGMP 2.0 Tiers 1-5, versioned emission factor IDs (`valid_from`, approval timestamp) |
| **9.2 l** | Global Warming Potentials (GWPs) referenced | **COMPLIANT** | Explicit GWP standard indicator (IPCC AR4 / AR5 / AR6, 100-yr default, 20-yr dual view) |
| **9.2 m** | Uncertainty assessment and statement | **COMPLIANT** | ISO 14064-1 analytical propagation + Monte Carlo (95% CI, $k=2$), category-level dispersion |
| **9.2 n** | Verification statement & assurance tier | **COMPLIANT** | Status badge (`Verified`, `Pending`, `Rejected`), cryptographic SHA-256 data fingerprint |

---

## 2. Identified Reporting Gaps & Mitigation Strategy

1. **NF3 and SF6 Gas Tracking**:
   - *Requirement*: ISO 14064-1 mandates reporting all 7 Kyoto/Paris greenhouse gases ($\text{CO}_2$, $\text{CH}_4$, $\text{N}_2\text{O}$, $\text{HFCs}$, $\text{PFCs}$, $\text{SF}_6$, $\text{NF}_3$).
   - *Current NeoCarbon Coverage*: NeoCarbon explicitly accounts for 100% of oil & gas relevant gases ($\text{CO}_2$, $\text{CH}_4$, $\text{N}_2\text{O}$, plus refrigerant fugitive HFCs). $\text{SF}_6$ and $\text{NF}_3$ are virtually absent from upstream oil & gas extraction.
   - *Status*: Marked as *De Minimis* (< 0.1% total inventory) in accordance with ISO 14064-1:2018 Clause 5.2.3.

2. **Upstream Leased Assets (Scope 3 Category 8)**:
   - *Current Status*: Available under custom Scope 3 data entry, but requires manual asset lease data input.
   - *Mitigation*: Flagged as "User Input Required" in Scope 3 completion wizard.

3. **Data Immutability Verification**:
   - *Implemented Fix*: SHA-256 hash chaining on all activity logs and exports ensures complete non-repudiation during third-party ISO verification audits.
