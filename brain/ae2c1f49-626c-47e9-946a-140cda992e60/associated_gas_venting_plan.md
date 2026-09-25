# Implementation Plan: Associated Gas Venting (API GHG Compendium 2021)

## Overview
Add the new **Associated Gas Venting** process to Neocarbon following the **API GHG Compendium 2021 (Section 6.3.1, Equations 6-8, 6-9, Exhibits 6-5/6-6, and Table 6-8)** across the entire pipeline:
`UI → Validation → Backend → Calculation Engine → Database/Reference Factors → API → Dashboard/Reports`.

---

## 1. Calculation Methodology & Equations
- **Equation 6-8 (Direct / Vent Rate basis):**
  $$E_x = VR \times F_x \times \frac{MW_x}{\text{Molar Volume}} \times T_v$$
  - $VR$: Vent rate (scfh or $\text{Sm}^3/\text{hr}$)
  - $F_x$: Molar fraction of GHG ($CH_4, CO_2$)
  - $MW_x$: Molecular weight ($16.0425$ for $CH_4$, $44.01$ for $CO_2$)
  - Molar volume: $379.3 \text{ scf/lb-mole}$ (US standard, $60^\circ\text{F}$, $14.7 \text{ psia}$) / $23.685 \text{ Sm}^3/\text{kg-mole}$ (metric standard, $15^\circ\text{C}$, $101.325 \text{ kPa}$)
  - $T_v$: Venting duration (hours or days)

- **Equation 6-9 (GOR approach):**
  $$VR = GOR \times Oil_p$$
  - Total Gas = $GOR \times \text{Oil Production}$
  - Net Vented Gas = $\text{Total Gas} - V_{\text{recovered}} - V_{\text{flared}}$ (or duration fraction)
  - Zero double counting: Only net vented gas is converted to atmospheric emissions; flared gas is partitioned and referenced to Section 5 flaring.

- **Table 6-8 (Tier 1 Default Emission Factors):**
  - US Average: $1.4 \text{ kg } CH_4/\text{bbl}$ ($89 \text{ scf whole gas/bbl}$)
  - Gulf Coast Basin (220): $0.7 \text{ kg } CH_4/\text{bbl}$ ($47 \text{ scf whole gas/bbl}$)
  - Anadarko Basin (360): $9.7 \text{ kg } CH_4/\text{bbl}$ ($622 \text{ scf whole gas/bbl}$)
  - Williston Basin (395): $8.9 \text{ kg } CH_4/\text{bbl}$ ($570 \text{ scf whole gas/bbl}$)
  - Permian Basin (430): $6.5 \text{ kg } CH_4/\text{bbl}$ ($419 \text{ scf whole gas/bbl}$)
  - Other US Basins: $0.4 \text{ kg } CH_4/\text{bbl}$ ($26 \text{ scf whole gas/bbl}$)
  - Gas composition adjustment per footnote b for site-specific $CH_4$ and $CO_2$.

---

## 2. Pipeline Implementation Steps

1. **Calculation Engine (`new/server/calculations/vented.py`):**
   - Implement `AssociatedGasVentingCalculator` inheriting from `BaseCalculator`.
   - Implement Tier 1 (Table 6-8 + composition adjustment), Tier 2 (GOR + net vented balance), and Tier 3 (measured vent rate/volume).
   - Implement standard molar volume conversions ($379.3 \text{ scf/lb-mole}$ and $23.685 \text{ Sm}^3/\text{kg-mole}$).
   - Implement uncertainty propagation via `uncertainty.py`.

2. **Factor Catalog (`new/server/emission_factors_api2021.py` & `new/server/process_categories.py`):**
   - Add Table 6-8 regional emission factors with metadata, uncertainties, and citations.
   - Define `associated_gas_venting` process under Upstream segment.

3. **Dispatcher & Uncertainty (`new/server/calculations/dispatcher.py`, `uncertainty.py`):**
   - Register `AssociatedGasVentingCalculator` in `dispatcher.py`.
   - Map process category in `uncertainty.py`.

4. **API Validation & Routes (`new/server/routes/emissions.py`, `routes/dashboard.py`):**
   - Validate gas composition ($CH_4 + CO_2 \le 100\%$).
   - Validate mass balance ($V_{\text{recovered}} + V_{\text{flared}} \le V_{\text{total produced}}$).
   - Validate durations ($\le$ period maximum) and non-negative physical values.
   - Ensure dashboard aggregation includes `associated_gas_venting` under Venting.

5. **Frontend Form & UI (`new/client/src/components/scope1/AssociatedGasVentingForm.jsx`, `Scope1Form.jsx`):**
   - Create interactive form with Tier 1, Tier 2, Tier 3 workflows.
   - Table 6-8 preset basin dropdown with real-time preview.
   - Net-vented mass balance auto-calculator with double-counting prevention indicator.
   - Field-level validation messages.

6. **Comprehensive Testing:**
   - Pytest unit and integration tests (`tests/test_associated_gas_venting.py`) verifying Exhibits 6-5 & 6-6 golden numbers, Tiers 1-3, validations, and dashboard aggregation.
   - Vitest UI component tests (`src/__tests__/AssociatedGasVenting.test.jsx`) verifying user interaction, calculations, and result display.
