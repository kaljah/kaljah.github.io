# Merge Diagnostics with QA/QC & Reimagine Dashboard

## Executive Summary
This proposal merges the standalone **Diagnostics** page (`/diagnostics`) and **QA/QC** page (`/qa-dashboard`) into a single, cohesive, audit-grade **QA/QC & System Diagnostics** center (`/qa-dashboard`).

Currently, the two pages are disconnected:
- **`Diagnostics.jsx`** used a legacy hardcoded dark theme (`#0f172a`, `#1e293b`), its own redundant header bar, and performed client-side data quality checks.
- **`QADashboard.jsx`** provided ISO 14064-1 / IPCC SRSS uncertainty calculations and an anomaly review queue with bulk verification/rejection.

The reimagined page unifies both tools into Carbon Tech's modern glassmorphic enterprise theme (`#ff6600` brand accent, light glass cards, semantic statuses, Outfit/Inter typography), creating an intuitive 3-stage ESG data verification and auditing workflow.

---

## User Review Required

> [!IMPORTANT]
> **Consolidated Route and Sidebar Navigation**:
> - The sidebar menu will now feature a single unified item: **"QA/QC & Diagnostics"** under the Compliance/Auditor section (replaces the two separate links).
> - The primary route is `/qa-dashboard`.
> - Route `/diagnostics` will be redirected (or aliased) to `/qa-dashboard` to preserve existing bookmarks and backward compatibility.

> [!NOTE]
> **Backend Efficiency**:
> - We will enrich the `/api/qaqc/dashboard` endpoint to compute diagnostic metrics (completeness score, missing-field statistics, facility coverage, custom factors coverage, and issue tallies) directly at SQL speed.
> - This replaces the unscalable client-side scanning of `/emissions`, providing sub-second load times even for millions of records.

---

## Architecture & Workflow Design

### 1. Unified Assurance Header & KPI Strip
- **Header**: "QA/QC & System Diagnostics" with an ISO 14064-1 & GHG Protocol assurance badge.
- **Global Context Bar**: Scope Filter (All, Scope 1, Scope 2, Scope 3), Reporting Year Filter (All, 2020–2026), "Run Diagnostics" button, and "Export QA Report" CSV button.
- **Executive Metric Cards**:
  1. **Overall Data Health & Integrity Score**: Composite percentage score (0–100%) with visual radial/progress gauge, status badge ("Optimal", "Attention Needed", "Critical Action"), and scanned field completeness rate.
  2. **ISO 14064-1:2018 Uncertainty (IPCC Tier 1 SRSS)**: Overall inventory uncertainty % with Scope 1, Scope 2, Scope 3 mini-meters and total audited emissions volume ($t\text{CO}_2\text{e}$).
  3. **Anomaly & Outlier Queue**: Total flagged records count, pending review count, verified count, and rejection tally.
  4. **Inventory & Factor Coverage**: Active vs. total facilities, custom emission factor coverage, and recent ingestion activity (last 30 days).

### 2. Segmented Workflow Tabs
- **Tab 1: Flagged Anomalies & Resolution Queue** (Badge: total flagged count)
  - Interactive table with quick filters (search by process/source/flag, filter by status: Pending, Verified, Rejected).
  - Bulk actions bar when records are selected: "✓ Approve / Mark Verified", "✕ Reject Flag", with selection counter.
  - Granular table columns: Checkbox, Record ID (monospace badge), Scope tag (Scope 1 emerald, Scope 2 blue, Scope 3 purple), Year/Period, Process/Source, QA Flag reason, Calculated Emissions ($t\text{CO}_2\text{e}$), Status badge, and inline quick action buttons.
  - Clean pagination.
  - Zero-state illustration when 100% compliant.

- **Tab 2: Health & Completeness Diagnostics** (Badge: issue/warning count)
  - **Attribute Completeness Progress**: Visual breakdown across critical dimensions (Facility mapping, Fuel & Source specifications, Quantities & Units, Emission Calculations, Uncertainty metadata).
  - **Categorized Diagnostic Findings**:
    - **Critical Issues** (Red / High Impact): e.g. Missing facility assignments, uncalculated emissions, non-positive quantities.
    - **Warnings** (Amber / Medium Impact): e.g. Missing fuel/source classifications, statistical outliers (>3$\sigma$), stale ingestion data (>30 days).
    - **Advisory & Best Practices** (Blue / Optimization): e.g. Facilities without activity logs, opportunities for facility-specific custom factors.
  - Each finding card includes affected record counts, explanatory guidance, and direct jump links to the Anomaly Queue, Manage Data, or Reference Data.

- **Tab 3: Uncertainty Methodology & IPCC Rigor**
  - Mathematical model display for IPCC SRSS:
    $$U_{\text{total}} = \frac{\sqrt{\sum (U_i \cdot E_i)^2}}{\sum E_i}$$
  - Scope 1, Scope 2, and Scope 3 variance contribution breakdown cards.
  - 95% Confidence Interval bounds ($\pm t\text{CO}_2\text{e}$).

---

## Proposed Changes

### Server Layer

#### [MODIFY] [qaqc.py](file:///c:/Users/samsung/Desktop/H2/new/server/routes/qaqc.py)
- Enhance `get_qaqc_dashboard()`:
  - Add SQL-level data completeness metrics (records with missing facility, missing fuel/source, zero/negative quantity, uncalculated totals).
  - Add facility coverage metrics (total facilities vs facilities with activity).
  - Add custom factor count and 30-day activity freshness.
  - Compute a composite health score: `health_score = max(0, completeness - critical_issues * 10 - warnings * 5)`.
  - Include categorized diagnostic findings array in JSON response.

---

### Client Layer

#### [MODIFY] [Sidebar.jsx](file:///c:/Users/samsung/Desktop/H2/new/client/src/components/layout/Sidebar.jsx)
- Merge the two separate admin navigation items (`QA/QC` and `Diagnostics`) into a single item:
  - Label: `QA/QC & Diagnostics`
  - Route: `/qa-dashboard`
  - Unified shield-pulse icon.

#### [MODIFY] [App.jsx](file:///c:/Users/samsung/Desktop/H2/new/client/src/App.jsx)
- Ensure `/qa-dashboard` mounts the reimagined unified page.
- Add redirect / alias from `/diagnostics` to `/qa-dashboard` so legacy bookmarks and links remain functional.

#### [MODIFY] [QADashboard.jsx](file:///c:/Users/samsung/Desktop/H2/new/client/src/pages/QADashboard.jsx)
- Complete reimaging of the page:
  - Integrate all diagnostic health scores, completeness audits, and issue findings.
  - Integrated 3-tab workflow (Anomaly Resolution, Health Diagnostics, Uncertainty Methodology).
  - Responsive KPI cards matching the Carbon Tech glassmorphism design system.
  - Inline single-record resolution and bulk verification/rejection.
  - Real-time diagnostics re-run and CSV export.

#### [NEW] [QADashboard.css](file:///c:/Users/samsung/Desktop/H2/new/client/src/pages/QADashboard.css)
- Scoped stylesheet providing:
  - Glass cards, radial score presentation, progress bars, and tab transitions.
  - Strict compliance with `index.css` design tokens (`--accent-color`, `--bg-card`, `--border-color`, etc.).
  - Responsive layout for tablet and mobile screens.

#### [MODIFY] [Diagnostics.jsx](file:///c:/Users/samsung/Desktop/H2/new/client/src/pages/Diagnostics.jsx)
- Update `Diagnostics.jsx` to render the unified `QADashboard` component as a drop-in wrapper (maintaining component-level backward compatibility).

---

## Verification Plan

### Automated Tests
- Build verification: Run `npm run build` in `new/client` to guarantee zero syntax or bundling errors.
- Run server tests: `python -m pytest tests/` in `new/server` to ensure backend APIs remain green.
- Run `graphify update .` per project rule to synchronize the knowledge graph after code modifications.

### Manual Verification
1. Navigate to `/qa-dashboard` and observe:
   - Harmonized Carbon Tech enterprise light theme (no dark mode clashes).
   - Unified executive KPI strip showing Health Score, SRSS Uncertainty, Anomaly Count, and Facility Coverage.
   - Tab 1 (Anomaly Queue): Filtering by Scope & Year, selecting items, bulk Approve & Reject, pagination, and CSV Export.
   - Tab 2 (Health Diagnostics): Checking completeness bars, critical issues, warnings, suggestions, and clicking "View in Queue" action links.
   - Tab 3 (Uncertainty): Checking IPCC SRSS formula display and Scope 1/2/3 variance cards.
2. Navigate to `/diagnostics` and verify smooth seamless redirection/render to the unified page.
3. Check Sidebar to ensure only one clean "QA/QC & Diagnostics" navigation entry is rendered.
