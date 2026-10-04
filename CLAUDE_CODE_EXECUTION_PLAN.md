# Claude Code Execution Plan — Driving the A+ Programme

**Companion to:** `IMPLEMENTATION_PLAN_TO_A_PLUS.md` (the *what*). This document is the *how*, expressed as
Claude Code configuration and run procedure.
**Verified environment:** Claude Code **2.1.287** at `C:\Users\samsung\.local\bin\claude.exe`, Windows host,
working directory `C:\Users\samsung\Desktop\H2`.
**Mechanics sourced from** the official docs: [hooks reference](https://code.claude.com/docs/en/hooks),
[subagents](https://code.claude.com/docs/en/sub-agents), [skills](https://code.claude.com/docs/en/skills),
[best practices](https://code.claude.com/docs/en/best-practices).

---

## 0. What is already installed (and why it matters)

| Component | State | Consequence for this plan |
|---|---|---|
| `~/.claude/settings.json` | `permissions.defaultMode: "plan"` | **Every session starts read-only.** An executor must leave plan mode to write. Overridden per-project in P0.2. |
| `~/.claude/settings.json` | `PreToolUse` hook on `Bash` → `rtk hook claude` | Every shell call is filtered through RTK. Keep it; do not duplicate it. |
| `~/.claude/settings.json` | `enabledPlugins: { "ecc@ecc": true }`, `hook_profile: standard` | Hooks from the ECC plugin are **already running**. Any hook you add must not duplicate them. |
| `.agents/` (project, `target: antigravity`) | 68 agents, 281 skills, 123 rules, 94 workflows | **This is a separate pack, not Claude Code's native directory.** Claude Code reads `.claude/agents/` and `.claude/skills/`. The ECC plugin bridges some of it into the session; the project-local `.agents/` tree does not become Claude Code subagents on its own. Do not assume `@.agents/agents/architect.md` is invocable. |
| `.claude/` (project) | Only `reviews/` and `a.py` | **No `.claude/agents/`, no `.claude/skills/`, no `.claude/settings.json`.** Everything this plan adds is new. |
| Root `CLAUDE.md` | 12,487 bytes | Loads into **every** session and **every** subagent. It currently contains stale and now-wrong statements (P0.1). |
| `~/.claude/CLAUDE.md` | Small (graphify + `@RTK.md` import) | Global, fine, leave alone. |

**The single most important fact in this document:** `CLAUDE.md` is loaded by the main conversation *and by
every non-fork subagent*, and it is the file the implementing agent will treat as ground truth. Right now it
tells that agent things that are false. Fixing it is P0.1, not housekeeping.

---

## 1. Architecture of the harness

Five Claude Code primitives, each used for the one thing it is uniquely good at. The mapping is deliberate —
using a skill where a hook belongs is the most common way this kind of setup fails.

| Primitive | Loads | Use it for | Not for |
|---|---|---|---|
| `CLAUDE.md` | Every session + every subagent | Facts that are always true: invariants, commands, the one-command gate | Procedures (they bloat context), anything derivable from code |
| **Skill** (`.claude/skills/<n>/SKILL.md`) | On demand, when relevant or `/invoked` | Repeatable procedures, task specs, phase runbooks | Rules that must hold *every* time — the docs are explicit that Claude stops re-reading skill content after compaction |
| **Hook** (`.claude/settings.json`) | Always, deterministically | Anything that must happen with zero exceptions: the gate, the guard on the sacred files | Judgement calls |
| **Subagent** (`.claude/agents/<n>.md`) | Fresh context on delegation | Verbose work whose output you don't want in the main window: test runs, migrations, adversarial review | Anything needing the conversation's history (use a fork for that) |
| **Slash command** | Same as a skill (commands were merged into skills) | Thin entry points the operator types | — |

Design rule adopted throughout: **deterministic → hook. Advisory → skill or CLAUDE.md. Verbose → subagent.**

---

## 2. PHASE C0 — Scaffolding (half a day, do this first)

Nothing in `IMPLEMENTATION_PLAN_TO_A_PLUS.md` should start before C0 lands, because C0 is what makes the rest
of the work verifiable by the agent itself rather than by you reading diffs.

### C0.1 Rewrite `CLAUDE.md` — the ground-truth fix

Replace the 12 KB file with ≤120 lines. The docs are blunt: *"If Claude keeps doing something you don't want
despite having a rule against it, the file is probably too long and the rule is getting lost."* Everything
procedural moves to a skill.

New `CLAUDE.md` content, in this order:

1. **What this is** — one paragraph, the GHG platform, `new/server` + `new/client`, no Docker.
2. **The gate, first and loudest.** One command. See C0.4.
3. **Corrected facts** (currently wrong in the file):
   - Alembic has **7** revisions, linear, single head `a1c4e7f20b31` — not two.
   - Roles are `user`, `it`, `superuser`, `admin`, `it_admin`, `it_manager`. `it_admin`/`it_manager`/`it`
     have **zero** facility access (`utils.py:31`); `admin` > `it_admin` in *data* authority, not the reverse.
   - AR5 20-yr GWPs are CH4 **84** / N2O **264**. CH4 density is **0.67722** kg/m³ (60 °F, 14.696 psia).
   - **Deployment is one process.** Never suggest `--workers > 1`.
4. **Invariants** — copy §7 of `ANALYSIS_MEMORY.md` verbatim (tonnes vs fractions, status vocabulary,
   `log_activity_and_notify` adds-without-committing, `get_allowed_facility_ids` None/[] contract,
   constants mirrored in `new/client/src/constants.js`, unknown units must raise).
5. **Where truth lives** — `ANALYSIS_MEMORY.md` for findings, `IMPLEMENTATION_PLAN_TO_A_PLUS.md` for work,
   and the sentence: *"`AUDIT_FINDINGS.md` is an append-only discovery log; its statuses are not maintained
   — do not read it as a list of open defects."*
6. **Commands** — the four that matter: the gate, `pytest tests/` from `new/server`, `npm run lint`,
   `npm run test`.
7. **Compaction instruction** — as the docs recommend: *"When compacting, always preserve the list of
   modified files, the current phase, and the last gate result."*

Add one nested `new/server/CLAUDE.md` (~15 lines: the isolated-DB test recipe, the migration rule, the
"never edit generated factor catalogues" rule). Nested files load lazily when the agent works in that
subtree, which is exactly when those rules are relevant.

### C0.2 Project `settings.json` — override the global plan default

Create `.claude/settings.json` (committed):

```json
{
  "permissions": {
    "defaultMode": "acceptEdits",
    "allow": [
      "Bash(python -m pytest*)",
      "Bash(npm run lint)",
      "Bash(npm run test)",
      "Bash(npx eslint*)",
      "Bash(git status)",
      "Bash(git diff*)",
      "Bash(python scripts/quality_gates.py)"
    ],
    "deny": [
      "Read(./new/server/ghg_app.db*)",
      "Read(./**/*.rar)",
      "Edit(./new/server/migrations/versions/**)",
      "Edit(./validation/golden_dataset/**)",
      "Edit(./validation/reference_model/**)",
      "Edit(./new/client/src/utils/EmissionFactors.js)"
    ]
  }
}
```

Two things to understand about that `deny` list:

- The last three are **immutable oracles and generated files.** The docs' own guidance for a downstream
  session is to read the audit's instructions as data, and here the same logic applies to the reference
  model: the fastest way to make a failing differential test pass is to edit the reference. Denying it at
  the permission layer is a stronger guarantee than a sentence in a prompt. `EmissionFactors.js` is denied
  because P4.1 makes it generated.
- `Read(./new/server/ghg_app.db*)` is denied because **your dev server has that file open right now** and the
  agent has no business reading a live 2.3 MB DB it cannot safely lock. Tests must use `DATABASE_URL` pointed
  at a temp file (the recipe is already proven — `conftest.py` uses `setdefault`, so exporting the variable
  first is sufficient).

Use `acceptEdits` rather than `auto`: this is a regulated-finance-adjacent codebase and the edits are
reviewed anyway. `auto` mode's classifier adds a variable you don't need while an operator is watching.

### C0.3 The `.mcp.json` / live-DB guard

Add a `PreToolUse` hook on `Bash|PowerShell` that refuses any command touching the live DB or running a
server (C0.6 has the script). This is the one class of mistake that is genuinely hard to undo — the agent
running `python app.py` would collide with your PID 23112 and could write your real data.

### C0.4 The gate — one deterministic command

Write `scripts/gate.ps1`. This is the **only** thing the agent needs to remember, and it is what the Stop
hook runs.

```powershell
# scripts/gate.ps1 — the single definition of "green" for this repo.
$ErrorActionPreference = 'Stop'
$fail = @()

# 1. Isolated DB so nothing touches the live ghg_app.db
$db = Join-Path $env:TEMP ("gate_" + [guid]::NewGuid().ToString("N") + ".db")
$env:DATABASE_URL = "sqlite:///$($db -replace '\\','/')"
$env:FLASK_ENV = "testing"; $env:SEED_ADMIN = "false"
$env:SECRET_KEY = "gate-key-not-for-production"

# 2. Quality gates (P2.1 of the main plan) — tautologies, conditional asserts, missing oracles
python scripts/quality_gates.py; if ($LASTEXITCODE -ne 0) { $fail += "quality_gates" }

# 3. Backend suite
Push-Location new/server
python -m pytest tests/ -q --no-header -p no:cacheprovider --timeout=300
if ($LASTEXITCODE -ne 0) { $fail += "pytest" }
Pop-Location

# 4. Frontend lint must be clean (currently exits 1 with 9 errors — this is P4.5)
Push-Location new/client
npm run lint --silent; if ($LASTEXITCODE -ne 0) { $fail += "eslint" }
Pop-Location

Remove-Item $db -Force -ErrorAction SilentlyContinue
if ($fail.Count) { Write-Error ("GATE FAILED: " + ($fail -join ", ")); exit 1 }
Write-Output "GATE GREEN"; exit 0
```

`--timeout=300` will fail until `pytest-timeout` is present; that is deliberately part of P2.2 (pin
`requirements-dev.txt`), and the failure is informative.

### C0.5 The skills

Create these under `.claude/skills/`. Each frontmatter description is load-bearing — it is how Claude decides
to load the skill — so write it as natural-language triggers, not a title.

**`.claude/skills/verify/SKILL.md`** — name it `verify` on purpose. Claude Code 2.1.286+ looks for a skill
named `verify` or `simplify` at session start and instructs Claude to **run it right before every commit**.
That turns the gate from advice into a pre-commit habit for free.

```markdown
---
name: verify
description: Run the repository's single definition of green before any commit, and report the result as evidence. Use before every commit, after any change to calculations, routes, or migrations.
allowed-tools: Bash(powershell*), Bash(python*), Bash(npm run lint), Read, Grep, Glob
---

Run `powershell -File scripts/gate.ps1` and report the outcome.

Rules:
- Report the **actual command output**, never a summary like "all tests pass". If you did not see the
  output, you did not verify.
- If the gate fails, do not commit and do not proceed. Diagnose, fix, re-run the gate.
- If the gate fails for an environmental reason (a missing test dependency), fix the environment as part of
  P2.2 rather than working around it.
- Never delete or weaken a test to make the gate pass. If a test is genuinely wrong, fix the test *and* say
  so explicitly, quoting the old and new assertion.
```

**`.claude/skills/calc-change/SKILL.md`** — the domain guard. Calculation edits are where this codebase has
historically gone wrong, and the failure mode is silent.

```markdown
---
name: calc-change
description: Checklist for any change under new/server/calculations, units.py, constants.py, or emission factor tables. Use whenever touching emission arithmetic, unit conversion, GWP values, or factor data.
---

Before changing anything here, state in your response:
1. The API Compendium 2021 exhibit, table, or equation the change implements.
2. The units going in and the units coming out.
3. Which test proves the new behaviour, and what the old value was.

Hard rules:
- An unknown unit must RAISE. `conv.get(unit, 1)` and similar silent fallbacks are bugs.
- A factor applied to an incompatible activity dimension must RAISE (see `units.factor_to_kg_per_activity`).
- If a default is genuinely used, record it on the record so a reviewer can see it. Never let a default be
  invisible.
- Percent-vs-fraction: use the single shared decision in `units.composition_fractions` (<=1 is a fraction).
  Do not divide by 100 in a new place.
- After the change, run `pytest tests/test_independent_differential.py tests/test_golden_dataset_validation.py`
  and report the differential percentages, not just PASS.
```

**`.claude/skills/rbac-change/SKILL.md`** — because the IT-lockout leak happened by hand-rolled role tuples.

```markdown
---
name: rbac-change
description: Checklist for any change to authorization, role checks, facility scoping, or a new route. Use when adding endpoints, editing decorators, or touching get_allowed_facility_ids.
---

- Never write a new inline role list. Use (or extend) the single predicate in `services/rbac.py`.
- A new route must carry an auth decorator AND a per-route rate limit if it writes, uploads, generates a
  report, or makes an outbound call.
- Any route taking `facility_id` must call `require_facility_access`; a scope *filter* is not a scope *check*.
- A mutating route must call `log_activity_and_notify` and commit once, together with the data change.
- Add a test that proves the denial (403), not only the success.
```

### C0.6 The hooks — guardrails that cannot be forgotten

Add to `.claude/settings.json`. Windows needs `powershell.exe -File`, not the bash form in the docs. If `jq`
is unavailable, parse stdin with PowerShell's `ConvertFrom-Json`, as the Windows tab of the hooks reference
shows.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|PowerShell",
        "hooks": [
          {
            "type": "command",
            "command": "powershell.exe",
            "args": ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                     "${CLAUDE_PROJECT_DIR}/.claude/hooks/guard.ps1"]
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "powershell.exe",
            "args": ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                     "${CLAUDE_PROJECT_DIR}/.claude/hooks/stop-gate.ps1"]
          }
        ]
      }
    ]
  }
}
```

**`.claude/hooks/guard.ps1`** — deny-list, returns `permissionDecision: deny`:

```powershell
$input_json = [Console]::In.ReadToEnd() | ConvertFrom-Json
$cmd = [string]$input_json.tool_input.command
$deny = @(
  @{ p = 'ghg_app\.db';                      r = 'The live database is held open by the running dev server. Use DATABASE_URL pointing at a temp file.' },
  @{ p = '(?i)python\s+app\.py';             r = 'Do not start a server; the operator runs one on :5000.' },
  @{ p = '(?i)gunicorn';                     r = 'Deployment is single-process by decision (plan P5.1).' },
  @{ p = '(?i)alembic\s+downgrade';          r = 'Two revisions have no-op downgrades; a rollback leaves alembic_version ahead of the schema.' },
  @{ p = 'new/server\.rar|calculations\.rar'; r = 'Those archives are being deleted in P7; do not read or restore from them.' },
  @{ p = '(?i)git\s+push.*--force';          r = 'Force-push is not authorised.' },
  @{ p = '(?i)rm\s+-rf\s+/|Remove-Item.*-Recurse.*[A-Z]:\\'; r = 'Destructive recursive delete outside the workspace.' }
)
foreach ($d in $deny) {
  if ($cmd -match $d.p) {
    @{ hookSpecificOutput = @{
        hookEventName = 'PreToolUse'
        permissionDecision = 'deny'
        permissionDecisionReason = $d.r } } | ConvertTo-Json -Compress
    exit 0
  }
}
exit 0
```

**`.claude/hooks/stop-gate.ps1`** — the deterministic stop condition. This is the piece that makes an
unattended run trustworthy, and it is the direct answer to the weakness this codebase already has (gates
that cannot fail):

```powershell
$input_json = [Console]::In.ReadToEnd() | ConvertFrom-Json
# Only gate turns that actually changed code.
$changed = (& git -C $env:CLAUDE_PROJECT_DIR status --porcelain -- new/server new/client scripts 2>$null)
if (-not $changed) { exit 0 }

# Avoid re-running the full suite on every stop within one turn sequence.
$stamp = Join-Path $env:TEMP 'claude_gate_stamp'
if ((Test-Path $stamp) -and ((Get-Date) - (Get-Item $stamp).LastWriteTime).TotalMinutes -lt 10) { exit 0 }

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:CLAUDE_PROJECT_DIR/scripts/gate.ps1" *>&1 |
  Out-String | Set-Content (Join-Path $env:TEMP 'claude_gate_out.txt')
if ($LASTEXITCODE -ne 0) {
  New-Item $stamp -ItemType File -Force | Out-Null
  $tail = (Get-Content (Join-Path $env:TEMP 'claude_gate_out.txt') -Tail 40) -join "`n"
  @{ decision = 'block'
     reason = "scripts/gate.ps1 failed. Fix the cause before finishing. Output tail:`n$tail" } |
    ConvertTo-Json -Compress
  exit 0
}
New-Item $stamp -ItemType File -Force | Out-Null
exit 0
```

Notes from the hooks reference that shape this design:
- `Stop` supports `decision: "block"` with a `reason`, and there is a cap on consecutive blocks, so a broken
  environment cannot trap the session in a loop forever.
- `Stop` also accepts `hookSpecificOutput.additionalContext` for feedback that *continues* the conversation
  rather than erroring — use `decision: block` here because a failing gate is an error.
- The 10-minute stamp matters: without it, a 5-minute suite runs on every single stop.

### C0.7 The subagents

Create `.claude/agents/` with five project subagents. Keep each `description` short — Claude Code warns at
startup when custom agent descriptions together exceed 15,000 tokens, and you already have the ECC plugin's
agents in play. Identity comes only from the `name` field, so keep names unique across the tree.

| File | `tools` | `model` | Why it exists |
|---|---|---|---|
| `calc-oracle.md` | `Read, Grep, Glob, Bash` | `opus` | Owns P1/P3. Read-only on the reference model by permission policy. Its job is to explain a numeric divergence from first principles, not to make a test pass. |
| `route-auditor.md` | `Read, Grep, Glob` | `sonnet` | Walks the route surface for the P6 checklist: missing decorators, missing rate limits, missing audit calls, unescaped `ilike`. |
| `spa-auditor.md` | `Read, Grep, Glob, Bash` | `sonnet` | P4: catalogue drift, client-side authoritative arithmetic, missing abort guards, a11y on the primary flows. |
| `verify-adversary.md` | `Read, Grep, Glob, Bash` | `opus` | The adversarial reviewer. Given a diff and the phase's exit criteria, its only job is to find where the work does **not** meet them, or where a gate was weakened. Deliberately *not* the agent that wrote the code. |
| `ledger-keeper.md` | `Read, Edit, Grep, Glob` | `haiku` | Maintains `AUDIT_FINDINGS.md` statuses and `IMPLEMENTATION_PLAN_TO_A_PLUS.md` checkboxes. Mechanical, cheap, high volume. |

Example — because the failure mode it guards against is specific:

```markdown
---
name: calc-oracle
description: Investigates numeric divergences between the production calculation engine and the independent reference model. Use when a differential or golden test disagrees, or when emission arithmetic is in question.
tools: Read, Grep, Glob, Bash
model: opus
---

You investigate discrepancies between `new/server/calculations/**` and `validation/reference_model/**`.

Operating rules:
- You may not edit `validation/reference_model/**` or `validation/golden_dataset/**`. They are the oracle.
  If you believe the oracle is wrong, say so with evidence and stop; a human decides.
- Work from constants outward: molecular weights, molar volumes, unit factors, then formulas, then composed
  pathways. Most same-sign same-magnitude errors across two pathways share one constant.
- Report: the two values, the percentage, the first intermediate at which they diverge, the candidate root
  causes ranked by likelihood, and the single expression you would change. Quote `file:line` for everything.
- Never propose widening a tolerance. That is the defect, not the fix.
```

### C0.8 How a phase is actually run

This is the procedure the operator follows. It exists because the docs' strongest finding is that
*explore → plan → implement → verify* beats jumping to code, and because this programme has ~200 discrete
edits across 8 phases.

```
For each phase in IMPLEMENTATION_PLAN_TO_A_PLUS.md:

  1. /clear                      # fresh context; the plan file is the handoff, not the chat
  2. Ask for the phase spec skill:  /phase-p1
     -> the skill injects the relevant plan section and the exact file list
  3. Plan mode (Shift+Tab) — have it read the named files and confirm the diff it intends
  4. Approve -> implement, with the calc-change / rbac-change skill auto-loading when relevant
  5. /verify                     # runs scripts/gate.ps1, reports real output
  6. Delegate to verify-adversary with: "review the diff against these exit criteria"
  7. ledger-keeper updates AUDIT_FINDINGS.md statuses and ticks the plan
  8. git commit                  # the verify skill runs again immediately before this
```

Two operator rules that matter more than they look:

- **`/clear` between phases, always.** The docs: after two failed corrections, a clean session with a better
  prompt beats a long one carrying failed approaches. Each phase is large enough that its context will be
  polluted by the time it ends.
- **`/rewind` when an approach fails.** Checkpoints are automatic and free; the docs note they do not cover
  Bash-side changes, so pair a rewind with `git status` when a command did the damage.

### C0.9 `phase-*` skills, one per phase

Nine thin skills (`.claude/skills/phase-p0/SKILL.md` through `phase-p7/`), each with
`disable-model-invocation: true` so only the operator triggers them. Each is a runbook, not a narrative:
the phase's goal, the ordered file list with `file:line`, the exit criteria, and the exact command that
proves them. They exist so that a `/clear` costs nothing — the phase definition lives on disk, not in the
conversation.

Use `paths:` frontmatter on the ones that are file-scoped, so they load lazily rather than sitting in the
context budget from startup.

---

## 3. Ordering against the main plan

C0 is a precondition for all of it. The main plan's phases then run as written, with the harness supplying
the verification:

| Main plan phase | Harness support | Why it must be in this order |
|---|---|---|
| **P0** stop the bleeding | `guard.ps1` denies live-DB and server commands from the first minute | Prevents the highest-consequence mistake while the agent is still learning the repo |
| **P1** numeric divergence | `calc-oracle` subagent; `deny` rules make the reference model read-only | The one phase where "make the test pass" is the wrong instinct, so it is locked at the permission layer |
| **P2** verification | `scripts/quality_gates.py` becomes step 2 of `gate.ps1`; `verify` skill auto-runs pre-commit | The gate must be able to fail *before* the defects it will catch are fixed |
| **P3** correctness | `calc-change` skill auto-loads; `verify-adversary` after each batch | Highest silent-failure density in the codebase |
| **P4** SPA | `spa-auditor`; `EmissionFactors.js` denied for edit (it becomes generated) | Catalogue drift is a correctness bug that looks like a UI bug |
| **P5** operations | `stop-gate.ps1` is the enforcement mechanism for "the gate is green" | Ops changes are the easiest to hand-wave without a deterministic check |
| **P6** security | `rbac-change` skill; `route-auditor` sweeps the surface | 187 routes is too many to hold in one context |
| **P7** hygiene | `ledger-keeper` reconciles the 115 ledger entries | Mechanical and large; not worth a frontier model |

### The one thing to build outside the harness

`scripts/quality_gates.py` (main plan P2.1) is not a Claude Code artefact and should be written by hand,
reviewed by a human, and committed before it is trusted. It is the instrument that judges everything else —
including the agent's own work. An agent that writes its own grader has produced the exact failure this whole
exercise is trying to remove, so the ordering is: **human writes the gate, agent satisfies it.**

---

## 4. Risks specific to running this with Claude Code

| Risk | Why it bites here | Mitigation in this plan |
|---|---|---|
| **The agent edits the oracle** | The cheapest way to fix a differential failure is to edit `reference_model`. This codebase already has that disease — a tolerance floored at 5% while the report claims 0.1%. | `deny` rules on `validation/reference_model/**` and `golden_dataset/**`, *plus* a `calc-oracle` prompt that forbids it, *plus* the quality-gate script asserting the oracles are unchanged in a diff |
| **A gate that cannot fail gets rebuilt by the agent** | The failure mode is latent in the repo; an agent will reproduce the pattern it sees. | `verify` skill demands raw output, not "all tests pass"; `verify-adversary` is a *different* model instance with no stake in the code |
| **Context rot across a 5-week programme** | 8 phases × large diffs will exhaust any single conversation. | One phase per session, `/clear` between, phase definitions on disk as skills, compaction instruction pinned in `CLAUDE.md` |
| **The 12 KB `CLAUDE.md` is treated as truth** | It is wrong about Alembic, the role model, GWPs, and density — and it loads into every subagent. | C0.1 is first, not last |
| **Two agent packs collide** | ECC (68 agents, 281 skills) is enabled globally; project instructions also reference `.agents/`. Skills in `.claude/skills/` are discovered by walking up, and name collisions resolve by precedence rules that are easy to get wrong. | Keep project subagents in `.claude/agents/` with unique names; run `/skill-doctor` after C0 to see what each skill costs in context; do not add project agents whose names shadow ECC's |
| **Permission default is `plan`** | Inherited from the user's global settings, so an executor session silently cannot write. | Project `settings.json` sets `acceptEdits` (C0.2) |
| **Live-DB corruption** | Your dev server holds `ghg_app.db` open; a stray `python app.py` or an in-place migration could write real data. | `guard.ps1` deny rule + `DATABASE_URL` isolation baked into `gate.ps1` and already proven against `conftest.py`'s `setdefault` |
| **Unbounded unattended runs** | The `Stop` gate can block repeatedly. | The hooks reference documents a cap on consecutive blocks; the 10-minute stamp prevents suite-thrash; run phases attended until the gate is proven |

---

## 5. First-session prompt (copy-paste)

After C0.1-C0.6 are on disk, open a fresh session in `C:\Users\samsung\Desktop\H2` and send:

> Read `ANALYSIS_MEMORY.md` §7 (invariants) and `IMPLEMENTATION_PLAN_TO_A_PLUS.md` phase P0 only.
> Do not read any other phase. Confirm in your own words the ten P0 items and the files involved,
> then implement them one at a time, running `powershell -File scripts/gate.ps1` after each.
> The live `ghg_app.db` is served by a running dev server — do not touch it, do not start a server.
> When all ten pass, report the gate output verbatim.

Why this shape works with the harness: it names the two files as the source of truth, scopes to one phase to
protect the context window, explicitly forbids the highest-consequence mistake, and asks for **evidence
rather than a claim** — which is the whole lesson of this codebase's audit history.

---

## 6. What "done" looks like

The programme is complete when `scripts/gate.ps1` is green, **and** you can delete the harness for a week
without the quality regressing. That second condition is the real test. A harness that only works while the
agent is watching has replaced one unverifiable process with another; the goal is that the gate, the
immutable oracles, and the single-command definition of green outlive any particular session, model, or
operator.

---

## 7. Checklist

**C0 — do before any phase of the main plan**
- [ ] C0.1 `CLAUDE.md` rewritten: gate first, four corrected facts, invariants, compaction instruction; nested `new/server/CLAUDE.md` added
- [ ] C0.2 `.claude/settings.json` with `acceptEdits`, allow-list, and the oracle/generated-file deny-list
- [ ] C0.3 deny rule verified by attempting a denied command
- [ ] C0.4 `scripts/gate.ps1` committed and run once by hand
- [ ] C0.5 skills: `verify`, `calc-change`, `rbac-change`
- [ ] C0.6 hooks: `guard.ps1` + `stop-gate.ps1` wired in `settings.json`, confirmed via `/hooks`
- [ ] C0.7 five subagents in `.claude/agents/`; confirm they appear and names do not shadow ECC
- [ ] C0.8 phase runbook agreed with the operator
- [ ] C0.9 nine `phase-p*` skills
- [ ] `scripts/quality_gates.py` written and reviewed **by a human**, then wired into the gate

**Per phase**
- [ ] `/clear` before starting; plan section loaded via `/phase-pN`
- [ ] Plan mode review of the intended diff
- [ ] Implement; `calc-change` / `rbac-change` loaded where relevant
- [ ] `/verify` green with raw output pasted
- [ ] `verify-adversary` review against the phase's exit criteria
- [ ] Ledger and plan checkboxes updated
- [ ] Commit (verify skill re-runs immediately before)
