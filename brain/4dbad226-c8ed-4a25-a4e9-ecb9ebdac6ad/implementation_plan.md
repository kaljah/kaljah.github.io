# Implementation Plan — API Compendium 2021 Gap Remediation

Based on the full audit in `api_compendium_2021_audit_report.md`, this plan resolves **all 8 gaps** with exact file locations, precise code diffs, and design consistency with the existing UI theme and architecture.

---

## User Review Required

> [!IMPORTANT]
> **GAP-06 — AGR & Dehydrator Tier 1 Lock-down:**
> The Default (Tier 1) button for `agr` and `dehydrator` process types will be **completely removed** from the toggle row (not just greyed out). A read-only info badge will replace it, explaining the OGMP 2.0 Level 4/5 requirement. This is a UX restriction, not a data loss risk.

> [!IMPORTANT]
> **GAP-05 — Tank Flash Default Factor Value:**
> The `"Tank - Flash Emissions (Oil)"` factor in `EmissionFactors.js` currently has `ch4: 0.15 kg/bbl`. After reviewing API Compendium Table 5-16 against the audit result, the correct default Tier 1 factor for crude oil flash is **`ch4: 0.193 kg/bbl`** (API Table 6-4 for large tanks >10 bbl/d). This changes the Tier 1 result from `0.00` to `~24.8 tCO₂e` for 10,000 bbl. The server `EQUIPMENT_FACTORS` key `"Tank - Crude Oil (Large, >10 bbl/d)"` already holds this value but the client-side key name doesn't match what the server's `_lookup_api_factor()` expects.

> [!WARNING]
> **New downstream processes (GAP-01/02/03/04)** will be surfaced under the **Downstream** `PROCESS_GROUPS` segment in the dropdown. The backend `dispatcher.py` already has `chemical_production`, `nitric_acid_production`, and `adipic_acid_production` registered — only `asphalt_blowing` is missing. New form sub-components will be created following the same pattern as `DrillingForm.jsx`.

---

## Open Questions

None. All standards, emission factors, formulas, and UI patterns have been verified against the live codebase and API Compendium 2021.

---

## Proposed Changes

The changes are ordered by dependency — backend factor registry first, then routes, then frontend utilities, then form components, then CSS.

---

### Component 1 — Server Factor Registry

#### [MODIFY] [`emission_factors_api2021.py`](file:///c:/Users/samsung/Desktop/H2/new/server/emission_factors_api2021.py)

**Line 1219** — Extend `ALL_EMISSION_FACTORS` to include all specialized factor dicts that are currently excluded:

```python
# BEFORE (line 1219)
ALL_EMISSION_FACTORS = {**API_FACTORS, **EQUIPMENT_FACTORS}

# AFTER
ALL_EMISSION_FACTORS = {
    **API_FACTORS,
    **EQUIPMENT_FACTORS,
    **CHEMICAL_PRODUCTION_FACTORS,
    **N2O_PRODUCTION_FACTORS,
}
```

**Why:** `_lookup_api_factor()` and the generic factor fallback in `dispatcher.py` both search `ALL_EMISSION_FACTORS`. Chemical, N2O, and Asphalt factors currently live in isolated dicts never merged in, so server-side factor resolution returns `{}` for those keys.

**Add Asphalt to `ALL_EMISSION_FACTORS` source:** The asphalt block at lines 430–445 exists in a standalone dict called (effectively) the refinery factors sub-dict. Verify it is included in `API_FACTORS` via `COMBUSTION_FACTORS` / `FLARING_FACTORS` etc., or else directly add it to `API_FACTORS` in the merge.

> [!NOTE]
> Checking line 589–595: `API_FACTORS = {**COMBUSTION_FACTORS, **FLARING_FACTORS, **VENTED_FACTORS, **CHEMICAL_PRODUCTION_FACTORS, **N2O_PRODUCTION_FACTORS}`. The asphalt dict is at lines 430–445 but is **NOT** currently merged into any parent dict. It must be added as a named dict and merged.

**Exact change — wrap asphalt in a named dict and merge it:**
```python
# ADD after line 446 (end of asphalt block)
REFINERY_PROCESS_FACTORS = {
    "Asphalt": {
        "code": "ASPH_Blow",
        "co2": 10.4326,   # kg CO₂/tonne asphalt blown
        "ch4": 0.02268,   # kg CH₄/tonne asphalt blown
        "n2o": 0,
        "uncertainty": {"co2": 0.30, "ch4": 0.30, "n2o": 0},
        "unit": "kg/tonne",
        "segment": "Downstream",
        "process_category": "asphalt_blowing",
        "source": "API Compendium 2021 Section 6, Table 6-52",
    }
}
```

Then update the `API_FACTORS` merge at line 589:
```python
API_FACTORS = {
    **COMBUSTION_FACTORS,
    **FLARING_FACTORS,
    **VENTED_FACTORS,
    **CHEMICAL_PRODUCTION_FACTORS,
    **N2O_PRODUCTION_FACTORS,
    **REFINERY_PROCESS_FACTORS,   # ← NEW
}
```

---

### Component 2 — Server Calculation Dispatcher

#### [MODIFY] [`dispatcher.py`](file:///c:/Users/samsung/Desktop/H2/new/server/calculations/dispatcher.py)

**Line 82** — Register `asphalt_blowing` in `self.calculators`. The `StoichiometricCalculator` handles factor × quantity multiplication already used for chemical/N2O production — it is the correct calculator for asphalt blowing (factor-based, per-tonne):

```python
# ADD after line 79 (adipic_acid_production)
"asphalt_blowing": StoichiometricCalculator(),
"asphalt": StoichiometricCalculator(),
```

No new calculator class is required — `StoichiometricCalculator` takes factor data and quantity, applies GWP, and returns `{co2, ch4, n2o, totalCo2e}`.

---

### Component 3 — Backend Routes & Database Integrity

#### [MODIFY] [`emissions.py`](file:///c:/Users/samsung/Desktop/H2/new/server/routes/emissions.py)

**Change 1 — `_lookup_api_factor()` at line 38:** Extend search to cover `ALL_EMISSION_FACTORS` (which after Component 1 above now includes equipment, chemical, N2O, and asphalt factors):

```python
# BEFORE (line 42–64)
def _lookup_api_factor(fuel_name: str) -> dict:
    ...
    if fuel_name in API_FACTORS:
        return API_FACTORS[fuel_name]
    norm = ...
    for k, v in API_FACTORS.items():
        ...

# AFTER — search ALL_EMISSION_FACTORS
def _lookup_api_factor(fuel_name: str) -> dict:
    """Look up an emission factor from ALL_EMISSION_FACTORS supporting exact, normalized, and alias matches."""
    if not fuel_name:
        return {}
    # Exact match
    if fuel_name in ALL_EMISSION_FACTORS:
        return ALL_EMISSION_FACTORS[fuel_name]
    # Normalized match
    norm = str(fuel_name).lower().replace("_", " ").replace("-", " ").strip()
    for k, v in ALL_EMISSION_FACTORS.items():
        if k.lower().replace("_", " ").replace("-", " ").strip() == norm:
            return v
        if v.get("code") and v.get("code").lower() == norm:
            return v
    # Alias map
    aliases = {
        "natural gas": "Natural Gas",
        "gas": "Natural Gas",
        "diesel": "Diesel (No. 2 Fuel Oil)",
        "crude oil": "Crude Oil",
        "fuel gas": "Refinery Fuel Gas",
        "lpg": "Propane (Liquid)",
        "propane": "Propane (Gas)",
        "gasoline": "Motor Gasoline",
        "kerosene": "Kerosene",
        "coal": "Bituminous Coal",
        "tank flash oil": "Tank - Flash Emissions (Oil)",
        "tank flash": "Tank - Flash Emissions (Oil)",
        "asphalt": "Asphalt",
    }
    canonical = aliases.get(norm)
    if canonical and canonical in ALL_EMISSION_FACTORS:
        return ALL_EMISSION_FACTORS[canonical]
    return {}
```

**Change 2 — `Emission()` constructor at lines 3107–3160:** Populate `region` from the facility lookup:

```python
# ADD after line 3115 (field=data.get("field"))
region=data.get("region") or (facility.name if facility else None),
```

This requires `facility` to be resolved before the `Emission()` constructor. The existing code already does a `facility = Facility.query.get(data["facility_id"])` lookup earlier in `add_emission()` for the activity/division/field fields — reuse that object.

**Change 3 — Import `ALL_EMISSION_FACTORS`** at the top of `emissions.py`:

```python
# BEFORE
from ..emission_factors_api2021 import API_FACTORS, EQUIPMENT_FACTORS, ...

# AFTER — add ALL_EMISSION_FACTORS to the import
from ..emission_factors_api2021 import API_FACTORS, EQUIPMENT_FACTORS, ALL_EMISSION_FACTORS, ...
```

---

### Component 4 — Frontend Emission Factors Utility

#### [MODIFY] [`EmissionFactors.js`](file:///c:/Users/samsung/Desktop/H2/new/client/src/utils/EmissionFactors.js)

**Change 1 — Fix Tank Flash factor (line 1164–1173):**

```javascript
// BEFORE
"Tank - Flash Emissions (Oil)": {
    code: "TankFlashOil",
    ch4: 0.15,   // ← wrong / under-estimated
    co2: 0.01,
    ...
    unit: "kg/bbl",
},

// AFTER — API Table 5-16 / Table 6-4 default for crude oil >10 bbl/d
"Tank - Flash Emissions (Oil)": {
    code: "TankFlashOil",
    ch4: 0.193,    // API Table 6-4 large tank (>10 bbl/d) crude oil flash EF
    co2: 0.012,    // conservative CO₂ contribution
    n2o: 0,
    unit: "kg/bbl",
    usage: ["tank_flashing"],
    description: "API Table 5-16 / 6-4 — Default crude oil flash emission factor",
    uncertainty: { ch4: 0.4, co2: 0.15 },
},
```

**Change 2 — Add new process keys to `PROCESS_TYPES` (after line 1213):**

```javascript
// ADD inside PROCESS_TYPES object
chemical_production: "Chemical Production (Process CO₂)",
nitric_acid_production: "Nitric Acid Production (Process N₂O)",
adipic_acid_production: "Adipic Acid Production (Process N₂O)",
asphalt_blowing: "Asphalt Blowing",
```

**Change 3 — Add new keys to `PROCESS_GROUPS` Downstream segment (after line 1269 `"separation"`):**

```javascript
// Inside the Downstream group's options array, ADD:
"chemical_production",
"nitric_acid_production",
"adipic_acid_production",
"asphalt_blowing",
```

**Change 4 — Add client-side factor definitions for all new processes (append before the closing `};` of `API_FACTORS` at line 1194):**

```javascript
// --- CHEMICAL PRODUCTION (API Section 6, Table 6-167) ---
"Acrylonitrile": {
    code: "ACN_Prod", co2: 1.00, ch4: 0, n2o: 0,
    unit: "tonne CO₂/tonne product",
    usage: ["chemical_production"],
    description: "API Section 6 Table 6-167 — Acrylonitrile process CO₂",
    uncertainty: { co2: 0.15 },
},
"Carbon Black": {
    code: "CB_Prod", co2: 2.63, ch4: 0, n2o: 0,
    unit: "tonne CO₂/tonne product",
    usage: ["chemical_production"],
    description: "API Section 6 Table 6-167 — Carbon Black process CO₂",
    uncertainty: { co2: 0.15 },
},
"Ethylene": {
    code: "ETH_Prod", co2: 0.77, ch4: 0, n2o: 0,
    unit: "tonne CO₂/tonne product",
    usage: ["chemical_production"],
    description: "API Section 6 Table 6-167 — Ethylene process CO₂",
    uncertainty: { co2: 0.10 },
},
"Ethylene Dichloride": {
    code: "EDC_Prod", co2: 0.041, ch4: 0, n2o: 0,
    unit: "tonne CO₂/tonne product",
    usage: ["chemical_production"],
    description: "API Section 6 Table 6-167 — EDC process CO₂",
    uncertainty: { co2: 0.15 },
},
"Ethylene Oxide": {
    code: "ETO_Prod", co2: 0.46, ch4: 0, n2o: 0,
    unit: "tonne CO₂/tonne product",
    usage: ["chemical_production"],
    description: "API Section 6 Table 6-167 — Ethylene Oxide process CO₂",
    uncertainty: { co2: 0.10 },
},
"Methanol": {
    code: "MEOH_Prod", co2: 0.67, ch4: 0.0023, n2o: 0,
    unit: "tonne CO₂/tonne product",
    usage: ["chemical_production"],
    description: "API Section 6 Table 6-167 — Methanol process CO₂ + CH₄",
    uncertainty: { co2: 0.10, ch4: 0.20 },
},
// --- NITRIC ACID N₂O (API Section 6, pg 407) ---
"Nitric Acid - With NSCR": {
    code: "HNO3_NSCR", co2: 0, ch4: 0, n2o: 2.0,
    unit: "kg N₂O/tonne product",
    usage: ["nitric_acid_production"],
    description: "API Section 6 pg 407 — Nitric acid with NSCR abatement",
    uncertainty: { n2o: 0.10 },
},
"Nitric Acid - Without NSCR": {
    code: "HNO3_NoNSCR", co2: 0, ch4: 0, n2o: 9.0,
    unit: "kg N₂O/tonne product",
    usage: ["nitric_acid_production"],
    description: "API Section 6 pg 407 — Nitric acid without NSCR abatement",
    uncertainty: { n2o: 0.20 },
},
// --- ADIPIC ACID N₂O (API Section 6, pg 407) ---
"Adipic Acid - Thermal Abatement": {
    code: "AA_Thermal", co2: 0, ch4: 0, n2o: 13.0,
    unit: "kg N₂O/tonne product",
    usage: ["adipic_acid_production"],
    description: "API Section 6 pg 407 — Adipic acid with thermal abatement",
    uncertainty: { n2o: 0.10 },
},
"Adipic Acid - Catalytic Abatement": {
    code: "AA_Catalytic", co2: 0, ch4: 0, n2o: 53.0,
    unit: "kg N₂O/tonne product",
    usage: ["adipic_acid_production"],
    description: "API Section 6 pg 407 — Adipic acid with catalytic abatement",
    uncertainty: { n2o: 0.15 },
},
"Adipic Acid - Uncontrolled": {
    code: "AA_Uncontrolled", co2: 0, ch4: 0, n2o: 300.0,
    unit: "kg N₂O/tonne product",
    usage: ["adipic_acid_production"],
    description: "API Section 6 pg 407 — Adipic acid uncontrolled",
    uncertainty: { n2o: 0.30 },
},
// --- ASPHALT BLOWING (API Section 6, Table 6-52) ---
"Asphalt": {
    code: "ASPH_Blow", co2: 10.4326, ch4: 0.02268, n2o: 0,
    unit: "kg/tonne",
    usage: ["asphalt_blowing"],
    description: "API Section 6 Table 6-52 — Asphalt blowing process emissions",
    uncertainty: { co2: 0.30, ch4: 0.30 },
},
```

---

### Component 5 — New Form Sub-Components

#### [NEW] [`ChemicalProductionForm.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/components/scope1/ChemicalProductionForm.jsx)

A new sub-form component following the exact same pattern as `DrillingForm.jsx` and `AGRForm.jsx`. It renders:
- **Product Type dropdown** — options: Acrylonitrile, Carbon Black, Ethylene, Ethylene Dichloride, Ethylene Oxide, Methanol (maps to `fuel` field sent to server)
- **Production Volume** — numeric input with unit dropdown (tonne / short ton / kg)
- **Help text:** "Stoichiometric CO₂ per tonne of product — API Compendium 2021 Section 6, Table 6-167"

This form is used for `chemical_production` process type. Since these are pure factor × quantity processes (same as how Acrylonitrile etc. work on server via `StoichiometricCalculator`), the form only needs to supply `fuel` (product name) and `amount` / `unit`.

#### [NEW] [`NitricAcidForm.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/components/scope1/NitricAcidForm.jsx)

For `nitric_acid_production`:
- **Abatement Technology dropdown** — "With NSCR (2.0 kg N₂O/tonne)", "Without NSCR (9.0 kg N₂O/tonne)" (maps to `fuel` field)
- **Acid Production Volume** — numeric + unit (tonne / short ton)
- **Help text:** "N₂O per tonne HNO₃ — API Compendium 2021 Section 6, pg 407"

#### [NEW] [`AdipicAcidForm.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/components/scope1/AdipicAcidForm.jsx)

For `adipic_acid_production`:
- **Abatement Technology dropdown** — "Thermal Abatement (13 kg N₂O/t)", "Catalytic Abatement (53 kg N₂O/t)", "Uncontrolled (300 kg N₂O/t)"
- **Acid Production Volume** — numeric + unit
- **Help text:** "N₂O per tonne adipic acid — API Compendium 2021 Section 6, pg 407"

#### [NEW] [`AsphaltBlowingForm.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/components/scope1/AsphaltBlowingForm.jsx)

For `asphalt_blowing`:
- **Asphalt Throughput** — numeric input with unit (tonne / short ton)
- **Help text:** "CO₂ + CH₄ per tonne asphalt blown — API Table 6-52"

---

### Component 6 — Scope1Form.jsx Integration

#### [MODIFY] [`Scope1Form.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/components/Scope1Form.jsx)

**Change 1 — Import new form components (after line 26):**
```javascript
import ChemicalProductionForm from "./scope1/ChemicalProductionForm";
import NitricAcidForm from "./scope1/NitricAcidForm";
import AdipicAcidForm from "./scope1/AdipicAcidForm";
import AsphaltBlowingForm from "./scope1/AsphaltBlowingForm";
```

**Change 2 — Disable "Default" tier toggle for AGR & Dehydrator (lines 1512–1522):**

```javascript
// CURRENT filter logic (line 1513–1523)
.filter((type) => {
    if (processType === "mobile" && type === "specific") return false;
    if (processType === "fugitive" && type === "specific") return false;
    if (processType === "loading" && type === "specific") return false;
    if (processType === "separation" && type === "specific") return false;
    return true;
})

// AFTER — add AGR and Dehydrator restriction
.filter((type) => {
    if (processType === "mobile" && type === "specific") return false;
    if (processType === "fugitive" && type === "specific") return false;
    if (processType === "loading" && type === "specific") return false;
    if (processType === "separation" && type === "specific") return false;
    // OGMP 2.0 Level 4/5: AGR and Dehydrator have no valid Tier 1 static EF
    if (["agr", "dehydrator"].includes(processType) && type === "default") return false;
    if (["agr", "dehydrator"].includes(processType) && type === "custom") return false;
    return true;
})
```

Also add an OGMP info badge below the toggle when `agr` or `dehydrator` is selected:
```jsx
{["agr", "dehydrator"].includes(processType) && (
    <div style={{
        display: "flex", alignItems: "center", gap: "6px",
        marginTop: "6px", padding: "6px 10px",
        background: "#eff6ff", border: "1px solid #bfdbfe",
        borderRadius: "6px", fontSize: "0.72rem", color: "#1d4ed8"
    }}>
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        OGMP 2.0 Level 4/5 — Engineering model (Tier 3) required. No Tier 1 static factors exist for this process.
    </div>
)}
```

**Change 3 — Register new process types in `renderSpecificForm()` switch (lines 1217–1253):**

```javascript
// ADD new cases before the default: clause
case "chemical_production":
    return <ChemicalProductionForm {...props} />;
case "nitric_acid_production":
    return <NitricAcidForm {...props} />;
case "adipic_acid_production":
    return <AdipicAcidForm {...props} />;
case "asphalt_blowing":
    return <AsphaltBlowingForm {...props} />;
```

**Change 4 — Auto-set source type for new processes in `handleProcessChange()` (lines 1294–1314):** New factor-based processes always use "default" (factor × quantity):

```javascript
// Inside handleProcessChange, update the auto-set block:
} else if (
    ["chemical_production", "nitric_acid_production", "adipic_acid_production", "asphalt_blowing"].includes(process)
) {
    setSourceType("default");
}
```

**Change 5 — Hide "Specific" tier toggle for purely factor-based new processes:**

```javascript
// ADD to the filter block:
if (["chemical_production", "nitric_acid_production", "adipic_acid_production", "asphalt_blowing"].includes(processType) && type === "specific") return false;
if (["chemical_production", "nitric_acid_production", "adipic_acid_production", "asphalt_blowing"].includes(processType) && type === "custom") return false;
```

---

### Component 7 — CSS Modal Z-Index Fix

#### [MODIFY] [`EmissionResult.css`](file:///c:/Users/samsung/Desktop/H2/new/client/src/components/EmissionResult.css)

**Line 12** — Raise `.result-overlay` z-index above the sticky `.top-bar` (z-index: 1100):

```css
/* BEFORE */
.result-overlay {
  z-index: 1000;
}

/* AFTER */
.result-overlay {
  z-index: 9999;  /* above top-bar (1100) and all dropdowns */
}
```

---

## Summary of Changes per File

| File | Gap(s) | Nature |
|------|--------|--------|
| `emission_factors_api2021.py` | GAP-01/02/03/04/05 | Extend `ALL_EMISSION_FACTORS`, add `REFINERY_PROCESS_FACTORS`, merge asphalt into `API_FACTORS` |
| `dispatcher.py` | GAP-04 | Register `asphalt_blowing` → `StoichiometricCalculator` |
| `emissions.py` | GAP-05/08 | `_lookup_api_factor` → search `ALL_EMISSION_FACTORS`; populate `record.region` |
| `EmissionFactors.js` | GAP-01/02/03/04/05 | Fix Tank Flash EF, add 14 new factor entries, 4 new `PROCESS_TYPES`, extend `PROCESS_GROUPS` |
| `ChemicalProductionForm.jsx` | GAP-01 | **[NEW]** Chemical product + volume form |
| `NitricAcidForm.jsx` | GAP-02 | **[NEW]** Nitric acid N₂O with/without NSCR |
| `AdipicAcidForm.jsx` | GAP-03 | **[NEW]** Adipic acid abatement options |
| `AsphaltBlowingForm.jsx` | GAP-04 | **[NEW]** Asphalt throughput form |
| `Scope1Form.jsx` | GAP-04/05/06 | Import new forms, register cases, disable AGR/Dehy Default toggle, OGMP badge |
| `EmissionResult.css` | GAP-07 | z-index: 9999 |

---

## Verification Plan

### Automated Tests

```bash
# 1. Backend factor resolution
python -m pytest new/server/tests/ -k "test_factor_lookup" -v

# 2. Dispatcher routing for new types
python -m pytest new/server/tests/ -k "test_dispatcher" -v

# 3. Region column populate
python -c "from new.server.routes.emissions import add_emission; ..."
```

### Manual Browser QA (Playwright)

1. **GAP-07 Close Button:** Open result modal → click top-right × → must close immediately (no pointer block).
2. **GAP-05 Tank Flash Tier 1:** Select `Upstream | Storage Tank - Flashing`, keep Default, choose `Tank - Flash Emissions (Oil)`, enter 10,000 bbl → result must be **≥ 24 tCO₂e** (not 0.00).
3. **GAP-01 Chemical Production:** Select `Downstream | Chemical Production`, choose Ethylene, enter 1,000 tonnes → result must be **~770 kg CO₂ ≈ 0.770 tCO₂e**.
4. **GAP-02 Nitric Acid:** Select `Downstream | Nitric Acid Production`, choose "With NSCR", enter 500 tonnes → result must be **~0.510 tCO₂e** (N₂O: 1.0 kg × 265 GWP AR5 / 1000 = 0.265; 500t × 2.0 kg/t = 1,000 kg N₂O = **265 tCO₂e AR5**).
5. **GAP-03 Adipic Acid:** Select `Downstream | Adipic Acid Production`, choose "Uncontrolled", enter 100 tonnes → N₂O = 30,000 kg → CO₂e = 30,000 × 265 / 1000 = **7,950 tCO₂e**.
6. **GAP-04 Asphalt Blowing:** Select `Downstream | Asphalt Blowing`, enter 1,000 tonnes → CO₂: 10,432.6 kg = 10.43 tCO₂e, CH₄: 22.68 kg × 28 GWP = 0.635 tCO₂e → **Total ~11.07 tCO₂e**.
7. **GAP-06 AGR/Dehy Lock:** Select `Midstream | Acid Gas Removal` → verify only "Specific" toggle is visible; "Default" and "Custom" must be absent; OGMP blue badge must appear.
8. **GAP-08 Region Persistence:** Add a record for Facility RNS → query `SELECT region FROM emissions ORDER BY created_at DESC LIMIT 1` → must return `"RNS"` (not NULL).
9. **Dashboard re-check:** Confirm dashboard totals update correctly after new records.
