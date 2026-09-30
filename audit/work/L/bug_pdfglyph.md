# BUG-XXX — Reports "PDF Report" prints every unit and gas name with a missing-glyph box: "tCO■e", "CO■", "CH■", "N■O"

**Status:** Confirmed
**Severity:** Low
**Category:** UI
**Discovered by:** Agent L (Browser)

## Location
`new/server/routes/reports.py` (`GET /api/reports/export`, reportlab; e.g. L141-142 `f"{scope1_total:,.2f} tCO₂e"`) — Unicode subscript digits (U+2082 ₂, U+2084 ₄) are drawn with the built-in Helvetica font, which has no glyphs for them.

## Reproduction
1. :5190 as audit_admin → Reports → Filter & Group Data: Year 2025, Region AUDIT-L Plant.
2. Click "PDF Report" → `GET /api/reports/export?scope=all&year=2025&facility_id=173` 200 → `emissions_2025_all.pdf`.
3. Open the PDF.

## Input
Any data.

## Expected
"tCO₂e", "CO₂", "CH₄", "N₂O" (or ASCII "tCO2e") in the summary table and detail headers.

## Actual
Rendered page shows "58.54 tCO■e", "Total CO■ Gas Mass", "tonnes CH■", "N■O" (screenshot `audit/work/L/rep_pdf.png`; text extraction gives "tCOne", "CHn", "NnO"). The numbers themselves match the DB/dashboard (S1 58.54, S2 11,845.52, S3 1.85 for facility 173 / 2025, Verified only).

## Evidence
`audit/work/L/rep.pdf`, `rep_pdf.png`; `audit/work/L/w22_export.mjs`.

## Root Cause
reportlab standard Type 1 fonts only cover Latin-1; subscript characters need an embedded TTF (e.g. DejaVuSans) or `<sub>` markup in Paragraphs.

## Impact
The regulatory-facing PDF export looks broken on every unit label; recipients cannot tell CO₂ from CH₄ columns reliably in the detail table.

## Affected Components
`/api/reports/export` PDF; possibly other reportlab outputs using the same strings (not checked individually).

## Recommended Fix
Register and use a Unicode TTF font in the PDF styles, or render subscripts with `<sub>2</sub>` / ASCII "CO2e".
