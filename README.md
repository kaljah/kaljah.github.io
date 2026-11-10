# Greenhouse Gas (GHG) Accounting & Reporting Platform

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Backend-Flask%203.1-green.svg)](https://flask.palletsprojects.com/)
[![React](https://img.shields.io/badge/Frontend-React%2019%20%2B%20Vite-61dafb.svg)](https://react.dev/)
[![License](https://img.shields.io/badge/License-MIT-lightgrey.svg)](LICENSE)

A Greenhouse Gas (GHG) accounting, emission analytics, and reporting platform designed for oil & gas, industrial, and enterprise operations. Built on standard emission calculation methodologies (API Compendium 2021, GHG Protocol, IPCC AR5/AR6).

---

## 🌟 Key Features

- **Multi-Scope GHG Accounting**:
  - **Scope 1**: Direct emissions across Combustion (stationary/mobile), Flaring, Venting (tank, blowdown, AGR, dehydrators), Pneumatic devices, Completions, Drilling, and Fugitive components.
  - **Scope 2**: Indirect emissions from purchased electricity, steam, heating, and cooling (Market-based and Location-based methods).
  - **Scope 3**: Spend-based screening across GHG Protocol value chain categories (EEIO / NAICS factors and activity estimates).
- **Regulatory Compliance & Intensity Analytics**:
  - **Carbon & Methane Intensity**: Field-level and corporate intensity indicators (kg CO2e/boe, % methane loss).
  - **OGMP 2.0 Framework**: Survey tracking and pathway view (preview, reconciliation logic in development; marked **Preview / Roadmap** in the UI).
  - **CBAM Reporting**: EU CBAM Excel template export plus XML export preview (marked **Preview / Roadmap** in the UI).
  - **Uncertainty Assessment**: Basic error propagation (Monte Carlo planned) and confidence interval assessment for emission data.
- **Ingestion & Reporting**:
  - In-process background processing for CSV/Excel emission datasets and PDF master reports.
  - Intelligent column mapping wizard with schema detection.
- **Audit Trails & Security**:
  - Immutable audit logs for calculation parameter changes and record creations.
  - Role-Based Access Control (RBAC) with tenant-scoped isolation.
  - Login rate limiting, CSRF protection, and session timeout controls.

---

## 🏗️ Architecture & Tech Stack

```text
H2/
├── new/
│   ├── server/               # Flask RESTful API Backend
│   │   ├── app.py            # Application factory & entrypoint
│   │   ├── config.py         # Environment-driven configuration
│   │   ├── models.py         # SQLAlchemy ORM models
│   │   ├── calculations/     # Scope 1/2/3 calculation engines & stoichiometry
│   │   ├── routes/           # REST API blueprint routes (auth, emissions, etc.)
│   │   ├── migrations/       # Alembic database migration scripts
│   │   └── tests/            # Pytest automated test suite
│   ├── client/               # React 19 + Vite Frontend SPA
│   │   ├── src/
│   │   │   ├── components/   # Scope forms, wizards, modals, charts
│   │   │   ├── pages/        # Dashboard, Emissions, Intensity, Reports, etc.
│   │   │   ├── context/      # Auth & Layout state providers
│   │   │   └── utils/        # Emission factor catalogs & PDF generators
│   │   ├── package.json
│   │   └── vite.config.ts
│   ├── setup.bat             # Windows installation & demo seed script
│   ├── reset_sandbox.bat     # Restore pristine demo sandbox snapshot (Windows)
│   ├── reset_sandbox.sh      # Restore pristine demo sandbox snapshot (Linux/macOS)
│   └── start_all.bat         # Windows launch script
├── scripts/
│   ├── seed_demo.py          # Idempotent synthetic demo seeder (generated passwords)
│   └── leak_scan.py          # Sensitive string scanner across code, DB, PDFs, dist
└── README.md
```

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python**: 3.10 or higher
- **Node.js**: 18.0 or higher (with npm)
- **Git**

---

### Option A: One-Click Sandbox Setup (Windows)

1. **Install Dependencies & Seed Demo Sandbox**:
   Run `new/setup.bat`:
   ```cmd
   cd new
   setup.bat
   ```
   `setup.bat` installs Python and Node dependencies, initializes the SQLite schema via Alembic, runs `scripts/seed_demo.py`, creates the pristine template snapshot (`new/server/instance/demo_template.db`), and prints one-time generated credentials for `demo.admin@example.org`, `demo.operator@example.org`, and `demo.auditor@example.org`.

2. **Start the Platform**:
   Run `new/start_all.bat`:
   ```cmd
   start_all.bat
   ```
   - **Backend API**: http://localhost:5000
   - **Frontend UI**: http://localhost:5173

3. **Resetting the Sandbox**:
   To restore the pristine template DB, re-seed, and clear uploads/caches:
   ```cmd
   cd new
   reset_sandbox.bat
   ```
   On Linux/macOS, run `bash new/reset_sandbox.sh`.

---

### Option B: Manual Setup

#### 1. Backend Setup (Flask)
```bash
# Navigate to backend directory
cd new/server

# Create and activate virtual environment (optional but recommended)
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables (from repo root)
cp ../../.env.example .env

# Run database migrations
flask db upgrade

# Seed synthetic demo dataset (prints generated passwords once)
python ../../scripts/seed_demo.py

# Start backend server
python app.py
```
*Backend runs at http://localhost:5000.*

#### 2. Frontend Setup (React + Vite)
```bash
# Navigate to frontend directory
cd new/client

# Install dependencies
npm install

# Start development server
npm run dev
```
*Frontend runs at http://localhost:5173.*

---

## 🧪 Running Automated Tests

Run backend unit and security tests using pytest:

```bash
cd new/server
python -m pytest
```

Run frontend checks:

```bash
cd new/client
npm run typecheck
npm run lint
npm test
npm run build
```

---

## 🔒 Security & Environment Configuration

Copy `.env.example` (at repo root and `new/server/.env.example`) to `.env` and set appropriate production values before deploying. Never commit real credentials or client data:

| Variable | Description | Default |
| :--- | :--- | :--- |
| FLASK_ENV | Environment mode (development or production) | development |
| SECRET_KEY | Secret key for Flask sessions | Auto-generated in dev |
| CDSE_USERNAME / CDSE_PASSWORD | Copernicus Data Space Ecosystem credentials (optional) | Unset (disabled) |
| DB_TYPE | Database backend (sqlite or postgres) | sqlite |
| DATABASE_URL | Connection URI for SQLite or PostgreSQL | sqlite:///ghg_app.db |
| ALLOWED_ORIGINS | Comma-separated CORS allowed origins | http://localhost:5173 |
| VITE_API_URL | Frontend API backend endpoint | http://localhost:5000/api |

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
