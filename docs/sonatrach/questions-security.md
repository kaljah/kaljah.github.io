# Questions for Sonatrach security

The platform will be tested and approved by the Sonatrach security team before go-live. To build the test environment and the documents you need ahead of time, we ask for the answers below in the first week.

## 1. Test scope and method
| # | Question |
|---|----------|
| 1.1 | What will be tested: web application, API, infrastructure and operating system, containers, database, all of these? |
| 1.2 | Which method: black box, grey box with test accounts, or code review as well? Do you want source code access? |
| 1.3 | Which tools or standard do you test against (OWASP ASVS level, OWASP Top 10, an internal checklist)? Can you send the checklist? |
| 1.4 | Will you test a copy installed on your test servers, or an environment we host? |
| 1.5 | How many test accounts per role do you need? Roles: `user`, `superuser`, `admin`, `it_admin`, `it_manager` (vendor). |

## 2. Timeline
| # | Question |
|---|----------|
| 2.1 | When does the test window open and how long does it last? |
| 2.2 | How long do you need between receiving the package and starting? |
| 2.3 | How are findings delivered (report format, severity scale), and who is our contact? |
| 2.4 | How long do we have to fix findings, and do you retest each fix or batch them? |

## 3. Acceptance criteria
| # | Question |
|---|----------|
| 3.1 | What counts as a pass: no high or critical findings open, no medium open, other? |
| 3.2 | Which severity scale do you use (CVSS, internal)? |
| 3.3 | Are known risks accepted in writing (risk acceptance form), and who signs? |
| 3.4 | Is the approval per release, or does it cover later minor releases? What change triggers a retest? |

## 4. Documents you need from us
Tell us which of these you require, in which language and format:
- Architecture and data-flow diagram
- Threat model
- Role and permission matrix (generated from the code)
- List of every configuration setting and secret, and how each is protected
- Dependency audit results and a software bill of materials (CycloneDX)
- Description of audit logging and the tamper-evident audit chain
- Data classification and retention description
- Backup and recovery description
- Results of our own pre-test security sweep

## 5. Policy requirements
| # | Question |
|---|----------|
| 5.1 | Password, lockout and two-factor requirements for accounts that are not in the directory. |
| 5.2 | Session timeout requirements (idle and absolute). |
| 5.3 | TLS versions, cipher suites and certificate requirements. |
| 5.4 | Required security headers and cookie settings beyond the usual (HSTS, CSP, SameSite). |
| 5.5 | Logging requirements: which events, retention, format, forwarding to your SIEM. |
| 5.6 | Encryption at rest: database, backups, disks. Who manages keys? |
| 5.7 | Vendor remote access: is it permitted at all, and under which conditions (time limit, approval, session recording)? |
| 5.8 | Rules for file uploads (size, type scanning, antivirus). The platform accepts CSV and Excel files. |
| 5.9 | Rules about personal data stored (names and email addresses of staff) and where it may be stored. |
| 5.10 | Incident reporting: who do we notify, and how fast, if we find a vulnerability in a delivered release? |

## 6. For awareness (already in the platform)
The list lets you confirm these meet your policy:
- Production refuses to start without a real secret key, PostgreSQL, a restricted list of allowed origins and a shared rate-limit store.
- Role-based access with segregation of duties; IT accounts have no access to emission data.
- CSRF tokens on all state-changing requests except sign-in and password reset (`routes/auth.py:360` and `:439`). This closes once the platform is served from one origin (planned task T4.1).
- Login rate limiting. Account lockout and two-factor sign-in are planned (T4.2, T4.3).
- Tamper-evident audit log of data changes.
