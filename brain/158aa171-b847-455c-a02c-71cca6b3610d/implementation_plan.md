# Authentication and User-Specific Database Implementation

This plan restructures the GHG Tracker application to require authentication for all pages, makes the login page the index page, implements user-specific database isolation, and adds a user icon with login dropdown functionality.

## User Review Required

> [!IMPORTANT]
> **Database Architecture Decision**: The plan implements user-specific database isolation where each user gets their own SQLite database file (e.g., `user_1.db`, `user_2.db`). This ensures complete data separation between users. An alternative approach would be to keep a single database with strict user_id filtering. Please confirm this approach is acceptable.

> [!WARNING]
> **Data Loss**: All existing databases and user data will be deleted as requested. This includes:
> - `ghg.db` (main database)
> - `users.json` and `emissions.json` files
> - All existing user accounts and emission records
> 
> Please ensure you have backups if needed before proceeding.

> [!IMPORTANT]
> **Login UI Location**: The login functionality will be accessible via a user icon in the top navigation bar that appears on hover. The icon will show a dropdown with login/logout options. Confirm this matches your requirements.

## Proposed Changes

### Backend - Database Architecture

#### [MODIFY] [server.js](file:///c:/Users/samsung/Desktop/ghg%20old/server.js)

**Changes:**
- Implement user-specific database creation and management
- Create a master `users.db` for authentication only
- Each user gets their own database file: `user_{userId}.db`
- Update all API endpoints to use the authenticated user's database
- Add middleware for authentication checking
- Implement proper session management with user context
- Update `/api/emissions` endpoint to only access current user's database
- Update `/api/stats` endpoint to only show current user's statistics

**Key Functions to Add:**
- `getUserDatabase(userId)` - Returns database connection for specific user
- `authMiddleware(req, res, next)` - Validates user session
- `createUserDatabase(userId)` - Initializes new user's database with schema

---

### Frontend - Authentication UI

#### [MODIFY] [dashboard.html](file:///c:/Users/samsung/Desktop/ghg%20old/public/dashboard.html)

**Changes:**
- Update user profile section (currently hidden) to show user icon
- Add hover dropdown menu with user info and logout button
- Remove hidden class from `.user-profile`
- Add dropdown HTML structure with:
  - User name display
  - Organization name
  - Logout button

#### [MODIFY] [dashboard.css](file:///c:/Users/samsung/Desktop/ghg%20old/public/dashboard.css)

**Changes:**
- Add styles for user icon hover dropdown
- Implement smooth dropdown animation
- Style logout button
- Add hover effects for user profile area

#### [MODIFY] [dashboard.js](file:///c:/Users/samsung/Desktop/ghg%20old/public/dashboard.js)

**Changes:**
- Add logout functionality
- Update user profile display with full user information
- Add dropdown toggle logic
- Store complete user object (including userId) in localStorage
- Update API calls to include user authentication

---

### Frontend - Login Page Integration

#### [MODIFY] [script.js](file:///c:/Users/samsung/Desktop/ghg%20old/public/script.js)

**Changes:**
- Update login handler to store complete user object including `userId`
- Store user session data properly for authentication
- Add better error handling for login failures

#### [MODIFY] [auth-check.js](file:///c:/Users/samsung/Desktop/ghg%20old/public/auth-check.js)

**Changes:**
- Update to check for userId in addition to username
- Ensure all protected pages require authentication
- Improve redirect logic for unauthorized access

---

### Other Protected Pages

#### [MODIFY] All other HTML pages in public folder

**Changes:**
- Add user icon with dropdown to all pages with navigation
- Ensure consistent authentication UI across all pages
- Update to use the same user profile component

Files to update:
- [emission-selection.html](file:///c:/Users/samsung/Desktop/ghg%20old/public/emission-selection.html)
- [emissions-calculator.html](file:///c:/Users/samsung/Desktop/ghg%20old/public/emissions-calculator.html)
- [reports.html](file:///c:/Users/samsung/Desktop/ghg%20old/public/reports.html)
- [stationary-combustion.html](file:///c:/Users/samsung/Desktop/ghg%20old/public/stationary-combustion.html)
- [mobile-combustion.html](file:///c:/Users/samsung/Desktop/ghg%20old/public/mobile-combustion.html)
- [flaring.html](file:///c:/Users/samsung/Desktop/ghg%20old/public/flaring.html)
- [venting.html](file:///c:/Users/samsung/Desktop/ghg%20old/public/venting.html)
- [audit.html](file:///c:/Users/samsung/Desktop/ghg%20old/public/audit.html)

---

### Database Cleanup

#### [NEW] [cleanup-databases.js](file:///c:/Users/samsung/Desktop/ghg%20old/cleanup-databases.js)

**Purpose:**
- Script to delete all existing databases and user files
- Removes:
  - `ghg.db`
  - `users.json`
  - `emissions.json`
  - `emissions_audit.json`
  - Any existing `user_*.db` files
- Creates fresh `users.db` for new authentication system

---

### Shared Components

#### [NEW] [public/user-profile-component.html](file:///c:/Users/samsung/Desktop/ghg%20old/public/user-profile-component.html)

**Purpose:**
- Reusable HTML snippet for user profile dropdown
- Can be included in all pages for consistency

#### [NEW] [public/user-profile.js](file:///c:/Users/samsung/Desktop/ghg%20old/public/user-profile.js)

**Purpose:**
- Shared JavaScript for user profile functionality
- Handles logout, dropdown toggle, user display
- Can be included in all pages

#### [NEW] [public/user-profile.css](file:///c:/Users/samsung/Desktop/ghg%20old/public/user-profile.css)

**Purpose:**
- Shared styles for user profile component
- Ensures consistent look across all pages

## Verification Plan

### Automated Tests

1. **Database Cleanup Verification**
   ```bash
   node cleanup-databases.js
   # Verify all old databases are deleted
   # Verify users.db is created fresh
   ```

2. **Server Restart**
   ```bash
   node server.js
   # Verify server starts without errors
   # Verify users.db is initialized properly
   ```

### Manual Verification

1. **User Registration Flow**
   - Navigate to `http://localhost:3000/`
   - Should see login page (index.html)
   - Register a new user
   - Verify user database file is created (`user_1.db`)
   - Verify redirect to dashboard after registration

2. **User Login Flow**
   - Logout from dashboard
   - Login with registered credentials
   - Verify redirect to dashboard
   - Verify user icon appears in top navigation
   - Hover over user icon and verify dropdown appears
   - Verify user name and organization display correctly

3. **Data Isolation**
   - Register second user
   - Add emission data for user 1
   - Login as user 2
   - Verify user 2 sees no data from user 1
   - Add emission data for user 2
   - Login back as user 1
   - Verify user 1 still sees only their data

4. **Authentication Protection**
   - Logout from dashboard
   - Try to directly access `http://localhost:3000/dashboard.html`
   - Verify redirect to login page
   - Try to access other protected pages
   - Verify all redirect to login

5. **Logout Functionality**
   - Login as any user
   - Click user icon dropdown
   - Click logout button
   - Verify redirect to login page
   - Verify localStorage is cleared
   - Try to go back to dashboard
   - Verify redirect to login page

6. **Cross-Page Consistency**
   - Login and navigate to different pages
   - Verify user icon appears on all pages
   - Verify dropdown works consistently
   - Verify logout works from any page
