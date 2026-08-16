# Implementation Plan: QA/QC Module (IPCC & ISO 14064)

**Branch**: `002-qa-qc-ipcc-iso14064` | **Date**: 2026-08-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/002-qa-qc-ipcc-iso14064/spec.md`

## Summary

The QA/QC module introduces automated data validation, an immutable audit trail, uncertainty assessment using Tier 1 Error Propagation, and ISO 14064 compliant report generation. The implementation will involve updating the database models with uncertainty and QA fields, inserting validation logic into the backend import pipelines, hooking data modifications into the existing `ActivityLog` table, and building a new QA/QC Dashboard in React with PDF/CSV export capabilities.

## Technical Context

**Language/Version**: Python 3.11 (Flask Backend), JavaScript (React Frontend)

**Primary Dependencies**: SQLAlchemy, React, ReportLab (for PDF generation), CSV module

**Storage**: PostgreSQL

**Testing**: Pytest

**Target Platform**: Web Client

**Project Type**: React Web App + Flask Backend

**Performance Goals**: Validation rules on 10,000 record imports must run in < 10 seconds.

**Constraints**: Audit logs must be immutable.

**Scale/Scope**: Impacts all 3 Scopes of emission imports, plus custom factors and dashboards.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

No violations found. 

## Project Structure

### Documentation (this feature)

```text
specs/002-qa-qc-ipcc-iso14064/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── tasks.md
```

### Source Code

```text
server/
├── models.py             # Add uncertainty and QA flag fields
├── routes/
│   ├── emissions.py      # Update import wizards to run QC validation
│   ├── manage.py         # Handle QA/QC dashboard data API
│   └── reports.py        # Add PDF/CSV generation logic

client/src/
├── pages/
│   └── QADashboard.jsx   # New dashboard for QC anomalies and uncertainty
├── components/
│   └── Scope*ImportWizard.jsx # Minor updates to UI to handle uncertainty inputs
```

**Structure Decision**: The logic will be built into the existing Flask routing structure and React component architecture.

## Complexity Tracking

N/A
