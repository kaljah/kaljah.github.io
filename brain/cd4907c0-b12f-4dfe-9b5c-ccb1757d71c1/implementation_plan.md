# Implementation Plan: Full IT Manager Access & Inline Form Action Buttons

Ensure the **IT Manager** role has full, unrestricted access to the User Management ("Account Manager") page (including user creation, profile & role editing, region reassignment, account status toggle, password resets, and account deletion), and reposition the action buttons in the Account Creation, Account Edit, and Password Change drawers directly underneath the form fields.

---

## Proposed Changes

### 1. Backend: IT Manager Role Alignment & Unrestricted Permissions

#### [MODIFY] [`new/server/routes/auth.py`](file:///c:/Users/samsung/Desktop/H2/new/server/routes/auth.py)
- Support both `"it_manager"` and `"it_admin"` interchangeably as full administrative IT credentials managers:
  - Update `ROLE_RANK`: `{"user": 0, "it": 1, "superuser": 2, "admin": 3, "it_admin": 4, "it_manager": 4}`.
  - Update `VALID_ROLES`: include `"it_manager"`.
  - Update `@it_admin_required`: authorize both `["it_admin", "it_manager"]`.
  - Update `@it_access_required`: authorize `["it_admin", "it_manager", "it"]`.
  - Update `/register`, `/users/<id>` (PUT), `/users/<id>` (DELETE), `/forgot-password`, and `/users/<id>/reset-password` to fully support `it_manager` with rank 4 authority (can assign/reassign any role, edit any user profile, activate/deactivate accounts, and delete accounts).
  
#### [MODIFY] [`new/server/utils.py`](file:///c:/Users/samsung/Desktop/H2/new/server/utils.py) & Operational Route Decorators
- Ensure `it_manager` maintains the same strict zero-operational-data isolation as `it_admin` across emissions, facilities, manage data, and reporting endpoints.

---

### 2. Frontend: Button Placement & Unrestricted User Management UI

#### [MODIFY] [`new/client/src/pages/UserManagement.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/pages/UserManagement.jsx)
1. **Button Repositioning (Directly Under Form Fields)**:
   - **Account Creation (`!editingUser`)**:
     - Move the **"Create User"** and **"Cancel"** buttons out of the detached `<Drawer footer={...}>` and place them directly inside `<form id="um-user-form">` immediately below the Temporary Password field (Section 4).
   - **Account Edit (`editingUser`)**:
     - Move the **"Save Changes"** and **"Cancel"** buttons out of the detached `<Drawer footer={...}>` and place them directly inside `<form id="um-user-form">` immediately below the form fields.
   - **Password Change / Reset (`resetTarget`)**:
     - Move the **"Reset Password"** and **"Cancel"** buttons out of the detached `<Drawer footer={...}>` and place them directly inside `<form id="um-reset-pwd-form">` immediately below the Confirm New Password field and validation indicators.
2. **Remove All Limitations for IT Manager**:
   - Unlock System Role when editing a user (remove `disabled={!!editingUser}` and the "Locked by Policy" warning). IT Managers can reassign any user's role without limitation.
   - Unlock Assigned Region when editing a user (remove `disabled={!!editingUser}`). IT Managers can reassign a user's region without limitation.
   - Add an **Account Status** selector (`Active`, `Disabled`) in the Edit User form so IT Managers can activate/deactivate accounts directly.
   - Support `it_manager` alongside `it_admin` in `ROLE_META`, role filter dropdowns, and drawer role selector (`label: "IT Manager"`).
   - Ensure header badge reflects `"IT MANAGER CONSOLE"` for `it_admin` and `it_manager`.

#### [MODIFY] [`new/client/src/App.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/App.jsx) & [`new/client/src/components/layout/Sidebar.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/components/layout/Sidebar.jsx)
- Recognize `"it_manager"` in route guards and navigation items identically to `"it_admin"`.

---

## Verification Plan

### Automated Tests
1. **Pytest Security & Management Suite**:
   - Run `python -m pytest tests/test_it_role_security.py tests/test_audit_remediation.py tests/test_operational_defaults.py`.
   - Add test cases in `tests/test_it_role_security.py` verifying that an `it_manager` can create users, edit any user role/region/status, reset passwords, and delete accounts without limitation.
2. **Frontend Production Build**:
   - Run `npm run build` in `new/client` to guarantee zero compilation, bundling, or styling regressions.

### Manual / Visual Verification
1. Inspect the "Add New User" drawer: Verify the "Create User" and "Cancel" buttons are positioned directly under the Temporary Password field.
2. Inspect the "Edit User" drawer: Verify the "Save Changes" and "Cancel" buttons are positioned directly under the fields, and the System Role, Assigned Region, and Account Status fields are completely unlocked and editable.
3. Inspect the "Reset Password" drawer: Verify the "Reset Password" and "Cancel" buttons are positioned directly under the Confirm New Password field.
