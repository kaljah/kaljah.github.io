# Implementation Plan - Cement Industry GHG Emissions Calculator

## Goal Description
Create a professional, web-based software for calculating GHG emissions for the cement industry. The system will be compliant with the **WBCSD Cement CO2 and Energy Protocol** and **ISO 14064-1**. It will feature a robust backend for complex calculations, a secure database for historical data and audit trails, and a premium, environmental-themed dashboard for visualization.

## User Review Required
> [!IMPORTANT]
> **Stack Confirmation**: Proceeding with **Django (Python)** for the backend and **Next.js (React/TypeScript)** for the frontend as proposed.
> **Database**: We will start with SQLite for development speed and easy portability, but design the models to be PostgreSQL-ready for production.
> **Design**: Theme will be "Industrial Environmental" (Greens, Earth tones, Concrete Greys). Usage of SVGs only (no emojis).

## Proposed Changes

### Backend (Django)
We will create a new Django project structure.
#### [NEW] [backend/](file:///c:/Users/samsung/Desktop/cement/backend)
- Initialize Django project `config`.
- Create apps: `core` (users/auth), `emissions` (calculations/factors), `reporting` (audits/exports).
- **Core Models**: Custom User model for secure login.
- **Emissions Models**: `Facility`, `EmissionSource`, `ProductionData`, `EmissionFactor`.
- **Logic**: Implement the WBCSD specific equations for calcination, fuel combustion, etc.

### Frontend (Next.js)
We will create a modern Next.js application.
#### [NEW] [frontend/](file:///c:/Users/samsung/Desktop/cement/frontend)
- Initialize Next.js with TypeScript and Tailwind CSS.
- **Theme**: Custom Tailwind configuration for "Cement & Nature" palette (e.g., `#2E8B57` seagreen, `#708090` slate grey).
- **Assets**: Setup an SVG icon system (Lucide-React or Heroicons).
- **Components**: 
    - `Layout`: Sidebar navigation, clean headers.
    - `Dashboard`: Charts using Recharts (emissions over time).
    - `Forms`: Complex multi-step forms for data entry (Kiln inputs, Fuel usage).

## Verification Plan

### Automated Tests
- **Backend**: Run Django unit tests for calculation logic logic (`python manage.py test`).
- **Frontend**: Verify build succeeds (`npm run build`).

### Manual Verification
- **Visual Check**: Ensure the theme matches "Environmental/Cement" aesthetic (Grey/Green mix) and contains NO emojis.
- **Functional**: Register a user, log in, view the dashboard.
