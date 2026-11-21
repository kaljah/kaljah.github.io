# Note for the authors of the GB GHG Emissions Inventory Report RY 2022 (2023-05-02)

To: Groupement Berkine HSE (HBNS and El Merk inventory, API SANGEA, AR4).
From: the GHG platform validation, 2026-11-21. Every source in Tables 7 / 8 and 14 / 15 was recalculated from the
report's own inputs. Site totals agree within 0.3 %. The points below are in the report itself, not in the
recalculation. Details and evidence are in `docs/validation-gb-ry2022.md`.

## Points to correct

| # | Where | Observation | Suggested correction |
|---|---|---|---|
| R01 | Tables E-9 / 27 (JV partners) | The 2021 and 2022 column headers are out of order | Swap the headers |
| R02 | El Merk venting (processed gas) | El Merk's processed gas, 194,132.66 MMscf, is HBNS's figure. El Merk's own 140,012 MMscf reproduces the printed venting CH4 to 0.01 % | Print 140,012 MMscf for El Merk |
| R03 | Table 15, on-road row | The row (425.84 t CO2) holds only the heavy-duty diesel; the light-duty diesel and gasoline of Table 14 are in the module total (2,356.07 t) but not in the row | Show all on-road vehicles in the row, or split the row |
| R04 | Miscellaneous | "Flare – AP" appears twice | Remove the duplicate |
| R05 | HBNS gas-production leak row | The CO2 cell shows another row's CO2 | Recompute the cell |
| R06 | Text | "26,29.75" and "136,270,00" | Correct the number formats |
| R07 | Table 13 | 8 headers over 7 columns | Align headers and columns |
| R08 | El Merk HP well-site flare | Calculated with the fuel-gas composition, not the HP flare gas | Use the HP flare gas analysis |
| R09 | Appendix B | The BOE differs from Table 5 | Use one BOE basis |
| R10 | HBNS STP row | The CO2e does not equal its gases at AR4 | Recompute the CO2e |
| R11 | Method section | Names both SANGEA 4 and SANGEA 5 | State the version used |

## Basis differences worth stating in the report

- **Headline intensity (CO2e per BOE).** 0.0147 (HBNS) and 0.0190 (El Merk) t CO2e/BOE divide by total production
  including reinjected gas. The API Guidance Document for GHG Reporting 2.0 (2023) operated basis excludes gas
  reinjected into the reservoir. On that basis the figures are the report's own Appendix B values, e.g. HBNS
  1,061,969 t / 33.27 MMBOE = 0.032 t CO2e/BOE.
- **Flare N2O.** The report uses SANGEA's 3.716e-5 kg N2O per Nm3 on every flare. API Compendium 2021 Eq 5-6 (with
  the December 2025 corrected defaults) gives about 8 times less. The platform uses Eq 5-6 unless the operator enters
  its own factor.
- **NGSI methane intensity.** The report's 0.141 % / 0.176 % use the sites' own gas CH4 content and heating value;
  the NGSI defaults (1.235 MMBtu/Mcf and the segment CH4 content) give different figures. State which inputs were
  used.
- **Scope 2 location-based factor.** The report uses the IEA 2019 Algerian grid average (0.419 kg CO2/kWh). The
  most recent national figure (2024 energy balance) is 0.497 kg CO2/kWh. The report should name the factor's year
  and source.

The platform's figures for each row are in `docs/validation-gb-ry2022.md` (Phase 1 table).
