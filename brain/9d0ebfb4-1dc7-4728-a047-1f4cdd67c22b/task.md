# Task List

## Active Goal: Refactoring Filters to Scrollable Custom Dropdowns

- [x] Refactor `mobile-combustion.html`
- [x] Refactor `scope2-calculator.html`
- [x] Refactor `scope3-calculator.html`
- [x] Refactor `emission-factor.html`
- [x] Refactor `manage-data.html`
    - [x] Convert Activity/Division- [x] Fix Dropdown Issues
    - [x] Convert conversion unit selects (`conv-oil-unit`, `conv-gas-unit`)
    - [x] Standardize custom dropdown logic across all JS files
    - [x] Implement idempotent guards to prevent double-init bugs
    - [x] Fix Manage Data UI Bugs
    - [x] Standardize dropdown initialization guards
    - [x] Resolve `ReferenceError: loadRegions is not defined`
    - [x] Fix HTML structural nesting and layout breakage
    - [x] Verify tab-switching functionality
    - [x] Performance Optimization
    - [x] Investigate slowness bottlenecks
    - [x] Implement lightweight summary endpoint for notifications
    - [x] Implement pagination and year filtering for /api/emissions
    - [x] Add missing database indices
    - [x] Update frontend to use paginated/summary data
    - [x] Optimize Detailed Breakdown table with collapse/expand
    - [x] Optimize chart rendering with instance caching
    - [x] Make Emissions by Source chart filter-responsive
    - [x] Optimize dashboard box sizes and spacing
- [x] Global UI Consistency
    - [x] Refactor `dashboard.js` filters to use `setupCustomDropdownHelper`
    - [x] Refactor `carbon-intensity.js` filters to use `setupCustomDropdownHelper`
    - [x] Ensure `reference-data.html` is consistent

## Completed Goals
- [x] Explore codebase and database schema
- [x] Implement data reset and seeding script
- [x] Production Data Enhancements (Year filters)
- [x] Seed base year, goals, mitigation actions, production data
- [x] Seed Custom Emission Factors (Sonatrach Specific)
