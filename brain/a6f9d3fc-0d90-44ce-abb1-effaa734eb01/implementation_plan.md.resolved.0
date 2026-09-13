# Implementation Plan - API Compendium 2021 Verification Fixes

Analysis of the test results revealed several discrepancies between the software's calculation engine and the reference examples in the API Compendium 2021.

## Proposed Changes

### [Server] Calculation Engine Fixes

#### [MODIFY] [dispatcher.py](file:///c:/Users/samsung/Desktop/h/new/server/calculations/dispatcher.py)
- Update `dispatch` to use `emission_factors.get('unit')` as the default `ef_unit` if not provided in the payload.
- Align pneumatic parameter names (allow both `bleed_rate` and `pneu_bleed_rate`).

#### [MODIFY] [fugitive.py](file:///c:/Users/samsung/Desktop/h/new/server/calculations/fugitive.py)
- Correct `EquipmentFugitiveCalculator` to handle emission factors that are already in tonnes (check units or normalize).
- Currently, it assumes kg/hr and divides by 1000 even if the factor is already in tonnes/hr.

#### [MODIFY] [emission_factors_api2021.py](file:///c:/Users/samsung/Desktop/h/new/server/emission_factors_api2021.py)
- Update `Tank - Crude Oil (Large, >10 bbl/d)` from `0.12` to `0.193` kg/bbl to match Table 6-22 of the Compendium.
- Verify and update other factors if necessary based on the extraction results.

### [Tests] Test Suite Updates

#### [MODIFY] [test_compendium_examples.py](file:///c:/Users/samsung/Desktop/h/test_compendium_examples.py)
- Refine input payloads to match corrected dispatcher expectations.
- Add more granular checks for each failing case.

## Verification Plan

### Automated Tests
- Run `python test_compendium_examples.py` and ensure all tests pass (0 failures).
- Run `python verify_all_calcs.py` to ensure no regression in existing tests.

### Manual Verification
- Compare specific outputs for Exhibit 5.1, 6-12, 6-20, and 7-1 against the PDF reference.
