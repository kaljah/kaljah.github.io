# BUG-XXX — CustomDropdown is not keyboard-operable and form inputs have no programmatic labels: Region, Process Type, Emission Factor and Unit cannot be set without a mouse

**Status:** Confirmed
**Severity:** Medium
**Category:** UI
**Discovered by:** Agent K (Frontend/UI)

## Location
- `new/client/src/components/CustomDropdown.jsx` — trigger is `<div className="dropdown-selected" onClick={handleToggle}>` (≈L114): no `tabIndex`, `role`, `aria-haspopup/expanded`, or key handlers; options are clickable `<div>`s.
- Forms use `<label>` without `htmlFor` and inputs without `id`/`aria-label` (Scope1Form, Scope2Form, ManageData, Reports, AuditTrail, ReferenceData).

## Reproduction
1. UI :5191 admin → Emissions → Scope 1; focus "Group Name" and press Tab repeatedly (`audit/work/K/t_kbd.mjs`).
2. Count visible inputs/selects without an accessible name on each page (`audit/work/K/t_mobile.mjs`).

## Input
Keyboard only.

## Expected
Tab order reaches Region, Emission Source, Process Type, factor and Unit pickers; they open with Enter/Space and options are selectable with arrow keys; each input has an accessible name.

## Actual
Tab order: Group Name → Equipment ID → Tier 1/2/3 buttons → Quantity → Save as Draft → Submit … — every CustomDropdown is skipped (Region trigger: `tabIndex -1, role null, aria-haspopup null`). Submitting then fails with "Please fill in all identity fields (Year, Month, Region, Process)". Unlabelled form controls (no associated label/aria-label): Scope 1 11/11, Scope 2 6/6, Manage Data 15/15, Reports 12/12, Audit Trail 6/6, Reference Data 2/2.

## Evidence
`t_kbd.mjs` focus sequence and `t_mobile.mjs` output. Repro `audit/repro/BUG-<id>.mjs`.

## Root Cause
Custom div-based listbox without focus management/ARIA; labels not associated with controls.

## Impact
Keyboard and screen-reader users cannot record Scope 1/2 activity data at all (required pickers unreachable); fails WCAG 2.1.1 / 4.1.2 / 1.3.1.

## Affected Components
All pages using CustomDropdown (Scope 1/2/3 forms, dashboard filters, import wizards) and all forms listed above.

## Recommended Fix
Make the trigger a `<button aria-haspopup="listbox" aria-expanded>`, options `role="option"` with arrow-key navigation, and associate labels via `htmlFor`/`id` (or `aria-labelledby`).
