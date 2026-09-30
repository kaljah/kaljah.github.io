Independently confirmed by Agent D (Methane Auditor). The same substring-classification root cause also breaks the **methane** process split in `_query_intensity_stats` (`routes/dashboard.py` ~1814-1823):
`if "vent" in ptype → ch4_venting; elif "fugitive"/"leak" → ch4_fugitive; elif "flare" in ptype → ch4_flaring; else → ch4_combustion`.
- `"flare"` is not a substring of `routine_flaring` / `non_routine_flaring` / `safety_flaring` / `flaring`, so **`ch4_flaring` is 0 for every facility**.
- Flaring CH4 slip (6,765.3 t Verified in the snapshot) is reported as `ch4_combustion`.
- Pneumatics, tanks, completions, blowdown, dehydrator, unloading, AGR and drilling CH4 (vented sources) are also reported as `ch4_combustion`.
Evidence (`GET /api/dashboard/intensity-stats?year=all`, admin, `audit/work/D/s3.py`): API gives `ch4_venting 5,196.3`, `ch4_fugitive 12,872.7`, `ch4_flaring 0`, `ch4_combustion 84,320,881`. Hand classification of Verified DB rows gives vented 5,294.1, fugitive 12,872.7, flaring 6,765.3 and combustion 84,314,018.
Additional affected components: `/api/dashboard/intensity-stats` fields `ch4_venting/ch4_fugitive/ch4_flaring/ch4_combustion`, which are not rendered by the current client but are part of the API contract, and the batch-all `intensity_stats` payload.
