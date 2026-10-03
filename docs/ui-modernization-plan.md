# UI Modernization — Implementation Plan

| | |
|---|---|
| **Scope** | `new/client` (React 19.2, Vite 7.3, React Router 7.13) |
| **Status** | In progress on `feat/ui-modernization`. Decisions made 2026-10-02: S-1 system font, S-2 yes, S-3 darken to `#c2410c`, S-4 yes, S-5 remove intro, S-6 yes. See "Implementation status" at the end. |
| **Hard constraint** | Keep the light theme and the color palette (`AUDIT_MEMORY.md` §0 "UI theme (preserved)"). This plan only assigns *roles* to existing colors and removes accidental near-duplicates. |
| **Baseline** | vitest: 8 files, 38 tests passing. ESLint: 0 errors, 38 warnings. Client CSS: 39 files, 18,556 lines. Built JS 775 KB gzip, CSS 51 KB gzip. |
| **Evidence** | Code survey, plus every route checked in the running app (admin session) at 1440 px, and the Dashboard also at 390 px, on 2026-10-02 |

**Contents**
1. Goals, constraints, non-goals
2. Baseline: defects, metrics, contrast
3. Decisions
4. Target architecture
5. Phase 0: safety net and theme bug fixes
6. Phase 1: foundations
7. Phase 2: component kit
8. Phase 3: app shell
9. Phase 4: page migrations
10. Phase 5: accessibility, motion, cleanup
11. Testing and QA
12. Delivery: branching, sequencing, estimates
13. Risk register
14. Appendices A–G (tokens, mapping tables, inventory, e2e selectors, API sketches, PR checklist, commands)

**How to use this plan**
- Work is split into work packages (WPs) such as `P1-3`. One WP is one PR unless noted.
- Every PR keeps `npm run lint`, `npm run test` and `npm run build` green. It also keeps the Playwright suite green locally; if markup changes break a spec, update the spec in the same PR.
- Styling PRs never change calculation logic, API calls or data flow. Big-file splits (ManageData, Scope1Form) ship as separate, behavior-neutral PRs.
- Defect fixes (Phase 0) get an entry in `AUDIT_MEMORY.md` (new "UI" section), following the repo convention. Run `graphify update .` after code changes.

---

## 1. Goals, constraints, non-goals

**Goals**
1. One visual system on every page: tokens and shared components instead of per-page CSS.
2. A modern app shell: a sidebar that doesn't shift the page, real breadcrumbs, one account menu, search, shared filters.
3. Readable, data-dense tables and forms, with clear hierarchy: fewer colors, fewer font weights, consistent numbers.
4. WCAG 2.1 AA for keyboard use, focus, labels, motion, and text contrast as far as the palette allows (see S-3).
5. Zero functional regressions in calculations, permissions and exports.

**Constraints**
- Palette and light theme stay. New code uses only colors that already exist (Appendix A).
- URLs stay the same (bookmarks, e2e, `navigate(..., { state })` callers).
- Widely used APIs stay source-compatible: `useToast()` (261 call sites), `Modal`/`ConfirmModal`/`Drawer` props, `CustomDropdown` props.
- No backend changes required.

**Non-goals**
- Dark mode, rebrand, new colors, logo or illustration changes.
- TypeScript migration.
- PDF/Excel export styling (`utils/ModernReportGenerator.js`).
- Replacing Recharts or Leaflet.

---

## 2. Baseline (2026-10-02)

### 2.1 Defects (fixed in Phase 0)

| ID | Defect | Evidence |
|---|---|---|
| UI-01 | The accent color turns teal across the whole app | `pages/CarbonIntensity.css:2` declares `:root { --accent-color: #0d9488; --bg-card: #fff; --border-color: …; --bg-hover: … }`. Both `CarbonIntensity.jsx` and `MethaneIntensity.jsx` import it. Lazily loaded CSS stays in the document, so after either page is visited, all 126 `var(--accent-color)` uses render teal until a full reload. Verified live: on the Dashboard the GWP toggle and top-bar icon turned teal after visiting `/carbon-intensity`. |
| UI-02 | Login stylesheet overrides global tokens | `pages/Login.css:1` declares a `:root` block, and it ships in the main bundle. As a result `--text-muted` renders as `#64748b` (although `index.css` says `#94a3b8`) and `--border-light` as `#e2e8f0`. The Sign In button uses a second orange, `#f97316`. |
| UI-03 | Tailwind never compiles | `tailwindcss@4.1.18` is installed, but `index.css` uses the v3 `@tailwind` directives and no `@tailwindcss/vite`/PostCSS plugin is configured. The built `dist/assets/index-*.css` contains the literal text `@tailwind base;`. `tailwind.config.js` (v3 format) is ignored by v4. |
| UI-04 | The Dashboard's loading skeleton is invisible | `components/SkeletonLoader.jsx` uses only Tailwind classes, plus `--surface-color`, which is defined nowhere. |
| UI-05 | The brand font never loads, and the font changes from page to page | `index.css` declares "Outfit", but there is no `@font-face` or `<link>`, and neither Outfit nor Inter is installed. The app therefore renders in Segoe UI on Windows. Login, Settings and Carbon/Methane Intensity drop to Arial, because their stacks (`"Inter", sans-serif` and similar) have no `system-ui` entry. |
| UI-06 | Unused Google Fonts request | `components/LoadingSpinner.css:1` uses `@import` to load Orbitron, a render-blocking CSS request on every page load. Nothing uses the font. |
| UI-07 | Undefined button classes | `.btn-ghost` (31 uses) and `.btn-secondary-unified` (3 uses) have no CSS, so these render as browser-default buttons. |
| UI-08 | Generic class names collide across lazily loaded stylesheets | `.card` (228 uses) has top-level rules in both `Dashboard.css:865` and `CarbonIntensity.css:325`. Whichever loads last wins, by the same mechanism as UI-01. |
| UI-09 | The accessibility audit doc overstates compliance | `docs/validation/06-accessibility-audit.md` claims: Tailwind focus rings (the code has 0 `focus:ring` classes); modal focus trap and focus return (absent from `Modal`/`ConfirmModal`; `Drawer` only locks scrolling); toast `aria-live` (absent from `Toast.jsx`); AA contrast (white on `#ff6600` is 2.94:1). It also claims full keyboard navigability, but the Manage Data tabs are `div`s with no `tabIndex`. |
| UI-10 | Dead assets, files and dependencies | `src/assets/loading_animation.mp4` (2.6 MB) is unreferenced. `src/App.css` is imported by nothing. `pages/Diagnostics.jsx` and `Diagnostics.css` (251 lines) are lazily declared but never rendered, because the `/diagnostics` route redirects. `chart.js`, `formik` and `yup` have 0 imports. |
| UI-11 | Native alert | `components/UploadProgress.jsx:172` calls `alert(...)`. |
| UI-12 | Public asset paths ignore the base path | `/carbon_tech.svg` (Sidebar) and `/login_animation.mp4` (Login) don't use `import.meta.env.BASE_URL`, but CI builds with `VITE_BASE_PATH`. |

### 2.2 Fragmentation metrics and targets

| Metric | Baseline | Target after P2 | Final target |
|---|---:|---:|---:|
| Inline `style={{…}}` objects | 1,436 (ManageData alone: 348) | new code 0, total going down | ≤ 150 (dynamic CSS variables only) |
| Hex color literals (CSS + JS) | 2,595 (134 distinct) | going down | only in `styles/tokens.css` and the chart theme |
| Distinct `font-size` values | 51 | — | 8 tokens |
| Distinct `border-radius` values | 28 | — | 4 tokens |
| Distinct `box-shadow` values | 172 | — | 4 tokens |
| `!important` | 146 | going down | ≤ 10 (print and reduced-motion only) |
| Distinct z-index values | 20 (max 999999) | — | 10-step scale |
| Media-query breakpoints | 10 | — | 3 (+ xl) |
| Button classes | ~100 (`.btn-primary` defined in 4 stylesheets) | 1 `Button` component | 1 `Button` component |
| Dropdowns | 111 native `<select>` + 66 `CustomDropdown` | `Select` available | 1 `Select` |
| Ad-hoc number formatting | 139 `.toFixed` + 59 `.toLocaleString` (`formatters.js` used in 8 files) | — | formatters only |
| Inline `<svg>` icons | 149 | — | 0 (lucide-react) |
| Clickable non-semantic elements | 21 `div`/`span`/`tr` with `onClick` (1 has a role) | — | 0 |
| `prefers-reduced-motion` rules | 0 | global | global |
| `:focus-visible` styles | 2 (plus 38 `outline: none`) | global ring | global ring |
| Font weights | 400 ×2, 500 ×61, 600 ×205, 700 ×157, 800 ×28 | — | 400/500/600/700 assigned by role |
| Client CSS | 39 files, 18,556 lines | — | ≤ 6,000 lines |
| Bundle (gzip, dist of 2026-10-02) | JS 775 KB, CSS 51 KB | ≤ +40 KB JS | JS ≤ baseline +5%, CSS ≤ 51 KB |

### 2.3 UX problems the redesign addresses

**App shell**
- The sidebar expands on hover *inside* the layout flow (`Sidebar.css`: `.sidebar` → `.sidebar:hover { width: 260px }`), so every mouse pass reflows the page. Measured: content jumps about 215 px, and the top-bar Region filter is squeezed down to "A".
- The navigation is 13 ungrouped items. There are two account menus, and "Administrator" can appear three times on one screen.
- Breadcrumbs come in four styles: a static "Corporate ESG" label; injected into the top bar (Manage Data); a second header bar inside the page (Calculations, Reports); inline in the page (Reference Data, whose root "Resource Center" doesn't exist).
- Page names drift: "Emissions Map" is titled "Methane Recon Cockpit" and lives at `/methane-explorer`. "Uncertainty" is titled "Data Reliability Analysis". "Reports" is titled "Emission Database".
- Every browser tab is titled "Carbon Tech".
- Page filters are injected into the global top bar, but each page keeps its own copy of the filter state. Below 900 px the filters disappear entirely.
- The offline and session-timeout banners are drawn at the same position and overlap.

**Pages**
- The Scope 1 history table has 22 columns (2,005 px wide in a 1,158 px container). Total tCO₂e and Actions are off-screen, and rows are about 73 px tall because cells wrap.
- Manage Data opens on a create form, and its tabs aren't keyboard-operable. Reports shows five buttons in five colors and puts its data below the fold. Audit Trail uses about 155 px per event.
- Page titles range from 28 to about 48 px, at weights 700 to 900.
- Color meanings contradict each other: Scope 1 is red on the Dashboard, orange and green on Calculations, and green in QA. On the Uncertainty page, the cards and the legend disagree. Red is used for non-danger meanings, and KPI numbers are colored for decoration.

### 2.4 Contrast of the palette pairs (WCAG 2.1)

"Tint" means the existing 10% `--*-bg` background tokens over white.

| Pair | Ratio | AA normal text (4.5) | Large text / UI component (3.0) |
|---|---:|:---:|:---:|
| White on `#ff6600` (primary button, active nav) | 2.94 | ✗ | ✗ |
| White on `#e65c00` | 3.56 | ✗ | ✓ |
| White on `#c2410c` | 5.18 | ✓ | ✓ |
| `#ff6600` text on white | 2.94 | ✗ | ✗ |
| `#c2410c` text on white / on `#fff7ed` | 5.18 / 4.88 | ✓ | ✓ |
| `#0f172a` on white | 17.85 | ✓ | ✓ |
| `#64748b` on white | 4.76 | ✓ | ✓ |
| `#94a3b8` on white | 2.56 | ✗ | ✗ |
| `#10b981` text on white (Net Emissions KPI) | 2.54 | ✗ | ✗ |
| `#059669` on white / on success tint | 3.77 / 3.43 | ✗ | ✓ |
| `#2E7D32` (documented, unused) on success tint | 4.67 | ✓ | ✓ |
| `#d97706` on warning tint | 2.95 | ✗ | ✗ |
| `#b45309` on warning tint | 4.65 | ✓ | ✓ |
| `#dc2626` on danger tint | 4.23 | ✗ | ✓ |
| `#b91c1c` on danger tint | 5.66 | ✓ | ✓ |
| `#2563eb` / `#1d4ed8` on info tint | 4.62 / 5.99 | ✓ | ✓ |
| `#f59e0b` text on white (CH₄ KPI) | 2.15 | ✗ | ✗ |
| Current focus glow (18% `#ff6600`) | 1.22 | — | ✗ |
| 2 px `#e65c00` focus ring | 3.56 | — | ✓ |

**Takeaway:** every *text* role can meet AA using shades that already exist in the palette or the codebase. The one exception is white text on a `#ff6600` fill, which needs decision S-3.

---

## 3. Decisions

### 3.1 Accepted defaults (change only with a reason)

| ID | Decision | Why |
|---|---|---|
| D-1 | Wire Tailwind v4 through `@tailwindcss/vite`. Import only the `theme` and `utilities` layers (no preflight). Limit class scanning to the new folders (`source(none)` plus explicit `@source` entries) until each page migrates. | It's already a dependency, and tokens become both CSS variables and utilities. Skipping preflight and scanning means pages that haven't migrated see no visual change. |
| D-2 | Components are built from utilities plus `cva` variants and a `cn()` helper (`class-variance-authority`, `clsx`, `tailwind-merge` are already installed). No new per-page CSS files. | Finishes the shadcn-style setup that was started and never wired up. |
| D-3 | Radix primitives for Dialog, Sheet (side dialog), DropdownMenu, Popover, Tooltip and Tabs, wrapped behind the existing prop APIs. | Focus trap and return, scroll lock and keyboard support come for free. |
| D-4 | Evolve `CustomDropdown` into `ui/Select` rather than adopting Radix Select. | It already implements listbox, `aria-activedescendant` and a portal. 66 call sites depend on it, unit tests use `.dropdown-selected *`, and e2e uses `.dropdown-portal .dropdown-option`. |
| D-5 | `@tanstack/react-table@^8.21.3` (headless) for `DataTable`. | v8 is stable and well documented. v9 (currently 9.2.4) is a new major version; review its migration guide after Phase 4. |
| D-6 | Keep Recharts, with one central theme in `ui/charts/theme.js`. | Only 3 wrapper files import Recharts. |
| D-7 | Keep the `ToastProvider`/`useToast` API; restyle it and add a live region. | 261 call sites. |
| D-8 | `lucide-react` for all icons. | Already used in 25 files; replaces 149 inline SVGs. |
| D-9 | One route config is the single source of truth for routes, guards, navigation, breadcrumbs, the command palette and document titles. | Fixes the naming drift and duplicated role arrays. |
| D-10 | The URL is the source of truth for tabs and analytics filters. | Shareable links, and the Back button works. |
| D-11 | Number display rules in Appendix B.4, built on the existing `utils/formatters.js` defaults. | One look for numbers; reported precision doesn't change. |
| D-12 | `cmdk@^1.1.1` for the command palette, lazy-loaded. | Supports React 19; costs nothing until first use. |
| D-13 | Make `#64748b` the official `--text-muted` value (it's what users see today because of UI-02, and it passes AA at 4.76:1). Keep `#94a3b8` only for disabled and decorative uses (`--text-disabled`). | Fixing the leak shouldn't change what users see or introduce a contrast failure (`#94a3b8` is 2.56:1). |
| D-14 | Consolidate near-duplicate shades onto the nearest palette token (Appendix B.6), e.g. `#ea580c` → `#e65c00`, `#374151` → `#334155`. | Removes accidental colors without changing the palette. |

### 3.2 Needs your sign-off (recommendation first)

| ID | Question | Recommendation | Alternative |
|---|---|---|---|
| S-1 | Which font? | Self-host Outfit (`@fontsource-variable/outfit@^5.3.0`). It's the declared brand font, renders identically on every OS and makes no third-party request. Verify it has tabular figures (P0-6). | System stack only (`system-ui, "Segoe UI", Roboto, sans-serif`): no download, and it matches what Windows users see today. |
| S-2 | Scope colors | Scope 1 = brand orange `#ff6600`, Scope 2 = blue `#3b82f6`, Scope 3 = violet `#8b5cf6` (violet is already the Scope 3 color on Dashboard and Calculations). | Keep today's page-specific colors. |
| S-3 | Primary button contrast (white on `#ff6600` is 2.94:1) | Keep the `#ff6600` fill (brand) and document it as a known AA exception. Expose it as a single token, `--color-primary`, so switching to `#c2410c` (5.18:1) is a one-line change. Fix all orange *text* to `#c2410c` now. | Switch the primary fill to `#c2410c` now (passes AA, but is a visibly darker orange). |
| S-4 | Where does the account menu live? | Top-right avatar menu only. The sidebar footer keeps Settings and the collapse toggle. | Sidebar footer only. |
| S-5 | Login intro video | Play once per device, skip it under `prefers-reduced-motion`, and keep it skippable. Also check the corner sparkle in the video, which looks like a video-generator watermark. | Remove the intro. |
| S-6 | Branching | Create `feat/ui-modernization` from `main` after `fix/audit-remediation-rc` is merged, with short-lived PR branches off it. | Trunk-based small PRs straight to `main`. |

---

## 4. Target architecture

```
new/client/src/
  styles/
    index.css        entry: layer order, Tailwind imports, tokens, base, legacy
    tokens.css       @theme block: the only place hex values live (Appendix A)
    base.css         @layer base: body, focus ring, reduced motion, scrollbars, selection, print
    legacy.css       former index.css globals (.glass-panel, .status-pill, .component-select, …) until deleted
  ui/                design-system components, no page logic
    cn.js  Button.jsx  IconButton.jsx  Badge.jsx  StatusPill.jsx  Card.jsx  StatCard.jsx
    Page.jsx  PageHeader.jsx  Field.jsx  Input.jsx  NumberInput.jsx  Textarea.jsx  Switch.jsx
    Select.jsx  MultiSelect.jsx  SegmentedControl.jsx  RadioCard.jsx  Tabs.jsx
    Dialog.jsx  ConfirmDialog.jsx  Sheet.jsx  Menu.jsx  Popover.jsx  Tooltip.jsx
    Banner.jsx  EmptyState.jsx  Skeleton.jsx  Spinner.jsx  Stepper.jsx  Num.jsx  Unit.jsx  FilterBar.jsx
    table/DataTable.jsx  table/columnHelpers.js
    charts/theme.js
  app/
    routes.config.js     routes, nav groups, titles, icons, access rules
    RequireRole.jsx
    shell/  AppShell.jsx  Sidebar.jsx  TopBar.jsx  Breadcrumbs.jsx  AccountMenu.jsx
            CommandPalette.jsx  BannerStack.jsx
  filters/
    AnalyticsFiltersProvider.jsx  useAnalyticsFilters.js  useOrgHierarchy.js
  hooks/
    useUrlState.js  useDocumentTitle.js  useTabParam.js
  dev/
    UiGallery.jsx        /__ui, development builds only
  pages/                 compose ui/*; page CSS shrinks, then is deleted
```

**CSS cascade.** The layer order is declared once at the top of `styles/index.css`:

```css
@layer theme, base, legacy, components, utilities;
```

- Page stylesheets imported from JSX stay **unlayered** during the migration. Unlayered CSS beats every layer, so pages that haven't migrated keep their exact look.
- The consequence: new components must not sit under page rules with element selectors (`.manage-data-page input`) or `!important`. The per-page checklist (Appendix F) removes those before components go in.
- Never mix legacy classes and Tailwind utilities on the same element. Migrate a component wholesale.

**Filters.**
- `AnalyticsFiltersProvider` (inside the shell) is synced to the URL params `?year=&segment=&activity=&division=&region=&gwp=`.
- The last-used values are also stored in `sessionStorage`, so moving between analytics pages keeps the context.
- `useOrgHierarchy()` fetches `/facilities` once. Nine pages fetch it separately today, and three of them (Dashboard, Carbon Intensity, Methane Intensity) duplicate the option-building logic.

**Routes.** Paths stay unchanged. Groups and icons:

| Group | Pages (lucide icon) |
|---|---|
| Overview | Dashboard (`LayoutDashboard`), Carbon Intensity (`Gauge`), Methane Intensity (`Wind`), SBTi & Net-Zero (`Target`), Emissions Map (`Map`) |
| Data | Calculations (`Calculator`), Manage Data (`Database`), Reference Data (`Library`) |
| Assurance & Reporting | Reports (`FileText`), Uncertainty (`Sigma`), QA/QC & Diagnostics (`ShieldCheck`), Audit Trail (`History`) |
| Administration | User Management (`Users`), IT roles only |
| Pinned to the bottom | Settings (`Settings`) |

**Access rules** must reproduce today's guards exactly. These are locked by a unit test in P3-1.

| Rule | Roles | Redirect if denied |
|---|---|---|
| `nonIT` (today `NonITRoute`) | everyone except `it`, `it_admin`, `it_manager` | IT roles go to `/user-management` |
| `it` (today `ITRoute`) | `it`, `it_admin`, `it_manager` | `/` |
| `superuser` (today `SuperuserRoute`, used by `/qa-dashboard`) | `admin`, `superuser` | `/` |
| `audit` (today `AuditRoute`, used by `/audit-trail`) | `admin`, `superuser`, `it_admin`, `it_manager` | `/` |
| `AdminRoute` | defined but unused | delete |

---

## 5. Phase 0: safety net and theme bug fixes

**Goal:** protect existing behavior and fix §2.1, with no redesign. The only intended visible changes are:
- Carbon and Methane Intensity accents go from teal to orange.
- The login button uses the brand orange.
- Ghost buttons get a style.
- The font changes (if S-1 is Outfit).

**P0-1 Baseline screenshots and a portable Playwright setup (S)**
- Add `e2e/visual-baseline.spec.js`, tagged `@baseline`. It captures `/login` and every app route at 1440×900, 1024×768 and 390×844 (full page) into `e2e/artifacts/baseline/` (gitignored). Mask time-dependent text such as the "Updated hh:mm" badge.
  - `/user-management` needs a second storage state from an IT-role account, because admins are redirected away from it.
- In `playwright.config.js` and `generate_storage_state.js`, set `executablePath` only when the chromium-1208 path exists (`fs.existsSync`), so the suite runs on other machines too.
- **Done when:** every route has screenshots at all 3 widths, produced locally and attached to the Phase 0 PRs as the "before" set.

**P0-2 Stable test selectors (M)**
- Add `data-testid` attributes to everything the e2e suite finds by layout class (Appendix D). Keep the old classes in place.
- Inside `CustomDropdown`, add `data-testid="select-trigger"` and `data-testid="select-option"`, and keep the `.dropdown-*` classes.
- Rewrite the specs to use `getByTestId`, `getByRole` and `getByLabel`.
- **Done when:** the full e2e suite passes, and no spec uses the selectors listed in Appendix D.

**P0-3 Stop the teal leak (UI-01, UI-08) (S)**
- In `pages/CarbonIntensity.css`, delete the `:root` block and move the page-only variables onto the page root. The page keeps its look, minus the teal:
  ```css
  .intensity-content {
    --accent-secondary: #2563eb;
    --accent-tertiary: #e65c00;      /* was #ea580c (D-14) */
    --bg-app: #f8fafc;
    --bg-card: #ffffff;
    --border-color: #e2e8f0;
    --bg-hover: #f1f5f9;
    --card-shadow: 0 4px 6px -1px rgba(15, 23, 42, 0.05), 0 2px 4px -1px rgba(15, 23, 42, 0.03);
    --card-shadow-hover: 0 10px 15px -3px rgba(15, 23, 42, 0.08), 0 4px 6px -2px rgba(15, 23, 42, 0.04);
    /* --accent-color is not redefined, so the brand orange applies */
  }
  ```
- Scope the top-level `.card { … }` rule (`CarbonIntensity.css:325`) to `.intensity-content .card`.
- Add an e2e assertion: open `/carbon-intensity`, navigate client-side to `/`, then check that `getComputedStyle(document.documentElement).getPropertyValue('--accent-color').trim() === '#ff6600'`.
- **Done when:** that assertion passes, and the Carbon/Methane Intensity accents render orange.

**P0-4 Contain the Login tokens (UI-02) (S)**
- Move `--primary`, `--primary-hover`, `--accent` and `--bg-page` into `.login-body { … }`, with `--primary: #ff6600` and `--primary-hover: #e65c00`.
- Move the values users actually see today into the `:root` of `index.css`: `--text-muted: #64748b` (D-13), a new `--text-disabled: #94a3b8`, and `--border-light: #e2e8f0`.
- **Done when:** computed `--text-muted` is `#64748b` on every route (unchanged), the login button is `#ff6600`, and screenshot diffs show only the login button.

**P0-5 Wire Tailwind v4 without side effects (UI-03) (S)**
- Run `npm i -D tailwindcss@^4.3.3 @tailwindcss/vite@^4.3.3`, keeping both versions identical. Both are compatible with Vite 7 and Node 20.
- In `vite.config.js`, add `import tailwindcss from "@tailwindcss/vite"` and set `plugins: [react(), tailwindcss(), visualizer(…)]`.
- At the **very top** of `src/index.css` (`@import` must come before the `:root` block), replace the three `@tailwind` lines with:
  ```css
  @layer theme, base, legacy, components, utilities;
  @import "tailwindcss/theme.css" layer(theme);
  @import "tailwindcss/utilities.css" layer(utilities) source(none);
  @source "./ui";
  @source "./app";
  @source "./filters";
  @source "./dev";
  ```
  If the installed version rejects `source(none)` on the split import, drop it and use `@source not "./pages"; @source not "./components";` instead (supported since 4.1).
- Delete `tailwind.config.js`. Its values move to the tokens in P1-1.
- Known legacy class names that would match utilities once scanning reaches them (P5): `text-right` ×17, `font-bold` ×4, `rounded` ×3, `w-full` ×2, `flex` ×1, `border` ×1, `visible` ×1. These are all intended meanings, and they are inert while scanning is limited.
- **Done when:** `grep -c "@tailwind" dist/assets/*.css` returns 0, the built CSS contains no utilities generated from `pages/` or `components/`, and screenshot diffs show no change.

**P0-6 Fonts (UI-05, UI-06) (S, depends on S-1)**
- If S-1 is Outfit: run `npm i @fontsource-variable/outfit@^5.3.0` and add `import "@fontsource-variable/outfit";` to `main.jsx`. The font gets bundled, so it respects `VITE_BASE_PATH` and needs no third-party request.
- Set `font-family: "Outfit Variable", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif` on `:root`.
- Delete the per-file overrides that break the stack: `Login.css:18`; `CarbonIntensity.css:24, 225, 311`; `Settings.css:13`; `QADashboard.css:13`; `MethaneExplorer.css:12, 1558`; `Scope1ImportWizard.css:128`; `Sidebar.css:375`; `LoadingSpinner.css:95, 213`. Monospace stacks stay.
- Delete the Inter-specific `font-feature-settings: "cv02", "cv03", "cv04", "cv11"` and the Orbitron `@import`.
- Check for tabular figures: render `1111111111` and `0000000000` with `font-variant-numeric: tabular-nums`. If the two widths differ, Outfit has no `tnum`; in that case add `--font-numeric: system-ui, "Segoe UI", Roboto, sans-serif` for `.num` and numeric table cells.
- **Done when:** `document.fonts` reports "Outfit Variable" as loaded on every route including Login, no request goes to `fonts.googleapis.com`, and wrapping changes in the screenshots have been reviewed. Outfit's metrics differ from Segoe UI and Arial.

**P0-7 Skeleton fix (UI-04) (S)**
- Rewrite `components/SkeletonLoader.jsx` with a small `SkeletonLoader.css`: blocks use `--border-light`, with a pulse animation. Keep the `SkeletonRow`, `SkeletonTable` and `SkeletonCard` exports. It becomes `ui/Skeleton` in P2.
- **Done when:** the Dashboard loading state is visible with the network throttled.

**P0-8 Ghost and secondary buttons (UI-07) (S)**
- Add temporary definitions for `.btn-ghost` and `.btn-secondary-unified` to `index.css`, using existing variables: transparent background, `--text-secondary` text, `--bg-hover` on hover, 10 px radius. `Button variant="ghost"` replaces them in P4.

**P0-9 Cleanup (UI-10, UI-11, UI-12) (S)**
- Delete `src/assets/loading_animation.mp4`, `src/App.css`, `pages/Diagnostics.jsx`, `pages/Diagnostics.css`, and the unused `Diagnostics` lazy import in `App.jsx`. Keep the `/diagnostics` → `/qa-dashboard` redirect.
- Run `npm rm chart.js formik yup`.
- In `UploadProgress.jsx:172`, replace `alert()` with `toast.error()`.
- Prefix the public assets with `import.meta.env.BASE_URL` (Sidebar logo, Login video).
- Optional, after confirmation: move the one-off Python scripts out of `src/` (`src/patch_app.py`, `src/fix_wizards.py`, `components/patch_s3.py`, `components/patch_s3_form.py`, `components/layout/patch_sidebar.py`).

**P0-10 Documentation (UI-09) (S)**
- Correct `docs/validation/06-accessibility-audit.md`. Its claims about focus rings, modal focus management, the toast live region, keyboard-operable tabs and contrast don't match the code; replace them with the verified state and the §2.4 table, and link to this plan as the remediation.
- Add a "UI" section with UI-01 to UI-12 to `AUDIT_MEMORY.md`.
- In §0 "UI theme (preserved)", clarify the color roles: orange `#ff6600` is the interactive accent; green `#10b981` means positive or environmental; the documented dark greens `#2E7D32` and `#1B5E20` serve as accessible green text.

**Phase 0 exit criteria:** all P0 WPs merged; screenshot diffs show only the intended changes; lint, test and build green; e2e green, including the token-leak assertion.

---

## 6. Phase 1: foundations

**Goal:** tokens, base styles and guardrails exist, and nothing on existing pages changes visually except the focus ring.

**P1-1 Tokens: `src/styles/tokens.css` (M)**
- Full contents in Appendix A.
  - Reset Tailwind's defaults (`--color-*: initial`, and likewise for the text, radius, shadow, breakpoint, font and ease namespaces), so only palette colors exist as utilities. `bg-orange-500` then simply doesn't compile.
  - Palette values (existing values only) plus role aliases: primary, link, focus, selected, the status `fg` and `bg` pairs, scope, uncertainty, and the chart series.
  - An 8-step type scale, 4 radii, 4 shadows, a z-index scale, motion durations and easing, and 3 breakpoints plus xl.
- Bridge the old variable names to the tokens so legacy CSS keeps working, e.g. `--accent-color: var(--color-brand-500)` (Appendix A.2).
- **Done when:** the gallery shows swatches and the type scale; a Playwright check confirms the 10 bridged legacy variables compute to the same values as before.

**P1-2 Base layer: `src/styles/base.css` (S)**
- Move these from `index.css`: html/body sizing, the body background including its radial washes (part of the theme), scrollbars, the print stylesheet, and `.num-tabular`.
- New: `:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; }` (3.56:1). This replaces the global `input:focus, select:focus, textarea:focus, button:focus-visible { outline: none; box-shadow: … }` glow (1.22:1). Inputs keep a border-color change, and `outline-offset` is 0 for them.
- New: a global reduced-motion rule:
  ```css
  @media (prefers-reduced-motion: reduce) {
    *, ::before, ::after {
      animation-duration: 0.01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.01ms !important;
      scroll-behavior: auto !important;
    }
  }
  ```
- New: `::selection { background: var(--color-brand-100); }`.
- **Done when:** screenshot diffs show no change except focus states; a keyboard tab-through shows the ring on every control.

**P1-3 Restructure the global CSS (S)**
- Move `src/index.css` to `src/styles/index.css` and update the import in `main.jsx`. Update the `@source` paths to `../ui` and so on.
- `styles/index.css` imports `tokens.css`, `base.css` (layer `base`) and `legacy.css` (`@import "./legacy.css" layer(legacy)`).
- `legacy.css` holds `.glass-panel`, `.glass-panel-elevated`, `.glass-card`, `.glass-panel-dark`, `.card-icon-badge`, `.status-pill*`, `.component-select*` and the `select option` rules, `.notification-tray-panel`, `.table-responsive`, and the temporary `.btn-ghost`/`.btn-secondary-unified`.
- Move the classes that pages borrow from `pages/Dashboard.css` (`.data-table` and `.table-container` used by ManageData; `.card-title` and `.table-container` used by Reports) into `legacy.css`. Remove the unused `Dashboard.css` import from `QADashboard.jsx`.
- **Done when:** screenshot diffs show no change on any route.

**P1-4 Guardrails (M)**
- **stylelint:** add `stylelint@^17.16.0` and `stylelint-config-standard@^40.0.0` (needs Node ≥ 20.19, which the CI's `node-version: 20` satisfies).
  - Add `"lint:css": "stylelint \"src/styles/**/*.css\" \"src/ui/**/*.css\" \"src/app/**/*.css\""`.
  - Rules: `color-no-hex: true` (overridden off for `tokens.css`); `declaration-no-important: true` (except `base.css`); `declaration-property-value-allowed-list` restricting `z-index` to `var(--z-*)`, 0, 1, -1 and `auto`; `font-family-no-missing-generic-family-keyword`.
- **ESLint:** add `eslint-plugin-jsx-a11y@^6.10.2` with `jsxA11y.flatConfigs.recommended`, as `warn` across the repo and `error` for `src/ui/**`, `src/app/**` and `src/filters/**`.
  - For those same folders, add `no-restricted-syntax` with the selector `JSXAttribute[name.name='style']`. Dynamic CSS variables are allowed with a justified `eslint-disable-next-line`.
  - Record the new warning count as the baseline.
- **Metrics ratchet:** add `scripts/ui-metrics.mjs` and `ui-metrics.baseline.json`.
  - The script counts the §2.2 metrics, reports collisions (top-level class selectors defined in more than one stylesheet), and counts raw Tailwind palette class usage.
  - `npm run ui:metrics` prints the numbers; `npm run ui:metrics -- --check` exits non-zero when any metric goes above the baseline.
- **CI** (`.github/workflows/deploy-pages.yml`, client job): add `npm run lint:css` and `npm run ui:metrics -- --check` after `npm run test`.

**P1-5 `ui/cn.js` (S)**
```js
import { clsx } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

const twMerge = extendTailwindMerge({
  extend: { theme: { text: ["xs", "sm", "base", "md", "lg", "xl", "2xl", "3xl"] } },
});

export const cn = (...inputs) => twMerge(clsx(inputs));
```
- Unit test: `cn("text-md text-brand-700")` keeps both classes, and `cn("text-sm", "text-md")` keeps only `text-md`.

**P1-6 UI gallery (S)**
- Add `src/dev/UiGallery.jsx`, routed at `/__ui` only when `import.meta.env.DEV` is true. Use a conditional lazy import so it never ships in production.
- It shows token swatches labeled with their contrast ratios, the type scale, and (as P2 progresses) every component in every state.
- Add `e2e/ui-gallery.visual.spec.js` using `toHaveScreenshot()`. It needs no backend, so it's deterministic. Commit the Windows snapshots for local regression checks.

**Phase 1 exit criteria:** tokens, base and the legacy split are merged; no visual diff on any route except focus rings; stylelint, jsx-a11y and the metrics ratchet are running in CI.

---

## 7. Phase 2: component kit

**Goal:** every primitive the pages need exists, is shown in the gallery, is tested, and uses tokens only.

| # | Component | Replaces | Notes |
|---|---|---|---|
| 1 | `Button`, `IconButton` | ~100 button classes, `.btn-ghost` | Variants: primary, secondary, ghost, danger, link. Sizes: sm, md, lg. `loading`, icon slots, and `asChild` via the installed `@radix-ui/react-slot`. `IconButton` requires `aria-label`. |
| 2 | `Badge`, `StatusPill` | `.status-pill`, scope and category tags | Tones come from the role tokens, with the `-fg` shades for text (§2.4). `StatusPill` maps the canonical statuses (Pending, Verified, Draft, Rejected). |
| 3 | `Card`, `Page`, `PageHeader` | 6 `.card` definitions, 7+ title styles | `PageHeader` follows the Settings pattern: eyebrow, title, description, actions, and a tabs slot. `Page` sets max width (1600 px) and padding (24 px, or 16 px below `sm`). |
| 4 | `StatCard` | 7+ KPI card styles | Label, value (via `Num`), unit, `delta { value, goodWhen }`, footnote, icon, loading. Values are neutral ink; only deltas are colored. |
| 5 | `Field`, `Input`, `NumberInput`, `Textarea`, `Switch` | `.input-group` (299 uses), `.mole-input` (245), `.form-group` | Labels are linked with `useId`, which lets `a11yLabels.js` go in P5. Hint and error text are wired through `aria-describedby`, with `aria-invalid`. Units appear as a suffix, with `inputMode="decimal"`. `Switch` is a styled `input type="checkbox" role="switch"`. |
| 6 | `Select`, `MultiSelect` | 111 native `<select>`, 66 `CustomDropdown`, `MultiSelectDropdown` | Evolved from `CustomDropdown` (D-4). Keeps its props, `.dropdown-*` classes and test ids, and adds `size`, `invalid`, `searchable` (type-to-filter for long lists such as parent fuels) and `name`. |
| 7 | `SegmentedControl` | GWP-100/20 toggles, tier pickers, chart/heatmap toggle, the "All scopes / Scope 1+2" toggle | `role="radiogroup"`, arrow keys, roving `tabindex`. |
| 8 | `Tabs` + `useTabParam` | Manage Data `div` tabs, Settings and QA tabs, the Calculations scope switcher | Radix Tabs, synced with `?tab=` (or `?scope=` on Calculations). |
| 9 | `Dialog`, `ConfirmDialog`, `Sheet` | `Modal`, `ConfirmModal`, `Drawer`, ~10 bespoke modals | Radix Dialog. `Modal`, `ConfirmModal` and `Drawer` become thin adapters with **the same props** (`{ isOpen, onClose, title, children, maxWidth }` and so on). |
| 10 | `Menu` | export button rows, row-action clusters, account menus | Radix DropdownMenu. |
| 11 | `Popover`, `Tooltip` | notification panel, long `title=` attributes | Radix. |
| 12 | `RadioCard` | the Settings GWP standard cards | Radio semantics. |
| 13 | `Banner` | pending banner, offline and session banners, compliance pills | Tones: info, success, warning, danger. Uses `role="status"`, or `role="alert"` for danger. |
| 14 | `EmptyState`, `Skeleton`, `Spinner` | ad-hoc empty texts, `SkeletonLoader`, `LoadingSpinner` | `Spinner` keeps the orange ring and drops Orbitron. |
| 15 | `Num`, `Unit`, formatter extensions | 139 `.toFixed`, 59 `.toLocaleString` | Rules in Appendix B.4. `Unit` renders tCO₂e, tCH₄, kSm³, m³ and kg/BOE consistently. |
| 16 | `DataTable` | ~15 table styles | TanStack v8. Sticky header; pinned first and actions columns; column-visibility menu (remembered per table in `localStorage`); density toggle; numeric column meta (right-aligned, tabular figures, unit in the header); sorting; client or server pagination; row selection; expandable rows; empty, loading and error states. |
| 17 | `FilterBar` | filters injected into the top bar | Built from `Select`, `MultiSelect` and `SegmentedControl`. Shows the active-filter count and a Reset action, and becomes a `Sheet` below 900 px. |
| 18 | `Stepper` | wizard step headers (BulkImport, ColumnMapping, Scope1/2/3ImportWizard, BatchReview) | |
| 19 | Chart theme | hard-coded axis, grid and tooltip colors in the 3 wrappers | `ui/charts/theme.js` exports axis, grid and tooltip props plus the `SERIES` palette. The wrappers require a series `name`, which fixes the "value" legends on Carbon Intensity. |
| 20 | `Toast` restyle | — | Same API. Adds `role="status"` with `aria-live="polite"` (errors use `assertive`), pauses on hover, shows at most 3. |

**Definition of done (per component)**
- Styles use tokens only: no hex values and no inline styles, just `cn()` and `cva`.
- Keyboard and screen-reader behavior follow the matching WAI-ARIA pattern, and jsx-a11y is clean.
- Vitest + RTL tests cover render, variants, keyboard interaction and ARIA.
- The gallery shows every state: default, focus, disabled, loading, error, long text, and narrow width.
- Where a component replaces an existing one, every existing call site compiles unchanged and the existing tests pass.

**Phase 2 exit criteria:** the kit is merged and shown in the gallery. `Modal`, `ConfirmModal`, `Drawer`, `Toast` and `CustomDropdown` already run on the new implementations through their adapters, which on its own fixes focus trapping and toast announcements app-wide.

---

## 8. Phase 3: app shell

**P3-1 Route config and guards (M)**
- Create `app/routes.config.js` (D-9) with paths, titles, groups, icons, access rules and lazy loaders. `RequireRole` replaces the five guard components and keeps the same redirects (§4).
- Unit test: a role × route matrix for `user`, `superuser`, `admin`, `it`, `it_admin` and `it_manager`, asserting both nav visibility and the redirect target.
- `useDocumentTitle()` sets titles such as "Reports · Carbon Tech".
- Page names, one each: Dashboard, Carbon Intensity, Methane Intensity, SBTi & Net-Zero, Emissions Map, Calculations, Manage Data, Reference Data, Reports, Uncertainty, QA/QC & Diagnostics, Audit Trail, User Management, Settings.

**P3-2 Sidebar (M)**
- Two states: expanded (240 px) and a collapsed 64 px rail. Toggle with a footer button or the `[` key; the choice is remembered in `localStorage`.
- The collapsed rail "peeks" open on hover after 150 ms and on `:focus-within`, **as an overlay** (`position: absolute` with a shadow). The layout column never changes width, so nothing reflows.
- Groups as in §4. Group labels show when expanded, and dividers with tooltips show on the rail.
- Active item: `bg-brand-50`, `text-brand-700`, a 3 px `brand-500` indicator bar and a `brand-500` icon. This replaces the full gradient pill with a glow.
- lucide icons replace the 18 inline SVGs in `Sidebar.jsx`.
- Below 900 px, the sidebar is a Radix Dialog drawer: focus is trapped, Escape closes it, and labels are always visible. This also fixes the hidden user info in today's mobile drawer.
- Per S-4, the account block moves out. The footer keeps Settings and the collapse toggle.

**P3-3 Top bar (M)**
- **Left:** `Breadcrumbs` generated from the route config, plus `useBreadcrumbExtra()` for sub-stages such as "Scope 1". Remove the static "Corporate ESG" label, or show the organization name if one becomes available.
- **Right:**
  - A search button that opens the palette and shows the `Ctrl K` hint.
  - `NotificationCenter`, restyled: the button's `aria-label` includes the unread count, and the panel becomes a Radix Popover.
  - `AccountMenu`: initials avatar, name, job title or role, and email; links to Settings and Audit Trail (when permitted); Sign out.
- Once P3-4 has landed, delete `topBarLeft`/`topBarRight` from `LayoutContext`. Today it's used by AuditTrail, CarbonIntensity, DashboardEnhanced, ManageData, MethaneIntensity and UncertaintyAssessment.

**P3-4 Shared analytics filters (L)**
- `filters/useOrgHierarchy.js`: fetches `/facilities` once, caches it in context, and derives the segment, activity, division and region options. This replaces duplicated logic in `DashboardEnhanced.jsx:518–573`, `CarbonIntensity.jsx:318–352` and `MethaneIntensity.jsx:482–516`.
- `useAnalyticsFilters()` returns `{ year, segment, activity, division, region, gwp }`, kept in the URL with defaults of `all` and `100`, and remembered in `sessionStorage`.
- Each page keeps its own mapping to API parameters: Carbon Intensity sends `facilityId`, while Uncertainty sends `facility_id`. No backend change.
- A sticky `FilterBar` sits under the top bar on Dashboard, Carbon Intensity, Methane Intensity, SBTi (year only), Uncertainty (year, scope, facility) and Emissions Map (year, activity, region).
- GWP horizon becomes one control, "GWP-100 | GWP-20", with a tooltip naming the AR standard and the CH₄ factor. This unifies "AR5 100-Yr" and "GWP-100".
- **e2e:** filters persist when moving between pages, and the deep link `/?year=2025&activity=EP` restores the state.

**P3-5 Command palette (M)**
- `cmdk`, lazy-loaded on the first `Ctrl/Cmd+K`.
- Groups:
  - Pages, filtered by role from the route config.
  - Actions: new Scope 1/2/3 entry (`/emissions?scope=…`), bulk import, export audit log, manage factors.
  - Recent: the last 5 pages visited.

**P3-6 Shell layout, banners, transitions (S)**
- `AppShell` replaces `Layout`. `BannerStack` stacks the offline and session-timeout banners, using `role="status"` or `role="alert"`, in place of two overlapping fixed `div`s with inline styles.
- Remove the `AnimatePresence mode="wait"` exit animation, which delays every route change. Pages fade in over 120 ms on entry, with no animation under reduced motion.
- The Suspense fallback becomes a page skeleton (header plus cards) instead of a spinner.

**P3-7 Remove the in-page second headers (S)**
- Delete `pages/Emissions.jsx:225` and `pages/Reports.jsx:461`, which each render a second `<header className="top-bar">`. Breadcrumbs now come from the shell, the Calculations scope switcher becomes `Tabs` in its `PageHeader`, and the duplicate user name on Reports disappears.

**Phase 3 exit criteria:**
- Sidebar interaction causes no layout shift (Lighthouse CLS of 0 on the Dashboard).
- The whole shell works with the keyboard alone.
- Breadcrumbs and document titles are correct on every route.
- Filters persist through the URL.
- e2e green.

---

## 9. Phase 4: page migrations

Ordered by value against risk. Apply the Appendix F checklist to every PR.

| # | Page | Files (JSX lines / CSS lines) | Size |
|---|---|---|---|
| 4.1 | Calculations | `Emissions` 323/737, `Scope1Form` 3,354/392, `scope1/*` 4,890/279, `Scope2Form` 955, `Scope3Form` 815, `CalculationDetails` 308/494 | XL |
| 4.2 | Dashboard | `DashboardEnhanced` 1,844 / `Dashboard.css` 1,662 | L |
| 4.3 | Manage Data | `ManageData` 4,250/991 | XL |
| 4.4 | Reports | 1,261/450 | M |
| 4.5 | Carbon & Methane Intensity | 1,015 + 1,676 / 970 (shared CSS) | L |
| 4.6 | SBTi & Net-Zero | 682/422 | S |
| 4.7 | Audit Trail | 935/1,075 | M |
| 4.8 | QA/QC & Diagnostics | 1,167/887 | M |
| 4.9 | Uncertainty | 388/469 | S |
| 4.10 | Reference Data | 605/192 | S |
| 4.11 | Settings | 1,256/1,141 | M |
| 4.12 | Emissions Map | 1,638/1,786 | M |
| 4.13 | User Management | 1,848 (87 references to an inline `S` style object) | M |
| 4.14 | Login | 436/407 | S |
| 4.15 | Wizards and modals | `BulkImportModal` 1,784/269, `ColumnMappingWizard` 1,460/712, `Scope1ImportWizard` 958/878, `Scope2ImportWizard` 548, `Scope3ImportWizard` 578, `BatchReviewWizard` 993/408, `QuickAddCustomFactorModal` 499, `GasCompositionCalculator` 480/249, `UploadProgress` 505/555, `NotificationCenter` 734 | L |

**4.1 Calculations (core workflow)**
1. **Primitives PR (behavior-neutral).** Swap in `Field`, `Input`, `Select`, `SegmentedControl` and `Button` inside the forms without moving any markup. The scope 1 e2e specs (about 90 KB) must stay green.
2. **Layout PR.** Add a `PageHeader` with scope `Tabs` (01 Scope 1, 02 Scope 2, 03 Scope 3), synced to the existing `?scope=` parameter. The scope selection cards remain the landing state.
3. **Live result.** From 1200 px up, use two columns: the form (numbered sections stay) and a sticky `ResultPanel` showing CO₂, CH₄, N₂O, CO₂e, method/tier, ±% uncertainty and factor source. Below 1200 px, the panel becomes a sticky bottom summary.
4. **Sticky action bar.** "Save draft" and "Calculate & submit". Keep the current submit label, or update the e2e spec in the same PR.
5. **History in an "Entries" tab, using `DataTable`.**
   - Default columns: Period, Facility (activity · division · region in one cell), Source/Process, Fuel, Method (tier badge), Quantity with unit, CO₂e (t), Status, Actions.
   - Hidden by default: the per-gas columns, Equipment ID, and the six uncertainty columns (1σ and 95% CI). They're available from the column menu and in the expanded row.
6. Periods show as "Sep 2026" so they don't wrap, and quantities are right-aligned with units.

**4.2 Dashboard**
- `PageHeader` with "Updated hh:mm" as muted text (replacing the pulsing "Live" pill). Actions: "Set target" and "Export ▾" (Executive brief PDF).
- **KPI strip:** 4 `StatCard`s with neutral values. Only the deltas are colored (against the prior year or target: lower is green, higher is red). This removes the decorative green, amber and violet values.
- **Scope breakdown:** one stacked bar with a legend in the S-2 scope colors, replacing the three red, blue and purple pastel bars.
- **Pending banner:** a warning `Banner`, with the preview `Switch` and a "Review" action.
- **Flaring section:** a collapsible `Card` with a `Banner` for the Decree 21-330 status; the stream cards become compact `StatCard`s.
- **Charts:** use the chart theme and named series. The Detailed Breakdown becomes a `DataTable` with a totals row.

**4.3 Manage Data**
- **Prerequisite (behavior-neutral PR).** Split the page into `pages/manage-data/`:
  - `index.jsx` holds the shell and tabs.
  - One file per tab: `PendingTab`, `FactorsTab`, `RegionsTab`, `ProductionTab`, `SourcesTab`, `GoalsTab`, `MitigationTab`, `OgmpTab`, `CbamTab`.
  - Shared hooks.
  - Keep `navigate('/manage-data', { state: { tab } })` working (used by the Dashboard), while adding `?tab=`.
- **Tabs:** real `role="tab"` buttons, vertical from 1200 px up and a horizontally scrolling row below that. The Pending count shows as a badge.
- **List first:** each tab is a `FilterBar`, then a `DataTable`, then a "New …" button that opens the form in a `Sheet` (custom factor, production data, goals and so on).
- **Pending review:** row selection with bulk Approve and Reject (`ConfirmDialog`, plus a `Dialog` for the rejection reason) and `StatusPill`s.
- This removes 348 inline style objects and 36 native `<select>` elements.

**4.4 Reports**
- The title becomes "Reports" (description: "Emission database & exports").
- **Actions:** a primary "Create report" button opening a `Dialog` with today's "Create New Report" fields, and an "Export ▾" `Menu` (OGMP 2.0 Excel, Excel, PDF, Master report PDF) that uses file-type icons instead of colors.
- **Layout:** a collapsible `FilterBar`, and the `DataTable` above the fold.

**4.5 Carbon & Methane Intensity** (one shared template, since they share CSS today)
- `PageHeader`, the shared `FilterBar`, `StatCard`s, a `Banner` for OGMP 2.0 compliance, and themed charts.
- The base-year selector becomes a `SegmentedControl`.
- Large totals use `Num` in compact form with the exact value on hover, so values like "10,000,000,000 BOE" no longer overflow.
- Delete `CarbonIntensity.css` and the `.intensity-content` variables added in P0-3.

**4.6 SBTi.** `PageHeader` with the segmented scope filter, "Configure target" as a secondary button, and "Export ▾". `StatCard`s and the chart theme.

**4.7 Audit Trail**
- **Default view:** a compact table with Time, User, Action badge, Entity, Description and IP. Rows expand to show the raw JSON (monospace, with a copy button). Day headers separate the rows.
- **Alternative view:** the timeline, via a "Table | Timeline" toggle.
- Filters move to the `FilterBar`, and the KPI tiles become small `StatCard`s.
- **Backend follow-up, out of scope here:** event text says "1000 of None" because Python `None` leaks into it.

**4.8 QA/QC.** Already close to the target. Move to `Tabs`, `DataTable` and `StatusPill`. The selected status chip uses the selected role (brand tint) instead of near-black, and scope badges use the scope tokens.

**4.9 Uncertainty.** The title becomes "Uncertainty" (description: "Data reliability analysis…"). Cards and legend share the uncertainty tokens (low green, medium amber, high red), which fixes the current contradiction. Tier shares show as a stacked bar.

**4.10 Reference Data.**
- One `DataTable` per category, inside collapsible `Card`s.
- Factors keep their stored precision and are aligned on the decimal point (B.4).
- Category tags use neutral or brand tones, so "FLARING" is no longer red.
- The breadcrumb comes from the route config, which drops "Resource Center".

**4.11 Settings.** This page is the reference pattern. Migrate its primitives: the standard cards become `RadioCard`, the tabs use `?tab=`, "Save all changes" moves into the `PageHeader` actions, and the read-only notice for non-admins becomes a `Banner`.

**4.12 Emissions Map.**
- Keep the floating panels.
- Use "Emissions Map" as the title and sentence-case panel titles. This drops "Methane Recon Cockpit", "Target Reconnaissance" and the wide letter-spacing.
- Controls move to `Select`, `SegmentedControl` and `Switch`.
- The Leaflet and Sentinel-5P overlay logic stays untouched.

**4.13 User Management.** Replace the `S` inline-style object with components. Users go in a `DataTable`, the `Drawer` becomes a `Sheet`, and role badges use neutral or status tones.

**4.14 Login.**
- Put the logo on the card.
- Play the intro once per device (`localStorage` key `ct_intro_seen`) and skip it under reduced motion (S-5).
- Use the brand orange and visible labels. Keep the "Email Address" placeholder, or update the e2e spec.
- Add a show/hide password `IconButton`.
- Replace the olive `GhgCloud` blob with the orange radial wash already used on the app background.
- The trust badges become single-line `Badge`s.

**4.15 Wizards and modals.**
- Move them onto `Dialog` and `Sheet`, with a `Stepper` header and `DataTable` previews.
- Footers are consistent: secondary actions on the left, the primary action on the right.
- Delete the bespoke overlays: `.calc-overlay`, `.cmw-overlay`, `.s1w-overlay`, `.csv-modal-overlay`, `.batch-wizard-backdrop`, `.rejection-modal-backdrop`, `.forgot-modal-overlay`.

---

## 10. Phase 5: accessibility, motion, cleanup

- Once every form uses `Field`, retire `utils/a11yLabels.js` (and `installLabelLinker` in `main.jsx`). Verify with axe that no route has a label violation.
- Make jsx-a11y an `error` across the repo. Add `e2e/a11y.spec.js` using `@axe-core/playwright@^4.13.0` (`withTags(['wcag2a', 'wcag2aa'])`) on every route and every open dialog: 0 serious or critical violations.
- Do a keyboard walkthrough of every page for each role (Appendix F).
- **Motion:** use only the duration and easing tokens. Remove `framer-motion` if Login turns out to be its last user (replace with CSS keyframes) and measure the bundle difference.
- **Delete:**
  - `legacy.css` and the remaining page CSS
  - the `LayoutContext` top-bar API and the old `components/layout/*`
  - `TopBarFilters.css` and `CustomDropdown.css` (moved into `ui/Select`)
  - `a11yLabels.js`, and `tailwind.config.js` if it's still there
- Remove the scanning limit (`source(none)`) so the whole of `src` is scanned; no legacy markup remains at this point.
- **Docs:**
  - CLAUDE.md "Frontend architecture": `ui/`, `styles/`, `app/routes.config.js`, `filters/`.
  - The `AUDIT_MEMORY.md` UI section.
  - Re-run the accessibility audit and record the axe results in `docs/validation/06-accessibility-audit.md`.
- Compare the final metrics with the §2.2 targets.

---

## 11. Testing and QA

| Layer | What | When |
|---|---|---|
| Unit (vitest + RTL) | Every `ui/*` component; `cn`; formatters (extend `mathParityAndFormatters.test.js`); the role × route matrix; URL filter sync | Every PR, in CI |
| E2E (Playwright, local) | The existing specs (scope 1 form engine and scenarios, dashboard and intensity audits, bulk CSV, workflow), plus new ones: token-leak assertion, filter persistence, keyboard navigation smoke test | Every PR that touches a page |
| Visual | P0-1 route screenshots (human review, before/after attached to the PR); automated gallery snapshots (`toHaveScreenshot`) | Every UI PR |
| Accessibility | jsx-a11y (CI); axe e2e (P5); manual keyboard pass and NVDA spot check | Every phase |
| Performance | Bundle size (`stats.html` from rollup-plugin-visualizer); Lighthouse on Dashboard and Calculations (CLS, LCP) | Every phase |
| Manual matrix | Roles `user`, `superuser`, `admin`, `it`/`it_admin`/`it_manager` × widths 1440/1280/1024/768/390 × Chrome/Edge/Firefox/Safari | End of P3, end of P4 |

The CI client job runs `npm ci`, `npm run lint`, `npm run test` and `npm run build` on Node 20. Keep those, and add `lint:css` and `ui:metrics --check`. Playwright stays local because it needs the backend and a database; a seeded-backend CI job is possible later.

---

## 12. Delivery

**Branching (S-6).** Create `feat/ui-modernization` from `main` after the current RC is merged.
- PRs should stay at or below about 500 changed lines; mechanical moves and file splits are the exception.
- Each PR includes before/after screenshots (1440 / 1024 / 390) and the Appendix F checklist.
- Merge to `main` at the end of each phase, or per WP once that WP is stable.

**Rough sequencing and effort for one front-end developer:**

| Phase | Effort | Parallelizable |
|---|---|---|
| P0 Safety net and bug fixes | 3–4 days | — |
| P1 Foundations | 4–5 days | — |
| P2 Component kit | 8–12 days | Components split well across 2 people |
| P3 App shell | 6–9 days | The palette (P3-5) runs in parallel |
| P4 Page migrations | 25–35 days | Pages run in parallel once 4.1 sets the pattern |
| P5 Accessibility, motion, cleanup | 4–6 days | — |
| **Total** | **about 10–14 weeks (one developer); 6–8 weeks with two after P2** | |

**Milestones**
- M1 (end of P0): theme bugs fixed.
- M2 (end of P2): gallery complete, and modals/toasts accessible app-wide.
- M3 (end of P3): new shell live.
- M4 (4.1–4.3): core workflows migrated.
- M5 (end of P5): done.

---

## 13. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Markup changes break e2e specs | High | Medium | Stable test ids (P0-2); update specs in the same PR |
| Big-file refactors break calculations (ManageData 4,250 lines, Scope1Form 3,354) | Medium | High | Behavior-neutral split PRs; no logic edits in styling PRs; vitest math parity and the scope 1 e2e specs |
| The route-config refactor breaks permissions | Low | High | Role × route matrix test (P3-1) |
| Tailwind utilities apply to legacy markup | Medium | Medium | `source(none)` plus explicit `@source` (D-1); the collision report in `ui:metrics` |
| The new font changes text wrapping | High | Low | Screenshot review; adjust widths; fallback stack |
| Legacy CSS overrides new components (unlayered page CSS, element selectors, 146 `!important`) | Medium | Medium | Migrate components wholesale; the checklist removes page element selectors first |
| Two styles side by side during a long migration | High | Low | Shell first, so the frame is consistent; migrate whole pages |
| Bundle growth (Radix, TanStack, cmdk) | Medium | Low | Lazy-load the palette; tree-shaken lucide imports; drop framer-motion; budget check each phase |
| S-3 (primary button contrast) stays undecided | Medium | Low | One token switch; document the exception in the a11y audit |
| Scope creep | Medium | Medium | Non-goals list; exit criteria per phase |

---

## Appendix A: tokens

### A.1 `src/styles/tokens.css`
```css
@theme {
  /* Remove Tailwind defaults so only the palette exists */
  --color-*: initial;
  --text-*: initial;
  --radius-*: initial;
  --shadow-*: initial;
  --breakpoint-*: initial;
  --font-*: initial;
  --ease-*: initial;

  /* Fonts (S-1) */
  --font-sans: "Outfit Variable", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;

  /* Palette: existing values only (usage counts from the 2026-10-02 survey) */
  --color-white: #ffffff;

  --color-brand-50: #fff7ed;   /* 20 */
  --color-brand-100: #ffedd5;
  --color-brand-400: #ff8533;  /* 18 */
  --color-brand-500: #ff6600;  /* 186, the accent */
  --color-brand-600: #e65c00;  /* hover, focus ring */
  --color-brand-700: #c2410c;  /* orange text (AA) */

  --color-ink-900: #0f172a;    /* 178, primary text */
  --color-ink-800: #1e293b;
  --color-ink-700: #334155;
  --color-ink-600: #475569;
  --color-ink-500: #64748b;    /* 170, secondary and muted text */
  --color-ink-400: #94a3b8;    /* disabled and decorative only */
  --color-ink-300: #cbd5e1;
  --color-ink-200: #e2e8f0;    /* 184, borders */
  --color-ink-100: #f1f5f9;    /* app canvas */
  --color-ink-50: #f8fafc;

  --color-green-50: #ecfdf5;
  --color-green-500: #10b981;  /* 160, positive / environmental */
  --color-green-600: #059669;
  --color-green-700: #2E7D32;  /* documented palette, AA text */
  --color-green-900: #1B5E20;  /* documented palette */

  --color-blue-50: #eff6ff;
  --color-blue-500: #3b82f6;
  --color-blue-600: #2563eb;
  --color-blue-700: #1d4ed8;
  --color-sky-600: #0284c7;

  --color-amber-50: #fffbeb;
  --color-amber-500: #f59e0b;
  --color-amber-600: #d97706;
  --color-amber-700: #b45309;

  --color-red-50: #fef2f2;
  --color-red-500: #ef4444;
  --color-red-600: #dc2626;
  --color-red-700: #b91c1c;

  --color-violet-500: #8b5cf6;

  /* Roles */
  --color-primary: var(--color-brand-500);         /* S-3: switch to brand-700 for AA */
  --color-primary-hover: var(--color-brand-600);
  --color-on-primary: var(--color-white);
  --color-link: var(--color-brand-700);
  --color-focus: var(--color-brand-600);
  --color-selected-bg: var(--color-brand-50);
  --color-selected-fg: var(--color-brand-700);

  --color-text: var(--color-ink-900);
  --color-text-secondary: var(--color-ink-500);
  --color-text-disabled: var(--color-ink-400);
  --color-border: var(--color-ink-200);
  --color-surface: var(--color-white);
  --color-canvas: var(--color-ink-100);

  --color-success: var(--color-green-500);
  --color-success-bg: var(--color-green-50);
  --color-success-fg: var(--color-green-700);
  --color-warning: var(--color-amber-500);
  --color-warning-bg: var(--color-amber-50);
  --color-warning-fg: var(--color-amber-700);
  --color-danger: var(--color-red-500);
  --color-danger-bg: var(--color-red-50);
  --color-danger-fg: var(--color-red-700);
  --color-info: var(--color-blue-500);
  --color-info-bg: var(--color-blue-50);
  --color-info-fg: var(--color-blue-700);

  --color-scope-1: var(--color-brand-500);         /* S-2 */
  --color-scope-2: var(--color-blue-500);
  --color-scope-3: var(--color-violet-500);

  --color-unc-low: var(--color-green-500);
  --color-unc-medium: var(--color-amber-500);
  --color-unc-high: var(--color-red-500);

  /* Type scale: 8 steps */
  --text-xs: 0.75rem;    --text-xs--line-height: 1rem;
  --text-sm: 0.8125rem;  --text-sm--line-height: 1.25rem;
  --text-base: 0.875rem; --text-base--line-height: 1.375rem;
  --text-md: 1rem;       --text-md--line-height: 1.5rem;
  --text-lg: 1.125rem;   --text-lg--line-height: 1.625rem;
  --text-xl: 1.5rem;     --text-xl--line-height: 2rem;
  --text-2xl: 1.875rem;  --text-2xl--line-height: 2.25rem;
  --text-3xl: 2.25rem;   --text-3xl--line-height: 2.5rem;

  /* Radius */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
  --radius-full: 9999px;

  /* Elevation: the existing shadow values */
  --shadow-xs: 0 1px 3px rgba(15, 23, 42, 0.04);
  --shadow-card: 0 4px 20px -2px rgba(15, 23, 42, 0.05), 0 2px 6px -1px rgba(15, 23, 42, 0.02);
  --shadow-raised: 0 12px 32px -4px rgba(15, 23, 42, 0.08), 0 4px 12px -2px rgba(15, 23, 42, 0.03);
  --shadow-overlay: 0 12px 32px -4px rgba(15, 23, 42, 0.15);

  /* Breakpoints */
  --breakpoint-sm: 40rem;     /* 640 px */
  --breakpoint-md: 56.25rem;  /* 900 px: sidebar becomes a drawer */
  --breakpoint-lg: 75rem;     /* 1200 px: two-column layouts */
  --breakpoint-xl: 96rem;     /* 1536 px */

  /* Motion */
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
}

:root {
  /* z-index scale (use as z-(--z-modal)) */
  --z-sticky: 100;
  --z-sidebar: 200;
  --z-topbar: 300;
  --z-dropdown: 1000;
  --z-overlay: 1100;
  --z-modal: 1200;
  --z-popover: 1300;  /* select and menu portals opened inside modals */
  --z-toast: 1400;
  --z-banner: 1500;

  --duration-fast: 120ms;
  --duration-base: 200ms;
  --duration-slow: 300ms;

  /* Chart series, in this order */
  --chart-1: var(--color-brand-500);
  --chart-2: var(--color-blue-500);
  --chart-3: var(--color-green-500);
  --chart-4: var(--color-violet-500);
  --chart-5: var(--color-amber-500);
  --chart-6: var(--color-sky-600);
  --chart-7: var(--color-ink-500);
  --chart-8: var(--color-red-500);  /* last, and only for negative series */
}
```

### A.2 Bridge from the legacy variables (kept until P5)
```css
:root {
  --accent-color: var(--color-brand-500);
  --accent-hover: var(--color-brand-600);
  --accent-subtle: rgba(255, 102, 0, 0.1);
  --accent-gradient: linear-gradient(135deg, #ff6600 0%, #ff8533 100%);
  --bg-body: var(--color-ink-100);
  --bg-card: rgba(255, 255, 255, 0.9);
  --bg-card-elevated: rgba(255, 255, 255, 0.96);
  --bg-hover: rgba(255, 247, 237, 0.85);
  --text-primary: var(--color-ink-900);
  --text-main: var(--color-ink-900);
  --text-secondary: var(--color-ink-500);
  --text-muted: var(--color-ink-500);       /* D-13: today's rendered value */
  --text-disabled: var(--color-ink-400);
  --border-color: rgba(226, 232, 240, 0.8);
  --border-light: var(--color-ink-200);     /* today's rendered value */
  --border-focus: var(--color-brand-500);
  --danger: #ef4444;  --danger-bg: rgba(239, 68, 68, 0.1);
  --success: #10b981; --success-bg: rgba(16, 185, 129, 0.1);
  --warning: #f59e0b; --warning-bg: rgba(245, 158, 11, 0.1);
  --info: #3b82f6;    --info-bg: rgba(59, 130, 246, 0.1);
  --shadow-card: 0 4px 20px -2px rgba(15, 23, 42, 0.05), 0 2px 6px -1px rgba(15, 23, 42, 0.02);
  --shadow-card-elevated: 0 12px 32px -4px rgba(15, 23, 42, 0.08), 0 4px 12px -2px rgba(15, 23, 42, 0.03);
  --shadow-hover: 0 16px 36px -4px rgba(255, 102, 0, 0.12), 0 6px 16px -2px rgba(15, 23, 42, 0.04);
}
```

---

## Appendix B: mapping tables for mechanical migration

**B.1 Font sizes.**

| Existing values | Token | Size |
|---|---|---|
| 0.62–0.72rem | `text-xs` | 12 px (this raises today's 10–11.5 px text to the 12 px minimum) |
| 0.74–0.82rem | `text-sm` | 13 px |
| 0.84–0.9rem | `text-base` | 14 px |
| 0.92–1.05rem | `text-md` | 16 px |
| 1.1–1.25rem | `text-lg` | 18 px |
| 1.35–1.75rem | `text-xl` | 24 px |
| 1.875–2rem | `text-2xl` | 30 px |
| > 2rem | `text-3xl` | 36 px |

**B.2 Radius.**

| Existing values | Token |
|---|---|
| 2–7 px | `rounded-sm` (6 px) |
| 8–12 px | `rounded-md` (10 px) |
| 14–34 px | `rounded-lg` (16 px) |
| 50%, 100 px, 999 px, 9999 px | `rounded-full` |

**B.3 Font weight by role.**

| Role | Weight |
|---|---|
| Body text | 400 |
| Labels and table headers | 500 |
| Buttons, tabs and card titles | 600 |
| Page titles and KPI values | 700 |
| 800 and 900 | retired |

Uppercase with letter-spacing is reserved for eyebrow labels and table headers (`text-xs font-medium uppercase tracking-wide`).

**B.4 Numbers and units.** Formatting goes through `utils/formatters.js`, whose current defaults are kept.

| Context | Format | Example |
|---|---|---|
| KPI tiles and dashboards | `formatCompactNumber` with 1 decimal; exact value in a tooltip | 660.9K tCO₂e (hover: 660,943.175) |
| Emissions in tables (t) | `formatEmission`: grouped digits, 3 decimals (unchanged precision) | 660,943.175 |
| Emission factors and GWPs | Stored precision, no rounding; aligned on the decimal point; scientific notation below 1e-4 with the full value on hover | 0.010836 |
| Percentages and uncertainty | 1 decimal, with ± for uncertainty | ±52.2 % |
| Intensities | 2 decimals by default; 4 below 0.01 | 0.07 kg CO₂e/BOE |
| Period | `MMM yyyy` | Sep 2026 |
| Units | Always via `<Unit>`: tCO₂e, tCH₄, kSm³, m³, kg CO₂e/BOE. Never "tCO2e" | |

Numbers in tables are right-aligned and use `tabular-nums` (or `--font-numeric`, see P0-6).

**B.5 Color usage rules.**
- Brand orange is for interactive and selected states.
- Status colors use the `-fg` shade for text and the `-bg` tint for the background.
- Data categories (scope, uncertainty, chart series) use their tokens.
- KPI numbers are never colored decoratively.
- Red only ever means negative, error or danger.

**B.6 Near-duplicate consolidation (D-14).**

| From | To |
|---|---|
| `#f97316`, `#fb923c` | brand-500 / brand-400 |
| `#ea580c` | brand-600 |
| `#374151` | ink-700 |
| `#6b7280` | ink-500 |
| `#9ca3af` | ink-400 |
| `#111827` | ink-900 |
| `#16a34a` | green-600 |
| `#7c3aed`, `#6366f1` | violet-500, or the series palette for chart use |
| `#0d9488` (the teal leak) | removed |

---

## Appendix C: file inventory (2026-10-02)

| File | JSX lines | Own CSS lines | `style={{}}` | `<select>` | `CustomDropdown` | inline `<svg>` |
|---|---:|---:|---:|---:|---:|---:|
| `pages/ManageData.jsx` | 4,250 | 991 | 348 | 36 | 3 | 1 |
| `components/Scope1Form.jsx` | 3,354 | 392 | 101 | 5 | 7 | 1 |
| `components/scope1/*.jsx` (17 files) | 4,890 | 279 (`ui.css`) | 207 | 22 | 29 | — |
| `pages/DashboardEnhanced.jsx` | 1,844 | 1,662 (`Dashboard.css`) | 42 | 0 | 5 | 8 |
| `pages/UserManagement.jsx` | 1,848 | — | 58 | 5 | 0 | 15 |
| `components/BulkImportModal.jsx` | 1,784 | 269 | 69 | 2 | 0 | 0 |
| `pages/MethaneIntensity.jsx` | 1,676 | shares `CarbonIntensity.css` | 44 | 0 | 5 | 0 |
| `pages/MethaneExplorer.jsx` | 1,638 | 1,786 | 5 | 3 | 0 | 0 |
| `components/ColumnMappingWizard.jsx` | 1,460 | 712 | 35 | 3 | 0 | 12 |
| `pages/Reports.jsx` | 1,261 | 450 | 49 | 13 | 0 | 9 |
| `pages/Settings.jsx` | 1,256 | 1,141 | 23 | 2 | 0 | 0 |
| `pages/QADashboard.jsx` | 1,167 | 887 | 83 | 2 | 0 | 0 |
| `pages/CarbonIntensity.jsx` | 1,015 | 970 | 21 | 0 | 5 | 0 |
| `components/BatchReviewWizard.jsx` | 993 | 408 | 62 | 2 | 0 | 0 |
| `components/Scope1ImportWizard.jsx` | 958 | 878 | 3 | 2 | 0 | 24 |
| `components/Scope2Form.jsx` | 955 | — | 38 | 2 | 4 | 0 |
| `pages/AuditTrail.jsx` | 935 | 1,075 | 4 | 5 | 0 | 0 |
| `components/Scope3Form.jsx` | 815 | — | 43 | 2 | 3 | 0 |
| `components/NotificationCenter.jsx` | 734 | — | 29 | 0 | 0 | 0 |
| `pages/SbtiDashboard.jsx` | 682 | 422 | 19 | 0 | 0 | 0 |
| `pages/ReferenceData.jsx` | 605 | 192 | 19 | 1 | 0 | 0 |
| `components/Scope3ImportWizard.jsx` | 578 | — | 4 | 1 | 0 | 16 |
| `components/Scope2ImportWizard.jsx` | 548 | — | 3 | 1 | 0 | 17 |
| `components/layout/Sidebar.jsx` | 563 | 483 | 3 | 0 | 0 | 18 |
| `components/UploadProgress.jsx` | 505 | 555 | 5 | 0 | 0 | 7 |
| `components/QuickAddCustomFactorModal.jsx` | 499 | — | 41 | 1 | 0 | 0 |
| `components/GasCompositionCalculator.jsx` | 480 | 249 | 1 | 0 | 0 | 0 |
| `pages/Login.jsx` | 436 | 407 | 4 | 0 | 0 | 5 |
| `pages/UncertaintyAssessment.jsx` | 388 | 469 | 14 | 0 | 3 | 0 |
| `pages/Emissions.jsx` | 323 | 737 | 4 | 0 | 0 | 6 |
| `components/CalculationDetails.jsx` | 308 | 494 | 3 | 0 | 0 | 0 |
| `components/layout/Layout.jsx` | 173 | 65 | 7 | 0 | 0 | 0 |
| `components/layout/TopBar.jsx` | 90 | 282 | 7 | 0 | 0 | 0 |

---

## Appendix D: e2e selector migration (P0-2)

| Current selector (approx. uses) | Replacement |
|---|---|
| `.stat-item:has-text("Gross Operational Emissions")` (17) | `getByTestId('kpi-gross')` |
| `.stat-item:has-text("Net Emissions")` (4), `…("Total CH4")` (3) | `getByTestId('kpi-net')`, `getByTestId('kpi-ch4')` |
| `.kpi-card` (6), `.kpi-label` (4) | `getByTestId('kpi-<name>')` |
| `.scope-pill.scope-1 .pill-value` (4), `.scope-pill.scope-3 .pill-value` (4) | `getByTestId('scope-1-total')`, `getByTestId('scope-3-total')` |
| `.total-value` (12), `.result-overlay` (4) | `getByTestId('calc-total')`, `getByTestId('calc-result')` |
| `.grid-title` (10) | `getByRole('heading', { level: 1 })` |
| `.dropdown-selected` (10), `.drilling-form .dropdown-selected` (3) | `getByTestId('select-trigger')`, scoped with `within(...)` |
| `.dropdown-portal .dropdown-option:has-text(…)` (3 + templates) | `getByRole('option', { name })` |
| `.top-bar-injected-left .filter-wrapper` (5) | `getByTestId('filter-year')`, `getByTestId('filter-activity')` and so on (these move into the `FilterBar` in P3-4) |
| `button.btn-toggle-sm:has-text("specific")` (9), `…("default")` (3) | `getByTestId('factor-source-specific')`; after P2, `getByRole('radio', { name })` |
| `button:has-text("GWP-20")` (5), `…("GWP-100")` (3) | `getByRole('radio', { name: 'GWP-20' })` once the `SegmentedControl` lands; until then, test ids |
| `.combustion-form .input-group:has-text("Unit")` (5), `.input-group:has-text("Process Type")` (3), `…("Emission Factor")` (3) | `getByLabel('Unit')` and so on, scoped to the form's test id |
| `.calculator-grid-container table tbody tr` (4), `.calculator-grid-container` (3) | `getByTestId('history-table').locator('tbody tr')` |
| `.detailed-table-card` (4) | `getByTestId('breakdown-table')` |
| `button.btn-add-activity, button:has-text("+ Calculate & Submit for Review")` (4) | `getByRole('button', { name: /calculate & submit/i })` |
| `input[placeholder="Email Address"]` (8), `input[type="password"]` (8) | `getByLabel('Email address')`, `getByLabel('Password')` |
| `.login-intro-overlay` (8), `button.skip-intro-btn` (12) | `getByTestId('login-intro')`, `getByRole('button', { name: /skip intro/i })` |
| `button[type="submit"]:has-text("Sign In")` (7) | `getByRole('button', { name: 'Sign In' })` |
| Unit tests: `getByText("Stationary Combustion", { selector: ".dropdown-selected *" })` | `within(getByTestId('select-trigger')).getByText(…)` (the class is also kept) |

---

## Appendix E: component API sketches

```jsx
// ui/Button.jsx
const button = cva(
  "inline-flex items-center justify-center gap-2 rounded-md font-semibold transition-colors " +
    "disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        primary: "bg-primary text-on-primary hover:bg-primary-hover",
        secondary: "border border-border bg-surface text-text hover:bg-selected-bg",
        ghost: "text-text-secondary hover:bg-ink-100 hover:text-text",
        danger: "bg-danger-fg text-white hover:bg-red-600",
        link: "px-0 text-link underline-offset-4 hover:underline",
      },
      size: {
        sm: "h-8 px-3 text-sm",
        md: "h-10 px-4 text-base",
        lg: "h-11 px-5 text-md",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);
```

```jsx
<StatCard
  label="Gross operational emissions"
  sublabel="Scope 1+2"
  value={660943.175}
  unit="tCO₂e"
  format="compact"
  delta={{ value: -0.042, goodWhen: "down", label: "vs 2025" }}
  footnote="Target 2030: 118,500 tCO₂e"
  icon={Factory}
  data-testid="kpi-gross"
/>

<Field label="Quantity" hint="Volume consumed in the period" error={errors.quantity} required>
  <NumberInput unit="m³" value={quantity} onChange={setQuantity} />
</Field>

<SegmentedControl
  label="GWP horizon"
  value={gwp}
  onChange={setGwp}
  options={[
    { value: "100", label: "GWP-100" },
    { value: "20", label: "GWP-20" },
  ]}
/>
```

```js
// DataTable columns (TanStack v8)
const columns = [
  col.accessor("period", { header: "Period", cell: (c) => formatPeriod(c.getValue()) }),
  col.accessor("co2e_total", { header: "CO₂e", meta: { numeric: true, unit: "t", format: "emission" } }),
  col.display({ id: "actions", header: "", meta: { pin: "right" }, cell: RowActions }),
];
```

```jsx
<DataTable
  tableId="scope1-history"
  data={rows}
  columns={columns}
  density="compact"
  defaultHidden={["co2_unc_1s", "ch4_unc_1s", "n2o_unc_1s", "co2_ci95", "ch4_ci95", "n2o_ci95"]}
  pagination={{ pageSize: 25 }}
/>
```

```js
// filters/useAnalyticsFilters.js
const { filters, setFilter, reset } = useAnalyticsFilters();
// filters = { year: "all", segment: "all", activity: "all", division: "all", region: "all", gwp: "100" }
```

```js
// app/routes.config.js (excerpt)
{
  path: "/audit-trail",
  title: "Audit Trail",
  group: "Assurance & Reporting",
  icon: History,
  access: "audit",
  lazy: () => import("../pages/AuditTrail"),
},
```

---

## Appendix F: per-page PR checklist

- [ ] The page is wrapped in `<Page>`. Title, description and actions are in `PageHeader`, and the title matches the route config.
- [ ] Filters use `FilterBar` / `useAnalyticsFilters`; nothing is injected into the top bar.
- [ ] KPIs use `StatCard`; numbers use `Num` and the formatters; units use `Unit`.
- [ ] Buttons use `Button`/`IconButton`, with a `Menu` when there are more than 2 secondary actions. There is one primary action per view.
- [ ] Inputs use `Field` plus `Input`/`NumberInput`/`Select`/`SegmentedControl`/`Switch`.
- [ ] Tables use `DataTable`, with numeric meta, pinned actions, and empty/loading/error states.
- [ ] Overlays use `Dialog`/`Sheet`/`ConfirmDialog`.
- [ ] Colors come only from role tokens (brand, status, scope, uncertainty, series). No decorative KPI colors.
- [ ] In the page CSS, element selectors and `!important` are removed and replaced rules deleted. Target: at least 70% fewer lines, or the file deleted.
- [ ] Inline `style` remains only for dynamic CSS variables.
- [ ] Icons come from lucide; no inline `<svg>`.
- [ ] Keyboard: every action is reachable, focus is visible, Escape closes overlays, and focus returns to the trigger.
- [ ] axe reports 0 serious or critical violations on the page, including with dialogs open.
- [ ] Before/after screenshots at 1440, 1024 and 390 px are attached.
- [ ] e2e and vitest are green, and the `ui-metrics.baseline.json` values have gone down.
- [ ] `AUDIT_MEMORY.md` and the docs are updated if a defect was fixed, and `graphify update .` has been run.

---

## Appendix G: commands

```bash
# all commands run from new/client
npm run dev                         # :5173, proxies /api to :5000 (start the backend first)
npm run lint && npm run lint:css
npm run test
npm run build
npm run ui:metrics                  # print the metrics
npm run ui:metrics -- --check       # CI ratchet
npx playwright test                 # needs the backend on :5000 and storageState.json
npx playwright test --grep @baseline   # capture the route screenshots (P0-1)
```


---

## Implementation status (updated as work lands)

| Phase | Status | Notes |
|---|---|---|
| P0 | Done | S-1 resolved as the system stack, so no web font was added. Login intro removed (S-5). `data-testid` hooks added to `CustomDropdown`; a Playwright run against a worktree server is possible via `E2E_BASE_URL`. |
| P1 | Done | Deviation: `base.css` and `legacy.css` are unlayered (only Tailwind `theme`/`utilities` are layered), so the focus ring beats legacy `outline: none` rules and legacy cascade order is unchanged. Gallery at `/__ui` (dev only, excluded from production builds). 1,511 CSS hex literals were replaced by tokens (CSS hex count 1,823 to about 290). |
| P2 | Done | Button, IconButton, Badge/StatusPill, Card, Page/PageHeader, Banner, StatCard, Num/Unit, Field/Input/NumberInput/Textarea/Switch, SegmentedControl, Tabs, Dialog/Sheet/ConfirmDialog, Menu, Popover, Tooltip, DataTable, Skeleton, EmptyState, Select/MultiSelect (wrapping the existing dropdowns), RadioCardGroup, Stepper, FilterBar, chart theme. `Modal`, `ConfirmModal`, `Drawer` are adapters. |
| P3 | Done | Route config, guards, sidebar, top bar, command palette, banner stack, document titles, shared analytics filters (URL + sessionStorage) on Dashboard, Carbon Intensity and Methane Intensity. Page-injected filters render in a dedicated filter row under the top bar. |
| P4 | Pragmatic subset done | Reports (PageHeader + Export menu), Dashboard (SegmentedControl GWP toggle, neutral KPI values), Calculations history (sticky header, pinned first/last columns, opt-in uncertainty columns), Audit Trail (compact table view + details dialog), Login (logo, show/hide password, Banner, reduced motion), Uncertainty (consistent band colors), Manage Data tabs (real buttons), scope colors (S-2), standard page title size. Not rewritten onto the kit: the remaining markup of ManageData, Scope1Form, Settings, QA, SBTi, Reference Data, User Management, Emissions Map and the import wizards. They still use legacy markup and CSS, with tokens, accessible dialogs and AA colors applied underneath. |
| P5 | Mostly done | axe-core (WCAG 2.0/2.1 A and AA) reports zero violations on all 13 admin routes and on the gallery with dialogs open; `e2e/a11y.spec.js` enforces it. 29 clickable non-semantic elements now have role, tabindex and Enter/Space activation. Not done: retiring `utils/a11yLabels.js` (forms are not all on `Field`), removing legacy CSS, and the `User Management` route (IT roles) was not scanned. |

Later work (same branch): ManageData split into per-tab components and Scope1Form into three sections (AST codemods, `scripts/split-managedata*.mjs` and `scripts/extract-jsx.mjs`, behavior-neutral); 178 dead CSS rules pruned (`scripts/prune-css.mjs`); radius, shadow and font-size values mapped to tokens (`scripts/normalize-css.mjs`; distinct font sizes 51 to 10, radii 27 to 12); 111 raw `<select>` elements now go through `ui/NativeSelect`; 435 static inline styles converted to utility classes (`scripts/inline-to-tailwind.mjs`, inline styles 1,436 to 942). All of these were checked with the pixel-diff harness (`e2e/visual-baseline.spec.js` plus `scripts/compare-baseline.mjs`); the only differences were intended (text-size normalization, and spacing utilities on migrated pages that had been inert).

Section extraction was then applied to the other very large files (Dashboard, UserManagement, BulkImportModal, MethaneIntensity, ColumnMappingWizard, Settings, QADashboard, CarbonIntensity, Scope1ImportWizard, Scope2Form, Scope3Form, AuditTrail) with the automatic mode of `scripts/extract-jsx.mjs` (`--auto 120 --max 450`): candidates that depend on `.map()` callback variables are skipped, module-level locals become props. Pixel diffs were unchanged and `e2e/pages-smoke.spec.js` clicks through every tab and toggle.

Further passes: legacy buttons (35) and text fields (207) now use `Button`/`Input`/`Textarea`, 202 `input-group` wrappers use `Field`, a second inline-style pass brought inline styles from 1,436 to 361, and an AA pass (`scripts/aa-colors.mjs`, `scripts/aa-inline.mjs`) moved text colors to AA-safe shades and darkened fills that carry white text. That pass also fixed real findings in the import wizards, Scope 2/3 forms and the IT User Management page (unnamed close buttons, unfocusable scroll regions, contrast).

Deviations to revisit: Tailwind now also scans `src/pages` and `src/components` (needed for the converted inline styles), so legacy class names that equal Tailwind utilities (`text-right`, `font-bold`, `flex`, `border`, `visible`) now take effect. `--z-overlay/modal/popover` are 10000+ until the legacy 9999 modals are gone. Inline SVG replacement stopped at 8 of 123 (lucide redrew most Feather icons, so an exact match is rare).
