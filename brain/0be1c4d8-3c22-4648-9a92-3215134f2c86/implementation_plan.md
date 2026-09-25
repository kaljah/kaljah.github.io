# Implementation Plan: E2E Product Experience & Feature Polish Remediation

Remediate the remaining verified defects (**DEF-09** to **DEF-12**) identified during the comprehensive End-to-End Product Experience & Feature Verification Audit across the Sonatrach Enterprise GHG & Methane Accounting platform.

## User Review Required

> [!NOTE]
> All proposed changes maintain strict backward compatibility with existing backend contracts and database schemas. No breaking API changes or database migrations are introduced.

1. **Session Timeout Warning Behavior (DEF-10):**
   - At 9 minutes of inactivity (60 seconds prior to the 10-minute timeout), a pre-expiry warning toast will be triggered: *"Your session will expire in 60 seconds due to inactivity. Move your mouse to stay signed in."*
   - If timeout occurs, the user is redirected to `/login`, where a clear alert banner informs them that their session timed out due to inactivity, rather than presenting an unexplained login form.
2. **Missing Production vs. Zero Intensity (DEF-11):**
   - If emissions $> 0$ but total production ($BOE$) is $0$, instead of rendering `0.00 kg/BOE`, the metric card will explicitly display `Pending Production` with an alert badge, clarifying that production import is required.
3. **Double-Click Submission Locks (DEF-09):**
   - Buttons across `Scope1Form`, `Scope2Form`, and `Scope3Form` will be disabled during in-flight network requests, preventing duplicate emission logs on high-latency networks.

---

## Proposed Changes

### Client Application & Authentication

#### [MODIFY] [AuthContext.jsx](file:///c:/Users/samsung/Desktop/H2/new/client/src/context/AuthContext.jsx)
- Add a 9-minute warning timer (`IDLE_WARNING_MS = 9 * 60 * 1000`) before the 10-minute hard timeout.
- Trigger an automatic warning notice or expose `sessionWarning` / `sessionExpired` state.
- Ensure user activity events seamlessly cancel both the warning and expiry timers.

#### [MODIFY] [Login.jsx](file:///c:/Users/samsung/Desktop/H2/new/client/src/pages/Login.jsx)
- Consume `sessionExpired` from `useAuth()`.
- If `sessionExpired === true`, render an alert banner above the form explaining that the session timed out due to 10 minutes of inactivity.
- Reset `sessionExpired` upon user typing or submitting login credentials.

---

### Manual Ingestion Forms (Concurrency & Double-Submission Guards)

#### [MODIFY] [Scope1Form.jsx](file:///c:/Users/samsung/Desktop/H2/new/client/src/components/Scope1Form.jsx)
- Introduce a `submitting` state.
- Wrap `handleAddEntry` in `setSubmitting(true)` / `finally { setSubmitting(false) }`.
- Disable both `Save as Draft` and `+ Calculate & Submit for Review` buttons when `submitting === true`, updating button labels to indicate ongoing processing.

#### [MODIFY] [Scope2Form.jsx](file:///c:/Users/samsung/Desktop/H2/new/client/src/components/Scope2Form.jsx)
- Introduce a `submitting` state and disable submission buttons during in-flight `POST /scope2` requests.

#### [MODIFY] [Scope3Form.jsx](file:///c:/Users/samsung/Desktop/H2/new/client/src/components/Scope3Form.jsx)
- Introduce a `submitting` state and disable submission buttons during in-flight `POST /scope3` requests.

---

### Analytics & Intensity Dashboards (Zero-Production Handling)

#### [MODIFY] [DashboardEnhanced.jsx](file:///c:/Users/samsung/Desktop/H2/new/client/src/pages/DashboardEnhanced.jsx)
- Update the Performance Intensity KPI calculation: if `totalBoeForIntensity === 0` but `totalEmissionsForIntensity > 0`, set an indicator that production data is pending.
- Display a descriptive `Missing Production` badge instead of `0.00 kg/BOE` when production data is missing.

#### [MODIFY] [CarbonIntensity.jsx](file:///c:/Users/samsung/Desktop/H2/new/client/src/pages/CarbonIntensity.jsx)
- In `loadIntensityData`, if `tBoe === 0` and `tCo2e > 0`, set `avgCo2Intensity: null`.
- When rendering the intensity value, if `null`, display `Pending Production` with a warning badge instead of `0.00 kg/BOE`.

---

### Governance & Reporting Polish

#### [MODIFY] [ManageData.jsx](file:///c:/Users/samsung/Desktop/H2/new/client/src/pages/ManageData.jsx)
- In the tab rendering logic, when `activeTab === 'pending' && !isPrivileged`, render a styled informative card explaining that pending queue approval is restricted to Managers and Administrators under Maker-Checker governance, preventing a blank screen.

#### [MODIFY] [Reports.jsx](file:///c:/Users/samsung/Desktop/H2/new/client/src/pages/Reports.jsx)
- Remove stray in-JSX debug logging (`console.log` on line 401 and line 356) to maintain a clean production console.

---

## Verification Plan

### Automated Tests
- Run backend pytest test suite to ensure calculation dispatcher and API contracts are unaffected:
  ```powershell
  python -m pytest new/server/tests/ -q
  ```
- Run frontend production build to verify zero compilation or bundling errors:
  ```powershell
  npm --prefix new/client run build
  ```

### Manual Verification
1. **Double Submission:** Click rapid-fire on "Calculate & Submit for Review" in Scope 1, Scope 2, and Scope 3; verify buttons disable instantly and only one request is dispatched in the network monitor.
2. **Session Expiry Notice:** Verify that when `logout(true)` triggers, `/login` displays the inactivity timeout alert banner.
3. **Zero Production Display:** Verify that on a facility with logged emissions but 0 BOE production, the dashboard and carbon intensity KPI display "Missing Production" instead of "0.00 kg/BOE".
4. **Manage Data Pending Tab:** As a non-admin user, navigate to `/manage-data?tab=pending`; verify the informative permission card is displayed instead of a blank screen.
