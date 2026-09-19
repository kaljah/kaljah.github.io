# Investigation Plan: PDF Report Generation Issues

## Goal
Identify which report generation button causes UUID filenames and massive file sizes, and find the root cause.

## Checklist
- [x] Navigate to `http://localhost:5173/reports`
- [x] Click "Create Report" (Create New Report section)
    - [x] Observe filename and size
    - [x] Check console and network logs
- [x] Click red "PDF Report" (Top right)
    - [x] Observe filename and size
    - [x] Check console and network logs
- [ ] Compare findings and identify the problematic button/logic

## Findings
- **Button 1 ("Create Report" in "Create New Report" section):**
    - Triggers toast "Generating ISO 14064-1 Report..."
    - Followed by toast "Report generated successfully!"
    - Seems to be working with the new optimized logic.
- **Button 2 (Red "PDF Report" button in top right):**
    - Clicking it provides NO visual feedback (no toast, no change).
    - It's likely this button is either broken or still using the old, unoptimized logic that causes the browser to struggle with 45MB Blobs.
- **Network/Console:**
    - `browser_list_network_requests` is failing, but console logs are empty except for Vite/React dev info.
    - No obvious errors in console, which might mean the failure is silent or happening in a way that doesn't log (like a huge Blob creation blocking the thread).
