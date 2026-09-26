# BUG-XXX — Scope 1 entry form does not reflow at phone width (390 px): Field input, Tier selector and factor picker are clipped off-screen

**Status:** Confirmed
**Severity:** Low
**Category:** UI
**Discovered by:** Agent K (Frontend/UI)

## Location
`new/client/src/components/Scope1Form.jsx` / `Scope1Form.css` — identity grid keeps 4 columns (Activity / Division / Region / Field) and the process section keeps 2 columns at 390 px; the card clips overflow.

## Reproduction
1. Playwright viewport 390×844, admin, open /emissions?scope=scope1 (`audit/work/K/t_mobile.mjs`).

## Input
390 px viewport.

## Expected
Single-column layout; every control fully visible.

## Actual
Screenshot `audit/work/K/m390__emissions_scope_scope1.png`: "Field" input cut at the right edge, Activity/Division inputs ~45 px wide ("Aut"), "Calculation Methodology" tier buttons and "Select Standard Em…" picker extend past the card edge and are clipped (document scrollWidth stays 390, so the hidden parts cannot be scrolled to).

## Evidence
Screenshot above.

## Root Cause
Fixed multi-column grid without a small-screen breakpoint.

## Impact
Tier 2/3 selection and some fields are unusable on phones.

## Affected Components
Scope 1 form (and Scope 2 form grids, same pattern).

## Recommended Fix
Add a `@media (max-width: 600px)` rule collapsing `.form-grid-*`/identity grid to one column and wrapping the tier selector.
