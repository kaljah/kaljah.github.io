# Modern "Glassy" PDF Report Overhaul

## Goal
Create a visually stunning, "glassy", ISO 14064-1 & API Compliant PDF report.
The report must include charts, exhaustive data tables, and comprehensive explanatory text.

## User Requirements
- Aesthetics: "Out of this world", "Glassy", "Classy", "Modern".
- Content: Data from ALL tools (Scope 1, 2, 3, Intensity).
- Standards: ISO 14064-1, GHG Protocol, API Reporting.
- Format: PDF with charts and modern tables.

## Design Aesthetics (Sonatrach "Glassy" Theme)
- **Palette**:
    - **Primary Base**: Deep Slate/Charcoal (simulating professional dark mode) - `[15, 23, 42]`
    - **Brand Accent**: **Sonatrach Orange** - `[255, 107, 0]` (Vibrant Orange)
    - **Secondary**: Cool Greys and White
- **"Glassy" Effect**:
    - Content containers will be semi-transparent white (`rgba(255, 255, 255, 0.9)`) on top of the dark rich background (or vice versa for specific sections).
    - Subtle drop shadows for depth.
- **Branding**:
    - Sonatrach logo prominently displayed on the cover.
    - Orange gradients for charts and headers.

## API Reporting Requirements (2023 Guidance Analysis)
Based on API 2023/Compendium standards for O&G:
1.  **Explicit Breakdown**: Combustion vs. Flaring vs. Venting vs. Fugitives (already in our data).
2.  **Methane Focus**: Dedicated section for CH4 emissions (Mass and CO2e) is mandatory.
3.  **Intensity Metrics**: GHG Intensity (Total CO2e / Hydrocarbon Production).
4.  **Scope 2**: Location-based reporting.

## Structure Refined

1.  **Cover Page**
    - **Logo**: Sonatrach Logo (top center).
    - **Title**: Large, bold typography.
    - **Background**: Dark premium gradient with abstract geometric shapes (canvas drawn).
    - **KPI Cards**: Three "Glass" cards at bottom: Total Emissions, Methane %, Intensity.

2.  **Executive Summary (API & ISO Compliant)**
    - Text blocks complying with ISO 14064-1.
    - Table: Global Warming Potentials (AR5: CO2=1, CH4=28, N2O=265).

3.  **Visual Analytics (The "Page of Charts")**
    - **Top**: Source Breakdown Bar Chart (Orange/Grey theme).
    - **Middle Left**: Gas Composition Pie (High focus on CH4).
    - **Middle Right**: Scope 1 vs Scope 2 Doughnut.

4.  **Detailed API Data Tables**
    - Table 1: Scope 1 by Source Category (Stationary, Flaring, Venting...).
    - Table 2: Greenhouse Gas Speciation (CO2, CH4, N2O mass).

## Technical Implementation Steps
1.  **Data Gathering**: New `fetchAllData(year)` function to aggregate API/Scope1/Scope2 data.
2.  **Chart Generation**: Use `Chart.js` to render charts to hidden canvas, export as Base64 images.
3.  **PDF Construction**: Use `jsPDF` for layout, `autotable` for data, and `addImage` for the charts.
4.  **Styling**: Apply Sonatrach Orange `[255, 107, 0]` for all accents, headers, and chart highlights.

## Technical Implementation

### File: `public/modern-report.js`
- **Dependency**: Requires `Chart.js` (already linked in index) and `jspdf`/`jspdf-autotable`.
- **New Helper**: `createChartImage(type, data, options)`
    - Creates a hidden `<canvas>` in the DOM.
    - Renders a Chart.js instance.
    - Converts to Base64 Image (`toDataURL`).
    - Cleans up canvas.
- **Data Fetching**:
    - Function will need to fetch `/api/intensity-stats` and `/api/calc/scope2`, `/api/calc/scope3` to get the full picture, as `reportData` passed in is likely just Scope 1/Emissions Log.

### Proposed Changes
1.  **Modify `generateModernPDF` in `modern-report.js`**:
    - Accept `year` and `facilityNames`.
    - **Step 1**: Fetch complementary data (Scope 2, Scope 3, Intensity).
    - **Step 2**: Generate Chart Images.
    - **Step 3**: Construct PDF pages.

## Verification
- User will need to click "Create New Report".
- Verify PDF opens/downloads.
- visual check of "Glassy" aesthetic and Charts.
