# Audit Agent Protocol (mandatory for every workstream)

You are one specialist in a live, parallel audit of the GHG platform at `C:/Users/samsung/Desktop/H2`
(Flask backend `new/server`, React client `new/client`). Read `C:/Users/samsung/Desktop/H2/AUDIT_SCOPE.md` and
`C:/Users/samsung/Desktop/H2/CLAUDE.md` first.

## Hard rules
1. **Discovery only.** Do NOT edit anything under `new/`, `validation/`, or the tests. Do NOT touch `new/server/ghg_app.db`
   or the user's servers on ports 5000/5173/5174. Write only inside `audit/` and append to the findings files via the tool.
2. **Work on your own DB copy:** `make_db("<your-db-name>")` → `audit/db/<name>.db`. Never use another agent's db.
3. **Do not trust** existing tests, existing calculations, dashboard values, or API responses. Derive expected values
   independently (hand math from first principles / published factors), never by calling the same function again.
4. Never claim something was tested if it wasn't. Never inflate severity.
5. Put scratch scripts in `audit/work/<your-agent-letter>/`.

## Harness
```python
import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql, get_app
c = api_client("agentX", "admin")   # roles: admin | superuser (West) | user (West) | it_admin ; ONE db per process
r = c.post("/api/...", json={...}); r.status_code, r.get_json()
sql("agentX", "select ... from emissions where id=?", (id,))
```
Calculation modules can also be imported directly after `get_app("agentX")` (server dir is on sys.path).
Browser (Playwright + local Chromium, headless) — see `audit/tools/browser_smoke.mjs` for a working login script
(login page: click `.skip-intro-btn` if present, fill `input[placeholder="Email Address"]` and `input[type="password"]`, press Enter).
Chromium: `%USERPROFILE%/AppData/Local/ms-playwright/chromium-1208/chrome-win64/chrome.exe`; import playwright from
`C:/Users/samsung/Desktop/H2/new/client/node_modules/playwright/index.mjs`. Screenshots → `audit/work/<letter>/*.png`
(you can view them with the Read tool).
Isolated stacks (already running): L browser → UI :5190 / API :5055 (db browser) · K UI → :5191 / :5056 (db ui) ·
F dashboard → :5192 / :5057 (db dashboard). Only use the stack assigned to you. Accounts: `audit_admin@audit.local`,
`audit_superuser@audit.local`, `audit_user@audit.local`, `audit_itadmin@audit.local`, password `AuditPass!2026`.

## Reporting — IMMEDIATELY on confirmation, then keep auditing
1. Before filing, `grep "^# BUG-" C:/Users/samsung/Desktop/H2/AUDIT_FINDINGS.md` and read any entry that may share
   your root cause. **If it's the same root cause, do NOT file a new bug**: write a note and run
   `python C:/Users/samsung/Desktop/H2/audit/tools/report_bug.py --confirm BUG-NNN note.md`
   (note: "Independently confirmed by Agent X (<name>)" + new evidence + additional affected components).
2. For a new confirmed bug write a draft file starting with `# BUG-XXX — <short title>` (literal XXX) in exactly this format:

```
# BUG-XXX — [SHORT TITLE]

**Status:** Confirmed
**Severity:** Critical / High / Medium / Low
**Category:** Calculation / Emissions / Methane / Carbon Intensity / Dashboard / Uncertainty / SBTi / UI / Backend / API / Database / Security / Performance
**Discovered by:** Agent X (<name>)

## Location
## Reproduction
1.
## Input
## Expected
## Actual
## Evidence
## Root Cause
## Impact
## Affected Components
## Recommended Fix
```
   then run `python C:/Users/samsung/Desktop/H2/audit/tools/report_bug.py <draft.md>` — it prints the assigned ID.
3. Save a runnable reproduction as `audit/repro/<BUG-ID>.py` (or `.mjs`) that prints expected vs actual and exits non-zero
   while the bug exists. It must use the harness + its own db copy (never app source edits).
4. Severity guide: Critical = wrong reported emissions/totals at material scale, data corruption, auth bypass/privilege
   escalation, cross-tenant data exposure. High = wrong numbers in a specific pathway / metric, broken core workflow,
   RBAC gap. Medium = edge-case miscalculation, validation gap that admits bad data, misleading UI. Low = cosmetic / minor.
5. Not fully proven → append ONE line to `C:/Users/samsung/Desktop/H2/audit/SUSPECTED_AND_QUESTIONS.md`
   (`- [SUSPECTED] (Agent X) title — evidence — what would confirm`) or `[DESIGN-Q]` for possibly-intended behavior.
   Use `>>` append only; never rewrite the file.
6. Distinguish **code bugs** from **bad seed data**: if a strange number comes from absurd stored data, check whether the
   application *should have rejected/flagged* it (validation gap = bug) and whether the calculation on that data is right.

## Final report (your last message)
Return: (a) list of BUG IDs you filed and confirmations you added; (b) coverage table of what you actually verified
(item → method → result); (c) what you could NOT verify and why. Keep it factual and concise.
