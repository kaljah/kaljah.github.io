# BUG-XXX — Bulk-upload job status and error CSV have no owner check: any logged-in account (incl. it_admin) can read another user's job rows; absolute server temp path is disclosed

**Status:** Confirmed
**Severity:** Low
**Category:** Security
**Discovered by:** Agent I (Backend/API/Security)

## Location
`new/server/routes/emissions.py:2953-2975` `upload_status()` / `upload_errors()` — `@login_required` only; `background_processor.upload_jobs[job_id]` does not store the uploader's user id, so ownership cannot be checked. `get_job_status()` returns `error_csv_path` (absolute server path).

## Reproduction
1. Role `user` starts `POST /api/emissions/upload/start` (scope 1 CSV with an unknown facility).
2. Role `it_admin` calls `GET /api/emissions/upload/status/<job_id>` and `GET /api/emissions/upload/errors/<job_id>`.
Script: `audit/repro/<BUG-ID>.py`.

## Expected
403/404 for anyone but the uploader (and admins); no server filesystem path in the response.

## Actual
Both 200 for it_admin: `skipped_preview` contains the uploaded rows (facility, quantity, reason), `error_csv_path = C:\Users\samsung\AppData\Local\Temp\tmp….csv_errors.csv`, error CSV downloaded (228 bytes).

## Evidence
```
actual: status 200 skipped_preview=[{'facility': 'NoSuchFacility', 'month': '1', 'quantity': '10', 'reason': "Region 'NoSuchFacility' not found..."}] error_csv_path=C:\Users\samsung\AppData\Local\Temp\tmpdzg0i8h2.csv_errors.csv; errors csv 200 228 bytes
```

## Root Cause
Job records lack an owner field; endpoints don't authorize.

## Impact
Exploitation requires the job UUID (uuid4, not guessable), so severity is Low; but job ids appear in logs/URLs and IT roles are meant to have zero business-data access. Path disclosure aids other attacks.

## Affected Components
`/api/emissions/upload/status/<job_id>`, `/api/emissions/upload/errors/<job_id>`, `background_processor.upload_jobs`.

## Recommended Fix
Store `user_id` in the job dict; return 404 unless `session user == owner` (or admin); drop `error_csv_path` from the response.
