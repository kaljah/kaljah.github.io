<!-- Generated: 2026-10-27 | Files scanned: 637 | Token estimate: ~800 -->
# Frontend Architecture

React 19 + TypeScript SPA built with Vite, Tailwind CSS, Lucide icons, and Radix UI primitives.

## Page Hierarchy & Navigation Groups

Configured in `new/client/src/app/routes.config.ts`:

```
App (App.tsx)
 ├── /login                     → Login.tsx (Lazy, framer-motion)
 └── AppShell (AppShell.tsx)     → Authenticated shell with Sidebar & Breadcrumbs
       │
       ├── [ Overview ]
       │     ├── /                      → DashboardEnhanced.tsx (KPIs, Charts, Breakdowns)
       │     ├── /carbon-intensity      → CarbonIntensity.tsx (kg CO2e/boe benchmarks)
       │     ├── /methane-intensity     → MethaneIntensity.tsx (OGMP 2.0 preview, reconciliation logic in development)
       │     ├── /sbti                  → SbtiDashboard.tsx (Net-zero target trajectories)
       │     └── /methane-explorer      → MethaneExplorer.tsx (Leaflet interactive GIS map)
       │
       ├── [ Data ]
       │     ├── /emissions             → Emissions.tsx (Scope 1/2/3 calculation forms)
       │     ├── /manage-data           → ManageData.tsx (Batch upload wizard & table editor)
       │     └── /reference-data        → ReferenceData.tsx (Emission factor library)
       │
       ├── [ Assurance & Reporting ]
       │     ├── /reports               → Reports.tsx (PDF exporter, CBAM [Preview / Roadmap XML], OGMP)
       │     ├── /uncertainty           → UncertaintyAssessment.tsx (Basic error propagation; Monte Carlo planned)
       │     ├── /qa-dashboard          → QADashboard.tsx (Diagnostics & anomaly review)
       │     └── /audit-trail           → AuditTrail.tsx (Immutable ledger view)
       │
       └── [ Administration ]
             ├── /user-management       → UserManagement.tsx (RBAC user CRUD)
             └── /settings              → Settings.tsx (User profile, theme, locale)
```

## State & Context Hierarchy

```
ErrorBoundary
  └─► BrowserRouter
        └─► AuthProvider (AuthContext.tsx: user, role, token, permissions, login/logout)
              └─► LayoutProvider (LayoutContext.tsx: sidebar collapse, active filters)
                    └─► ToastProvider (Toast.tsx: notifications, alerts)
                          └─► AppRoutes (Route guard via RequireRole)
```

## Role-Based Access Control (RBAC)

Guarded by `RequireRole.tsx` using `AccessRule` definitions:
- `nonIT`: Standard operational access (Dashboard, Emissions, Intensity, Reports, Settings).
- `superuser`: QA/QC diagnostics and advanced operational overrides.
- `audit`: Read-only access to immutable audit trails and compliance records.
- `it`: IT administration and user account management.

## Key Frontend Modules

- `new/client/src/App.tsx` (94 lines): Application wrapper, lazy route registration, CSRF bootstrap.
- `new/client/src/app/routes.config.ts` (79 lines): Single source of truth for routes, navigation, and icons.
- `new/client/src/pages/ManageData.tsx` (1905 lines): Bulk data management, CSV/Excel wizards, batch review.
- `new/client/src/pages/Reports.tsx` (1778 lines): Multi-scope compliance reporting and client-side PDF compilation.
- `new/client/src/pages/DashboardEnhanced.tsx` (1133 lines): Interactive Recharts visualizations, intensity rollups.
- `new/client/src/components/BatchReviewWizard.tsx` (1035 lines): Multi-step staged data validation and import review.
- `new/client/src/components/ColumnMappingWizard.tsx` (234 lines): Schema matching for user-supplied datasets.
- `new/client/src/context/AuthContext.tsx` (336 lines): Session persistence, CSRF syncing, and identity hooks.
