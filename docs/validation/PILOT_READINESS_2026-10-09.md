# Pilot readiness check (2026-10-09)

Bug hunt before the Sonatrach pilot, run against a production-mode install, then fixes for every finding.

## How it was run

- `FLASK_ENV=production`, PostgreSQL 16 (fresh database, `flask db upgrade`), Redis for rate limits, `gunicorn -w 4`.
- Two regions (North, South), one facility each, and a user per role: admin, superuser (North), user (North), user (South), IT, IT admin, IT manager.
- Checks: schema against the models, every GET route as every role (156 routes, by name and by totals), cross-region writes and approvals, sign-in and session behaviour, hand-checked calculations, dashboard vs records list vs PDF, AR5 to AR6 switch across workers, CSV upload with French number formats, re-upload, backup and restore (including a broken backup), malformed input on every POST/PUT route and on the query parameters of every GET route.

## What held

- Migrations from an empty PostgreSQL database reach head; the schema matches the models (0 differences).
- No cross-region read or write: admin sees 116.629 t, each region its own 58.315 t; IT roles see no operational data; self-promotion is ignored; IT staff cannot create or reset admin / superuser accounts. Logout revokes old cookies.
- Calculations checked by hand (natural gas, diesel, flaring, GWP-20). Dashboard, records list and PDF agree; switching AR5 to AR6 recalculates consistently on all workers.
- Backup and restore round-trip exactly (`pg_dump --clean`), including over a populated database.

## Findings and fixes

| # | Severity | Finding | Fix |
|---|---|---|---|
| F6 | High | The import guessed the decimal separator: `1,000` read as 1000 (1 for a French user), `1.000` as 1. The check step reported the rows as fine. | The wizard asks for the file's decimal format (`decimal_mark`); numbers are read strictly by it and a value that does not fit is reported. Without a choice (API clients) an ambiguous `1,000` is refused. |
| F11 | High | Duplicate detection missed fuels written by an alias (`Diesel` vs the stored `Diesel (No. 2 Fuel Oil)`): re-uploading a monthly file inserted those rows again. | New rows are keyed by the stored catalog name, like the existing ones. |
| F12 | High | The audit "hash chain" was recomputed from the current rows, ignored `details`, and always answered "verified" / "anchored". A direct database edit went unnoticed. Exports printed an "ISO 14064-3 / ISAE 3410 ... digitally sealed" digest of the record count and the time. | Each entry is sealed when written (`entry_hash` over the full content, chained by `prev_hash`; advisory lock against concurrent workers). Verification reports edits, deletions and insertions. PostgreSQL trigger makes the table append-only (except clearing `user_id` on user deletion). Existing rows are sealed by migration `d4e8a1b7c2f0`. Exports carry a fingerprint of their data, recorded in a `REPORT` audit entry; the conformance claims are removed. Audit Trail page: "Verify integrity" button. |
| F3 | High | Sign-in limit of 20 per 15 minutes per address, successful sign-ins included: behind a shared address the whole site was locked out. | Only failed sign-ins count (`LOGIN_RATE_LIMIT`, default 50 per 15 minutes per address). |
| F4 | High | `ProxyFix` was always on in production, so a forged `X-Forwarded-For` bypassed the limit; no per-account lockout. | `X-Forwarded-*` trusted only with `TRUSTED_PROXIES` (production warns when unset). Per-account lockout after 10 failures from any address (`LOGIN_ACCOUNT_LIMIT`). Failures are audited (`FAILED_LOGIN`). |
| F9 | High | `restore.py` reported success after a partial restore (empty users table). | `psql` with `ON_ERROR_STOP=1` and `--single-transaction`: the first error stops the restore and nothing changes. |
| F1 | Medium | `seed_admin.py` created `it@ghg.com` (role `it`) in production with a password printed to the console. | Created only when `IT_EMAIL` and `IT_PASSWORD` are both set. |
| F2 | Medium | `SEED_ADMIN=true` re-enabled a disabled admin at every restart. | Existing accounts are left unchanged. |
| F5 | Medium | Map tiles from Google's tile server without an API key: blank offline, against Google's terms. | Tiles from `MAP_TILE_URL` (`/api/map-config`); unset, the map shows the facilities without a basemap. |
| F7 | Low | Batch approve answered success with 0 records and no reason. | Each skipped record is listed with its reason; the review screens show them. |
| F13 | Low | 11 write endpoints and 50 read-parameter cases answered 500 to malformed input (non-JSON body, unknown facility, junk ids, `year=abc`, NUL characters). | Non-JSON bodies read as `{}`; unknown facilities 404; ids validated; NUL characters refused; dashboard / production filters validated centrally. Both fuzz sweeps: 0 server errors. |
| F14 | Low | Session cookie `SameSite=None`; CSP allowed Google Fonts and any https image. | `SameSite=Lax`; CSP without external sources. |
| F10 | Low | `backup.py --output` documented but not implemented. | `--output-dir`. |
| F15 | Medium | A manual Scope 1 entry without a quantity was saved as a Verified record of 0 t. | Refused (`'quantity' is required`) unless the entry is a Tier 3 / engineering calculation with its own inputs. A quantity of 0 is still accepted. |
| F16 | Low | Editing a Scope 1, 2 or 3 record to an unknown or malformed facility answered 500. | 404 for an unknown facility, 422 for a malformed id (`utils.facility_access_error`). |
| F17 | Low | The upload error file echoed uploaded cells unescaped; an admin can download any user's file, so a cell like `=HYPERLINK(...)` ran as a formula in Excel. | Cells are escaped like the other exports. |
| F18 | Low | A second sweep that edited existing records found 40 more 500s: text longer than its column, lists or objects in text fields, numbers in name fields (PostgreSQL writes 1e308 out as 309 digits). | Every length-limited text column checks the value when it is assigned (`services/column_guard.py`): too long or not text is a 400 naming the field; numbers are stored as their text. Custom factor names and Scope 1 fuel types must be text. Edit sweep: 0 server errors. |
| F8 | Decision | Admin manual entries are saved as Verified without a second reviewer (uploads go to Pending). | Kept as is (owner decision 2026-10-09). |

Regression tests: `new/server/tests/test_pilot_readiness_2026_10_09.py`, `new/client/src/__tests__/importWizardDecimalMark.test.tsx`, `auditIntegrityCheck.test.tsx`, `reviewResultSkipped.test.ts`.

## Still open for the install

- Set `TRUSTED_PROXIES=1` behind nginx, and `ALLOWED_ORIGINS` to the Sonatrach hostname.
- The web server that serves the SPA must send its own `Content-Security-Policy` (Flask's covers API responses only).
- `MAP_TILE_URL`: an internal tile server, or none.
- `WTF_CSRF_SSL_STRICT` is still `False` (it dates from the cross-domain GitHub Pages setup). Turn it on once the proxy passes the right host and scheme, and check that saving works.
- The audit chain attests to the log from the migration onward, not to edits made before it.
- The OGMP workbook states "Operational Control (GHG Protocol Corporate Standard)" as the reporting boundary; the boundary approach (readiness plan A3) is still to be confirmed by HSE.
