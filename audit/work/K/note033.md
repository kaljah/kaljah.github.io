Independently confirmed by Agent K (Frontend/UI).

New affected component: the OGMP 2.0 Excel export (`GET /api/reports/ogmp-export`, `routes/reports.py` ≈L814-913) builds gas production with
`GAS_UNIT_TO_M3.get(str(p.gas_unit or "mscf").lower(), 28.3168)`; the table has "m3" but not the "m³" spelling that the Manage Data production form stores
(`ManageData.jsx` gas/oil unit `<option value="m³">`), so m³ production rows are multiplied by 28.3168 in the export as well (methane intensity denominator 28× too high → intensity 28× too low).
The Manage Data "Convert m³" helper converts to mscf correctly (×0.0353147) — only rows saved with the m³ unit option are affected.
Client-side fix option: send the ASCII value "m3" from the unit `<select>` (display label can stay "m³").
