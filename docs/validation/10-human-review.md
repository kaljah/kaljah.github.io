# Mandatory Human Review & Domain Expert Governance Register

**Document**: `docs/validation/10-human-review.md`  
**Classification**: Regulatory Governance & Domain Expert Sign-Off Register  
**Compliance Standard**: ISO 14064-1 §9, GHG Protocol Corporate Standard Ch. 10  
**Evaluation Target**: `kaljah/kaljah.github.io` (`c:\Users\samsung\Desktop\H2`)  
**Audit Date**: September 20, 2026  
**Auditor**: Senior GHG Accounting Specialist & Regulatory Auditor  

---

## 1. Principle of Automated Testing Boundaries

In compliance with Master Audit Specification §55, automated software tests can verify mathematical correctness, numerical stability, and API integrity, but **cannot legally certify domain assumptions, statutory interpretations, or organizational boundaries**.

All ambiguous standards, conflicting methodologies, and custom inputs are explicitly flagged with:
```
HUMAN REVIEW REQUIRED
```
No regulatory disclosure may be officially finalized while any relevant gate remains uncertified by the designated corporate authority.

---

## 2. Mandatory Human Review Gates Register

| Gate ID | Domain Category | Affected Subsystem | Domain Issue / Regulatory Ambiguity | Automated Default Stance | Mandatory Human Review Action & Sign-Off Role |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **HRG-001** | **Inventory Boundary** | Scope 1 / Scope 2 | Consolidation approach (Operational Control vs Financial Control vs Equity Share). Joint ventures with non-operated equity stakes. | System defaults to facility-level Operational Control ($100\%$ attribution). | **Corporate Sustainability Officer (CSO)** must formally review joint venture assets and verify whether equity-share fractional accounting is required for statutory filings. |
| **HRG-002** | **Emission Factors** | Tier 2 Custom Factors | Source validation for factors in `custom_factors.csv` (e.g. custom fuel heating values, composition-based emission factors). | System validates non-negativity, dimension consistency, and uncertainty bounds. | **Chief Environmental Engineer** must certify that active custom factors match accredited laboratory Gas Chromatography (GC) reports or supplier Environmental Product Declarations (EPDs). |
| **HRG-003** | **Scope 3 Boundary** | Categories 1–15 | Distinguishing Category 4 (Upstream Transportation) from Category 9 (Downstream Distribution), and Category 1 (Purchased Goods) from Category 2 (Capital Goods). | System applies generic physical activity and spend EEIO models per user selection. | **Carbon Accounting Lead** must audit procurement category mappings to ensure compliance with the GHG Protocol Corporate Value Chain Standard and prevent double-counting. |
| **HRG-004** | **Flaring Combustion**| Flaring (API §5.2) | Cross-wind and high-velocity efficiency degradation in offshore or open desert flares. | System applies static flare lookup ($\eta=0.98$ for elevated, $\eta=0.995$ for enclosed) per API Table 5-11. | **Operations Safety Engineer** must inspect flare operating logs and audit optical flare monitors (OGI) to verify whether cross-winds exceed 5 m/s, requiring efficiency derating. |
| **HRG-005** | **Dehydrators** | Midstream (API §6.6) | Stripping gas volumes and flash tank gas recycling in triethylene glycol (TEG) regeneration systems. | System applies Henry's Law methane solubility correlation assuming pure TEG. | **Midstream Process Engineer** must confirm whether fuel gas or nitrogen is utilized as stripping gas and certify operating hours of vapor recovery units (VRU). |
| **HRG-006** | **Acid Gas Removal** | Midstream (API §6.5) | Disposition of stripped acid gas: Claus sulfur recovery thermal destruction, Acid Gas Injection (AGI), or direct atmospheric venting. | System models Claus thermal oxidation of methane slip and total geologic sequestration for AGI. | **Facility Process Engineer** must certify that the declared abatement technology (`claus`, `agi`, `ccus`, `vent`) matches the mechanical P&ID drawings of the facility. |
| **HRG-007** | **OGMP 2.0 Recon** | OGMP Level 4 / 5 | Reconciling bottom-up source inventories against top-down aerial/satellite surveys across varying temporal intervals. | System averages top-down survey passes ($T = \frac{1}{N} \sum S_i$) and flags discrepancies when $|T - B| / T > 0.20$. | **Regulatory Compliance Director** must evaluate flagged discrepancies ($>20\%$) against UNEP IMEO Technical Guidance prior to official submission to the OGMP Secretariat. |
| **HRG-008** | **Regulatory GWP** | Corporate Reporting | Conflicting statutory requirements across jurisdictions (e.g. EU CBAM mandates IPCC AR6, whereas US EPA Subpart W / Part 99 mandates AR5 or AR4). | System enforces a single global `SystemSetting` GWP standard (AR5 default, configurable to AR6 or AR4). | **Legal & Compliance Counsel** must review and configure the active corporate GWP standard to ensure alignment with target disclosure frameworks (CSRD, SEC, EU CBAM). |
| **HRG-009** | **Uncertainty Model**| Statistical QA/QC | Zero-covariance assumption between facilities in IPCC Eq. 3.2 summation ($\text{Cov}(X_i, X_j) = 0$). | System assumes independent error distributions across facilities and fuel streams. | **Lead Environmental Verifier / Auditor** must confirm whether shared regional grid emission factors or common pipeline gas supplies introduce correlated systemic uncertainties. |
| **HRG-010** | **Waste Emissions** | US EPA Part 99 WEC | Applicability of the 0.20% sales gas methane intensity exemption threshold under Clean Air Act §136. | System computes methane intensity and evaluates WEC fee liability based on the statutory fee schedule. | **Corporate General Counsel** must verify whether specific facilities qualify for regulatory exemptions (e.g. unreasonable delay in environmental permitting or shut-in wells). |

---

## 3. Governance Protocol & Audit Sign-Off Requirements

1. **Pre-Submission Sign-Off**:
   - No GHG emissions inventory report may be marked as "Final Official Disclosure" while any item in the Human Review Register remains uncertified.
2. **Cryptographic / Immutable Audit Trail**:
   - Every human review certification must be logged into `ActivityLog` with the certifying expert's name, role, IP address, and attached validation artifact ID.
3. **Annual Recertification**:
   - All 10 gates must be re-certified annually prior to base-year recalculations and third-party verification under ISO 14064-3.
