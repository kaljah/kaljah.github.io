<!-- Generated: 2026-10-27 | Files scanned: 637 | Token estimate: ~850 -->
# Data Architecture & Schemas

SQLAlchemy ORM relational data layer supporting SQLite (development/testing) and PostgreSQL (production).

## Entity Relationship Overview

```
[ User ] (users)
   │  1:N
   ├─► [ ActivityLog ] (activity_log: immutable audit ledger)
   └─► [ Notification ] (notifications)

[ Facility ] (facilities)
   │  1:N
   ├─► [ Emission ] (emissions: Scope 1 activity, fuel, flaring, venting)
   │     └─► [ FlaringDetail ] (flaring_details: gas composition, tip D, combustion eff)
   ├─► [ Scope2Emission ] (scope2_emissions: location/market electricity)
   ├─► [ Scope3Emission ] (scope3_emissions: protocol categories 1-15)
   ├─► [ ProductionData ] (production_data: boe, oil, gas volumes for intensity metrics)
   ├─► [ EmissionSource ] (emission_sources: equipment, compressors, flares, tanks)
   ├─► [ ComponentInventory ] (component_inventories: valves, flanges, seals for LDAR)
   ├─► [ FugitiveSurvey ] (fugitive_surveys: leak detection & repair campaign logs)
   ├─► [ CustomFactor ] (custom_factors: facility-specific emission overrides)
   ├─► [ OgmpSurvey ] (ogmp_surveys: level 1-5 measurement validation)
   └─► [ FacilityEquityShare ] (facility_equity_shares: JV accounting)
         ▲
         │ 1:N
   [ JvPartner ] (jv_partners)

[ Baseline & Regulatory Targets ]
   ├── [ BaseYear ] (base_year) ──► [ BaseYearRecalculation ] (base_year_recalculations)
   ├── [ SbtiTarget ] (sbti_targets)
   ├── [ Goal ] (goals)
   └── [ MitigationProject ] (mitigation_projects) ──► [ MitigationRecord ]

[ System Configuration & Import ]
   ├── [ SystemSetting ] (system_settings)
   ├── [ ImportMapping ] (import_mappings)
   └── [ CbamProductExport ] (cbam_product_exports)
```

## Core Tables (29 Total)

| Table | Model Class | Key Fields & Relationships | Purpose |
|---|---|---|---|
| `facilities` | `Facility` | `id, name, type, location, operational_status` | Operating assets / asset boundaries |
| `emissions` | `Emission` | `facility_id, scope, category, co2e, ch4, n2o, date` | Core Scope 1 transaction records |
| `production_data` | `ProductionData` | `facility_id, gross_boe, net_oil, gas_produced, date` | Denominator for carbon/methane intensity |
| `flaring_details` | `FlaringDetail` | `emission_id, flare_type, tip_diameter, eff_percent` | High-fidelity flaring combustion specs |
| `scope2_emissions` | `Scope2Emission` | `facility_id, mwh_consumed, method, grid_factor` | Indirect energy emissions (Scope 2) |
| `scope3_emissions` | `Scope3Emission` | `facility_id, category, spend_usd, activity_val` | Value chain emissions across 15 categories |
| `component_inventories`| `ComponentInventory`| `facility_id, component_type, count, service_stream` | Fugitive emission factor equipment census |
| `fugitive_surveys` | `FugitiveSurvey` | `facility_id, survey_date, leakers_found, method` | EPA Method 21 / OGI leak campaign log |
| `activity_log` | `ActivityLog` | `user_id, action, entity_type, entity_id, timestamp` | Append-only security & audit history |
| `ogmp_surveys` | `OgmpSurvey` | `facility_id, source_type, ogmp_level, measured_rate`| UNEP OGMP 2.0 Level 4/5 Gold Standard |
| `facility_equity_shares`| `FacilityEquityShare`| `facility_id, partner_id, share_percentage` | Operational vs. Equity share boundaries |
| `import_mappings` | `ImportMapping` | `source_column, target_field, facility_id` | Cached column mapping wizard profiles |

## Database Migration & Sync

- **Engine**: Alembic + Flask-Migrate (`new/server/migrations/`)
- **Runtime Sync**: `new/server/schema_sync.py` provides automated verification and column synchronization on startup.
- **Constraints**: Enforces foreign keys, cascade deletes where appropriate, and unique indexing on facility names and user emails.
