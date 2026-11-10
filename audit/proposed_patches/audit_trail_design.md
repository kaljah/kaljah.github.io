# Comprehensive Design Proposal: Factor Provenance & Silent Default Audit Trail

**Document**: `/audit/proposed_patches/audit_trail_design.md`  
**Governing Standard**: ISO 14064-1:2018 §9 (GHG Inventory Quality Management) | GHG Protocol Corporate Standard Ch. 11  
**Status**: Architecture & Implementation Proposal (Unapplied Diff & Schema Specification)  
**Target Modules**: `new/server/models.py`, `new/server/calculations/dispatcher.py`, `new/client/src/components/`

---

## 1. Executive Architecture Summary

To ensure 100% auditability and prevent silent assumptions from compromising carbon accounting integrity, this proposal establishes an end-to-end **Factor Provenance & Lineage Tracking Framework**.

Every emission factor, physical constant, process efficiency, and Global Warming Potential (GWP) is registered with complete statutory metadata:
- Exact parameter value and dimensional unit
- Reference document, publication edition, and publication year
- Exact chapter, section, table, or equation number
- User overridability permissions
- Warning and assurance classification flags

Whenever a calculation executes, the engine tracks every default and factor consumed, attaching a `provenance_trail` to the calculation record. If any parameter was derived from an unverified or silent fallback (e.g. 80% boiler efficiency or 0% line loss), the API flags `has_silent_defaults: true`, triggering an amber warning banner across the web dashboard and export artifacts.

---

## 2. Relational Database Schema Design

Two tables are introduced to govern factor provenance and record execution lineage:

### 2.1 `factor_provenance_registry` Table
Stores authoritative metadata for every calculation factor, constant, and default across the platform.

```sql
CREATE TABLE factor_provenance_registry (
    id VARCHAR(64) PRIMARY KEY,                    -- e.g. 'PHY-012', 'FLR-001', 'SCP2-004'
    factor_key VARCHAR(128) NOT NULL,              -- e.g. 'density_ch4_std', 'flare_destruction_efficiency'
    category VARCHAR(64) NOT NULL,                -- 'physical_constant', 'emission_factor', 'efficiency', 'gwp'
    parameter_name VARCHAR(255) NOT NULL,          -- 'Standard Methane Density'
    value NUMERIC(18, 8) NOT NULL,                 -- 0.67722000
    unit VARCHAR(64) NOT NULL,                     -- 'kg/m3'
    basis VARCHAR(64) NOT NULL,                    -- '60 F, 14.696 psia, molar volume 23.685 m3/kmol'
    source_document VARCHAR(255) NOT NULL,         -- 'API Compendium'
    edition_year VARCHAR(32) NOT NULL,             -- '4th Edition (November 2021)'
    table_or_equation_ref VARCHAR(128) NOT NULL,   -- 'Section 3.4 / Table 3-7'
    page_number VARCHAR(32),                       -- 'p. 3-8'
    verbatim_citation VARCHAR(512) NOT NULL,       -- 'Gas density is molecular weight divided by molar volume (16.04 / 23.685).'
    is_user_overridable BOOLEAN NOT NULL DEFAULT 1,-- Whether site can provide custom measured value
    is_silent_default BOOLEAN NOT NULL DEFAULT 0,  -- True if applied automatically when input is omitted
    warning_flag VARCHAR(32) NOT NULL DEFAULT 'NONE',-- 'NONE', 'INFO', 'CAUTION_ASSUMPTION', 'NON_STANDARD'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2.2 `calculation_factor_lineage` Table
Maintains the immutable link between every stored calculation result and the exact factors it consumed.

```sql
CREATE TABLE calculation_factor_lineage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    calculation_id INTEGER NOT NULL REFERENCES emission_records(id) ON DELETE CASCADE,
    factor_id VARCHAR(64) NOT NULL REFERENCES factor_provenance_registry(id),
    applied_value NUMERIC(18, 8) NOT NULL,
    applied_unit VARCHAR(64) NOT NULL,
    was_user_override BOOLEAN NOT NULL DEFAULT 0,
    override_provenance_note TEXT,
    warning_flag VARCHAR(32) NOT NULL DEFAULT 'NONE',
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_lineage_calc_id ON calculation_factor_lineage(calculation_id);
CREATE INDEX idx_lineage_factor_id ON calculation_factor_lineage(factor_id);
```

---

## 3. Calculation Result Payload Specification

The backend calculation dispatcher (`new/server/calculations/dispatcher.py`) returns a structured `provenance` block inside the calculation response JSON:

```json
{
  "calculation_id": 4182,
  "status": "success",
  "emissions": {
    "co2_tonnes": 132.496,
    "ch4_tonnes": 0.0025,
    "n2o_tonnes": 0.00025,
    "total_co2e": 132.632
  },
  "provenance_trail": {
    "total_factors_consumed": 4,
    "has_silent_defaults": true,
    "warning_level": "WARNING",
    "factors": [
      {
        "id": "SCP2-004",
        "name": "Default Steam Boiler Efficiency",
        "value": 0.80,
        "unit": "fraction",
        "source": "EPA GHG Emission Factors Hub (2024) Table 7",
        "is_silent_default": true,
        "was_user_override": false,
        "warning_flag": "CAUTION_ASSUMPTION",
        "message": "Calculated using silent default 80% boiler efficiency (unspecified by user)."
      },
      {
        "id": "SCP2-005",
        "name": "Default Steam Transmission Loss",
        "value": 0.00,
        "unit": "fraction",
        "source": "Application Internal Default",
        "is_silent_default": true,
        "was_user_override": false,
        "warning_flag": "CAUTION_ASSUMPTION",
        "message": "Calculated assuming 0% transmission loss. Compendium Exhibit 8.3 indicates ~10% loss."
      },
      {
        "id": "GWP-005",
        "name": "IPCC AR5 CH4 100-yr GWP",
        "value": 28.0,
        "unit": "kg CO2e / kg CH4",
        "source": "IPCC AR5 Table 8.7 (Without CC Feedbacks)",
        "is_silent_default": false,
        "was_user_override": false,
        "warning_flag": "NONE",
        "message": "Platform statutory default standard."
      }
    ]
  }
}
```

---

## 4. Frontend User Interface Experience

When `has_silent_defaults: true` is returned:
1. **Amber Warning Banner**: Renders above the KPI summary:
   > ⚠️ **Silent Default Notice**: This result relied on 2 default assumptions (Boiler Efficiency: 80%, Transmission Loss: 0%). [Inspect Factor Provenance]
2. **Provenance Inspector Modal**: Clicking allows the auditor or site engineer to inspect each factor's primary literature source, table number, and verbatim quote, with a one-click button to input a verified site-specific parameter.
3. **Audit Export Watermark**: PDF and CSV exports automatically tag the record as `METHODOLOGY: DEFAULT_ASSUMPTION` rather than `MEASURED_PRIMARY`.

---

## 5. Accompanying Patch Files in this Directory

- `schema_factor_provenance.patch`: SQLAlchemy model definitions and migration script adding `FactorProvenanceRegistry` and `CalculationFactorLineage`.
- `ui_silent_default_warning.patch`: React component adding `SilentDefaultBanner.tsx` and `FactorLineageModal.tsx`.
