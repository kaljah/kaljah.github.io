# Bug Remediation Task Tracker

## Implementation Steps
- [x] Task 1: Fix Session, /auth/me 401 response, and /auth/users POST route in auth.py
- [x] Task 2: Scope superuser strictly to region in utils.py (only admin is global unrestricted)
- [x] Task 3: Validate numeric inputs (finite, non-negative) and enforce regional deletion in emissions.py
- [x] Task 4: Clean up all viewer role references across scope2, scope3, satellite, data routes
- [x] Task 5: Run automated verification tests (all API swarm agents 0 bugs, pytest 52/52 pass)
- [x] Task 6: Run graphify update . to keep knowledge graph current
