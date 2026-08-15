README.md b/README.md
index 211630e..2fac72c 100644
--- a/README.md
+++ b/README.md
@@ -5,7 +5,7 @@
 [![React](https://img.shields.io/badge/Frontend-React%2018%20%2B%20Vite-61dafb.svg)](https://reactjs.org/)
 [![License](https://img.shields.io/badge/License-MIT-lightgrey.svg)](LICENSE)
 
-An enterprise-grade Greenhouse Gas (GHG) accounting, emission analytics, and compliance reporting platform designed for oil & gas, industrial, and enterprise operations. Built on standard emission calculation methodologies (API Compendium 2021, GHG Protocol, IPCC AR5/AR6, OGMP 2.0, and EU CBAM).
+An enterprise-grade Greenhouse Gas (GHG) accounting, emission analytics, and compliance reporting platform designed for oil & gas, industrial, and enterprise operations. Built on standard emission calculation methodologies (API Compendium 2021, GHG Protocol, IPCC AR5/AR6, and OGMP 2.0).
 
 ---
 
@@ -18,7 +18,6 @@ An enterprise-grade Greenhouse Gas (GHG) accounting, emission analytics, and com
 - **Regulatory Compliance & Intensity Analytics**:
   - **Carbon & Methane Intensity**: Field-level and corporate intensity indicators (kg CO2e/boe, % methane loss).
   - **OGMP 2.0 Framework**: Gold Standard level 4/5 measurement and survey tracking.
-  - **EU CBAM Support**: Embedded carbon calculations and export reporting for carbon border adjustment.
   - **Uncertainty Assessment**: Analytical propagation and confidence interval assessment for emission data.
 - **High-Performance Ingestion**:
   - Background asynchronous batch processor for large CSV/Excel emission datasets.
@@ -85,6 +84,11 @@ ew/start_all.bat or run:
    - **Backend API**: http://localhost:5000
    - **Frontend UI**: http://localhost:5173
 
+3. **Default Admin Login**:
+   - **Email**: `admin@ghg.com`
+   - **Password**: `Admin12345!`
+   *(To seed or reset admin credentials anytime: `python seed_admin.py` in `new/server`)*
+
 ---
 
 ### Option B: Manual Setup
