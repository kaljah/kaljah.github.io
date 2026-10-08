# Sonatrach production readiness plan

Goal: run the platform as Sonatrach's GHG system of record, on Sonatrach servers, for the whole group, within 3-6 months.

"100% ready" here means every gate in **Definition of ready** is met and signed by the named owner. No system is risk-free; the gates are what turns "we think it works" into "Sonatrach has checked that it works".

## Decisions recorded (2026-10-08)
| Topic | Decision |
|-------|----------|
| Hosting | Sonatrach on-premise. Sonatrach IT operates it; we provide updates and support. |
| Sign-in | Not decided. Build for corporate SSO, keep local accounts with MFA as fallback (see C). |
| Frameworks | Algerian regulator, OGMP 2.0, corporate GHG Protocol / ISO 14064-1 inventory, API Compendium 2021 methods. |
| Methodology sign-off | Sonatrach HSE team. |
| Languages | English and French. |
| Rollout | Whole group, in waves, first cycle run in parallel with the current method. |
| Data | Start from empty (no historical import). |
| Integrations | None: manual entry and CSV/Excel upload. |
| Security approval | Sonatrach security team tests and approves. |
| Team | Small team, 3-6 months. |

## Starting point (verified 2026-10-08)
- Backend suite: 2,558 passed, 1 skipped. CI (build/test/deploy and the 21-test e2e smoke tier) green on `40ee323`.
- Production config fails closed (secret, PostgreSQL, CORS, Redis).
- Open: the 10 expert questions in `docs/validation/HUMAN_REVIEW_REQUIRED.md` (none signed off); no deployment package (the Dockerfile was removed in `9ac7e65`); no SSO or MFA; `/api/auth/login` and `/forgot-password` are CSRF-exempt; UI is English-only; frontend defaults point at GitHub Pages and `ghg-accounting.onrender.com`.

## Definition of ready (go-live gates)
| # | Gate | Owner |
|---|------|-------|
| G1 | HR-01 to HR-10 answered in writing; code matches the answers | Sonatrach HSE |
| G2 | Each framework (Algerian regulator, OGMP 2.0, ISO 14064-1) has a report the HSE team accepts as submittable | Sonatrach HSE |
| G3 | Runs from an installable package on Sonatrach servers with no internet access | Sonatrach IT |
| G4 | Backup and restore drill passed on Sonatrach infrastructure (time to restore recorded) | Sonatrach IT |
| G5 | Security test passed, all high/critical findings fixed and retested | Sonatrach security |
| G6 | Sign-in method approved by Sonatrach IT (SSO or local + MFA) | Sonatrach IT |
| G7 | French UI, exports and templates reviewed by HSE users | Sonatrach HSE |
| G8 | Load test at whole-group size passed | Us + Sonatrach IT |
| G9 | Parallel run of each wave reconciles with the current method within agreed tolerance, differences explained | Sonatrach HSE |
| G10 | Runbooks, training and support process accepted | Sonatrach IT |

## Workstreams

### A. Methodology and regulatory sign-off (owner: methodology lead + Sonatrach HSE)
| # | Task | Done when |
|---|------|-----------|
| A1 | Get the official Algerian reporting requirement (text, template, GWP set, deadlines) and the OGMP 2.0 reporting template Sonatrach submits. | Documents in hand |
| A2 | Turn HR-01 to HR-10 into a one-page answer sheet per item: current code behaviour, the options, our recommendation. HSE answers in writing. | All 10 answered |
| A3 | Define the organisational boundary for the group: operational vs equity control, how joint ventures and equity shares are consolidated. | Written rule; app reproduces it on a test JV |
| A4 | Trace at least 3 reference cases per calculation family to published API Compendium 2021 worked examples (HR-10), so validation is not circular. | Cases cite page/exhibit; tests pass |
| A5 | Plausibility bounds for custom factors, agreed with HSE (HR-06). | Out-of-range factors need a justification and admin approval |
| A6 | One report output per framework (regulator, OGMP 2.0, ISO 14064-1), each using the GWP set that framework requires. | HSE accepts a sample of each (G2) |
| A7 | Base year: with no historical import, decide whether the first full year in the app becomes the base year or HSE enters base-year totals. | Decision recorded; dashboards handle it |

### B. On-premise package and operations (owner: backend/infra)
| # | Task | Done when |
|---|------|-----------|
| B1 | Recover the Dockerfile from history (`git show 9ac7e65^:Dockerfile`), fix the duplicate `FROM` stage noted in `08-production-readiness.md`, and add a compose file: PostgreSQL, Redis, gunicorn, nginx. | `docker compose up` gives a working app on a clean machine |
| B2 | Serve the SPA and API from the **same origin** behind nginx. Remove the GitHub Pages and onrender defaults; set `CORS_STRICT=true`. | No cross-origin requests; app works with only the Sonatrach hostname |
| B3 | Offline install: vendor Python wheels and npm build output, ship images as a tarball, no CDN or external font calls. Make internet features (Copernicus/Sentinel-5P) optional and off by default. | Installs and runs with outbound network blocked |
| B4 | TLS with Sonatrach certificates; config reference listing every environment variable. | Install guide followed by Sonatrach IT without our help |
| B5 | Backups: scheduled `scripts/backup.py`, PostgreSQL point-in-time recovery, retention policy. Restore drill on their hardware (HR-08). | G4 |
| B6 | Upgrade procedure: versioned release bundles, Alembic migration on upgrade, rollback steps. | Upgrade from release N to N+1 rehearsed with data |
| B7 | Logs and health checks that plug into Sonatrach monitoring (health endpoint, log shipping format). | Their monitoring sees the app |

### C. Identity and security (owner: backend/security)
| # | Task | Done when |
|---|------|-----------|
| C1 | Week 1: ask Sonatrach IT for their sign-in standard (AD/ADFS, Azure AD/Entra ID, LDAP) and their security requirements checklist. | Answers in hand |
| C2 | Add OIDC sign-in behind a setting (Entra ID and ADFS both support it); add SAML or LDAP only if C1 requires it. Map directory groups to app roles. | Test sign-in against their test directory |
| C3 | Local accounts (break-glass and until SSO is approved): authenticator-app MFA, per-account lockout after failed attempts. | Tests cover both |
| C4 | Re-enable CSRF on `/login` and `/forgot-password` once B2 makes it same-origin (closes HR-07). | Security tests updated and green |
| C5 | Vendor access: on-premise, the `it_manager` role gets no data access by default; support access only through accounts Sonatrach creates and can disable. | Documented and enforced |
| C6 | Security pack for Sonatrach: architecture and data-flow diagram, threat model, SBOM, `pip-audit`/`npm audit` results, role matrix. | Delivered before their test |
| C7 | Support the Sonatrach security test, fix findings, retest. | G5 |

### D. French (owner: frontend)
| # | Task | Done when |
|---|------|-----------|
| D1 | Add i18next; extract strings page by page, starting with data entry, review and reports. | No hard-coded English in translated pages |
| D2 | French translations, technical terms reviewed by HSE users (glossary first). | G7 |
| D3 | French number formats: decimal comma in display **and** in CSV/Excel import (a misread `1,5` is a 1000x error). | Import tests with French-formatted files pass |
| D4 | French CSV/Excel templates, PDF and Excel exports. | HSE accepts samples |

### E. Group scale (owner: backend)
| # | Task | Done when |
|---|------|-----------|
| E1 | Get the group size: number of facilities, users, records per year. | Numbers in hand |
| E2 | Organisation hierarchy: group > division > region > facility. Today `superuser` is limited to one facility; decide with HSE whether division leads need a multi-facility scope, and implement it without weakening segregation of duties. | RBAC tests cover the new scope |
| E3 | Group-level consolidation reports with JV equity shares (follows A3). | Totals reconcile across levels |
| E4 | Load test at whole-group size with several gunicorn workers and Redis. | G8 |

### F. Quality and acceptance (owner: whole team + HSE)
| # | Task | Done when |
|---|------|-----------|
| F1 | Run the full 124-test e2e matrix nightly in CI, not manual-only. | Scheduled run green |
| F2 | User acceptance scripts per role (user, superuser, admin, IT admin), run by HSE users in French. | Signed UAT per wave |
| F3 | Parallel run per wave: same period entered in the app and in the current method; reconcile per facility and gas. | G9 |
| F4 | Bug triage with severities; calculation bugs block the wave. | Process agreed |

### G. Handover and support (owner: whole team)
| # | Task | Done when |
|---|------|-----------|
| G-1 | Runbooks: install, upgrade, backup/restore, incident, user administration. | Sonatrach IT accepts |
| G-2 | Training: admins (Sonatrach IT), HSE reviewers, data-entry users, in French. | Sessions held per wave |
| G-3 | Support contract: response times by severity, channel, release cadence. | Signed |

## Timeline (24 weeks)
| Weeks | Phase | Content |
|-------|-------|---------|
| 1-2 | Kick-off | A1, C1, E1; HSE gets the HR answer sheet (A2); Sonatrach IT gets the infrastructure requirements. |
| 2-10 | Build | B1-B4, C2-C5, D1-D3, E2, A4-A6 in parallel. |
| 8-12 | Approve | Install on Sonatrach test servers (G3), backup drill (G4), security test and fixes (G5), HSE sign-off (G1, G2), load test (G8). |
| 12-16 | Wave 1 | 2-3 facilities, parallel run of one month or quarter, UAT (F2, F3). |
| 16-20 | Wave 2 | One division. |
| 20-24 | Wave 3 | Rest of the group; parallel run continues until the first full reporting period closes. |

Suggested split for a small team: one person on B and C, one on D and the frontend parts of E/F, one methodology lead running A with HSE.

## Main risks
| Risk | Mitigation |
|------|------------|
| HSE answers to HR items change calculations late | Send the answer sheet in week 1; nothing goes to Wave 1 before G1 |
| Sonatrach security approval takes longer than the build | Get their checklist in week 1; deliver C6 before their test window |
| SSO decision slips | Local accounts with MFA (C3) are a valid fallback for Wave 1 |
| Whole group in 6 months | Waves; each wave has its own gate; a failed gate delays only the next wave |
| No historical data | Year-over-year and SBTi views stay empty until the base year is set (A7) |
| French decimal format in uploads | D3 before any French user uploads data |

## Questions for Sonatrach (week 1)
1. IT: server OS, container runtime allowed (Docker/Podman/Kubernetes), PostgreSQL provided or ours, internet access from servers, certificate process, monitoring stack.
2. IT: sign-in standard and directory groups for roles.
3. Security: test scope, timeline, and acceptance criteria.
4. HSE: official regulator template and GWP set; OGMP 2.0 template; boundary approach for JVs; group size.
