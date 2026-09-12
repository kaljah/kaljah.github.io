# Greenhouse Gas (GHG) Accounting & Reporting Platform

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Backend-Flask%203.0-green.svg)](https://flask.palletsprojects.com/)
[![React](https://img.shields.io/badge/Frontend-React%2018%20%2B%20Vite-61dafb.svg)](https://reactjs.org/)
[![License](https://img.shields.io/badge/License-MIT-lightgrey.svg)](LICENSE)

An enterprise-grade Greenhouse Gas (GHG) accounting, emission analytics, and compliance reporting platform designed for oil & gas, industrial, and enterprise operations. Built on standard emission calculation methodologies (API Compendium 2021, GHG Protocol, IPCC AR5/AR6, and OGMP 2.0).

---

## 🌟 Key Features

- **Multi-Scope GHG Accounting**:
  - **Scope 1**: Direct emissions across Combustion (stationary/mobile), Flaring, Venting (tank, blowdown, AGR, dehydrators), Pneumatic devices, Completions, Drilling, and Fugitive components.
  - **Scope 2**: Indirect emissions from purchased electricity, steam, heating, and cooling (both Market-based and Location-based methods).
  - **Scope 3**: Upstream and downstream value chain emissions across all 15 GHG Protocol categories.
- **Regulatory Compliance & Intensity Analytics**:
  - **Carbon & Methane Intensity**: Field-level and corporate intensity indicators (kg CO2e/boe, % methane loss).
  - **OGMP 2.0 Framework**: Gold Standard level 4/5 measurement and survey tracking.
  - **Uncertainty Assessment**: Analytical propagation and confidence interval assessment for emission data.
- **High-Performance Ingestion**:
  - Background asynchronous batch processor for large CSV/Excel emission datasets.
  - Intelligent column mapping wizard with automatic schema detection.
- **Audit Trails & Security**:
  - Immutable audit logs for all calculation parameter changes and record creations.
  - Role-Based Access Control (RBAC) with Organization Row-Level Security (RLS).
  - Rate limiting, CSRF protection, and secure session management.

---

## 🏗️ Architecture & Tech Stack

`	ext
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
│   ├── client/               # React 18 + Vite Frontend SPA
│   │   ├── src/
│   │   │   ├── components/   # Scope forms, wizards, modals, charts
│   │   │   ├── pages/        # Dashboard, Emissions, Intensity, Reports, etc.
│   │   │   ├── context/      # Auth & Layout state providers
│   │   │   └── utils/        # Emission factor catalogs & PDF generators
│   │   ├── package.json
│   │   └── vite.config.js
│   ├── setup.bat             # One-click Windows installation script
│   └── start_all.bat         # One-click Windows launch script
└── README.md
`

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python**: 3.10 or higher
- **Node.js**: 18.0 or higher (with npm)
- **Git**

---

### Option A: One-Click Launch (Windows)

1. **Install Dependencies**:
   Double-click 
ew/setup.bat or run:
   `cmd
   cd new
   setup.bat
   `
2. **Start the Platform**:
   Double-click 
ew/start_all.bat or run:
   `cmd
   start_all.bat
   `
   - **Backend API**: http://localhost:5000
   - **Frontend UI**: http://localhost:5173

3. **Admin Account Setup**:
   - Initial administrative accounts are configured via environment variables `ADMIN_EMAIL` and `ADMIN_PASSWORD` (defaults to `admin@ghg.com` with initial dev credentials).
   - In production, ensure `ADMIN_PASSWORD` and `IT_ADMIN_PASSWORD` are set in `.env` before running setup.
   - To seed or update admin credentials at any time:
     ```bash
     cd new/server
     python seed_admin.py
     ```
     *(To overwrite existing passwords, pass `--force-reset-password`)*

---

### Option B: Manual Setup

#### 1. Backend Setup (Flask)
`ash
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

# Configure environment variables
cp .env.example .env

# Run database migrations
flask db upgrade

# Start backend server
python app.py
`
*Backend runs at http://localhost:5000.*

#### 2. Frontend Setup (React + Vite)
`ash
# Navigate to frontend directory
cd new/client

# Install dependencies
npm install

# Configure environment variables
cp .env.example .env

# Start development server
npm run dev
`
*Frontend runs at http://localhost:5173.*

---

## 🧪 Running Automated Tests

Run backend unit and security tests using pytest:

`ash
cd new/server
python -m pytest tests/
`

---

## 🔒 Security & Environment Configuration

Copy .env.example in both 
ew/server and 
ew/client to .env and set appropriate production values before deploying:

| Variable | Description | Default |
| :--- | :--- | :--- |
| FLASK_ENV | Environment mode (development or production) | development |
| SECRET_KEY | Secret key for JWT sessions | Auto-generated in dev |
| DB_TYPE | Database backend (sqlite or postgres) | sqlite |
| DATABASE_URL | Connection URI for SQLite or PostgreSQL | sqlite:///ghg_app.db |
| ALLOWED_ORIGINS | Comma-separated CORS allowed origins | http://localhost:5173 |
| VITE_API_URL | Frontend API backend endpoint | http://localhost:5000/api |

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
