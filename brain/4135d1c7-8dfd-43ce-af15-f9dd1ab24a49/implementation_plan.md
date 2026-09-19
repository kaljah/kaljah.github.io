# Project Reorganization & Root Entry Plan

The goal is to move `index.html` and other pages to the root directory to make the entry point immediately obvious and simplify the structure for free hosting (eliminating the `public/` folder).

## Proposed Changes

### 1. New Directory Structure (Zero-Public)
- **Root**: All `.html` files (starting with `index.html`), `server.js`, `package.json`, `README.md`.
- **`assets/css/`**: All `.css` files.
- **`assets/js/`**: All frontend `.js` files.
- **`data/`**: All `.db` files.

### 2. File Relocations
- Move `public/*.html` to the project root.
- Move `public/*.css` to `assets/css/`.
- Move `public/*.js` to `assets/js/`.
- Move `*.db` to `data/`.

### 3. [MODIFY] [server.js](file:///c:/Users/samsung/Desktop/ghg%20old/server.js)
- Update static middleware: `app.use('/assets', express.static(path.join(__dirname, 'assets')))`
- Ensure the root route `/` explicitly serves `./index.html`.
- Update DB paths to point to `./data/`.

### 4. [MODIFY] [seed_script.js](file:///c:/Users/samsung/Desktop/ghg%20old/seed_script.js)
- Update DB path to `./data/users_v2.db`.

### 5. [MODIFY] All HTML Files
- Update all `<link>` tags to point to `assets/css/...`
- Update all `<script>` tags to point to `assets/js/...`
- Update internal links between pages (if necessary, though most should stay as simple filenames).

## Verification Plan

### Automated Tests
- Run `npm start` and verify:
  - Root URL serves `index.html`.
  - Assets (CSS/JS) load correctly from the new `/assets` route.
  - Databases are initialized in `/data`.

### Manual Verification
- Check login, dashboard, and audit history.
- Ensure all images and icons (if any) are correctly re-mapped.
