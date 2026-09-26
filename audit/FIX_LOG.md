# FIX LOG

One line per fix: bug · files · verification.

- BUG-016 · migrations/versions/* (idempotent), migrations/versions/9c3e1a7b5d20 (reconcile head), schema_sync.py, app.py (ensure_model_columns), Dockerfile (flask db upgrade) · repro exit 0 (existing + fresh DB reach head)
- BUG-001 · routes/emissions.py upload_start (role whitelist per scope, IT roles 403), background_processor._process_row_facilities (region restriction) · repro exit 0 (403, DB unchanged)
- BUG-083 · validation.py (new), app.py (non-finite JSON guard, FiniteJSONProvider, ValidationError->400) · repro exit 0
- BUG-099/060/043/073/097 (partial: scope2 create/update/bulk, scope3 create/update) · routes/scope2.py, routes/scope3.py, utils.py (initial_record_status, can_approve) · BUG-043 repro exit 0; others see final rerun
