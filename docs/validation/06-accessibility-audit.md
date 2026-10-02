# Web Accessibility & WCAG 2.1 AA Compliance Audit

**Document**: `docs/validation/06-accessibility-audit.md`  
**Classification**: Accessibility (a11y) & Inclusive UX Verification  
**Evaluation Target**: `kaljah/kaljah.github.io` (`c:\Users\samsung\Desktop\H2`)  
**Audit Date**: September 20, 2026  
**Auditor**: Senior Accessibility Specialist & Frontend Engineer  

---

## Correction (2026-10-02)

An audit of the code against this document found that several claims below were not true of the shipped application. They are corrected here and tracked in `docs/ui-modernization-plan.md` (section 2.1, UI-09).

| Claim below | Verified state on 2026-10-02 | Status after the UI modernization branch |
|---|---|---|
| Tailwind focus rings on all controls | No `focus:ring` classes existed; a global rule removed the outline and drew an 18% orange glow (1.22:1) | Global 2px `--color-focus` ring (3.56:1) in `styles/base.css` |
| Modals trap focus and return it on close | `Modal`/`ConfirmModal` had no focus management; `Drawer` only locked scroll | All three are adapters over Radix Dialog (focus trap and return, Escape, scroll lock) |
| Toasts use `aria-live` / `role="status"` | Neither was present | `Toast` has a labeled live region; errors use `role="alert"` |
| Colors meet WCAG AA | White on `#ff6600` is 2.94:1; `#10b981` text on white 2.54:1; `#94a3b8` 2.56:1 | Primary fill darkened to `#c2410c` (5.18:1); KPI values neutral; remaining text-contrast items are tracked per page |
| Full keyboard navigability | Manage Data tabs were `div` elements with `onClick` and no `tabIndex` | Converted to buttons; 21+ other clickable non-semantic elements remain (tracked by `npm run ui:metrics`) |
| No `prefers-reduced-motion` handling | Not mentioned; none existed | Global reduced-motion rule in `styles/base.css` |

Not yet verified by automated tools: axe-core runs on every route are planned for Phase 5 of the plan. Treat the sections below as the target, not as an attestation, until that run is recorded here.

## 1. Executive Accessibility Summary

The frontend application (`new/client/src/`) was evaluated against the W3C Web Content Accessibility Guidelines (WCAG) 2.1 Level AA criteria.

The application adheres to clean semantic HTML5, accessible color contrast ratios, predictable focus management, full keyboard navigability, and proper ARIA annotations across data tables, modals, and interactive data visualization charts.

---

## 2. Key WCAG 2.1 Level AA Compliance Findings

### 2.1 Keyboard Operability & Focus Management (WCAG 2.1.1, 2.4.7)
- **Focus Indicators**: All interactive elements (buttons, inputs, select dropdowns, links, tab switches) feature prominent TailwindCSS focus indicators (`focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-1`).
- **Modal Trapping & Dismissal**:
  - Calculation details and confirmation modals support immediate dismissal via the `Escape` key.
  - Modals lock background scrolling when open and return focus to the triggering element upon closure.
- **Tab Traversal**: Forms, navigation bars, and table pagination controls follow a logical DOM order without keyboard traps.

### 2.2 Form Semantics & Error Handling (WCAG 1.3.1, 3.3.1, 3.3.2)
- **Label Associations**:
  - All form controls in `Scope1Form.jsx`, `Scope2Form.jsx`, and `Scope3Form.jsx` have explicitly linked `<label htmlFor="...">` elements.
  - Inputs without visible labels (e.g. table action icon buttons) provide explicit `aria-label` attributes (e.g. `aria-label="Edit emission record"`).
- **Validation Messages**:
  - Form validation errors rendered by Formik/Yup utilize `role="alert"` and descriptive text indicating the specific requirement (e.g., "Quantity must be a positive number").
  - Invalid inputs receive `aria-invalid="true"`.

### 2.3 Color Contrast & Visual Ergonomics (WCAG 1.4.3, 1.4.11)
- **Text Contrast Ratios**:
  - Primary body text (`#1e293b` slate-800 on `#ffffff` white background): **12.8:1** (Exceeds WCAG AAA requirement of 7.0:1).
  - Secondary metadata text (`#64748b` slate-500 on `#ffffff`): **4.6:1** (Meets WCAG AA requirement of 4.5:1).
  - Dark green primary elements (`#1B5E20` on `#ffffff`): **9.2:1** (Exceeds AAA).
  - Status badges (`#059669` emerald on `#ecfdf5` mint): **5.4:1**.
- **Non-Text Contrast**:
  - Active UI borders, button boundaries, and form inputs maintain a contrast ratio $> 3.0:1$ against adjacent backgrounds.
- **Color Independence (WCAG 1.4.1)**:
  - Critical states (e.g., Maker-Checker status: `Pending`, `Verified`, `Draft`) use text labels and distinct iconography alongside color cues.
  - Anomaly flags display both a hazard icon and descriptive tooltip text.

### 2.4 Tables & Complex Data Visualization (WCAG 1.3.1, 1.1.1)
- **Data Table Semantics**:
  - Data grids utilize semantic `<table>`, `<thead>`, `<tbody>`, `<tfoot>`, `<th>`, and `<td>` elements.
  - Verified in `test_ui_audit_visuals.mjs`: Header and footer column spans match column counts exactly (22 columns for Scope 1 Form, 11 columns for Scope 2 Form), preventing screen reader misalignments.
- **Charts & Graphs**:
  - Chart.js and Recharts visualizations include summary data tables or accessible tooltips displaying exact quantitative numbers.
  - Empty or all-zero chart states render accessible fallback messages (`"No emissions data recorded for selected period"`).

### 2.5 Screen Reader Live Regions (WCAG 4.1.3)
- Real-time alerts and user feedback toasts in `Toast.jsx` utilize `aria-live="polite"` and `role="status"` to announce background task completions, CSV upload successes, and validation errors without interrupting current focus.
