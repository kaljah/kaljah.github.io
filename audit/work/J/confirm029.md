Independently confirmed by Agent J (Database).

New evidence / additional affected component: **every bulk upload (Scope 1/2/3, production, sources, ...) by a Global-scope user fails with a fatal error** while any facility has a NULL name.
- `background_processor.py:332` `fac_name_map = {fac.name.lower(): fac for fac in all_facilities}` raises `AttributeError: 'NoneType' object has no attribute 'lower'`; job ends `status="error"`, `errors=["Fatal error: 'NoneType' object has no attribute 'lower'"]`, nothing imported.
- Reproduced on agentJ copy of the snapshot (admin, POST /api/emissions/upload/start with a 1-row Scope 1 CSV) — `audit/work/J/bulk.py`.
- DB state: 13 facilities (ids 149,151-154,156,157,159,161,163,164,166,167) have name NULL or '' — schema has `facilities.name` nullable with no CHECK, and `code` is the only unique column (NULLs allowed).
- Fix should include `nullable=False` + non-empty validation on `Facility.name` (and ideally a unique constraint), plus a data clean-up of the 13 existing rows.
