# Enhanced Profile with Professional Information

Expand the user profile system to include comprehensive professional and work-related information, displayed both in the profile page and the dashboard.

## Proposed Changes

### Profile Page

#### [MODIFY] [profile.html](file:///c:/Users/samsung/Desktop/ghg%20old/public/profile.html)
- Add new form section: "Professional Information"
- Include fields:
    - **Job Title/Role** (e.g., "Sustainability Manager")
    - **Department** (e.g., "Environmental Compliance")
    - **Company Name**
    - **Phone Number**
    - **Office Location**
- Store in localStorage and sync with backend API

### Dashboard Display

#### [MODIFY] [dashboard.html](file:///c:/Users/samsung/Desktop/ghg%20old/public/dashboard.html)
- Update account dropdown to show job title dynamically
- Display company/department info in the dropdown header

#### [MODIFY] [dashboard.js](file:///c:/Users/samsung/Desktop/ghg%20old/public/dashboard.js)
- Load and populate professional information from user object
- Update all relevant display elements
