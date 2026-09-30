Independently confirmed by Agent H (SBTi Auditor) — same root cause (single corporate baseline reused against a subset of actuals), second affected dimension: **region / facility scoping**.

- Regional users (role `user`/`superuser`, location West) automatically get `allowed_fids` filtering of the actuals in `/api/dashboard/sbti-trajectory`, but `base_year_emissions`, the target line and `reduction_achieved_pct` stay corporate-wide.
- Controlled data (repro scenario of this bug, `audit/repro/_H_scenario.py`): corporate 2020 = 1000 t, West 2020 = 500 t, West 2023 = 450 t. West user gets `current_actual=450, current_target=874, reduction_achieved_pct=55.0, on_track=true`; expected (West baseline 500, 4.2 %/yr) target 437, reduction 10 %, **behind**. The base year row itself shows actual 500 vs target 1000 → "Achieved", -500 t variance.
- `?facility_id=<id>` (admin) behaves the same way.
- Additional affected components: SbtiDashboard.jsx for every region-restricted login; DashboardEnhanced.jsx SBTi banner for region-restricted users.
