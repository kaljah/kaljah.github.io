# Data Model: Batch Approve/Reject

This feature does not introduce any new data models. It operates on the existing emission records:

- `Emission` (Scope 1)
- `Scope2Emission`
- `Scope3Emission`

The only state transition involved is changing the `status` field of these records from `"Pending"` to `"Verified"` (on approve) or deleting them (on reject).
