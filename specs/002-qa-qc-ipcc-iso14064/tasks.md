# Implementation Tasks: QA/QC Module (IPCC & ISO 14064)

## Phase 1: Setup (Shared Infrastructure)
**Purpose**: Project initialization and basic structure

*(No setup required)*

---

## Phase 2: Foundational (Blocking Prerequisites)
**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

- [x] T001 [P] Update `c:\Users\samsung\Desktop\H2\new\server\models.py` to add `uncertainty_pct` (Float) and `qa_flag` (String) to `Emission`, `Scope2Emission`, `Scope3Emission`, and `CustomFactor`.
- [x] T002 Generate and apply database migration for the new model fields.

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel.

---

## Phase 3: User Story 1 - Automated Data Validation (Priority: P1) ⭐ MVP
**Goal**: The system automatically flags outliers during data import.

**Independent Test**: Upload a massive outlier value via the import wizard and see it get flagged with "Pending Review" and a qa_flag reason.

### Implementation for User Story 1
- [x] T003 [US1] Update `c:\Users\samsung\Desktop\H2\new\server\routes\emissions.py` batch upload handlers to detect outliers (e.g. qty > 10,000,000) and set `qa_flag` and `status="Pending Review"` instead of strictly rejecting.
- [x] T004 [US1] Update `c:\Users\samsung\Desktop\H2\new\client\src\pages\ManageData.jsx` to display the `qa_flag` column in the Pending Review tables.

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently.

---

## Phase 4: User Story 2 - Uncertainty Assessment (Priority: P2)
**Goal**: Aggregate Tier 1 Uncertainty percentages and drill down on a dashboard.

**Independent Test**: Visit the QA Dashboard and see the calculated uncertainty.

### Implementation for User Story 2
- [x] T005 [US2] Add a backend endpoint in `c:\Users\samsung\Desktop\H2\new\server\routes\manage.py` (or similar) to fetch and aggregate uncertainty percentages across the inventory.
- [x] T006 [US2] Create a new React component `c:\Users\samsung\Desktop\H2\new\client\src\pages\QADashboard.jsx` to visualize the uncertainty data and QC anomalies.
- [x] T007 [US2] Update frontend routing and navigation to include the new QA Dashboard.

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently.

---

## Phase 5: User Story 3 - Audit Trail & Reports (Priority: P3)
**Goal**: Full audit logging of modifications and PDF/CSV export.

**Independent Test**: Modify a pending record, verify it appears in the `ActivityLog`, and export a CSV report.

### Implementation for User Story 3
- [x] T008 [US3] Update backend routes in `c:\Users\samsung\Desktop\H2\new\server\routes\emissions.py` to hook into `ActivityLog` and save `metadata_json` with before/after states upon editing records.
- [x] T009 [US3] Create backend endpoint in `c:\Users\samsung\Desktop\H2\new\server\routes\qaqc.py` to generate the CSV QA/QC report.
- [x] T010 [US3] Add "Export QA Report" button to `c:\Users\samsung\Desktop\H2\new\client\src\pages\QADashboard.jsx` that triggers the download.

---

## Phase 6: Polish & Cross-Cutting Concerns
**Purpose**: Improvements that affect multiple user stories

- [ ] T011 Run quickstart.md validation locally.

---

## Dependencies & Execution Order
- Phase 2 (DB Models) must be completed first as all other tasks depend on the new fields.
- User Stories 1, 2, and 3 can be implemented sequentially to build up the QA capabilities.
