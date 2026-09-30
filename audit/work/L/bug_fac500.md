# BUG-XXX — "Add Region" (create facility) form fails with HTTP 500 unless the optional Latitude/Longitude fields are filled

**Status:** Confirmed
**Severity:** Medium
**Category:** Backend
**Discovered by:** Agent L (Browser)

## Location
- `new/server/routes/facilities.py:176-177` (`latitude=data.get("latitude")`, `longitude=data.get("longitude")` passed straight to Float columns); same pattern at `:286-289` in the update route
- `new/client/src/pages/ManageData.jsx:920-941` (`handleAddFacility` posts the form with `latitude: ""`, `longitude: ""`; catch shows the generic "Failed to add region")

## Reproduction
1. Log in as audit_admin on :5190 and open Manage Data → Regions.
2. Fill Region Name, Activity, Division, Field, Location. Leave Latitude/Longitude empty (the UI does not mark them as required).
3. Click "Add Region".

## Input
Request body sent by the UI: `{"name":"AUDIT-L Plant","activity":"EP","division":"Production","field":"AUDIT-L Field","location":"West","boundary_type":"","boundary_detail":"","equity_share_pct":"","segment":"","latitude":"","longitude":"","boundary_notes":""}`

## Expected
Facility created (201) with NULL coordinates, or a clear 400 validation message.

## Actual
`POST /api/facilities` → `500 {"error":"Internal server error"}`. Server log: `sqlalchemy.exc.StatementError: (builtins.ValueError) could not convert string to float: ''` on the INSERT into facilities. The UI shows only "Failed to add region". The same form with Latitude=31.5 / Longitude=5.2 → 201 (facility id 173).

## Evidence
`audit/work/L/w2_facility.mjs` run 1 (no coordinates): `POST 500 ... request_id 77a570e5-...`; `audit/work/backend_5055.log` line ~1721 traceback. Run 2 with coordinates: `POST 201 {"id":173}`.

## Root Cause
The route does not coerce empty strings for the Float columns latitude/longitude (unlike `equity_share_pct`/`reconciliation_threshold`, which use `float(x or default)`), and the form always sends them as "".

## Impact
The only UI path for creating a facility fails in the default case (coordinates are optional and usually unknown). Users see a non-actionable error. The side effect also shows the 500 handler is reached for plain input-type errors.

## Affected Components
Manage Data → Regions → Add Region; `PUT /api/facilities/<id>` has the same pattern (assigns `data["latitude"]` directly), not separately exercised.

## Recommended Fix
Parse latitude/longitude as `float(v) if v not in (None, "") else None` (with range checks -90..90 / -180..180) in both create and update, and return 400 on invalid values. The client should also omit empty numeric fields.
