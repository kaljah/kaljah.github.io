# Third-Party Licensing and Commercial Redistribution Audit

**Product**: NeoCarbon GHG / MRV Platform  
**Target Market**: Multi-operator commercial deployment (Algeria / MENA first)  
**Document Purpose**: Legal and commercial compliance audit of shipped datasets, libraries, factor tables, map tiles, and assets (Item 8.10).  

---

## 1. Scientific & Regulatory Datasets / Emission Factor Tables

| Dataset / Catalog | Source Organization | License / Terms of Use | Commercial Redistribution Posture | Flag for Legal Review |
| :--- | :--- | :--- | :--- | :---: |
| **API Compendium 2021** | American Petroleum Institute (API) | Public technical standard & methodology document | Permissible for implementing engineering formulas and algorithmic calculations. Raw proprietary tables should not be sold as a standalone database. | **YES (Verify API citation wording)** |
| **IPCC Emission Factor Database (EFDB)** | Intergovernmental Panel on Climate Change | United Nations public domain / open science | Free for use and algorithmic embedding with standard academic attribution. | **NO (Open)** |
| **IPCC AR4 / AR5 / AR6 GWPs** | WMO / UNEP / IPCC Assessment Reports | Open international scientific reference | Public reference data freely redistributable. | **NO (Open)** |
| **OGMP 2.0 Reporting Framework** | UNEP / IMEO / Climate & Clean Air Coalition | UNEP open governance standard | Open public framework for oil & gas operators. | **NO (Open)** |
| **Algerian Executive Decree 21-330** | Official Gazette of the Republic of Algeria | Public statutory regulation | Public law / governmental decree; unrestricted reference. | **NO (Public Statutory)** |
| **UK DEFRA / DESNZ Factors** | UK Department for Energy Security and Net Zero | Open Government Licence (OGL v3.0) | Permissible for worldwide commercial and non-commercial redistribution with attribution. | **NO (OGL v3.0 Compliant)** |
| **US EPA GHG Hub** | United States Environmental Protection Agency | US Government Public Domain | Unrestricted public domain worldwide. | **NO (Public Domain)** |

---

## 2. Geospatial Assets & Map Tiles

| Asset / Service | Provider | License / Terms | Commercial Risk Analysis | Recommendation |
| :--- | :--- | :--- | :--- | :--- |
| **OpenStreetMap Vector Tiles** | OpenStreetMap Foundation | ODbL (Open Database License) | Map display is permissible; any modified OSM spatial database must remain ODbL. | Add explicit OSM attribution: `"© OpenStreetMap contributors"`. |
| **CartoDB Positron / Dark Matter Tiles** | CARTO | Creative Commons CC-BY 4.0 | Permissible for commercial SaaS with attribution. | Maintain CARTO attribution in map footer. |

---

## 3. Fonts and Typography

| Font Family | Format | License | Redistribution Status |
| :--- | :--- | :--- | :--- |
| **System Font Stack (Segoe UI, Roboto, SF Pro)** | System-native CSS stack | OS Native / Client Platform | **Zero redistribution liability**; no font files are embedded or bundled. |
| **Inter / System Monospace** | CSS declaration | Open Font License (OFL) / Native | OFL permits commercial use and embedding. |

---

## 4. Software Dependencies (Runtime Libraries)

### Frontend (npm dependencies)
- **React 19 / ReactDOM**: MIT License (Permissive commercial use).
- **Vite 7**: MIT License.
- **Lucide React**: ISC License (Equivalent to MIT/BSD).
- **Recharts**: MIT License.
- **Radix UI**: MIT License.
- **Framer Motion**: MIT License.
- **i18next**: MIT License.

### Backend (Python packages)
- **Flask**: BSD 3-Clause License.
- **SQLAlchemy**: MIT License.
- **ReportLab**: BSD License (Open-source core version used; commercial Plus features not required).
- **OpenPyXL**: MIT License.
- **NumPy / SciPy**: BSD 3-Clause License.
- **Argon2-cffi / Cryptography**: Apache 2.0 / BSD.

---

## 5. Summary Findings for Corporate Counsel

1. **Copyleft Protection**: No AGPL or GPL-licensed components are bundled in the proprietary core application.
2. **Proprietary Factor Libraries**: All emission factor numbers in the database are standard published industry factors or user-created custom factors; no proprietary commercial vendor data (e.g. Ecoinvent, GaBi) is bundled without license.
3. **Attribution Statements**: Maintained in `LICENSE`, footer, and exported reports to fulfill MIT, BSD, and CC-BY requirements.
