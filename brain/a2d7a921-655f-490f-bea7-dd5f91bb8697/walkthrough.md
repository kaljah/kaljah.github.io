# Walkthrough: Cement GHG Emissions Calculator

I have successfully built the Cement Industry GHG Emissions Calculator, establishing a professional-grade platform compliant with WBCSD and ISO 14064-1 standards.

## 1. Login & Registration
- **Login**: A modern, split-screen page combining industrial cement aesthetics with environmental themes.
- **Registration**: Integrated registration flow allows new organizations to join seamlessly.

## 2. Modern Dashboard
The dashboard has been modernized with a premium grid layout:
- **Visuals**: **Area Charts** with gradient fills (replacing simple bars) and **Donut Charts** for scope breakdown.
- **Insights**: Stat cards now feature **Trend Indicators** (e.g., "4.2% down vs last year").
- **Activity Feed**: A real-time log of production updates (simulated).

## 3. Backend Logic (WBCSD Compliance)
The Django backend performs complex calculations automatically:
- **Fuel Consumption**: Automatically calculates CO2 based on NCV * Emission Factors.
- **Clinker Production**: Uses the detailed oxide method (CaO/MgO) to compute process emissions (Method A1).
- **Audit Logic**: Every change is tracked in an `AuditLog` for ISO compliance.

## 4. Verification
- **Build**: The Frontend is built using `npm run build` (Next.js 15).
- **API**: The Backend (Django Rest Framework) exposes secure endpoints at `/api/`.
