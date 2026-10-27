<!-- Generated: 2026-10-27 | Files scanned: 637 | Token estimate: ~650 -->
# Dependencies & External Integrations

Third-party libraries, runtime engines, and integration touchpoints for both backend and frontend.

## Backend Python Dependencies (`new/server/requirements.txt`)

| Category | Package | Version | Purpose |
|---|---|---|---|
| **Core Framework** | `Flask` | 3.1.3 | WSGI Web framework and application factory |
| **ORM & DB** | `Flask-SQLAlchemy` | 3.1.1 | Database abstraction & model mapping |
| **DB Driver** | `psycopg2-binary` | >=2.9.9 | PostgreSQL connector for production workloads |
| **Migrations** | `Flask-Migrate` | 4.0.5 | Alembic migration management |
| **Security & Auth** | `Flask-WTF` | 1.2.1 | CSRF token generation and validation |
| **Rate Limiting** | `Flask-Limiter` | 3.5.0 | Memory / Redis-backed request throttling |
| **Async & Cache** | `redis` | >=5.0.0 | Redis queue and state store for background jobs |
| **Spreadsheets** | `openpyxl` | >=3.1.5 | Excel workbook ingestion & template generation |
| **Reports & Charts** | `reportlab` | >=4.1.0 | Server-side PDF generation engine |
| **Plotting** | `matplotlib` | >=3.8.0 | Server-side intensity & trend chart rendering |
| **API Docs** | `flask-swagger-ui`| 4.11.1 | OpenAPI / Swagger interactive documentation |
| **Production WSGI**| `gunicorn` | >=21.2.0 | Production HTTP server |
| **Testing** | `pytest`, `hypothesis`| >=8.0.0 | Unit, integration, property-based testing |

## Frontend JavaScript/TypeScript Dependencies (`new/client/package.json`)

| Category | Package | Version | Purpose |
|---|---|---|---|
| **Core UI** | `react`, `react-dom` | ^19.2.0 | Reactive component rendering engine |
| **Build & Bundler** | `vite` | ^7.2.4 | High-performance dev server and Rollup packager |
| **Routing** | `react-router-dom` | ^7.13.0 | Client-side SPA routing and navigation guards |
| **Styling** | `tailwindcss` | ^4.3.3 | Utility-first styling framework |
| **Primitives** | `@radix-ui/*` | ^1.x - 2.x | Accessible dialogs, popovers, dropdowns, tooltips |
| **Icons** | `lucide-react` | ^0.563.0 | Consistent vector icon system |
| **Charts** | `recharts` | ^3.7.0 | SVG charting for emissions and intensity trends |
| **Maps** | `leaflet`, `react-leaflet`| ^1.9.4 | Interactive GIS map for facility & methane plumes |
| **Table Virtualization**| `@tanstack/react-table`| ^8.21.3 | High-throughput tabular data handling |
| **CSV Parser** | `papaparse` | ^5.5.4 | Client-side CSV stream parsing for bulk uploads |
| **Client PDF Export** | `jspdf`, `html2canvas`| ^4.1.0 | In-browser high-resolution PDF rendering |
| **Motion** | `framer-motion` | ^13.1.0 | Micro-interactions and login animations |
| **Testing** | `vitest`, `@playwright/test`| ^5.0 / ^1.63 | Unit testing and cross-browser E2E automation |

## External Integrations & Protocol Standards

- **GHG Protocol**: Corporate Standard calculation logic for Scope 1, 2, and 3.
- **API Compendium (2021)**: Primary oil & gas emission factors and stoichiometric formulas.
- **UNEP OGMP 2.0**: Gold Standard reporting templates and measurement levels (1 through 5).
- **EU CBAM**: Embedded carbon export compliance calculation templates.
- **SBTi**: Science Based Targets initiative trajectory tracking and net-zero milestone verification.
