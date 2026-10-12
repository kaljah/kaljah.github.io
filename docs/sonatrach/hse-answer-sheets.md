# HSE answer sheets

For Sonatrach HSE. One sheet per open methodology item (HR-01 to HR-10, from `docs/validation/HUMAN_REVIEW_REQUIRED.md`), followed by four boundary and template questions. Each sheet says what the code does today, gives the options, and gives our recommendation. The recommendation is a proposal, not a decision: **the code changes only after HSE signs the answer**.

Code references are `file:line` in `new/server/`, checked 2026-10-08. Where the 2026-09-20 audit text is out of date, the sheet says so.

How to answer: tick one option (or write your own), sign and date. Return the signed file; each answer becomes a change request (task T8.1) with a test that cites your answer.

---

## HR-01: N2O default emission factor for flaring
**Today.** The audit found two different defaults. They are now the same: when no N2O factor is supplied, every flaring path uses **0.0001 kg N2O per MMBtu flared**, commented as "API Compendium 2021 Table 5-3" (`calculations/combustion.py:590`, `calculations/vented.py:70`, `calculations/vented_ccus_transport.py:63`, `calculations/vented_downstream.py:103`, `calculations/vented_completion.py:200`). Nobody has checked that value against the published table.

| Option | Effect |
|--------|--------|
| A. Keep 0.0001 kg/MMBtu if HSE confirms it matches the Compendium table. | No change. |
| B. Use another value required by the Algerian regulator or OGMP (state the value, unit and source). | One constant changes in five places; results shift. |
| C. Require a site factor and give no default (flaring without a factor is rejected). | Stricter data entry. |

**Recommendation.** A, after HSE checks the table value, because a default removes a blocking input and N2O from flaring is small next to CO2 and CH4.

Answer: ☐ A ☐ B (value/unit/source: ________) ☐ C ☐ Other: ________
Signed: ____________  Date: ________

---

## HR-02: Mobile vs stationary combustion boundary
**Today.** `mobile_combustion` and `stationary_combustion` use the same calculator (`calculations/dispatcher.py:132-134`). The calculation is identical; the distinction is only the process type chosen when the record is entered. The platform has no rule that company-owned vehicles are Scope 1 and contractor-owned ones Scope 3 category 4, and no operated/non-operated asset flag.

| Option | Effect |
|--------|--------|
| A. Keep one calculation. Document the rule for data entry: owned and operated mobile sources go in Scope 1; contractor fleets go in Scope 3 category 4. | Documentation and training only. |
| B. Add a "control" field (owned, leased, contractor) to mobile records and warn when contractor fuel is entered in Scope 1. | Small form and validation change. |
| C. Different factors for on-road, off-road, marine and aviation fuels. | Needs the factor source from HSE. |

**Recommendation.** A for the first waves, B if HSE sees contractor fuel mixed into Scope 1.

Questions for HSE: (1) Are leased vehicles under operational control Scope 1? (2) Which contractor activities, if any, are inside the boundary?
Answer: ☐ A ☐ B ☐ C   Notes: ________
Signed: ____________  Date: ________

---

## HR-03: OGMP 2.0 level assignment
**Today.**
- Each emission record gets a level 1 to 4 from an explicit `ogmp_level` if set, otherwise from its factor source and calculation method: site-specific, engineering or direct measurement is level 4; custom, API table or component count is level 3; default or generic is level 2; anything else is level 2 (`services/ogmp.py:9-56`). Level 1 is used only when the record is missing.
- A facility's bottom-up level is the highest level that carries at least 50% of its verified methane (`services/ogmp.py:59-80`).
- The facility level is 5 only when top-down and bottom-up totals both exist, agree within the facility's reconciliation threshold (default 20%), and the bottom-up inventory is already level 4; reconciled with level 2 or 3 it is capped at 4; a top-down measurement alone gives 4 (`services/ogmp.py:83-146`).
- There is no mapping from survey type (for example satellite) to a level. A survey contributes a top-down methane total; any total above zero reaches level 4.

| Question | Options |
|----------|---------|
| 1. Is the record-level mapping right? | ☐ Yes ☐ Change: ________ |
| 2. Should satellite surveys count as top-down for level 4/5, or be informational only? | ☐ Count ☐ Informational ☐ Only above a stated detection limit ________ |
| 3. Reconciliation threshold | ☐ 20% ☐ Other: ____ % |
| 4. Materiality share for the bottom-up level | ☐ 50% ☐ Other: ____ % |
| 5. Reporting-year cutoff | ☐ Calendar year ☐ Other: ________ |

**Recommendation.** Keep the code as is until HSE confirms the OGMP 2.0 technical guidance version Sonatrach reports against; answer questions 2 and 4 first.
Signed: ____________  Date: ________

---

## HR-04: Scope 3 categories
**Today.** The 15 GHG Protocol categories are accepted (`input_validation.py:171`, "Category N"); the form defaults to category 11 (`routes/scope3.py:130`). The calculation reference cases cover spend-based and physical-activity methods only; category 15 (investments) has no reference case. Nothing prevents counting the same fuel in category 3 and in Scope 1 or 2.

| Question | Answer |
|----------|--------|
| 1. Which categories are reported by Sonatrach? | ________ |
| 2. Which are material and must have a validated method? | ________ |
| 3. Category 11 (use of sold products): method for natural gas, crude and products (full combustion of volumes sold?) | ________ |
| 4. Category 3 (fuel and energy-related activities): rule to avoid double counting with Scope 1 and 2 | ________ |
| 5. Should unused categories be hidden in the form? | ☐ Yes ☐ No |

**Recommendation.** Report only the categories HSE names as material; build and validate those; hide the rest.
Signed: ____________  Date: ________

---

## HR-05: GWP uncertainty in total CO2e uncertainty
**Today.** Per-gas uncertainty is combined by root-sum-of-squares. The uncertainty of the GWP values themselves (AR5 methane 28, ±11%) can be included (`calculations/uncertainty.py:176-199`, parameter `include_gwp_uncertainty`). The dashboard includes it only when the user switches it on (`routes/dashboard.py:1068`, default off), while the calculation function's own default is on.

| Option | Effect |
|--------|--------|
| A. Always include GWP uncertainty in reported totals. | Wider reported intervals. |
| B. Never include it; state the method in reports. | Narrower intervals. |
| C. Keep the toggle; set the default to the framework's rule (state which). | Per-report setting. |

**Recommendation.** Decide per framework (ISO 14064-1 verifier's view first); we recommend C with the default matching what the verifier accepts.
Answer: ☐ A ☐ B ☐ C (default: ____)
Signed: ____________  Date: ________

---

## HR-06: Custom emission factor governance
**Today.**
- Anyone with the right to create a factor can; non-admin factors start `Pending` and only an `admin` approves (`routes/custom_factors.py:204`). A factor created by an admin is approved immediately. Editing an approved factor sets it back to `Pending` (`routes/custom_factors.py:343`).
- Value checks only warn: methane factor outside 0 to 100, N2O factor outside 0 to 10, with similar bounds for other fields (`routes/custom_factors.py:145-158`). The factor is saved anyway.
- The platform does not require a source or method reference. How earlier calculations behave when a factor changes has not been verified; HSE should say what the rule must be.

| Question | Options |
|----------|---------|
| 1. Out-of-range factor | ☐ Warn only ☐ Block unless a written justification is attached and an admin approves |
| 2. Ranges | ☐ Keep ☐ Replace with HSE's table (attach) |
| 3. Source/method reference | ☐ Optional ☐ Required |
| 4. Admin's own factors | ☐ Auto-approved ☐ Need a second admin |
| 5. A factor is changed | ☐ Past records keep their value ☐ Flag past records for recalculation |

**Recommendation.** Block out-of-range factors without justification, require a source reference, a second approver for admin-created factors, and keep past records unchanged with a visible flag.
Signed: ____________  Date: ________

---

## HR-07: CSRF on sign-in and password reset
**Today.** `/api/auth/login` and `/api/auth/forgot-password` skip CSRF checks (`routes/auth.py:360`, `:439`) because the original deployment served the site and API from different domains. The session cookie is `SameSite=None; Secure` in production (`config.py:134-140`). On Sonatrach servers the site and API share one origin.

| Option | Effect |
|--------|--------|
| A. Remove the exemptions and use `SameSite=Lax` once served from one origin (task T4.1). | Closes the item. |
| B. Keep the exemptions and record a risk acceptance. | Not recommended. |

**Recommendation.** A. The security team should confirm.
Answer: ☐ A ☐ B   Signed (security): ____________  Date: ________

---

## HR-08: Database and backups
**Today.** Production requires PostgreSQL (SQLite is development only). `scripts/backup.py` backs up SQLite or PostgreSQL and keeps the last 10 backups (`scripts/backup.py:72`, `retain_count=10`); there is no schedule, no point-in-time recovery and no restore drill yet (planned M3).

| Question | Answer |
|----------|--------|
| 1. Recovery point objective (maximum data lost) | ________ |
| 2. Recovery time objective (maximum downtime) | ________ |
| 3. Retention (days, and legal minimum for GHG data) | ________ |
| 4. Point-in-time recovery | ☐ Required ☐ Not required |
| 5. Backup location | ________ |

**Recommendation.** Daily backups, 30-day retention, PITR on, quarterly restore drill. Final values from Sonatrach IT and HSE retention rules.
Signed: ____________  Date: ________

---

## HR-09: Regulatory framework and GWP set
**Today.** The default GWP set is IPCC AR5 (`calculations/constants.py:23-26`); AR4 and AR6 are available (`calculations/constants.py:20`, `get_active_gwp` at `:38`). Calculations follow API Compendium 2021. Reports per framework are not built yet (M8).

| Question | Answer |
|----------|--------|
| 1. Algerian regulator and legal text | ________ |
| 2. GWP set required for the regulator | ☐ AR4 ☐ AR5 ☐ AR6 ☐ Other |
| 3. GWP set for OGMP 2.0 | ☐ AR4 ☐ AR5 ☐ AR6 |
| 4. GWP set for the ISO 14064-1 corporate inventory | ☐ AR4 ☐ AR5 ☐ AR6 |
| 5. Is the Compendium method accepted by the regulator? | ☐ Yes ☐ No, use: ________ |
| 6. Is third-party verification required? | ☐ Yes (by whom) ☐ No |
| 7. Deadlines and submission format | ________ |

**Recommendation.** One GWP set per report, chosen from your answers; the dashboard default stays AR5 unless HSE names a corporate set.
Signed: ____________  Date: ________

---

## HR-10: Independent checks of the calculations
**Today.** 25 reference cases in `validation/golden_dataset/golden_cases.json` have expected values derived independently of the production code, but not yet traced to published examples. Task T8.2 adds at least three cases per calculation family, each citing the exhibit and page.

| Question | Answer |
|----------|--------|
| 1. Can HSE supply worked examples (Compendium, EPA, IPCC) or a copy of the Compendium? | ☐ Supplied ☐ Please obtain |
| 2. Acceptable tolerance versus a published example | ☐ 0.01% ☐ 0.1% ☐ 1% ☐ Other |
| 3. Who reviews the traced cases? | ________ |

**Recommendation.** Tolerance 0.1%, because published examples round intermediate values.
Signed: ____________  Date: ________

---

## B1. Organisational boundary and joint ventures
**Today.** The platform stores time-sliced equity shares per facility and partner (`models.py:787`, `FacilityEquityShare`). Totals are not yet consolidated by equity share.

| Question | Answer |
|----------|--------|
| Approach for the group inventory | ☐ Operational control ☐ Equity share ☐ Financial control ☐ Both views |
| JV where Sonatrach is not operator | ________ |
| JV where Sonatrach is operator with partners | ________ |
| Mid-year ownership change | ☐ Pro rata by days ☐ Year-end ownership |

## B2. Group size
Number of facilities ____, divisions ____, regions ____, users ____, records per year ____.

## B3. Base year
With no historical import, the year-over-year and SBTi views stay empty until a base year is set (`routes/dashboard_sbti.py:105`). Options: ☐ The first full year in the platform is the base year. ☐ HSE enters base-year totals by hand (give years and totals). ☐ Other: ________

## B4. Official templates
Please send, or confirm we should obtain: the Algerian regulator reporting template, the OGMP 2.0 template Sonatrach submits, and any corporate inventory template.
Received: ☐ Regulator ☐ OGMP ☐ Corporate   Date: ________
