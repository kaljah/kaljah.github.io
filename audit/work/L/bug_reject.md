# BUG-XXX — Maker-checker outcome is invisible to the maker: reject/approve send no notification, the Scope 1 list shows Rejected/Pending rows exactly like Verified ones, and the reject dialog claims the record is "permanently deleted" although it is kept as Rejected

**Status:** Confirmed
**Severity:** Medium
**Category:** UI
**Discovered by:** Agent L (Browser)

## Location
- `new/client/src/pages/ManageData.jsx` reject modal (text "Rejecting will permanently delete the staged record from the pending queue")
- `new/server/routes/emissions.py` `reject_emission` (~L4515-4560: sets `status="Rejected"`, `approved_by=<rejecter>`; logs activity; creates no Notification for `created_by`) and `approve_emission` (same, no maker notification)
- `new/client/src/components/Scope1Form.jsx` "Recent Activity (Scope 1)" table (~L2900-2960): renders a marker only for `status === "Draft"`; no status column although `/api/emissions?scope=1` returns `status`

## Reproduction
1. As audit_user, enter a Scope 1 record through the Scope 1 form (AUDIT-L Plant, 2025-07, Diesel 1000 gal) → id 753, Pending.
2. As audit_admin, Manage Data → Pending Review → Reject #753; the dialog says the record will be permanently deleted; enter reason "Audit L: wrong quantity" → `POST /api/emissions/reject/753` 200 `{"status":"Rejected"}`.
3. As audit_user, reopen Calculations → Scope 1 and check the Recent Activity table and the bell notifications.

## Input
Record 753 (Pending → Rejected), record 754 (Pending → Verified via Approve in the same queue).

## Expected
The dialog describes what actually happens. The maker is notified of the approval/rejection and the reason. The maker's list distinguishes Verified / Pending / Rejected rows (the API already returns `status`).

## Actual
- DB: `emissions.id=753 status='Rejected' approved_by=16` — not deleted; the reason exists only in `activity_log` (id 1354).
- `notifications` created after the approve/reject: 0 rows (the submit created 4 "awaiting your approval" notifications for admins).
- The user's Recent Activity table shows row 753 ("1,000.00 gal … 10.240") with no status, identical to the Verified rows 752/754. `/api/emissions?scope=1` returned 2 Rejected, 2 Pending, 16 Verified rows in the first page, and none of them is marked.

## Evidence
`audit/work/L/w4_maker.mjs`, `w4_approve.mjs approve`, `w4_reject.mjs`, `w4_uview.mjs` output; screenshot `audit/work/L/w4_reject_modal.png`.

## Root Cause
The review workflow notifies only in one direction (maker → checkers). The list UI ignores the `status` field except for Draft, and the modal copy predates the change to soft rejection.

## Impact
Makers cannot tell that a figure they entered was excluded from the inventory, or why, so rejected data is not corrected and resubmitted. Users may also double-enter because Pending rows look final. The dialog misstates the data-retention behaviour to the approver.

## Affected Components
Manage Data Pending Review (approve/reject), Scope 1 form list (Scope 2/3 lists not checked separately), notifications.

## Recommended Fix
Create a Notification for `created_by` on approve/reject including the reason. Add a status badge column (Verified / Pending / Rejected / Draft) to the scope lists. Change the dialog text to "The record will be marked Rejected and excluded from totals".
