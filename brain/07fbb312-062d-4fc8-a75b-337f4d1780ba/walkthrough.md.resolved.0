# API Compendium Calculation Logic Fixes

I have successfully resolved the calculation logic failures to ensure complete compliance with the API Compendium (2021) methodologies. I made targeted changes exclusively to the routing logic to fix the reported issues without altering or breaking any other calculations.

## Changes Made

### 1. Fixed Acid Gas Removal (AGR) Compliance

> [!NOTE]
> The original logic was reading the incorrect input variables (`co2_in`/`co2_out` instead of `agr_co2_in`/`agr_co2_out`), causing the API 2021 calculator to return zero and forcing a fallback to an incorrect method that resulted in massive CH4 emissions.

**Implementation**:
- Updated `dispatcher.py` to correctly map the inputs. It now looks for `agr_co2_in` and `agr_co2_out` and passes them down to the `AGRCalculator`.

**Verification Result**:
The `AGR (Specific)` test now correctly reports the `Acid Gas Removal` method and properly calculates the CO2 emissions based on the throughput and CO2 differential, generating zero CH4 emissions as intended.

### 2. Fixed Storage Tank Default Fallback

> [!NOTE]
> The original logic forced all tank calculations through the Gas-Oil Ratio (GOR) flashing model. In default scenarios where GOR was not provided (zero), this resulted in a failed calculation and an unnecessary fallback to a legacy method instead of the standard API 2021 pipeline.

**Implementation**:
- Updated `dispatcher.py` to intelligently handle default tank calculations. If the process is a default calculation and no GOR is provided, the process is re-routed as a `tank_working` process. This instructs the `TankFlashingCalculator` to bypass the flashing logic and properly apply the default API 2021 emission factor.

**Verification Result**:
The `Storage Tank (Default)` test now correctly reports the `Storage Tank Emissions` method and calculates the CH4 emissions based on the provided default emission factor, keeping the calculation within the API 2021 framework.

---

> [!SUCCESS]
> I have run the `verify_all_calcs.py` test suite, which confirms that both of these issues are resolved and all other calculations remain perfectly intact and accurate!
