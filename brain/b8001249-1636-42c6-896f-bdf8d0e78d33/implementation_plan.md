# Comprehensive Bug Remediation Plan

This implementation plan resolves the bugs discovered by the 10-agent swarm, adhering strictly to all design decisions agreed upon during the grilling interview.

---

## User Review Required

> [!IMPORTANT]
> **Key Decisions Embedded in this Plan:**
> 1. **Session & Logout**: `GET /api/auth/me` will now return HTTP `401 Unauthorized` with `{"error": "Not authenticated"}` when the user is logged out or has no active session. `AuthContext.jsx` in the frontend already handles 401 via its `catch` block.
> 2. **Superuser Regional Scoping**: In [utils.py](file:///c:/Users/samsung/Desktop/H2/new/server/utils.py), only `admin` has global unrestricted data access (`return None`). Superusers will **always** be scoped to their assigned region/location (`user.location`), ensuring they cannot view, modify, or delete emission records outside their region.
> 3. **Delete `viewer` Role Completely**: Remove all leftover references to the `viewer` role from [routes/auth.py](file:///c:/Users/samsung/Desktop/H2/new/server/routes/auth.py), [routes/emissions.py](file:///c:/Users/samsung/Desktop/H2/new/server/routes/emissions.py), [routes/data.py](file:///c:/Users/samsung/Desktop/H2/new/server/routes/data.py), [routes/scope2.py](file:///c:/Users/samsung/Desktop/H2/new/server/routes/scope2.py), [routes/scope3.py](file:///c:/Users/samsung/Desktop/H2/new/server/routes/scope3.py), and [routes/satellite.py](file:///c:/Users/samsung/Desktop/H2/new/server/routes/satellite.py).
> 4. **Input Sanitization & Finite Numbers**: Validate all float/numeric fields in `POST /api/emissions` to reject `Infinity`, `-Infinity`, `NaN`, and invalid negative quantities with clean HTTP `422 Unprocessable Entity` responses.
> 5. **No Aliases / No Redirects**: Canonical internal route names (`/qa-dashboard`, `/audit-trail`, `/api/dashboard/intensity-trend`, etc.) remain unchanged without alias redirects, as requested.

---

## Proposed Changes

### Backend Authentication & Permissions

#### [MODIFY] [auth.py](file:///c:/Users/samsung/Desktop/H2/new/server/routes/auth.py)
- In `GET /api/auth/me`: If `not user_id` or `not user`, return `jsonify({"error": "Not authenticated", "authenticated": False, "user": None}), 401`.
- Clean up any references to `"viewer"` in role checks.
- Add `POST /users` handler with `@it_admin_required` that delegates to `register()` or returns `403` for non-IT users, preventing `405 Method Not Allowed`.

#### [MODIFY] [utils.py](file:///c:/Users/samsung/Desktop/H2/new/server/utils.py)
- In `get_allowed_facility_ids(user)`:
  - Remove the branch that allowed `superuser` to be unrestricted if `location` is in `UNRESTRICTED_LOCATIONS`.
  - Only `user.role == "admin"` receives `return None` (unrestricted).
  - All `superuser` and `user` accounts are strictly scoped to their assigned location/region.

---

### Backend Calculations & Data Protection

#### [MODIFY] [emissions.py](file:///c:/Users/samsung/Desktop/H2/new/server/routes/emissions.py)
- In `POST /api/emissions` (`add_emission`):
  - Add numeric validation for `quantity`: reject non-finite values (`math.isinf`, `math.isnan`) and negative values with HTTP `422`.
  - Clean up any `"viewer"` role checks.
- In `DELETE /api/emissions/<id>` (`delete_emission`):
  - Ensure superusers can only delete records within their assigned region/facilities (`record.facility_id in allowed_fids`).

#### [MODIFY] [scope2.py](file:///c:/Users/samsung/Desktop/H2/new/server/routes/scope2.py) & [scope3.py](file:///c:/Users/samsung/Desktop/H2/new/server/routes/scope3.py)
- Remove `"viewer"` from role checks.
- Validate finite numeric inputs on energy and activity amounts.

#### [MODIFY] [satellite.py](file:///c:/Users/samsung/Desktop/H2/new/server/routes/satellite.py) & [data.py](file:///c:/Users/samsung/Desktop/H2/new/server/routes/data.py)
- Remove `"viewer"` role checks.

---

### Test Suite & Swarm Verification

#### [MODIFY] [test_results/bug_swarm/api_tester_base.py](file:///c:/Users/samsung/Desktop/H2/new/test_results/bug_swarm/api_tester_base.py)
- Update test scripts and expectations to verify all 47 fixed behaviors.
- Re-run the bug verification swarm to confirm all fixes pass cleanly.

---

## Verification Plan

### Automated Tests
1. **Pytest Security & API Suite**:
   ```bash
   cd new/server
   python -m pytest tests/test_audit_remediation.py -v
   ```
2. **Re-run the Bug Verification Swarm**:
   - Run `agent_03_admin_api.py` -> verify 0 critical bugs, /auth/me returns 401 post-logout.
   - Run `agent_04_superuser_api.py` -> verify superuser cannot delete out-of-region records.
   - Run `agent_05_user_api.py` -> verify finite float validation on extreme/inf values.
   - Run `agent_06_itadmin_api.py` -> verify clean RBAC responses.
   - Run `agent_12_compiler.py` -> generate updated verification report.

### Manual / Browser Verification
- Open `http://localhost:5173/login`, log in with `test_admin@ghg-test.com`, verify `/qa-dashboard` and `/audit-trail` render with data.
