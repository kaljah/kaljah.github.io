# Questions for Sonatrach IT

The GHG accounting platform will run on Sonatrach servers, operated by Sonatrach IT. The answers below decide how we package it, so we would like them in the first week. Short answers are fine; "not decided yet" is a valid answer, and we will say which of our defaults applies.

Please return the answers in this file or as a reply, keeping the question numbers.

## 1. Servers and runtime
| # | Question | Why we ask | Our default if unanswered |
|---|----------|-----------|---------------------------|
| 1.1 | Which operating system and version will the servers run (for example RHEL 8/9, Ubuntu LTS, Windows Server)? | Decides the package format. | Linux containers |
| 1.2 | Which container runtime is allowed: Docker, Podman, Kubernetes/OpenShift, none? | We ship container images and a compose file. | Docker Compose |
| 1.3 | If containers are not allowed, can we install Python 3.11, nginx and PostgreSQL directly on the host? | Needs a separate install guide. | Not built unless needed |
| 1.4 | How many servers: one all-in-one, or separate application and database servers? Is there a test environment that matches production? | Sizing and the install rehearsal. | One server plus one test server |
| 1.5 | CPU, memory and disk available per server? | We size the database and worker count. | 4 CPU, 16 GB, 200 GB |
| 1.6 | Is there a container image registry inside Sonatrach for our images? | How images reach the servers. | Images delivered as an archive file |

## 2. Database
| # | Question | Why we ask | Default |
|---|----------|-----------|---------|
| 2.1 | Will Sonatrach provide a PostgreSQL service (which version), or should we bundle PostgreSQL 15 in the package? | The application requires PostgreSQL in production. | Bundled PostgreSQL 15 |
| 2.2 | If provided: who creates the database and user, and can the user create tables (the application runs schema migrations on upgrade)? | Upgrade procedure. | Application user owns its own database |
| 2.3 | Is there a Redis service, or should we bundle one? | Used for login rate limits and shared caches. | Bundled Redis |

## 3. Network and certificates
| # | Question | Why we ask | Default |
|---|----------|-----------|---------|
| 3.1 | Will the servers have any outbound internet access? Through a proxy? | The package must run with none; some optional features (satellite data, map tiles) need it. | No internet; those features off |
| 3.2 | What hostname will users open (for example `ghg.sonatrach.dz`)? Is it reachable from every site that will use it? | Sets allowed origins and the certificate name. | |
| 3.3 | How do we get a TLS certificate: from your internal certificate authority, or do you install it yourselves? In which format (PEM, PFX)? | HTTPS is required. | You mount certificate and key files |
| 3.4 | Is there a load balancer or reverse proxy in front? Does it terminate TLS? Which header carries the client address? | Correct client addresses in logs and rate limits. | nginx in our package terminates TLS |
| 3.5 | Do you restrict which ports and protocols the servers may use? | Firewall requests. | 443 in, nothing out |

## 4. Sign-in
| # | Question | Why we ask | Default |
|---|----------|-----------|---------|
| 4.1 | Which identity system do staff use: Microsoft Entra ID (Azure AD), on-premise Active Directory with ADFS, plain LDAP, something else? | Decides single sign-on. | OpenID Connect |
| 4.2 | Does it support OpenID Connect or SAML 2.0? Who registers our application with it, and what do you need from us? | Setup steps. | |
| 4.3 | Which directory groups should map to application roles? Roles are `user` (one facility), `superuser` (one facility, approves), `admin` (all facilities, approvals), `it_admin` (accounts only, no data). | Role mapping table. | Mapping table edited by an admin |
| 4.4 | Is two-factor sign-in mandatory for local (non-directory) accounts? Which method: authenticator app, hardware token? | Fallback accounts. | Authenticator app, mandatory for admin and IT |
| 4.5 | Idle session timeout required by policy? Absolute session length? | Currently 8 hours absolute. | 30 minutes idle, 8 hours absolute |
| 4.6 | Password policy required for local accounts (length, expiry, history)? | Align the rules. | Current rules kept |

## 5. Email
| # | Question | Why we ask | Default |
|---|----------|-----------|---------|
| 5.1 | Is there an SMTP relay we can use (host, port, authentication, sender address)? | Password reset and notification emails. | Email off; in-app notifications only |

## 6. Operations
| # | Question | Why we ask | Default |
|---|----------|-----------|---------|
| 6.1 | Which monitoring stack do you use (Zabbix, Nagios, Prometheus, other)? | Health endpoint and log format. | `/api/health` plus JSON logs |
| 6.2 | Where do logs go (files, syslog, a central log system)? Retention required? | Log shipping format. | Container stdout |
| 6.3 | Backup: where can backups be stored (network share, backup system)? Required schedule, retention and recovery time and point objectives? | Backup service settings. | Daily, 30 days, to a mounted volume |
| 6.4 | Do you require point-in-time recovery for the database? | Needs WAL archiving. | Yes |
| 6.5 | How do you apply software updates to production: change board, maintenance windows, who runs them? | Upgrade procedure and runbooks. | |
| 6.6 | Do you scan images and dependencies before installing (which tool, which report format)? | We provide an SBOM and audit results. | CycloneDX SBOM |
| 6.7 | Can our support staff reach the production system? How (VPN, jump host, never)? | Vendor access policy. | No access unless you create a time-limited account |

## 7. Scale
| # | Question | Why we ask | Default |
|---|----------|-----------|---------|
| 7.1 | How many facilities will report in total, and in each wave? | Load testing and sizing. | 500 |
| 7.2 | How many named users, and how many at the same time at the busiest hour? | Same. | |
| 7.3 | How many emission records per year do you expect (rows entered or uploaded)? | Same. | 5 million in total |
| 7.4 | Are bulk uploads of tens or hundreds of thousands of rows expected, and how often? | Upload limits. | Up to 100,000 rows per file tested |

## 8. Languages and devices
| # | Question | Why we ask | Default |
|---|----------|-----------|---------|
| 8.1 | Which browsers and versions must be supported? | Test matrix. | Current Chrome, Edge, Firefox |
| 8.2 | Will anyone use phones or tablets in the field? | Layout testing. | Desktop first, phone usable |
| 8.3 | Any requirement for Arabic (right-to-left) in addition to French and English? | Scope of translation work. | Not planned |
