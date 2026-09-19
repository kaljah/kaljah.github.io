# Comprehensive Defect Remediation Implementation Plan

This implementation plan addresses and resolves all 12 defects identified during the full-stack system audit across computation, concurrency, security, and lifecycle domains.

## User Review Required

> [!IMPORTANT]
> - **Maker-Checker Segregation of Duties Enforced in QA/QC**: Reviewers cannot verify records they submitted themselves in the QA/QC dashboard, mirroring the emissions approval rules.
> - **Base Year Recalculation Authorization Restatement**: Access to `POST /api/dashboard/base-year-recalculation` is restricted to Admins and Superusers, harmonizing with `/api/base-years`.
> - **Scope 3 Spend-Based EEIO Correction**: Fixes the $1000\times$ unit discrepancy for Category 1 spend-based calculations ($kg \text{ CO}_2\text{e} / \$1,000 \to t \text{ CO}_2\text{e}$).

---

## Proposed Changes

Grouped by component layer:

### 1. Web & Real-Time Communications
#### [MODIFY] [notifications.py](file:///c:/Users/samsung/Desktop/H2/new/server/routes/notifications.py)
- Initialize `last_heartbeat = start_time` before the while loop in `stream_notifications.generate()` to prevent `UnboundLocalError`.

### 2. Computational & Numerical Logic
#### [MODIFY] [scope2.py](file:///c:/Users/samsung/Desktop/H2/new/server/routes/scope2.py)
- In `update_scope2_emission`, calculate indirect steam using the authoritative thermodynamic model (`_calc_indirect_steam`), including MMBtu enthalpy conversion ($2.0\times$) and boiler net efficiency division.

#### [MODIFY] [scope3.py](file:///c:/Users/samsung/Desktop/H2/new/server/routes/scope3.py)
- In `create_scope3_emission`, detect spend-based factor units (`kg CO2e / $1000`) and divide by $1,000,000$ instead of $1,000$ to correctly output metric tonnes $\text{CO}_2\text{e}$.

#### [MODIFY] [emissions.py](file:///c:/Users/samsung/Desktop/H2/new/server/routes/emissions.py)
- In `add_emission`, divide general `cf.uncertainty` by $100.0$ when populating `factor_data["uncertainty"]`, eliminating the $100\times$ inflation bug.
- In `update_emission`, merge existing record fields (`process_type`, `unit`, `fuel_type`, equipment ID, and calculation inputs) into `calc_payload` prior to calling `compute_emissions`, preventing partial updates from reverting to general combustion.

### 3. Security, Authorization & RBAC
#### [MODIFY] [scope3.py](file:///c:/Users/samsung/Desktop/H2/new/server/routes/scope3.py)
- In `bulk_import_scope3`, verify that each resolved facility is within `allowed_fids`.

#### [MODIFY] [scope2.py](file:///c:/Users/samsung/Desktop/H2/new/server/routes/scope2.py)
- In `bulk_import_scope2`, block `it_admin`, retrieve `allowed_fids`, and filter out facilities outside the caller's authorized scope.

#### [MODIFY] [qaqc.py](file:///c:/Users/samsung/Desktop/H2/new/server/routes/qaqc.py)
- In `resolve_flagged_record` and `bulk_resolve`, block `it_admin` and enforce Maker-Checker segregation of duties (`record.created_by != user.id` when `resolution == "Verified"`).

#### [MODIFY] [dashboard.py](file:///c:/Users/samsung/Desktop/H2/new/server/routes/dashboard.py)
- In `create_base_year_recalculation`, restrict access to `admin` and `superuser`, block `it_admin`, populate `created_by`, update the `BaseYear` singleton, and record an audit log.

#### [MODIFY] [data.py](file:///c:/Users/samsung/Desktop/H2/new/server/routes/data.py)
- In `save_cbam_export`, verify `require_facility_access(user, record.facility_id)` on existing records before updating to eliminate IDOR.

#### [MODIFY] [managedata.py](file:///c:/Users/samsung/Desktop/H2/new/server/routes/managedata.py)
- In `delete_mitigation`, require `admin` or `superuser` role to delete generic `MitigationRecord` entries.

#### [MODIFY] [auth.py](file:///c:/Users/samsung/Desktop/H2/new/server/routes/auth.py)
- In `update_user`, enforce a strict whitelist check on `role` (`{"user", "superuser", "admin", "it_admin"}`).

### 4. Concurrency & Background Processing
#### [MODIFY] [background_processor.py](file:///c:/Users/samsung/Desktop/H2/new/server/background_processor.py)
- Introduce `upload_jobs_lock = threading.Lock()` and wrap all access, pruning, and state transitions of `upload_jobs` with the lock.

---

## Verification Plan

### Automated Tests
1. Run full existing test suite to ensure zero regressions:
   ```powershell
   pytest tests/ -v
   ```
2. Add dedicated test cases in `new/server/tests/test_audit_remediation.py`:
   - `test_notifications_stream_heartbeat_unbound_fix`: Verify generator yields connected and handles heartbeats without `UnboundLocalError`.
   - `test_scope2_update_indirect_steam_thermodynamic_accuracy`: Verify PUT preserves boiler efficiency and enthalpy.
   - `test_scope3_spend_based_eeio_scale_correctness`: Verify Category 1 spend calculation divides by 1,000,000.
   - `test_custom_factor_general_uncertainty_scale`: Verify `cf.uncertainty` is converted to relative decimal ($0.05$).
   - `test_scope1_partial_update_preserves_process_type`: Verify partial quantity update on venting/fugitive does not revert to combustion.
   - `test_bulk_import_scope2_and_3_rbac_enforcement`: Verify facilities outside allowed regions are rejected.
   - `test_qaqc_resolve_maker_checker_enforcement`: Verify self-approval is rejected with 403.
   - `test_dashboard_base_year_recalc_rbac`: Verify standard users cannot post recalculation events.
   - `test_cbam_export_update_idor_protection`: Verify cannot mutate exports belonging to unauthorized facilities.
   - `test_auth_update_user_role_whitelist`: Verify invalid role strings are rejected.

### Manual / System Verification
- Compile frontend client bundle (`npm run build` in `new/client`) to ensure complete contract compatibility.
- Synchronize knowledge graph via `graphify update .`.
