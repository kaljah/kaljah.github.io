# Custom Factors Enhancement & Reference Data Page

## Overview
Enhance the custom emission factors functionality and create a comprehensive reference data page showing all available emission factors.

## Changes Required

### 1. Rename & Improve Navigation
- **files**: All HTML pages
- Rename "Settings" to "Custom Emission Factors"
- Add "Custom Emission Factors" link to top navigation on all pages (dashboard, emissions-calculator, reports, emission-selection)
- Add "Reference Data" link to all page navigations

### 2. Enhance Custom Factors Form
- **file**: `settings.html`
- Add Higher Heating Value (HHV) field
- Add Unit selection dropdown
- Add Usage/Process Type multi-select (combustion, flaring, venting, etc.)
- Improve form layout and validation
- Update database schema if needed

### 3. Create Reference Data Page
- **new file**: `reference-data.html`
- Display all emission factors from `emission-factors.js` in a searchable table
- Columns: Name, Type, HHV, CO2, CH4, N2O, Unit, Usage
- Add search/filter functionality
- Group by fuel type (Gases, Liquids, Solids, Equipment)
- Modern, responsive table design

### 4. Update Backend (if needed)
- **file**: `server.js`
- Update custom_factors table schema to include HHV and usage fields
- Ensure backward compatibility

## Implementation Order
1. Add action button CSS (fix earlier error)
2. Rename Settings to Custom Emission Factors across all pages
3. Add navigation links to all pages
4. Enhance custom factors form with HHV
5. Create reference-data.html with emission factors table
6. Test all functionality
