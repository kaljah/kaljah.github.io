# Walkthrough: Automatic Region Defaults, IT Role Security, & Unrestricted IT Manager Experience

This walkthrough documents three key features implemented in this project:
1. **Application-Wide Region, Division, and Activity Defaults**: Automatic default assignments for connected users and superusers across all forms, filters, and pages.
2. **"IT" Role Security & Credentials Isolation**: Restricting basic IT users (`role: "it"`) strictly to resetting/modifying user passwords, with zero access to business or operational data.
3. **"IT Manager" Full Unrestricted Access & Inline Form Button Placement**: Ensuring IT Managers have completely unrestricted access to user identities, roles, regions, status toggles, password resets, and account lifecycle management, with action buttons positioned directly below the input fields.

---

## Part 1: Automatic Region, Division, and Activity Defaults

- **Backend**:
  - Enhanced `/api/auth/login` and `/api/auth/me` with `get_user_operational_defaults(user)`, returning `default_region`, `default_division`, `default_activity`, `default_facility_id`, and `default_facility_name`.
  - Updated `/api/filters/available` to return both `region` (basin/code) and `location` for every facility.
- **Frontend Utility**:
  - Created `new/client/src/utils/userDefaults.js` with `getUserOperationalDefaults`, `matchesFacilityRegion`, `matchesActivity`, and `isUnrestrictedLocation`.
- **Pages & Forms Defaulted**:
  - `ManageData.jsx` (toolbar filters and all record creation forms defaulted).
  - `DashboardEnhanced.jsx`, `CarbonIntensity.jsx`, `MethaneIntensity.jsx`, `Reports.jsx`, `MethaneExplorer.jsx`.
  - `Scope1Form.jsx`, `Scope2Form.jsx`, `Scope3Form.jsx`, `BatchReviewWizard.jsx`, and `UncertaintyAssessment.jsx`.

---

## Part 2: "IT" Role Security & Credentials Management

- Basic IT users (`role: "it"`) can only access `/user-management` to modify and reset user passwords.
- Blocked on both backend and frontend from creating users, modifying profiles/roles, deleting users, modifying settings, or accessing any operational emissions or facility data.

---

## Part 3: "IT Manager" Full Access & Form Action Button Positioning

### 1. Full Unrestricted Access for IT Managers
- **Interchangeable Role Authority**: Supported both `it_manager` and `it_admin` roles at `ROLE_RANK = 4`.
- **System Role Reassignment**:
  - Removed previous locks (`disabled={!!editingUser}` and "Locked by Policy") from the User Management edit drawer.
  - IT Managers can change any user's role to Standard User, Super User, Admin, IT Manager, or IT.
- **Assigned Region Reassignment**:
  - Unlocked the Assigned Region dropdown when editing accounts, permitting regional scope reassignment.
- **Account Status Toggle**:
  - Added an **Account Status** selector (`Active (Full Access Granted)` / `Disabled (Account Suspended)`) to the Edit User form. IT Managers can directly suspend or reactivate accounts.
- **UI Labeling**:
  - Badges display **"IT Manager"** with gold styling (`#f59e0b`).
  - Header badge indicates **"IT MANAGER CONSOLE"**.
  - Role filter dropdown includes **"IT Manager"**.

### 2. Action Buttons Positioned Directly Under Input Fields
- **Account Creation (`Register New User`)**:
  - Moved the **"Create User"** (primary) and **"Cancel"** (secondary) buttons out of the detached `<Drawer footer>` and placed them directly inside `<form id="um-user-form">` immediately below the Temporary Password field (Section 4).
- **Account Edit (`Edit User Information`)**:
  - Moved the **"Save Changes"** (primary) and **"Cancel"** (secondary) buttons out of the detached footer and placed them directly inside `<form id="um-user-form">` immediately below Section 3 and the Account Status selector.
- **Password Reset (`Reset User Password`)**:
  - Moved the **"Reset Password"** and **"Cancel"** buttons out of the detached footer and placed them directly inside `<form id="um-reset-pwd-form">` immediately below the Confirm New Password field and match validation indicators.

---

## Verification Results

### 1. Automated Backend Tests
Ran `pytest tests/test_it_role_security.py tests/test_operational_defaults.py tests/test_audit_remediation.py`:
- **62 passed, 0 failed** in 4.43s.
- Includes `test_it_manager_full_management_capabilities` testing:
  - User creation with any role :white_check_mark:
  - Profile, role, region, and status modifications :white_check_mark:
  - Password resets :white_check_mark:
  - Account deletion :white_check_mark:
  - Zero operational GHG data access enforcement :white_check_mark:

### 2. Frontend Production Build
- Ran `npm run build` in `new/client`:
  - 3,203 modules transformed cleanly.
  - Built production bundle in 13.43s with zero bundling or syntax errors.

### 3. Knowledge Graph Updated
- Ran `graphify update .`:
  - 4,182 nodes, 6,957 edges, 367 communities synchronized in `graphify-out/`.
