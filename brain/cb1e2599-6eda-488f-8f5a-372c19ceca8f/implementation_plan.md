# Goal Description

Verify the software's calculation engine against the API GHG Compendium (2021) exhibits to ensure 100% compliance and accuracy.

## Open Questions

> [!WARNING]
> **Scope of Verification:** I extracted **81 exhibits** from the API Compendium. Developing a test suite for all 81 exhibits is a significant undertaking because it requires manually reading each exhibit from the PDF, translating its specific inputs into our payload structure, and hardcoding the expected outputs. 
> 
> **Question:** Do you want me to build a comprehensive test suite for *all 81* exhibits, or should I focus on a representative subset (~15-20 exhibits) that covers the core processes we actively support in the software (Stationary Combustion, Flaring, Tanks, Pneumatics, Fugitives, Drilling, and Completions)?

## Proposed Changes

### Calculation Verification Suite

#### [NEW] [test_api_exhibits.py](file:///c:/Users/samsung/Desktop/h/new/server/tests/test_api_exhibits.py)
Create a dedicated test file that runs our `CalculationDispatcher` against the exact inputs provided in the API Exhibits. This script will:
1. Define the input parameters exactly as stated in the API Compendium exhibits.
2. Run the calculation through our engine.
3. Assert that our calculated results (CO2, CH4, N2O, CO2e) match the published API results within an acceptable margin of error (accounting for rounding differences).
4. Output a detailed report of the comparisons.

## Verification Plan

### Automated Tests
- Execute `python -m pytest server/tests/test_api_exhibits.py -v` to run the suite and generate the verification report.
