# Human Review & Domain Expert Governance Gates

**Platform**: Greenhouse Gas (GHG) Accounting, MRV & Reporting Platform  
**Document**: Human Review Required Register  
**Compliance Standard**: ISO 14064-1 §9, GHG Protocol Corporate Standard Ch. 10  
**Purpose**: Transparently catalog all items that cannot be delegated to automated mathematical testing and require mandatory verification by domain experts, corporate GHG accountants, and environmental engineers.

---

## 1. Domain Expert Review Register

| Item ID | Category | Subsystem | Domain Issue / Ambiguity | Automated Stance | Mandatory Human Review Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **HRG-001** | Inventory Boundary | Scope 1 / Scope 2 | Organizational boundary consolidation (Operational Control vs Equity Share). | System defaults to facility-level Operational Control. | Corporate Sustainability Officer must confirm whether equity-share joint ventures require fractional attribution. |
| **HRG-002** | Emission Factors | Tier 2 Custom Factors | `custom_factors.csv` contains synthetic benchmark values (e.g., Factor 0: $\text{CO}_2=144.56$). | System validates numerical non-negativity and units. | Chief Environmental Engineer must certify that active custom factors match accredited laboratory gas chromatography reports or supplier EPDs. |
| **HRG-003** | Scope 3 Method | Categories 1–15 | Scope 3 calculations use generic activity $\times$ EF and spend EEIO models. | System applies `compute_scope3_co2e` with unit normalization. | Carbon Accounting Lead must verify boundary definitions (e.g., distinguishing Cat 4 Upstream Transportation from Cat 9 Downstream Distribution). |
| **HRG-004** | Flaring Efficiency | Flaring (API §5.2) | Offshore/high-wind cross-flow efficiency degradation. | System applies static flare lookup ($\eta=0.98$ for elevated, $\eta=0.995$ for enclosed). | Operations Engineer must audit flaring records against continuous optical flare monitoring (OGI) where wind speeds exceed 5 m/s. |
| **HRG-005** | Dehydrators | Midstream (API §6.6) | Glycol stripping gas volumes and flash separator recycling. | System calculates TEG Henry's law methane solubility. | Midstream Process Engineer must confirm whether nitrogen or fuel gas is used for stripping in regenerator columns. |
| **HRG-006** | AGR Tail Gas | Midstream (API §6.5) | Claus SRU thermal destruction vs Acid Gas Injection (AGI). | System applies stoichiometric methane combustion for Claus and total capture for AGI. | Facility Engineer must confirm control technology configuration (`agi`, `ccus`, `claus`, or `vent`) in facility equipment registry. |
| **HRG-007** | OGMP 2.0 Recon | OGMP Level 4/5 | Facility reconciliation threshold (default 20%). | System flags discrepancy when $|\bar{T} - B| / \bar{T} > 0.20$. | Regulatory Compliance Director must review flagged discrepancies against UNEP IMEO guidance prior to official submission. |
| **HRG-008** | Regulatory GWP | Corporate Reporting | GWP selection across statutory jurisdictions (AR4 vs AR5 vs AR6 vs 20-year). | System uses global `SystemSetting` GWP standard (AR5 default). | Legal & Compliance Counsel must verify statutory GWP requirements for specific regulatory filings (e.g., EU CBAM vs US EPA WEC). |
| **HRG-009** | Uncertainty Model | Statistical QA/QC | Uncorrelated parameter assumption in IPCC Eq. 3.2 summation. | System assumes zero cross-facility covariance ($\text{Cov}(X_i, X_j) = 0$). | Lead Verifier must review whether common fuel supply streams introduce systemic correlated uncertainties across facilities. |
| **HRG-010** | Waste Emissions | EPA Part 99 WEC | Facility exemption status and sales gas threshold definition. | System applies 0.20% sales gas threshold and fee schedule. | General Counsel must verify whether specific facilities qualify for regulatory exemptions under Clean Air Act §136. |

---

## 2. Decision Protocol for Human Review Gates

1. **Pre-Submission Sign-Off**:
   - No GHG emissions inventory report may be marked as "Final Regulatory Submission" while any item in the Human Review Register remains uncertified.
2. **Audit Trail Documentation**:
   - All human overrides, custom factor approvals, and boundary determinations must be logged into `ActivityLog` with the authorized expert's identity and justification note.
3. **Annual Recertification**:
   - The Human Review Register must be re-evaluated annually prior to base-year recalculations and assurance verification.
