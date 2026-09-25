# Modern Slide-Over Drawers & User Profile Editing in User Management

Modernize the user management experience by replacing centered popup modals with right-docked **Slide-Over Drawers** for Add User, Edit User, and Reset Password. In the Edit User form, lock the Role and Region selectors to adhere to administrative governance, and enable editing of standard profile fields (Full Name, Email, Department, Job Title).

## User Review Required

> [!IMPORTANT]
> - **Role & Region Locking in Edit Mode**: The user requested to "lock the role editor" and "also lock the region editor". In the Edit drawer, these fields will be displayed as read-only / disabled with visual lock badges (`Locked by IT Governance`). In the Register drawer, they remain fully selectable.
> - **Profile Fields Editable in Edit Mode**: Full Name, Email, Department, and Job Title will now be editable in Edit mode and saved to the backend database. Password changes remain safely separated into the dedicated Reset Password drawer.

## Proposed Changes

### Backend (`new/server/routes/auth.py`)

#### [MODIFY] [auth.py](file:///c:/Users/samsung/Desktop/H2/new/server/routes/auth.py)
- Expand `PUT /api/auth/users/<id>` (`update_user`):
  - Support `fullName`: update string after trimming.
  - Support `email`: validate format and ensure uniqueness across other users (reject with 400 if already in use).
  - Support `department`: update string after trimming.
  - Support `jobTitle`: update string after trimming.
  - Include updated `fullName`, `email`, `department`, `jobTitle`, `role`, `location`, `status` in the returned `user` dictionary.

---

### Frontend (`new/client/src/pages/UserManagement.jsx`)

#### [MODIFY] [UserManagement.jsx](file:///c:/Users/samsung/Desktop/H2/new/client/src/pages/UserManagement.jsx)
1. **Container & Layout Polish**:
   - Update `S.page` container max-width from `1400px` to `1600px` and `width: 100%` so the page spans naturally on modern displays matching the Dashboard and QA/QC layouts.
2. **Slide-Over Drawer Architecture**:
   - Replace the centered `<Modal>` elements with sleek, right-docked slide-over drawer panels:
     - Backdrop overlay with `backdrop-filter: blur(6px)`.
     - Smooth right-to-left slide-in transition (`transform: translateX(...)`).
     - Escape key listener to close active drawers.
     - Pinned header with icon badge, title, subtitle, and close button.
     - Scrollable body with clean card sections and field groups.
     - Pinned sticky footer with Cancel and Primary action buttons so controls are never hidden when scrolling.
3. **Register New User Drawer**:
   - Modern form sections:
     - *Account Identity*: Full Name, Email Address.
     - *Organization*: Department, Job Title.
     - *Access & Permissions*: System Role (Standard User, Super User, Admin, IT Admin), Assigned Region (required for Standard/Super users).
     - *Initial Credentials*: Temporary Password with length indicator.
4. **Edit User Drawer ("Edit User Information")**:
   - Action tooltip updated from "Edit Role / Region" to "Edit User Information".
   - *Editable Fields*: Full Name, Email Address, Department, Job Title.
   - *Locked Fields*:
     - **System Role**: Disabled with lock badge `<Lock size={12} /> Locked by IT Governance` and helper microcopy explaining role changes require administrative re-provisioning.
     - **Assigned Region**: Disabled with lock badge `<Lock size={12} /> Locked by IT Governance`.
   - `handleSubmit`: sends `{ fullName, email, department, jobTitle, role, location }` to backend `PUT /api/auth/users/<id>`, updates client state optimistically.
5. **Reset User Password Drawer**:
   - Dedicated right-docked drawer:
     - Target User Profile Card: avatar with initials, full name, email, role badge, department.
     - Security notice callout.
     - New Password input with Show/Hide toggle.
     - Live 5-segment password strength indicator (Length >= 10, Uppercase, Lowercase, Number, Special character).
     - Confirm Password input with real-time match verification.
     - Pinned footer with Reset Password button.

---

### Automated Backend Test (`new/server/tests/test_user_profile_update.py`)

#### [NEW] [test_user_profile_update.py](file:///c:/Users/samsung/Desktop/H2/new/server/tests/test_user_profile_update.py)
- Test `PUT /api/auth/users/<id>` updating `fullName`, `email`, `department`, `jobTitle`.
- Test email collision check (attempting to change email to an existing user's email returns 400).

## Verification Plan

### Automated Tests
1. Run `pytest tests/test_user_profile_update.py` in `new/server`.
2. Run `npx eslint src/pages/UserManagement.jsx` in `new/client`.
3. Run `npm run build` in `new/client` to guarantee zero bundling or syntax issues.

### Manual / Live Verification
1. Open User Management at `http://localhost:5173/users`.
2. Click **+ Register User** -> Verify the sleek slide-over drawer docks from the right side, all fields (including role and region) are editable.
3. Click **Edit User Information** on a user -> Verify the drawer opens from the right; Full Name, Email, Department, and Job Title are editable; Role and Region are locked with lock icons and badges; saving successfully updates the user table.
4. Click **Reset Password** on a user -> Verify the drawer opens from the right with user profile card, password strength meter, and match validation.
5. Hit `Escape` key and click backdrop -> Verify drawers close cleanly.
6. Run `graphify update .` to keep knowledge graph current per user rule.
