# Enterprise Platform Hardening & Full-Stack Reliability Plan

This implementation plan addresses the remaining production, user experience, compliance, and infrastructure aspects to elevate the GHG Enterprise Accounting Platform to bankable, enterprise-grade production readiness.

## User Review Required

> [!IMPORTANT]
> - **Multi-Tab Synchronization**: Logging out in one browser tab will immediately synchronize across all open browser tabs via `BroadcastChannel` and redirect them to `/login`.
> - **GWP Time Horizon**: A GWP-100 (standard 100-year, $\text{CH}_4=28$) vs GWP-20 (near-term 20-year, $\text{CH}_4=84$) toggle will be introduced in the Dashboard to allow dual-horizon analysis per IPCC AR5/AR6 guidelines.
> - **Readiness vs Liveness Health Probes**: `/api/health/live` (shallow, ping process) and `/api/health/ready` (deep, ping database with `SELECT 1`) will be added alongside the legacy `/api/health` route for full Kubernetes/Docker compatibility.

---

## Proposed Changes

The implementation is grouped into 4 functional modules:

---

### Component 1: User Experience & Session Resilience (Frontend)

#### [MODIFY] [`new/client/src/context/AuthContext.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/context/AuthContext.jsx)
- **Multi-Tab Logout Synchronization:** Initialize a `BroadcastChannel("ghg_auth_channel")` and `window.addEventListener("storage")`. When `logout()` executes in Tab A, a broadcast event notifies all sibling tabs to clear their in-memory user state and navigate to `/login` with an informative toast.
- **Cross-Tab Activity Keep-Alive:** Synchronize user interaction timestamps across tabs so active work in Tab B prevents an idle logout in Tab A.

#### [MODIFY] [`new/client/src/components/layout/Layout.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/components/layout/Layout.jsx)
- **Offline / Network Interruption Banner:** Listen to `window.addEventListener("online")` and `window.addEventListener("offline")`, with initial state from `navigator.onLine`. Display a floating warning banner if connection is lost: *"Network connection lost. Offline changes will not be saved until reconnected."*

#### [MODIFY] [`new/client/src/index.css`](file:///c:/Users/samsung/Desktop/H2/new/client/src/index.css)
- **Global Print Stylesheet (`@media print`):** Add comprehensive print rules:
  - Hide `.sidebar`, `.topbar`, action buttons, modals, and toasts (`display: none !important;`).
  - Expand `.main-content` to 100% width with no margin/padding clipping.
  - Optimize typography and tables for high-contrast B&W physical printing and PDF generation (`Ctrl+P`).

#### [NEW] [`new/client/src/hooks/useFormDraft.js`](file:///c:/Users/samsung/Desktop/H2/new/client/src/hooks/useFormDraft.js)
- **Form Draft Auto-Save Hook:** Lightweight custom hook that persists in-progress form inputs to `localStorage` under a scoped key (e.g., `draft_scope1_form`), with `saveDraft`, `loadDraft`, and `clearDraft` methods to ensure operators never lose data on accidental page refreshes.

---

### Component 2: Regulatory & GHG Protocol Standards Rigor (Backend & Analytics)

#### [MODIFY] [`new/server/routes/dashboard.py`](file:///c:/Users/samsung/Desktop/H2/new/server/routes/dashboard.py)
- **GWP-20 vs GWP-100 Dynamic Time Horizon:** Support optional query parameter `gwp_horizon=20|100` in `/api/dashboard/summary` and `/api/dashboard/analytics`. When `gwp_horizon=20` is requested, Methane $\text{CO}_2\text{e}$ calculations scale from $\text{GWP}_{100} = 28$ to $\text{GWP}_{20} = 84$ (3× factor) and Nitrous Oxide scales from $265$ to $264$, returning dual metrics for near-term climate impact assessment.

#### [MODIFY] [`new/client/src/pages/DashboardEnhanced.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/pages/DashboardEnhanced.jsx)
- **Time Horizon Selector:** Add a toggle in the dashboard header between **100-Year GWP (Standard)** and **20-Year GWP (Near-Term Warming)** with explanatory badge and tooltip explaining the Methane acceleration effect.

#### [MODIFY] [`new/server/routes/scope2.py`](file:///c:/Users/samsung/Desktop/H2/new/server/routes/scope2.py) & [`new/server/routes/reports.py`](file:///c:/Users/samsung/Desktop/H2/new/server/routes/reports.py)
- **Dual Scope 2 Reporting Summary:** Provide aggregate comparisons between Location-Based (grid average) and Market-Based (zero-emission contractual / PPA / REC instruments) emissions, ensuring compliance with GHG Protocol Scope 2 Guidance Chapter 6.

---

### Component 3: Cryptographic Audit Trail Sealing (Compliance & Non-Repudiation)

#### [MODIFY] [`new/server/routes/audit.py`](file:///c:/Users/samsung/Desktop/H2/new/server/routes/audit.py)
- **SHA-256 Audit Chain Verification Endpoint (`GET /api/audit/verify-chain`):**
  - Iterates through chronological `ActivityLog` entries and computes sequential cryptographic hashes:
    $$\text{BlockHash}_n = \text{SHA256}(\text{BlockHash}_{n-1} + \text{id} + \text{timestamp} + \text{action} + \text{user\_id} + \text{record\_id})$$
  - Returns chain integrity verification status (`valid: true`, total records verified, tamper-evident certificate) for third-party verifiers (PwC, EY, DNV).

---

### Component 4: Production Infrastructure & Enterprise Email Dispatching

#### [MODIFY] [`new/server/app.py`](file:///c:/Users/samsung/Desktop/H2/new/server/app.py)
- **Kubernetes / Docker Health Check Probes:**
  - `GET /api/health/live`: Shallow process liveness check (immediate 200).
  - `GET /api/health/ready`: Deep dependency readiness check that executes `db.session.execute(text("SELECT 1"))`. Returns 200 `{"status": "ready", "database": "connected"}` or 503 `{"status": "unhealthy", "database": "unreachable"}`.

#### [NEW] [`new/server/services/email_service.py`](file:///c:/Users/samsung/Desktop/H2/new/server/services/email_service.py)
- **Enterprise Email Dispatch Adapter:**
  - Configurable SMTP / SendGrid / AWS SES transport.
  - Safe local fallback (logs email payload cleanly to logger in dev/testing mode).
  - Templates for:
    1. Password reset notification.
    2. Batch upload pending review notification (for admins).
    3. QA/QC anomaly alert notification.

---

## Verification Plan

### Automated Tests
1. **API Health & Regression Verification:**
   - Execute `python new/test_all_apis_health.py` to confirm all existing + new `/api/health/ready`, `/api/health/live`, `/api/audit/verify-chain` endpoints return healthy status codes with 0 server errors.
   - Run `python -m pytest new/server/tests/ -q` to ensure 435/435 tests pass with zero regressions.
2. **Frontend Build Verification:**
   - Execute `npm run build` in `new/client` to guarantee clean TypeScript/JSX compilation without bundle errors.

### Manual Verification
1. **Multi-Tab Sync:** Open two browser tabs on `http://127.0.0.1:5173`. Log out in Tab 1, observe Tab 2 instantly redirecting to `/login`.
2. **Offline Banner:** Simulate network offline via DevTools Network tab or `window.dispatchEvent(new Event('offline'))`; verify clear warning banner appears and disappears on reconnect.
3. **Print Styles:** Press `Ctrl+P` on Dashboard and Reports; verify sidebar and buttons are hidden and content prints with high-contrast table formatting.
4. **GWP-20 Toggle:** Toggle between 100-Year and 20-Year GWP on the Dashboard; verify total $\text{CO}_2\text{e}$ updates dynamically to reflect 20-year methane potency ($84 \times \text{CH}_4$).
5. **Audit Chain Verification:** Call `GET /api/audit/verify-chain` as admin; verify 200 OK with cryptographic validation certificate.
