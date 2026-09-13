# Unified QA/QC & Data Health Page Implementation Plan

Merge the standalone Diagnostics page (`Diagnostics.jsx`) with the QA/QC Dashboard (`QADashboard.jsx`) into a unified, production-grade page named **QAQC**. The new page will strictly adhere to Carbon Tech's glassmorphic design system (`#f1f5f9` slate background, frosted glass cards, `#ff6600` brand accent, tabular numerals, Lucide icons, responsive layout).

---

## User Review Required

> [!IMPORTANT]
> **Unified Primary Route & Seamless Aliasing:**
> The primary navigation route will be `/qaqc`. To ensure zero broken links, bookmarks, or tests, `/qa-dashboard` and `/diagnostics` will remain active in the router as seamless aliases pointing to the unified `QAQC` component. Furthermore, `QADashboard.jsx` and `Diagnostics.jsx` will re-export `QAQC` as default for 100% backward compatibility.

> [!NOTE]
> **Sidebar Navigation Consolidation:**
> In `Sidebar.jsx`, the separate "QA/QC" and "Diagnostics" menu items under Administration will be consolidated into a single high-visibility item: **QA/QC** with a `ShieldCheck` icon, linking to `/qaqc` and remaining highlighted when any alias route is visited.

---

## Architecture & Reimagined UI Layout

The reimagined **QAQC** page unifies two critical compliance aspects of GHG accounting into a single pane of glass:
1. **System Data Health & Completeness Diagnostics** (8-field protocol validation, missing facility/fuel detection, activity checks, and health scoring).
2. **QA/QC Anomaly Review & Bulk Resolution** (automated anomaly rules, multi-select bulk resolve/reject, Scope/Year filtering, CSV audit export).
3. **IPCC Tier 1 Uncertainty Assessment** (SRSS combined uncertainty calculation, ISO 14064-1:2018 §7.5 compliance, 95% confidence intervals).

### Visual Structure
```
+----------------------------------------------------------------------------------------------------+
|  TopBar: [ShieldCheck] Quality Assurance / QA/QC & Data Health                  [User Profile]     |
+----------------------------------------------------------------------------------------------------+
|  Badge: ISO 14064-1 & GHG PROTOCOL COMPLIANT                                                       |
|  Title: QA / QC & Data Health                                                                      |
|  Subtitle: Unified inventory validation, uncertainty analysis, and automated diagnostics.          |
|  Actions: [🔄 Run Diagnostics]   [⬇️ Export QA Report]                                              |
+----------------------------------------------------------------------------------------------------+
|  4 KPI CARDS:                                                                                      |
|  [ 94% Overall Health ]  [ 98% Completeness (8 Fields) ]  [ 3 Unresolved Flags ]  [ ±4.2% Uncertainty ] |
+----------------------------------------------------------------------------------------------------+
|  TAB NAVIGATION:                                                                                   |
|  [ 🔍 Overview & Diagnostics ]   [ ⚠️ Flagged Anomalies (3) ]   [ 📊 Tier 1 Uncertainty ]           |
+----------------------------------------------------------------------------------------------------+
|  TAB CONTENT:                                                                                      |
|  - Tab 1: 8-field completeness breakdown + Critical Issues / Warnings / Suggestions cards          |
|  - Tab 2: Filter bar (Scope, Year, Search) + Bulk Approve/Reject + Interactive Anomalies Table     |
|  - Tab 3: IPCC Tier 1 SRSS Uncertainty Cards (Scope 1, Scope 2, Scope 3, Combined) + Methodology   |
+----------------------------------------------------------------------------------------------------+
```

---

## Proposed Changes

### Client Application & Routing

#### [NEW] [QAQC.css](file:///c:/Users/samsung/Desktop/H2/new/client/src/pages/QAQC.css)
- Create comprehensive stylesheet strictly adhering to Carbon Tech's design system:
  - Glassmorphic panels: `background: rgba(255, 255, 255, 0.85)`, `backdrop-filter: blur(12px)`, `border: 1px solid rgba(226, 232, 240, 0.8)`, `border-radius: 16px`.
  - Color palette: `#ff6600` primary accent, `#10b981` success/pass, `#f59e0b` warning, `#ef4444` danger, `#6366f1` info.
  - Interactive tab pills with smooth switching animations and badge counts.
  - Circular/linear health score indicators with color gradients.
  - 8-field completeness checklist grid with status indicators.
  - Anomaly table styling with sticky headers, checkbox selection, status pills, and bulk action floating toolbar.
  - IPCC Tier 1 uncertainty cards with mathematical formula callout.

#### [NEW] [QAQC.jsx](file:///c:/Users/samsung/Desktop/H2/new/client/src/pages/QAQC.jsx)
- Unify `Diagnostics.jsx` and `QADashboard.jsx` into a modular, highly responsive component:
  - **State Integration:**
    - Concurrent fetching of `/qaqc/dashboard` (anomalies, uncertainty, scores) and `/emissions`, `/facilities`, `/custom-factors` (diagnostics analysis).
    - Scope and year filtering with URL/state persistence.
    - Interactive bulk selection (`selectedIds` Set) with bulk resolve/approve/reject.
    - Real-time search query filtering over anomalies.
    - Tab switching: `activeTab` ('overview' | 'anomalies' | 'uncertainty').
  - **TopBar Sync:**
    - Connect with `useLayout()` to render breadcrumbs and user badge, with clean unmount cleanup.
  - **CSV Export:**
    - Seamless Axios blob export downloading `qa_qc_report.csv`.

#### [MODIFY] [QADashboard.jsx](file:///c:/Users/samsung/Desktop/H2/new/client/src/pages/QADashboard.jsx)
- Re-export `QAQC` as default to guarantee zero regressions for existing imports or route references.

#### [MODIFY] [Diagnostics.jsx](file:///c:/Users/samsung/Desktop/H2/new/client/src/pages/Diagnostics.jsx)
- Re-export `QAQC` as default for seamless backward compatibility.

#### [MODIFY] [App.jsx](file:///c:/Users/samsung/Desktop/H2/new/client/src/App.jsx)
- Import lazy `QAQC` component.
- Add `<Route path="qaqc" element={<AdminRoute><QAQC /></AdminRoute>} />`.
- Point `qa-dashboard` and `diagnostics` routes to `QAQC`.

#### [MODIFY] [Sidebar.jsx](file:///c:/Users/samsung/Desktop/H2/new/client/src/components/layout/Sidebar.jsx)
- Consolidate the two separate nav items into a single **QA/QC** item:
  - Links to `/qaqc`.
  - Active when on `/qaqc`, `/qa-dashboard`, or `/diagnostics`.
  - Uses `ShieldCheck` icon.

---

## Verification Plan

### Automated Build & Syntax Check
- Run Vite build / build verification to ensure all modules, JSX, and CSS compile cleanly without errors:
  ```powershell
  cd c:\Users\samsung\Desktop\H2\new\client
  npm run build
  ```

### Functional Verification
- Verify navigation to `/qaqc`, `/qa-dashboard`, and `/diagnostics` all render the unified QAQC page.
- Verify the 3 tabs:
  1. **Overview & Diagnostics:** Completeness meter, health gauge, critical issues, warnings, suggestions.
  2. **Flagged Anomalies:** Table rendering, scope & year filtering, search query filtering, checkbox multi-select, bulk resolve (Approve/Reject), and CSV export.
  3. **Uncertainty Analysis:** IPCC Tier 1 cards rendering correct Scope 1, 2, 3 and overall uncertainty % with confidence intervals.
- Verify TopBar breadcrumbs update properly on mount and clean up on unmount.
- Verify Knowledge Graph update: `graphify update .`.
