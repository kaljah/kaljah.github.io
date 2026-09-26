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
