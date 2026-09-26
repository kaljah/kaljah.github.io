"""Builds IMPLEMENTATION_PLAN.md from AUDIT_FINDINGS.md + lead-auditor phase/root-cause mapping + final re-run results."""
import csv
import os
import re

H2 = r"C:/Users/samsung/Desktop/H2"
FIND = open(os.path.join(H2, "AUDIT_FINDINGS.md"), encoding="utf-8").read()
RERUN = os.path.join(H2, "audit/work/rerun/results.tsv")
REPRO = os.path.join(H2, "audit/repro")

# ---------------------------------------------------------------- parse findings
bugs = {}
for part in re.split(r"(?m)^(?=# BUG-\d{3})", FIND)[1:]:
    m = re.match(r"# (BUG-\d{3}) — (.*)", part)
    bid, title = m.group(1), m.group(2).strip()
    main, *addenda = part.split("### Additional confirmation")
    confirm_blocks = re.findall(r"(?ms)^### Additional confirmation \((BUG-\d{3})\)", FIND)
    field = lambda k: (re.search(r"\*\*" + k + r":\*\*\s*(.*)", main) or [None, ""])[1].strip()

    def sec(name):
        s = re.search(r"(?ms)^## " + name + r"\s*\n(.*?)(?=^## |^---\s*$|\Z)", main)
        return s.group(1).strip() if s else ""

    bugs[bid] = dict(
        id=bid, title=title, sev=field("Severity"), cat=field("Category"), by=field("Discovered by"),
        loc=sec("Location"), expected=sec("Expected"), actual=sec("Actual"), root=sec("Root Cause"),
        impact=sec("Impact"), comps=sec("Affected Components"), fix=sec("Recommended Fix"),
        confirmations=confirm_blocks.count(bid),
    )

# ---------------------------------------------------------------- re-run results
rerun = {}
if os.path.exists(RERUN):
    for row in csv.reader(open(RERUN, encoding="utf-8"), delimiter="\t"):
        if len(row) >= 2 and row[0].startswith("BUG-"):
            rerun[row[0][:7]] = int(row[1])
repro_files = {f[:7]: f for f in sorted(os.listdir(REPRO)) if re.match(r"BUG-\d{3}", f)}

EXTERNAL = {"BUG-100", "BUG-101", "BUG-102", "BUG-103", "BUG-104"}
DUPLICATE = {"BUG-035": "BUG-033"}

# ---------------------------------------------------------------- lead-auditor mapping
PHASES = [
    ("P0", "Prerequisites (do first — other fixes depend on these)", ["BUG-016"]),
    ("P1", "Critical data-integrity & security defects",
     ["BUG-001", "BUG-015", "BUG-077", "BUG-020", "BUG-053", "BUG-067", "BUG-099", "BUG-083", "BUG-114", "BUG-078"]),
    ("P2", "Critical & high calculation errors",
     ["BUG-066", "BUG-011", "BUG-012", "BUG-023", "BUG-027", "BUG-047", "BUG-048", "BUG-049", "BUG-063", "BUG-110", "BUG-090"]),
    ("P3", "Systemic calculation / business-logic defects",
     ["BUG-003", "BUG-030", "BUG-037", "BUG-042", "BUG-068", "BUG-024", "BUG-051", "BUG-050", "BUG-013", "BUG-005",
      "BUG-109", "BUG-091", "BUG-096", "BUG-097"]),
    ("P4", "Backend / API defects",
     ["BUG-007", "BUG-029", "BUG-073", "BUG-085", "BUG-111", "BUG-112", "BUG-034", "BUG-039", "BUG-045", "BUG-060",
      "BUG-070", "BUG-074", "BUG-093", "BUG-032", "BUG-038", "BUG-046", "BUG-076", "BUG-106", "BUG-087"]),
    ("P5", "Database defects",
     ["BUG-057", "BUG-081", "BUG-089", "BUG-058", "BUG-065", "BUG-056", "BUG-009", "BUG-010", "BUG-069"]),
    ("P6", "Emissions / reporting defects",
     ["BUG-044", "BUG-084", "BUG-002", "BUG-006", "BUG-113", "BUG-031", "BUG-052", "BUG-075"]),
    ("P7", "Dashboard / intensity defects",
     ["BUG-040", "BUG-004", "BUG-017", "BUG-026", "BUG-094", "BUG-033", "BUG-036", "BUG-054", "BUG-041", "BUG-061",
      "BUG-071", "BUG-079", "BUG-064", "BUG-072", "BUG-080", "BUG-086", "BUG-088"]),
    ("P8", "Uncertainty / SBTi defects",
     ["BUG-008", "BUG-018", "BUG-025", "BUG-043", "BUG-055", "BUG-062", "BUG-014", "BUG-019", "BUG-028", "BUG-059"]),
    ("P9", "UI defects",
     ["BUG-092", "BUG-105", "BUG-107", "BUG-021", "BUG-095", "BUG-115", "BUG-022", "BUG-082", "BUG-098", "BUG-108"]),
]

ROOT_CAUSES = {
    "RC-1": ("No central input validation", "Numeric fields parsed with bare float() (NaN/Inf pass `< 0` checks), no required-field / "
             "year / month / unit / plausibility validation, and bulk import applies weaker rules than the manual API.",
             ["BUG-007", "BUG-029", "BUG-034", "BUG-039", "BUG-043", "BUG-045", "BUG-050", "BUG-073", "BUG-083", "BUG-085",
              "BUG-087", "BUG-099", "BUG-109", "BUG-111", "BUG-112"],
             "One shared validator module (`new/server/validation.py`): finite numbers, ranges, required fields, year 1900–(current+1), "
             "month 1–12, unit whitelist, per-unit plausibility caps; used by every create / PUT / JSON-bulk / file-bulk path; generic "
             "error bodies with request id."),
    "RC-2": ("Maker-checker / status policy duplicated per route", "Each scope and route decides status on its own; no guard on "
             "already-decided records; no concurrency control; outcome never reaches the maker.",
             ["BUG-053", "BUG-060", "BUG-067", "BUG-070", "BUG-074", "BUG-058", "BUG-092", "BUG-031"],
             "One status-policy helper (initial status by role and channel, allowed transitions, approver ≠ creator/last-modifier), "
             "conditional UPDATE … WHERE status IN (…) for approve/reject, notification to `created_by`."),
    "RC-3": ("Authorization / region scoping applied inconsistently", "`@login_required` alone on sensitive endpoints; "
             "`get_allowed_facility_ids` not applied to every read/write; client-side-only session.",
             ["BUG-001", "BUG-020", "BUG-032", "BUG-038", "BUG-046", "BUG-076", "BUG-093", "BUG-114", "BUG-106"],
             "Role + facility-scope decorator applied uniformly (inventory in `audit/notes/I_endpoints.md`); server-side session "
             "revocation (`session_version`)."),
    "RC-4": ("Units are not parsed / converted in one place", "Factor and activity units are matched by substring in several "
             "places; scale prefixes, time denominators, energy units, subscripts and rate-vs-annual units are mishandled; client "
             "labels disagree with what the server assumes.",
             ["BUG-011", "BUG-027", "BUG-033", "BUG-047", "BUG-048", "BUG-049", "BUG-051", "BUG-063", "BUG-066", "BUG-091",
              "BUG-096", "BUG-097"],
             "Single unit parser/normaliser in `calculations/units.py` (canonical unit tokens, numerator/denominator, scale "
             "prefixes, time basis); unknown units rejected, never passed through 1:1; custom factors stored with explicit units."),
    "RC-5": ("Edit / recalculation path diverges from the create path", "PUT re-computes from a stale `source_payload`, drops "
             "custom-factor ids, stores different uncertainty semantics, and create persists different fields than it computes from.",
             ["BUG-003", "BUG-030", "BUG-037", "BUG-042", "BUG-071"],
             "One `build_calc_payload()` + `persist_calc_result()` used by create, PUT, import and bulk; explicit cache "
             "invalidation after every write."),
    "RC-6": ("Client and server hold separate copies of catalogs, constants and formulas", "Tier 1 catalog, GWP tables, "
             "field names, preview formulas and segment rules are duplicated and have drifted.",
             ["BUG-015", "BUG-090", "BUG-110", "BUG-082", "BUG-012", "BUG-013", "BUG-005", "BUG-086", "BUG-080"],
             "Serve catalogs/constants from the API; server preview endpoint instead of client-side formulas; reject unknown "
             "`calc_inputs` keys."),
    "RC-7": ("Dashboard filters not applied through one base query", "Each dashboard sub-query re-implements year / segment / "
             "activity / division / pending / GWP filtering, so panels on the same page disagree.",
             ["BUG-004", "BUG-017", "BUG-026", "BUG-036", "BUG-040", "BUG-041", "BUG-054", "BUG-061", "BUG-064", "BUG-072",
              "BUG-079", "BUG-094", "BUG-088"],
             "One filtered base query per scope (joined through `Facility`) that every panel derives from; invariant tests "
             "(parts sum to totals under every filter combination)."),
    "RC-8": ("Uncertainty aggregation model", "Correlated EF uncertainty treated as independent; max-of-gases instead of "
             "CO2e weighting; inconsistent fraction/percent and k; overrides ignored.",
             ["BUG-008", "BUG-018", "BUG-025", "BUG-037", "BUG-043", "BUG-055", "BUG-062"],
             "One uncertainty service (IPCC Approach 1 with correlation by EF source, CO2e-weighted per gas, stored as 1σ "
             "fraction, displayed as 95 % k=2) used by the Uncertainty page, QA dashboard and result panel."),
    "RC-9": ("SBTi period / scope logic", "Progress year, scope coverage, empty data and pathway validation are not modelled.",
             ["BUG-014", "BUG-019", "BUG-028", "BUG-034", "BUG-059"],
             "Store scope coverage with the target; progress on the last complete year; explicit 'no data' state; validated pathway."),
    "RC-10": ("Bulk import integrity", "Duplicate keys too coarse or not updated in-batch, name-based factor lookup, silent "
              "defaults, no audit log, canonical forms differ from the manual API.",
              ["BUG-057", "BUG-058", "BUG-065", "BUG-081", "BUG-085", "BUG-089", "BUG-111", "BUG-001"],
              "Bulk rows go through the same validator + persistence helpers as manual create (RC-1, RC-5); natural-key unique "
              "indexes; per-row audit log."),
    "RC-11": ("Referential integrity on delete", "Hard deletes with hand-maintained clean-up lists; ids reused; name-based references.",
              ["BUG-009", "BUG-010", "BUG-056", "BUG-069"],
              "Soft-delete/deactivate users and factors; real FKs with explicit ON DELETE; AUTOINCREMENT ids."),
    "RC-12": ("Reports print unverified, mislabelled or fabricated content", "Client PDF generator hard-codes claims and "
              "mislabels scope/period; granular intensities invent constants.",
              ["BUG-077", "BUG-078", "BUG-044", "BUG-084", "BUG-002", "BUG-006", "BUG-113"],
              "Reports built only from server aggregates with explicit period/status labels; no literal performance claims."),
}

PHASE_RISK = {
    "P0": "Stamping existing databases wrongly can skip or duplicate columns. Test on copies of every deployed DB.",
    "P1": "Tightening authorization can lock out legitimate workflows (bulk facility import by superusers, report downloads). "
          "Re-run the full role matrix after the change.",
    "P2": "Correcting a formula changes every stored value computed by it. Stored records are NOT recomputed automatically — "
          "a controlled recalculation job with before/after diff and audit log is required, and reported totals for past "
          "periods will move.",
    "P3": "Shared payload/persistence helpers touch every Scope 1 write path (create, PUT, import, bulk).",
    "P4": "Stricter validation will reject data that is accepted today (including existing bulk templates); existing bad "
          "rows need a data-cleanup decision rather than silent correction.",
    "P5": "New unique constraints fail on existing duplicate rows — de-duplicate (with owner sign-off) before adding them.",
    "P6": "Report output changes visibly; stakeholders may compare against previously issued PDFs.",
    "P7": "Dashboard numbers change under filters; users will see different totals than before (they were wrong before).",
    "P8": "Uncertainty and SBTi progress figures will change materially; communicate before release.",
    "P9": "Mostly local UI changes; watch for layout regressions and keyboard focus traps.",
}

RC_RISK = {
    "RC-1": "Stricter validation will reject inputs accepted today (existing bulk templates, integrations, scripts). Existing invalid rows remain until a cleanup job runs.",
    "RC-2": "Status-policy changes alter who can approve and what edits reset records to Pending; re-run the full maker-checker role matrix (user, superuser, admin, it roles) for Scope 1/2/3, CAP and bulk.",
    "RC-3": "Tightening authorization can lock out legitimate workflows (superuser bulk facility import, report downloads, audit trail). Re-run the endpoint role matrix in `audit/notes/I_endpoints.md`.",
    "RC-4": "A central unit parser changes results for every unit it now interprets correctly; stored records keep old values until a controlled recalculation. Unknown units that used to pass through will now be rejected.",
    "RC-5": "Shared payload/persistence helpers touch every Scope 1 write path (create, PUT, import, bulk); edits to existing records will now produce different (correct) values than before.",
    "RC-6": "Removing a client-side catalog/formula can remove options users rely on; every factor still offered must exist server-side before the switch. Previews will change to server-computed values.",
    "RC-7": "Dashboard numbers under filters will change (they were inconsistent before). Watch query performance when all panels derive from one filtered base query.",
    "RC-8": "Reported uncertainty percentages will change materially (some up, some down); QA and Uncertainty pages must switch together.",
    "RC-9": "SBTi progress and on-track status will change; previously shown 'ON TRACK' states may flip.",
    "RC-10": "Bulk imports that previously succeeded may now fail row validation or de-duplicate differently; unique indexes fail on existing duplicates until cleaned.",
    "RC-11": "Soft-delete changes list/lookup queries everywhere (must filter inactive rows).",
    "RC-12": "Report output changes visibly; stakeholders may compare against previously issued PDFs.",
}

DB_NOTES = {
    "BUG-016": "Baseline Alembic revision matching current models; stamp existing DBs; stop import-time create_all/ALTER.",
    "BUG-009": "ON DELETE behaviour for `level_upgrade_logs.facility_id` (cascade or block with 409).",
    "BUG-010": "Data policy: delete with snapshot — ON DELETE SET NULL for every FK referencing `users.id` (derive the list from metadata), combined with the BUG-069 snapshot columns.",
    "BUG-029": "Data policy: block new bad data only — no NOT NULL constraint (13 existing nameless facilities would violate it). Enforce a required name in the API and bulk import; the UI tolerates legacy NULL names.",
    "BUG-038": "Add nullable `facility_id` to `activity_log`, filled for new entries only (no backfill, per data policy); legacy entries without facility are visible to unrestricted roles only.",
    "BUG-056": "Add `emissions.custom_factor_id` FK; AUTOINCREMENT on `custom_factors.id`.",
    "BUG-057": "Data policy: block new bad data only — no unique index (existing duplicate groups would violate it). Enforce the natural key in application code (in-batch map + existing-key check). Existing duplicates remain.",
    "BUG-065": "Data policy: block new bad data only — application-level case-insensitive uniqueness check on create/rename/import; no DB constraint while duplicates exist.",
    "BUG-069": "Data policy: delete with snapshot — add `approved_by_name`, `approved_by_email`, `created_by_name`, `created_by_email` columns to emission tables, filled at create/approval time; user delete keeps SET NULL on the FK. Historic rows are not backfilled.",
    "BUG-074": "Optional `version` column on emissions for optimistic locking (or conditional UPDATE only).",
    "BUG-081": "Extend the Scope 2/3 natural key (sub_category, meter/grid_region, NAICS) in application code; no DB unique index (data policy: existing rows untouched).",
    "BUG-089": "Data policy: block new bad data only — no migration of stored values. Normalise on every write; aggregations must map legacy '6' / 'Category 6' to one key when grouping so breakdowns stop splitting.",
    "BUG-114": "Per-user `session_version` column (or server-side session table).",
    "BUG-019": "Store scope coverage (and optional per-scope baselines) on `sbti_targets`.",
    "BUG-063": "Custom factor numerator/denominator unit columns for new/edited factors; existing bare-unit factors are not migrated (data policy) — the calculator must reject, not guess, factors whose unit it cannot interpret.",
    "BUG-046": "Validation only (no schema change) unless a per-period sum constraint is enforced in DB.",
}


def files_in(text):
    return sorted(set(re.findall(r"new/(?:server|client)/[\w./\-]+\.(?:py|jsx|js|mjs|css)", text)))


def classify(files):
    out = {"db": [], "backend": [], "frontend": [], "calc": []}
    for f in files:
        if "new/client/" in f:
            out["frontend"].append(f)
        elif "/calculations/" in f or "emission_factors" in f or "electricity_factors" in f:
            out["calc"].append(f)
        elif "models.py" in f or "/migrations/" in f:
            out["db"].append(f)
        else:
            out["backend"].append(f)
    return out


def squash(t, n):
    t = re.sub(r"\s+", " ", t).strip()
    return t if len(t) <= n else t[: n - 1].rstrip() + "…"


def status_line(bid):
    f = repro_files.get(bid)
    if bid in rerun:
        rc = rerun[bid]
        if rc == 1:
            return "**Still present** — `audit/repro/%s` re-run on the final code: bug reproduced." % f
        if rc == 0:
            return "**Not reproduced on the final code** — `audit/repro/%s` exited 0. Likely fixed by code changes made during the audit; confirm and close." % f
        return "**Re-run inconclusive** (exit %d) — `audit/repro/%s`; see `audit/work/rerun/%s.log`." % (rc, f, f.rsplit(".", 1)[0])
    if f and f.endswith(".mjs"):
        return "**Confirmed on the post-change code by the browser agent** (`audit/repro/%s`); not re-run in the final pass (needs a live UI stack)." % f
    return "No re-run available."


def rc_of(bid):
    return [k for k, v in ROOT_CAUSES.items() if bid in v[2]]


def section(b, phase):
    bid = b["id"]
    files = files_in(b["loc"] + " " + b["comps"] + " " + b["root"] + " " + b["fix"])
    cl = classify(files)
    rcs = rc_of(bid)
    repro = repro_files.get(bid)
    ui = bool(cl["frontend"]) or (repro or "").endswith(".mjs")
    L = []
    L.append(f"# {bid} — {b['title']}\n")
    L.append(f"**Severity:** {b['sev']} · **Category:** {b['cat']} · **Phase:** {phase} · "
             f"**Root cause group:** {', '.join(rcs) if rcs else '—'} · **Found by:** {b['by']}"
             + (f" · **Independent confirmations:** {b['confirmations']}" if b["confirmations"] else "") + "\n")
    L.append(f"**Current status:** {status_line(bid)}\n")
    if bid == "BUG-033":
        L.append("_BUG-035 (filed concurrently by Agent F) is a duplicate of this bug and is merged here; its prior-year conversion path and case-sensitive matching are in scope of this fix._\n")
    L.append("## Problem\n")
    L.append(squash(b["title"], 400) + "\n")
    if b["actual"]:
        L.append("- **Actual:** " + squash(b["actual"], 600))
    if b["expected"]:
        L.append("- **Expected:** " + squash(b["expected"], 600))
    L.append("\n## Root Cause\n")
    L.append(squash(b["root"], 1200) or "See AUDIT_FINDINGS.md.")
    L.append("\n## Affected Files\n")
    L.append("\n".join(f"- `{f}`" for f in files) if files else "- See Location in AUDIT_FINDINGS.md: " + squash(b["loc"], 300))
    L.append("\n## Affected Features\n")
    L.append(squash(b["impact"], 700) or squash(b["comps"], 500))
    L.append("\n## Required Changes\n")
    L.append(squash(b["fix"], 1400) or "See root-cause group.")
    if rcs:
        L.append("\nImplement through the shared fix for " + ", ".join(f"{r} ({ROOT_CAUSES[r][0]})" for r in rcs) + " rather than a local patch.")
    L.append("\n## Database Changes\n")
    L.append(DB_NOTES.get(bid, "None required." if not cl["db"] else "Model change in " + ", ".join(f"`{f}`" for f in cl["db"]) + " — ship as an Alembic migration (requires BUG-016)."))
    if bid in {"BUG-009", "BUG-010", "BUG-019", "BUG-038", "BUG-056", "BUG-063", "BUG-069", "BUG-074", "BUG-114"}:
        L.append(" Ship as an Alembic migration (requires BUG-016).")
    L.append("\n## Backend Changes\n")
    L.append(("Changes in " + ", ".join(f"`{f}`" for f in cl["backend"]) + " as described above.") if cl["backend"] else "None beyond the above.")
    L.append("\n## Frontend Changes\n")
    L.append(("Changes in " + ", ".join(f"`{f}`" for f in cl["frontend"]) + " as described above.") if cl["frontend"] else "None.")
    L.append("\n## Calculation Changes\n")
    if cl["calc"]:
        L.append("Changes in " + ", ".join(f"`{f}`" for f in cl["calc"]) + ". **Data policy: new data only** — records already stored are NOT recalculated; the fix applies to new "
                 "records and to records edited after the fix. Past reports keep their existing values.")
    else:
        L.append("None.")
    L.append("\n## Tests To Add/Change\n")
    t = []
    if repro:
        if repro.endswith(".py"):
            t.append(f"Port `audit/repro/{repro}` into a pytest regression test under `new/server/tests/` (assert the Expected value; independent hand-derived numbers, not a second call to the same function).")
        else:
            t.append(f"Port `audit/repro/{repro}` into a Playwright spec under `new/client/e2e/` (or a vitest test where it is pure component logic).")
    t.append("Add edge cases: zero, missing, negative, NaN/Inf, boundary values for every field the fix touches.")
    if rcs:
        t.append("Add the group-level invariant tests for " + ", ".join(rcs) + " (see Root-Cause Groups).")
    t.append("Review existing tests that assert the old behaviour; change an expected value only when the new value is independently derived and documented in the test.")
    L.append("\n".join("- " + x for x in t))
    L.append("\n## Browser Verification\n")
    if ui:
        L.append(f"- Reproduce the steps in AUDIT_FINDINGS.md on an isolated stack (`audit/tools/vite_audit.mjs` + backend on an audit DB copy) and confirm the Expected result on screen.\n"
                 f"- Compare the UI value with the API response and the DB row for the same record; refresh and reopen the record.")
    else:
        L.append("- API/backend fix. After the fix, open the page(s) that consume this data (see Affected Features) and confirm the displayed value matches the API and DB.")
    L.append("\n## Regression Risks\n")
    risks = [RC_RISK[r] for r in rcs if r in RC_RISK] or [PHASE_RISK.get(phase, "")]
    if cl["calc"] and PHASE_RISK["P2"] not in risks:
        risks.append(PHASE_RISK["P2"])
    L.append("\n".join("- " + r for r in risks))
    L.append("\n## Acceptance Criteria\n")
    ac = []
    if repro:
        ac.append(f"`audit/repro/{repro}` exits 0 on the fixed code (it prints expected vs actual).")
    if b["expected"]:
        ac.append("Expected behaviour holds: " + squash(b["expected"], 400))
    ac.append("Full backend suite (`python -m pytest tests/` in `new/server`) and frontend checks (`npm run lint`, `npm run test`) pass.")
    ac.append("No other open bug's repro changes from fail→pass or pass→fail unexpectedly (re-run `audit/work/rerun/run_all.sh`).")
    L.append("\n".join(f"{i+1}. {x}" for i, x in enumerate(ac)))
    L.append("\n---\n")
    return "\n".join(L)


# ---------------------------------------------------------------- assemble
assigned = [b for _, _, ids in PHASES for b in ids]
missing = sorted(set(bugs) - set(assigned) - EXTERNAL - set(DUPLICATE))
dupes = sorted({b for b in assigned if assigned.count(b) > 1})
assert not missing, missing
assert not dupes, dupes

counts = {}
for bid in assigned:
    counts[bugs[bid]["sev"]] = counts.get(bugs[bid]["sev"], 0) + 1
still = sum(1 for b in assigned if rerun.get(b) == 1)
notrep = [b for b in assigned if rerun.get(b) == 0]
incon = [b for b in assigned if b in rerun and rerun[b] not in (0, 1)]
browser_only = [b for b in assigned if b not in rerun]

out = []
out.append("# IMPLEMENTATION PLAN — GHG Platform Audit Remediation\n")
out.append("Prepared by the lead auditor after the discovery phase. **No fixes have been implemented.** "
           "Each entry is derived from the confirmed bug in `AUDIT_FINDINGS.md`. Priorities, root-cause groups, "
           "risks and the final re-run status were added by the lead auditor.\n")
out.append("## Summary\n")
out.append(f"- Bugs in this plan: **{len(assigned)}**. "
           + " · ".join(f"{k}: {counts.get(k, 0)}" for k in ("Critical", "High", "Medium", "Low")))
out.append(f"- Final re-run against the current code: **{still} still reproduce**, **{len(notrep)} no longer reproduce** "
           f"({', '.join(notrep) or 'none'}), {len(incon)} inconclusive ({', '.join(incon) or 'none'}), "
           f"{len(browser_only)} are browser repros confirmed by the agents on the post-change code but not re-run in the final pass.")
out.append("- Merged duplicate: BUG-035 → BUG-033.")
out.append("- Not in the plan: BUG-100 to BUG-104 — see *Excluded entries* at the end.\n")
out.append("## Before starting\n")
out.append("1. **Freeze the baseline.** The calculation engine and client forms were edited while the audit was running "
           "(`audit/baseline2_uncommitted.diff`). Commit or branch the current state so every fix is measured against a known tree.\n"
           "2. **Fix BUG-016 first.** Several fixes add constraints or columns and must ship as Alembic migrations.\n"
           "3. **Decide the data policy.** Many fixes stop bad data from entering but do not clean what is already stored "
           "(test rows of 1e13–1e15, NULL facility names, years 1800/2099, duplicate rows, rows computed with wrong formulas). "
           "Each cleanup or recalculation should be an explicit, logged job approved by the data owner.\n"
           "4. **Calculation scope.** At the user's request the calculation workstreams (A, C) were stopped mid-audit. The "
           "calculation bugs they had already confirmed are included (P2/P3). Other calculators were **not** audited and are listed "
           "as unverified in the final report.\n")
out.append("## Data policy (decided by the user, 2026-09-26)\n")
out.append("| Topic | Decision | Consequence |\n|---|---|---|")
out.append("| 9 absurd Scope 1 test rows (ids 640, 645, 649, 658, 662, 667, 669: 1e13 MMBtu gas; 655, 675: 1e15 t coal) | **Hard delete** | Step D-1 below. Irreversible: back up the DB first and get explicit go-ahead at execution time, since it runs on the live DB. |")
out.append("| Records stored with a wrong formula | **New data only** | No recalculation job. Past records and previously issued reports keep known-wrong values; fixed logic applies to new and re-edited records. |")
out.append("| Other invalid stored data (13 nameless facilities, years 1800/2099, month 99, duplicate groups, split Scope 3 categories) | **Block only new bad data** | Validation stops new occurrences. Constraints that existing rows would violate become application-level checks. Existing rows remain. |")
out.append("| User deletion vs approver evidence | **Delete, keep a snapshot** | Approver/creator name and email copied onto records at write/approval time. The 470 historic Verified rows without an approver stay as they are. |")
out.append("")
out.append("**Known residual after the policy:** once the 9 rows are deleted, Verified Scope 1 is still ≈5.1e9 t, mostly seed rows inserted by an "
           "external tester script with precomputed CO2e (Agent B). Under *block only new bad data* these stay, so dashboards will still show "
           "implausible totals until they are decided on separately.\n")
out.append("### Step D-1 — Delete the 9 test rows (runs once, in phase P1)\n")
out.append("1. Back up `new/server/ghg_app.db` (stop the app, or use the SQLite backup API).")
out.append("2. List the 9 rows (id, facility, quantity, unit, co2e_total, status, created_by) and confirm they are the test rows. The ids come from the audit snapshot and must be re-checked against the live DB.")
out.append("3. Delete them in one transaction, with one ActivityLog entry per row (action `DATA_CLEANUP_DELETE`, old values captured).")
out.append("4. Clear the dashboard cache and confirm the Verified and Pending Scope 1 totals drop by the deleted amounts (≈3.718e12 t Verified, ≈4.686e12 t Pending).\n")
out.append("## Root-cause groups (fix these once, not per bug)\n")
out.append("| Group | Root cause | Bugs | Shared fix |\n|---|---|---|---|")
for k, (name, desc, ids, fix) in ROOT_CAUSES.items():
    out.append(f"| {k} | **{name}** — {desc} | {', '.join(ids)} | {fix} |")
out.append("")
out.append("## Fix order\n")
out.append("| Phase | Focus | Bugs |\n|---|---|---|")
for p, name, ids in PHASES:
    tagged = ", ".join("%s (%s)" % (i, bugs[i]["sev"][:1]) for i in ids)
    out.append(f"| {p} | {name} | {tagged} |")
out.append("")
for p, name, ids in PHASES:
    out.append(f"\n# PHASE {p} — {name}\n")
    out.append(f"_Phase regression risk:_ {PHASE_RISK.get(p, '')}\n\n---\n")
    for bid in ids:
        out.append(section(bugs[bid], p))
out.append("\n# Excluded entries\n")
out.append("**BUG-035** — duplicate of BUG-033 (merged above).\n")
out.append("**BUG-100 to BUG-104** were appended to `AUDIT_FINDINGS.md` by a process outside this audit (signed "
           "\"API GHG Compendium Section 6 Auditor\"), during the period when the user had placed emission calculations out of scope. "
           "They have no reproduction scripts and were not verified by any audit workstream, and BUG-104 describes missing "
           "functionality rather than a defect. They are listed here for traceability and should be triaged by the user "
           "(accept into a calculation-methodology backlog, or verify first):\n")
for bid in sorted(EXTERNAL):
    b = bugs[bid]
    out.append(f"- **{bid}** ({b['sev']}) — {b['title']}")
open(os.path.join(H2, "IMPLEMENTATION_PLAN.md"), "w", encoding="utf-8").write("\n".join(out) + "\n")
print("plan bugs:", len(assigned), counts, "still:", still, "not reproduced:", notrep, "inconclusive:", incon, "browser-only:", len(browser_only))
