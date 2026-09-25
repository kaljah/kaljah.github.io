# Region Dropdown Bug — Root Cause & Fix Plan

## What's Actually Broken

The core problem is a **3-way data contract mismatch**. A facility can be identified by three different fields depending on which layer of code is running:

| Layer | How it resolves a region identifier |
|-------|--------------------------------------|
| **Server `utils.py`** (`get_allowed_facility_ids`) | `facility.region` OR `facility.location` OR `facility.name` — all three |
| **Server `facilities.py`** (`get_all_regions`) | `facility.region` falling back to `facility.name` — two of three |
| **Frontend dropdowns** (`ManageData.jsx`, `MethaneExplorer.jsx`, `userDefaults.js`) | `facility.region` OR `facility.location` — **missing `f.name`** |

When a region is uploaded via the bulk uploader, `_process_row_facilities` in `background_processor.py` maps **"Region Name" → `facility.name`** and leaves `facility.region = NULL`. The server resolves it correctly at query time (utils.py line 48–51). But the frontend never reads `f.name` when building filter dropdowns, so the newly uploaded regions are invisible in every dropdown.

---

## Affected Files (the same bug in 3 places)

### 1. [`ManageData.jsx` line 742](file:///c:/Users/samsung/Desktop/H2/new/client/src/pages/ManageData.jsx#L742)
```js
// BROKEN — misses f.name
const regions = [...new Set(data.flatMap(f => [f.region, f.location]).filter(Boolean))].sort();

// FIXED
const regions = [...new Set(data.flatMap(f => [f.region || f.name, f.location]).filter(Boolean))].sort();
```

### 2. [`MethaneExplorer.jsx` line 177](file:///c:/Users/samsung/Desktop/H2/new/client/src/pages/MethaneExplorer.jsx#L177)
```js
// BROKEN
...new Set(fetchedFacilities.flatMap((f) => [f.region, f.location]).filter(Boolean))

// FIXED
...new Set(fetchedFacilities.flatMap((f) => [f.region || f.name, f.location]).filter(Boolean))
```
Additionally, line 239 has a **separate bug**: the region *filter logic* also only checks `f.region`, so even if the dropdown is fixed, clicking a region in MethaneExplorer would show zero results for uploaded regions:
```js
// BROKEN — filters only on f.region, never matches facilities where region=NULL
(f.region && f.region === filters.region)

// FIXED — also match by f.name when region is null
(filters.region === "all" || f.region === filters.region || (!f.region && f.name === filters.region))
```

### 3. [`userDefaults.js` line 126](file:///c:/Users/samsung/Desktop/H2/new/client/src/utils/userDefaults.js#L126)
```js
// BROKEN — auto-defaulting misses the name fallback
const uniqueRegions = [...new Set(facilities.map(f => f.region || f.location).filter(Boolean))];

// FIXED
const uniqueRegions = [...new Set(facilities.map(f => f.region || f.name).filter(Boolean))];
```
> [!NOTE]
> `userDefaults.js` is used to auto-populate the logged-in user's default region when they only have access to one region. Without this fix, users whose only accessible region was uploaded via CSV would get no auto-fill.

---

## Why the One-Line Fix Isn't Enough

> [!IMPORTANT]
> Fixing only `ManageData.jsx` line 742 would make the **filter bar** show the region names, but:
> - **MethaneExplorer** still wouldn't filter correctly (line 239 bug)
> - **userDefaults** auto-fill still wouldn't work for restricted users
> - The **underlying data contract** remains undocumented, so the next developer building a new page will make the same mistake

---

## The Proper Fix: Add a Server-Side Computed Field

The most robust long-term fix is to have the `/facilities` API endpoint return a computed `region_identifier` field that already applies the fallback, so every client just reads one consistent field:

### [MODIFY] [`facilities.py`](file:///c:/Users/samsung/Desktop/H2/new/server/routes/facilities.py)
Add `"region_identifier": f.region or f.name` to the JSON response for each facility (alongside existing fields, non-breaking).

### [MODIFY] [`ManageData.jsx`](file:///c:/Users/samsung/Desktop/H2/new/client/src/pages/ManageData.jsx)
Use `f.region_identifier` instead of `f.region || f.name`.

### [MODIFY] [`MethaneExplorer.jsx`](file:///c:/Users/samsung/Desktop\H2/new/client/src/pages/MethaneExplorer.jsx)
Use `f.region_identifier` for both dropdown building (line 177) and filter matching (line 239).

### [MODIFY] [`userDefaults.js`](file:///c:/Users/samsung/Desktop/H2/new/client/src/utils/userDefaults.js)
Use `f.region_identifier` (line 126).

---

## Verification Plan

1. Re-upload `regions_upload.csv` via the bulk uploader.
2. Confirm all 39 region names (ADR, REB, HBK...) appear in:
   - ManageData filter bar dropdown
   - Production/Emissions/Sources "Select Region" dropdowns
   - MethaneExplorer region filter
3. Select a region in MethaneExplorer — confirm matching facilities appear on the map.
4. Log in as a restricted user assigned to one of the uploaded regions — confirm their default region auto-fills.

---

## Open Questions

- **Prefer server-side computed field vs. 3 frontend patches?** The server-side approach is cleaner long-term. The frontend-only patches are faster to ship and non-breaking. Your call.
