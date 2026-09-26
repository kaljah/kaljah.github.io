Independently confirmed by Agent D (Methane Auditor).
New evidence (own DB copy `agentD_fug`, via real `POST /api/emissions/`, admin, `factor_source=default`, amount 100, unit "count"):
- `process_type=fugitive`, fuel "Fugitive - Valve (Gas/Vapor)" (catalog 0.0045 kg/hr): stored CH4 = 0.00045 t. Expected annual: 100 × 0.0045 × 8760 / 1000 = 3.942 t.
- `process_type=fugitive_component`, fuel "Component - Control Valve" (1.11e-5 t/hr): stored CH4 = 0.00111 t. Expected 100 × 1.11e-5 × 8760 = 9.724 t.
- The snapshot already has Verified rows with this defect: ids 20 and 21 ("Fugitive - Valve (Gas/Vapor)", 50 and 10 sources give 0.000225 t and 0.000045 t CH4).
Additional affected components: methane loss rate %, ch4_intensity and OGMP bottom-up reconciliation (`/ogmp-metrics`, `/intensity-stats`, OGMP export). Understated fugitive CH4 makes top-down/bottom-up variance look like a large "discrepancy". Script: `audit/work/D/s11.py`.
