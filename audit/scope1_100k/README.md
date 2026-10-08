# Scope 1 bulk-import audit tooling (100,000 rows)

Scripts from the 2026-10-01 audit (findings and results: `docs/validation/SCOPE1_100K_BULK_AUDIT_2026-10-01.md`).
They are kept so the audit can be repeated; they are not part of the application or of CI.

- `gen.py` builds the 100,000-row dataset and an `expected.jsonl` oracle (seeded, so it can be regenerated;
  the generated files are not committed). Run `python gen.py --out out`.
- `harness.py`, `api_upload.py`, `check.py` import it through the HTTP API and compare every stored record with the oracle.
- `ui_*.mjs`, `ui_compare.py` do the same through the Scope 1 import wizard in headless Chromium.
- `form_parity.*`, `exhibits_e2e.py`, `probes.py`, `remaining_checks.py`, `pg_100k.py` cover manual-form vs CSV parity,
  Compendium exhibits, edge probes and a PostgreSQL run.

Run them against a throwaway database, never one you care about: they create and delete records.
The generated `*.csv`, `*.jsonl*` and `results/` output is git-ignored.
