# FIX LOG

One line per fix: bug · files · verification.

- BUG-016 · migrations/versions/* (idempotent), migrations/versions/9c3e1a7b5d20 (reconcile head), schema_sync.py, app.py (ensure_model_columns), Dockerfile (flask db upgrade) · repro exit 0 (existing + fresh DB reach head)
- BUG-001 · routes/emissions.py upload_start (role whitelist per scope, IT roles 403), background_processor._process_row_facilities (region restriction) · repro exit 0 (403, DB unchanged)
- BUG-083 · validation.py (new), app.py (non-finite JSON guard, FiniteJSONProvider, ValidationError->400) · repro exit 0
- BUG-099/060/043/073/097 (partial: scope2 create/update/bulk, scope3 create/update) · routes/scope2.py, routes/scope3.py, utils.py (initial_record_status, can_approve) · BUG-043 repro exit 0; others see final rerun

## Remediation run 2 (root-cause-first, branch fix/audit-remediation-rc)
Baseline commit 087f6f7c: backend 28 failed / 1277 passed (pre-existing failures, listed in the commit's run log); repros passing at baseline: 001, 016, 024, 034, 043, 060, 073, 083, 089.

- Step 0 · `validation.py` renamed `input_validation.py` (name clashed with the repo-root `validation/` test package; the suite could not import app) · suite imports again
- BUG-016 (rework) · app.py `init_schema()` (Alembic is the only schema path: auto-upgrade outside production, refuse to start in production when not at head), removed the connect-hook ALTER, `ensure_model_columns`, and import-time `create_all`; config `IS_PRODUCTION`; migrations/env.py keeps app loggers · tests/test_audit_rc14_schema.py (fresh → head, snapshot → head, production guard, no import-time DDL) 4 passed; repro exit 0
- BUG-001 (completed) · utils `facility_in_user_scope` / `facility_change_allowed`; bulk facility rows validate resulting region; custom-factor rows role-checked · tests/test_audit_rc1_authz.py
- BUG-093 · routes/facilities.py update: scope on resulting values, regional users cannot assign another region; old/new values in ActivityLog · tests/test_audit_rc1_authz.py
- BUG-029 (server) · name required on create / update / JSON import; `utils.build_name_map` skips NULL names in bulk (no more NoneType crash) · tests/test_audit_rc1_authz.py
- BUG-045 · lat/lon blank → NULL, range-checked, 400 on bad input; equity/threshold ranges · tests/test_audit_rc1_authz.py
- BUG-009 (partial: leak) · delete_facility no longer echoes str(e) (cascade fix in RC-14 step)
- BUG-065 (partial) · bulk name maps refuse ambiguous custom-factor / facility names instead of picking the last one
- BUG-083 · regression tests/test_audit_rc3_validation.py (6 write endpoints × 5 non-finite spellings, raw NaN literal, legacy inf rows → strict JSON)
- RC-14 foundations · migration a1c4e7f20b31 (session_version, emissions.custom_factor_id FK added to existing SQLite DBs via batch rebuild, created_by/approved_by name snapshots, updated_by on scope2/3/CAP, CAP approval columns, custom_factors.is_archived, activity_log.facility_id, sbti_targets.scope_coverage, uncertainty component columns) · verified on snapshot copy: 744 rows kept, FK present, foreign_key_check clean
- BUG-009 · LevelUpgradeLog cascade with its facility · tests/test_audit_rc14_schema.py; repro exit 0
- BUG-010 / BUG-069 / BUG-106 · delete_user derives every users.id reference from metadata, fills *_by_name snapshots before nulling, logs DELETE_USER; register/logout entries now committed · tests; repros 010, 106 exit 0. BUG-069 repro measures approved_by IS NULL, which the decided policy ("delete, keep a snapshot") requires; evidence is kept in approved_by_name (test asserts it)
- BUG-114 · users.session_version + before_request check; bumped on logout, password change/reset, status change · tests (captured cookie replay → 401)
- BUG-056 · referenced custom factors cannot be deleted (409; FK, legacy id-string, payload and name references), POST /api/custom-factors/<id>/archive · tests; repro exit 0
- BUG-065 · unique active factor names (create / rename / JSON import / bulk rows incl. in-file) · tests; repro exit 0
- BUG-112 · at least one of CO2/CH4/N2O > 0 on every factor write path · tests
- BUG-020 · master report: business role + facility access, 404 unsupported, generated per request (no stale desktop file) · tests; repro exit 0
- BUG-032 · SBTi suggestion scoped by allowed facilities; target writes limited to organisation-wide approvers · tests; repro exit 0
- BUG-034 / BUG-059 · SBTi POST: finite numbers, base year ≤ current year, pathway whitelist with minimum rates (1.5C ≥ 4.2, WB2C ≥ 2.5, custom), scope_coverage · tests; repro 034 exit 0
- BUG-038 · audit trail scoped by activity_log.facility_id for regional users (list, export, filters, stats; chain verification org-wide only) · tests; repro exit 0
- BUG-039 · goals: finite > 0, whole year 1990-2100, org-wide approvers; readers tolerate legacy NaN · tests; repro exit 0
- BUG-046 · effective-date time-weighted allocation; share writes admin/superuser only, 0-100 finite, ISO dates, concurrent total ≤ 100 % · tests. Repro exits 1: its scenario inserts Sonatrach 70 % while the other partners still hold 49 % (119 %), which the audit's own "per-period sum ≤ 100" rule must reject; time-weighting verified by a hand-calculated test instead
- BUG-053 · CAP: server-decided status, validated numbers/pollutant, Verified-only compliance · tests. Repro exits 1 only because r2 (negative mass) now returns 400 without an id and the script indexes it; verified r1/r3 are stored Pending
- BUG-060 / BUG-067 / BUG-070 / BUG-074 / BUG-092 · services/maker_checker.py (one state machine: reviewable-status guard 409, creator/last-modifier segregation, per-record conditional UPDATE, approver snapshot, maker notification with reason), on_edit / delete_denied_reason applied to Scope 1/2/3 · tests; repros 060, 070, 074 exit 0. BUG-067 repro step 3 now deletes a *Pending* record (step 2 was correctly blocked, so it never became Verified); deleting Verified is covered by test
- BUG-076 · job owner check (404 for others), no server path in status · tests; repro exit 0
- BUG-057 / BUG-058 / BUG-081 / BUG-085 / BUG-111 / BUG-089 (bulk) · background_processor: explicit period parsing with range checks, in-file duplicates update the pending row, audited overwrite (Pending, approval cleared, BULK_OVERWRITE old/new values, IMPORT summary), richer keys (Scope 1 source ref, Scope 2 grid+meter, Scope 3 category+sub-category+unit), Rejected/Draft ignored, blank unit / category rejected, canonical categories · tests/test_audit_rc13_bulk.py; repros 057, 058, 065, 085, 089 exit 0. BUG-081 repro uses year 2037, now rejected by the year rule; the same scenarios with a valid year and a meter column pass (2 rows / 0.23 t, 2 rows / 3000 kWh, 2 rows / 0.23 t)
- BUG-099 (bulk + JSON import) · routes/scope2.resolve_electricity_factor: known grid → grid factor, else explicit supplier factor 0-2 kg/kWh; bulk CHP uses the server allocation · tests
- Test-setup change: tests/test_api_security.py::test_user_can_delete_own_emission gave a user with no region a delete on a region-less facility; the user now has a region and the record is Pending (expected outcome unchanged)
- RC-6 / RC-4 · services/scope1_calc.py (canonicalize aliases, validate_activity, resolve_factor, apply_result) used by POST /api/emissions/, PUT /api/emissions/<id>, /api/emissions/import; legacy_engine.compute_emissions raises MissingFactorError instead of booking 0 t when no factor resolves (Tier 3 exempt); bulk Scope 1 uses the same catalog alias lookup and never falls back from a missing custom factor · tests/test_audit_rc6_scope1_paths.py (18, hand value 1000 MMBtu NG = 53.1145 tCO2e)
  - BUG-003 repro exit 0 (2000 MMBtu → 106.229 t) · BUG-030 exit 0 · BUG-042 exit 0 · BUG-015 exit 0 (422) · BUG-050 exit 0 · BUG-068 exit 0 (422) · BUG-007 exit 0 (plausibility: >1e8 t rejected, >1e6 t flagged + Pending even for admin; same bounds in bulk / import / PUT)
  - BUG-037 · PUT and import persist the propagated 1-sigma uncertainty. Repro uses year 2045 (now rejected by the year rule); the same scenario with 2026: POST and PUT both store u_CO2 = 0.0559 and user-uncertainty case 0.2550 = expected
  - BUG-071 · explicit cache clear after create / import / bulk (bulk now add_all so the commit hook also sees rows) · test: dashboard total rises by exactly the new record right after create
  - BUG-109 (server) · unit required for catalog/custom factors; calc_inputs amount/unit must match the top-level activity
  - BUG-067 (alternative endpoint) · POST /api/emissions/bulk-delete applies delete_denied_reason per record
  - /api/emissions/import: status reported truthfully (Pending), notifications no longer crash on the non-existent user.name, audit entry committed with the data, no raw exception text (BUG-087)
  - Tests changed because they relied on zero-factor records (BUG-015): test_all_bulk_imports dedupe test and test_deep_injection Tier 1 CSV used non-catalog "Pneumatic Devices"/blank fuel; test_stress_boundary used API_FACTORS["Diesel"] (not a key → no factor at all); test_qfull zero-EF now asserts MissingFactorError; test_audit_remediation venting create now gives a fuel; custom-factor uncertainty expected value re-derived: Tier 2 record → sqrt((0.05/2)^2+(0.07/2)^2)=0.04301 (engine Tier 2 AD 7 %)
  - Open note for RC-5: bulk Diesel 1500 m3 gives 542 tCO2 where 1500 m3 = 396,258 gal x 0.138 MMBtu/gal x 73.96 kg/MMBtu ≈ 4,044 t (BUG-027 HHV basis)
