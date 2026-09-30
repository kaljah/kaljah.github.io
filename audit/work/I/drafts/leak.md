# BUG-XXX — Malformed input on create endpoints returns HTTP 500/409 with raw exception and SQL text (≈40 handlers return `str(e)`)

**Status:** Confirmed
**Severity:** Low
**Category:** API
**Discovered by:** Agent I (Backend/API/Security)

## Location
Handlers that catch `Exception` and return `jsonify({"error": ... str(e)})` — 41 occurrences, e.g. `routes/emissions.py:962,3187`, `routes/scope2.py:156,287,475,666`, `routes/scope3.py:155,299,473`, `routes/data.py:343,563,642,846,880`, `routes/managedata.py:102,138,222,347,372,426,516,724,766,808,830,890,950,983,1073`, `routes/qaqc.py:616,738,812,906`, `routes/dashboard.py:341,972,1103`. The global handler in `app.py` correctly hides details, but these local handlers bypass it. Types are not validated before the DB insert. (BUG-009 is the facility-delete instance of the same leak; this covers the create/validation paths.)

## Reproduction
Admin (script `audit/repro/<BUG-ID>.py`):
1. `POST /api/emissions/ {"process_type": [] ...}`
2. `POST /api/scope2 {"facility_id": "abc", ...}`
3. `POST /api/data/production {"year": null, ...}`
4. `POST /api/goals {"year": "abc"}`
5. `POST /api/sources {"facility_id": -1e308, "name": "S"}`

## Expected
400 with a field-level validation message; no internals.

## Actual
```
/api/emissions/: HTTP 500 "(sqlite3.ProgrammingError) Error binding parameter 7: type 'list' is not supported\n[SQL: INSERT INTO e..."
/api/scope2: HTTP 500 "(sqlite3.IntegrityError) FOREIGN KEY constraint failed\n[SQL: INSERT INTO scope2_emissions (fac..."
/api/data/production: HTTP 409 "Concurrency conflict: (sqlite3.IntegrityError) NOT NULL constraint failed: production_data.year\n[SQL: ..."
/api/goals: HTTP 500 "invalid literal for int() with base 10: 'abc'"
/api/sources: HTTP 500 "Failed to add source: Python int too large to convert to SQLite INTEGER"
```
A fuzz of 15 create endpoints × 8 bad values produced 149 HTTP 500s and 71 responses containing internal exception/SQL text (`audit/work/I/fuzz.out`). Missing `year` on production is misreported as a "Concurrency conflict" (409).

## Root Cause
No schema validation of request types; broad `except Exception` handlers echo the exception.

## Impact
Schema/table/column disclosure; wrong status codes (500/409 instead of 400) hamper clients and monitoring.

## Affected Components
Most create/update/bulk endpoints in emissions, scope2, scope3, data, managedata, qaqc, dashboard.

## Recommended Fix
Validate types/required fields up front (400); log exceptions server-side and return a generic message with request id.
