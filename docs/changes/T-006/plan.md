# Initial Project Plan — Airline Management System (AMS)

## Document Metadata

| Field | Value |
|---|---|
| **Project** | Airline Management System |
| **Version** | v1.0 (Draft) |
| **Date** | 2026-06-11 |
| **Author** | Project Manager (via OpenUP Iteration 2, T-006) |
| **Phase** | Elaboration → Construction transition |
| **Sponsor** | Airline Operations Director |

---

## 1. Executive Summary

Airline Management System is a cloud-hosted web platform for unified airline operations management. The MVP (v1) covers **Flight Operations**, **Crew Management**, and **Dashboard & Reporting** — three of six feature areas, deferring Maintenance Tracking and Passenger Services to v2. Six P0 use cases define the MVP scope across 5 bounded contexts with a Python/FastAPI + React/TypeScript + PostgreSQL stack.

**Target**: First working prototype by end of Construction Iteration 4 (~12-16 weeks from construction start, assuming a team of 3 developers + 1 QA).

---

## 2. MVP Scope (v1) — 6 P0 Use Cases

| # | UC-ID | Use Case | Story Points (Est.) | Priority | Notes |
|---|---|---|---|---|---|
| 1 | UC-AD-01 | Manage Users and Roles (RBAC) | 8 | **P0** | Foundation — must be first |
| 2 | UC-DR-01 | View Operations Dashboard | 13 | **P0** | Depends on all modules for data aggregation |
| 3 | UC-FO-01 | Create and File Flight Plan | 13 | **P0** | Core flight ops workflow |
| 4 | UC-FO-02 | Track In-Flight Status | 21 | **P0** | SSE real-time pipeline; integration spike needed |
| 5 | UC-CM-01 | Generate Crew Roster | 34 | **P0** | Complex optimization algorithm + UI |
| 6 | UC-CM-04 | Track Duty-Time Compliance | 34 | **P0** | Regulation engine — highest risk, SME-dependent |

**Total MVP estimate: ~126 story points** (using standard Scrum scale)

### Out of Scope (v2 backlog)
| # | Feature | Notes |
|---|---|---|
| 7 | Maintenance Tracking | Deferred — work orders, parts inventory, defects |
| 8 | Passenger Services | Deferred — booking/PNR, check-in, rebooking |
| 9 | Mobile Apps | Deferred — pilot/ground staff apps |
| 10 | Weather Integration | Placeholder only in v1 |
| 11 | Loyalty Program | Deferred |

---

## 3. Technical Architecture Summary (from ADRs)

| Decision | Value | Rationale |
|---|---|---|
| **Backend** | Python 3.12+ / FastAPI | Built-in async, Pydantic validation, OpenAPI gen, best fit for rule-based domain logic |
| **Frontend** | React 18 / TypeScript / Vite | Mature ecosystem; drag-and-drop roster UI support via `@dnd-kit` or similar |
| **Database** | PostgreSQL 15+ | ACID compliance; JSONB for regulation rules, audit snapshots, flexible payloads |
| **Cache/Queue** | Redis 7+ | Real-time pub/sub (SSE), session storage, rate limiting |
| **Real-time** | Server-Sent Events + Redis pub/sub | Simpler than WebSockets; unidirectional push sufficient for MVP dashboard |
| **Deployment** | AWS ECS (Fargate) + RDS PostgreSQL + ElastiCache Redis | Containerized services; managed DB reduces ops burden |
| **Auth** | JWT with refresh token rotation | Scalable for multi-region SaaS; OAuth2/OIDC added later for SSO |
| **Regulation Engine** | Embedded Python module (Pydantic models) | Rapid iteration; versioned rule profiles stored in JSONB; SME-readable constraints |
| **Audit Logging** | Hash-chained append-only PostgreSQL table | Tamper-evident integrity; zero external dependencies |
| **CI/CD** | GitHub Actions → Docker → AWS ECS | Multi-stage builds; lint → test → build → deploy pipeline |

### Bounded Contexts (Domain-Driven Design)
1. **Flight Planning** — Flight, Aerodrome, Aircraft, Route aggregates
2. **Crew Management** — Person, CrewQualification, CrewAssignment, Roster
3. **Regulation** — RegulationProfile (immutable), DutyTimeComplianceResult
4. **Access Control** — User, Role, Permission (RBAC hierarchy)
5. **Audit & Events** — AuditLogEntry (hash chain), Event backbone

---

## 4. Work Items — Construction Phase Plan

### Sprint 0: Foundation (Weeks 1-2)
| ID | Task | Type | Points | Depends On | Notes |
|---|---|---|---|---|---|
| S0-T01 | Project scaffolding (FastAPI + React + PostgreSQL) | Dev | 5 | — | Tech stack bootstrap; CI pipeline setup |
| S0-T02 | Database schema design & migration setup (Alembic) | Dev | 8 | — | Based on domain model from ADR-0002 |
| S0-T03 | Authentication service skeleton (JWT, RBAC model) | Dev | 5 | S0-T01 | Foundation for all authenticated operations |
| S0-T04 | API contract definition (OpenAPI/Swagger spec) | Dev/PM | 8 | — | Critical for frontend/backend parallel work + future GDS adapter interface |
| S0-T05 | Audit logging infrastructure (hash chain module) | Dev | 5 | — | Cross-cutting; write once, use everywhere |

### Sprint 1: Access Control & Flight Ops Core (Weeks 3-5)
| ID | Task | Type | Points | Depends On | Notes |
|---|---|---|---|---|---|
| S1-T01 | RBAC implementation (User/Role/Permission CRUD + middleware) | Dev | 13 | S0-T01, S0-T03 | Covers UC-AD-01 |
| S1-T02 | Flight entity domain model & repository layer | Dev | 8 | S0-T02 | Flight, Aerodrome, Aircraft aggregates |
| S1-T03 | Crew entity domain model & repository layer | Dev | 8 | S0-T02 | Person, CrewQualification, CrewAssignment |
| S1-T04 | Flight plan form (frontend CRUD with validation) | Frontend | 13 | S1-T01, S1-T02 | Core UI for UC-FO-01 |
| S1-T05 | NOTAM stub service (read-only placeholder per vision) | Dev | 5 | — | Deferred to real integration in v2 |

### Sprint 2: Crew Roster & Regulation Engine (Weeks 6-8)
| ID | Task | Type | Points | Depends On | Notes |
|---|---|---|---|---|---|
| S2-T01 | **Regulation engine prototype** — Pydantic rule definitions for EU-OPS duty-time rules | Dev + SME | 21 | S0-T01 | **HIGHEST PRIORITY** — SME must be engaged Week 1. Property-based testing (hypothesis). |
| S2-T02 | Regulation engine test suite (unit + integration) | QA/Dev | 13 | S2-T01 | Budget 30-40% of UC-CM-04 effort here |
| S2-T03 | Crew roster algorithm (greedy assignment with constraint checking) | Dev | 13 | S2-T01, S1-T03 | MVP uses greedy; full optimizer deferred to v2 |
| S2-T04 | Roster editor UI (drag-and-drop with real-time validation) | Frontend | 21 | S1-T01, S2-T03 | Most complex frontend component |

### Sprint 3: In-Flight Status & Dashboard (Weeks 9-11)
| ID | Task | Type | Points | Depends On | Notes |
|---|---|---|---|---|---|
| S3-T01 | SSE streamer service + Redis pub/sub integration | Dev | 8 | S0-T01, S0-T02 | Real-time data pipeline foundation |
| S3-T02 | Flight status update ingestion (synthetic events for MVP) | Dev | 8 | S3-T01 | Adapter interface for real sources later |
| S3-T03 | Dashboard component aggregation layer | Frontend | 13 | S1-T01, S2-T04, S3-T01 | Thin view over pre-computed domain queries |
| S3-T04 | Real-time performance spike (SSE benchmark target <5s) | Dev/Architect | 8 | S3-T01 | R5 verification; ≤5s latency with 500 flights synthetic load |

### Sprint 4: Integration, Polish & Release Prep (Weeks 12-13)
| ID | Task | Type | Points | Depends On | Notes |
|---|---|---|---|---|---|
| S4-T01 | E2E test suite (Playwright) covering all 6 P0 UCs | QA | 13 | All prior sprints | Smoke tests for each use case workflow |
| S4-T02 | Security audit prep (OWASP top 10 checklist) | Dev + Architect | 8 | All prior sprints | R6 mitigation — encryption at rest/in transit |
| S4-T03 | Performance tuning & load testing (≥50 concurrent users) | Dev/QA | 8 | All prior sprints | Verify dashboard <2s render, SSE <5s delivery |
| S4-T04 | Documentation: API reference, runbooks, deployment guide | Dev/PM | 8 | All prior sprints | OpenAPI auto-generated; ops docs manual |

---

## 5. Resource Requirements

### Team Structure (Minimum for MVP)
| Role | Count | Notes |
|---|---|---|
| Backend Developer | 1 | FastAPI, PostgreSQL, regulation engine |
| Frontend Developer | 1 | React/TypeScript, roster editor, dashboard |
| Full-stack / QA | 1 | Cross-cutting work, test automation |
| Project Manager | 0.5 | Stakeholder communication, risk tracking |

**Note**: SME (aviation domain expert) is NOT a full team member — engagement as needed for regulation engine review, scenario validation, and sign-off gates. Budget ~10-15 hours of SME time across construction.

### Infrastructure
| Resource | Cost Estimate (Monthly) | Notes |
|---|---|---|
| AWS ECS Fargate (2 services) | ~$80 | dev + staging environments |
| RDS PostgreSQL (db.t3.small) | ~$50 | dev + staging |
| ElastiCache Redis | ~$30 | dev + staging |
| GitHub Actions | $0 free tier | CI/CD |
| **Total** | **~$160/mo** | Excludes production (not needed until construction end) |

---

## 6. Risk Mitigation Plan

### Active Risks from Inception → Construction Mapping

| Risk | Mitigation Status | Open Items | Owner |
|---|---|---|---|
| **R1 Regulatory compliance** (Critical) | ADR-0003 defines rule engine approach. Sprint 2 begins with prototype. | SME engagement required before Sprint 2 starts. Rule test scenarios must be provided by SME. | PM + Analyst |
| **R2 Scope creep** (Critical) | MVP scope formally cut at 6 P0 UCs. v2 backlog documented. Process discipline: one-for-one swap policy. | Must enforce in sprint planning — no new stories without removing existing ones. | PM |
| **R3 GDS integration** (High) | Adapter interface designed into architecture. Sprint 4 includes OpenAPI spec for eventual GDS connector. | Spike not yet run; API availability unknown. Defer to v2 with adapter stubs now. | Architect |
| **R4 Data model inadequacy** (High) | Domain model created in Elaboration. Event storming workshop recommended before Sprint 1 starts. | SME review of domain model required — schedule within first 2 weeks of construction. | Architect + Analyst |
| **R5 Real-time performance** (Medium) | SSE approach selected. Sprint 3 includes benchmark spike. Target: <5s with 500 flights. | Spike results may trigger architecture change if benchmarks fail. | Dev + Architect |
| **R6 Security & privacy** (High) | Audit logging built in S0. Encryption strategy defined in ADR-0004/0005. | Data retention policy not yet written; security audit prep in S4. | PM + Architect |
| **R7 Stakeholder availability** (Medium) | Executive sponsor identified. Async workshop recordings proposed. | If SME doesn't engage for Sprint 2 rule review, construction is blocked. | PM |
| **R8 Team skill gap** (High) | ADR-0003 includes SME pairing plan. Glossary and decision log to be maintained in docs/. | No SME assigned yet. This is a blocker — must assign before Sprint 2. | PM |

### New Risks Identified During Planning
| # | Risk | Probability | Impact | Mitigation |
|---|---|---|---|---|
| R9 | **Sprint 2 delay** if regulation engine prototype exceeds timebox (21pts) | Medium | High | Greedy fallback algorithm exists in design; can deliver MVP with basic compliance checking |
| R10 | **Roster editor UI complexity** underestimated for single frontend dev | Medium | Medium | Prototype drag-and-drop early in Sprint 1; consider library vs custom build decision by Week 3 |

---

## 7. Milestones & Timeline

```
Week 0:       Construction kickoff, SME engagement confirmed
Week 2:       ✓ Foundation complete (Auth, DB, CI/CD, Audit)
Week 4:       ✓ RBAC + Flight/Crew domain models done
Week 5:       ✓ Flight plan form prototype works
Week 7:       ✓ Regulation engine prototype tested with SME scenarios
Week 8:       ✓ Crew roster algorithm + editor UI integrated
Week 10:      ✓ In-flight status SSE pipeline operational
Week 11:      ✓ Dashboard aggregates all data streams
Week 12:      E2E tests passing, security checklist green
Week 13-14:   Performance tuning, documentation, release candidate
Week 14:      🚀 MVP Release Candidate ready for stakeholder demo
```

**Total duration**: ~14 weeks (Construction phase, sprint-based)
**Post-construction**: Transition phase (stakeholder UAT, production deploy) — estimate 2-3 additional weeks

---

## 8. Dependencies & Prerequisites

| Dependency | Status | Blocked By | Notes |
|---|---|---|---|
| SME engagement for regulation engine | **Not started** | PM action item | MUST be resolved before Sprint 2 starts (Week 6). Blocking path for R1 mitigation. |
| Tech stack decision confirmation | Complete | — | Confirmed by ADR-0001; architect + developer alignment achieved |
| Domain model stakeholder review | Not started | Event storming session scheduled | Required before Sprint 1 coding begins |
| GDS API documentation (for adapter interface) | Unknown | External vendor dependency | Defer to v2; build adapter stubs now |
| Data retention policy document | Not started | Legal/compliance team | R6 mitigation — required before S4-T02 security audit |

---

## 9. Success Criteria for Construction Phase Completion

1. [ ] All 6 P0 use cases implemented and passing E2E tests
2. [ ] Regulation engine passes SME-validated test suite (≥5 EU-OPS rules tested with known inputs/outputs)
3. [ ] SSE real-time performance benchmark: <5s latency with synthetic load of 500 flights
4. [ ] RBAC correctly restricts access across all 6 stakeholder roles
5. [ ] Audit log integrity verifiable via hash chain validation query
6. [ ] Security checklist (OWASP top 10) passed with zero critical/high findings
7. [ ] All documentation delivered (API reference, runbooks, deployment guide)
8. [ ] Stakeholder demo completed with positive feedback from Operations Director

---

## 10. Open Issues

| ID | Issue | Decision Required By | Notes |
|---|---|---|---|
| OI-01 | ORM framework finalization (SQLAlchemy vs. Peewee vs. raw SQL) | Sprint 0 start | Developer recommends SQLAlchemy 2.0+; architect needs to confirm in ADR follow-up |
| OI-02 | State management library for React frontend (Zustand vs. Redux Toolkit vs. Recoil) | Sprint 0 start | Zustand recommended for simplicity; should be decided with roster editor prototype evaluation |
| OI-03 | Deployment target: AWS ECS vs. Cloud Run vs. self-managed K8s | Sprint 0 start | ADR-0001 recommends ECS/Fargate (managed, lower ops); confirm during Sprint 0 |
| OI-04 | CI/CD pipeline: GitHub Actions deploy to staging automatically, production requires manual gate | Immediate | Default: auto-deploy to staging, manual gate for production |

---

## 11. Assumptions

1. Team has basic Python + React proficiency; no aviation domain expertise assumed
2. SME is available ~5 hours/week during Sprint 2 (regulation engine development)
3. Existing AWS account exists; no new infrastructure provisioning delay expected
4. GitHub repository access and CI/CD pipeline setup takes ≤1 day
5. No procurement or licensing delays for tools (all open-source stack)

## 12. Constraints

1. MVP scope is **strictly limited** to 6 P0 use cases — any addition requires removal of equivalent-complexity existing item (one-for-one swap policy)
2. Compliance with EU-OPS FTL / FAA Part 117 is non-negotiable — regulation engine must be SME-approved before any crew scheduling can go live
3. Data encryption at rest and in transit is mandatory for PII/PNR data (GDPR)
4. Initial release: web application only; no mobile apps in scope

---

*Plan created: 2026-06-11 by Project Manager during OpenUP Iteration 2 (T-006).*
*Risks and open issues will be reviewed weekly during sprint planning.*
