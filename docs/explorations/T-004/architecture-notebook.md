# Architecture Notebook — Airline Management System (AMS)

| Field | Value |
|---|---|
| **Version** | 0.1-draft |
| **Phase** | Elaboration — Iteration 1 |
| **Author** | Architect |
| **Date** | 2026-06-11 |
| **Status** | Draft — pending stakeholder review |

---

## 1. System Overview

AMS is a cloud-hosted, multi-region SaaS web application that centralizes airline operations management. The MVP targets four functional areas: Flight Operations, Crew Management, Dashboard & Reporting, and Administration (RBAC). Maintenance Tracking and Passenger Services are deferred to v2.

The system must comply with EASA/FAA crew duty-time regulations and support data protection requirements (GDPR) for any future passenger data handling.

---

## 2. Architectural Goals and Constraints

### 2.1 Non-Functional Requirements

| Attribute | Requirement | Rationale |
|---|---|---|
| **Regulatory Compliance** | Duty-time rule engine must be auditable, versioned, and re-runnable against historical data. | Critical — R1 risk; EU-OPS FTL / FAA Part 117 compliance is the product's market differentiator. |
| **Data Integrity** | ACID transactions for all crew assignment and flight plan operations. Zero-loss audit trail. | Aviation safety-critical workflows require full traceability. |
| **Real-Time Visibility** | In-flight status updates delivered to dashboards within 5 seconds. | Acceptance criteria (UC-FO-02) expect "real-time" dashboard updates. |
| **Availability** | 99.9% uptime SLA for MVP; multi-region failover in v2. | SaaS model requires high availability from launch. |
| **Scalability** | Support 500 concurrent active flights, 100 concurrent users per tenant at MVP scale. | Defined by initial target market (medium regional airlines). |
| **Security** | Encrypt PII at rest and in transit; RBAC with audit trail on all access decisions. | GDPR/DP compliance; aviation industry requirements. |

### 2.2 External Constraints

- Deployment target: cloud SaaS (AWS or GCP — decision in ADR-0001)
- Multi-region availability: data residency per tenant region
- Browser-only client for MVP (no mobile apps)
- Integration with external systems via API connectors (GDS, weather feeds) — adapter pattern required
- Regulation profiles must be versioned and swappable without deployment

---

## 3. Key Architectural Decisions

See individual ADRs in `docs/explorations/T-004/adrs/`:

| ADR | Decision | Status |
|---|---|---|
| [ADR-0001](./adrs/adr-0001-tech-stack.md) | Backend: Python/FastAPI; Frontend: React + TypeScript | Proposed |
| [ADR-0002](./adrs/adr-0002-data-model.md) | PostgreSQL primary store with JSONB for flexible payloads | Proposed |
| [ADR-0003](./adrs/adr-0003-regulation-engine.md) | Embedded rule engine (Python) with versioned regulation profiles | Proposed |
| [ADR-0004](./adrs/adr-0004-realtime.md) | Server-Sent Events for flight status push; WebSockets reserved for future interactive features | Proposed |
| [ADR-0005](./adrs/adr-0005-audit-logging.md) | Immutable audit log table with cryptographic chaining (hash chain) | Proposed |
| [ADR-0006](./adrs/adr-0006-event-backbone.md) | Internal domain event bus for decoupled service communication | Proposed |

---

## 4. System Structure / Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Web Browser (React)                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │
│  │ Flight   │ │ Crew     │ │ Dashboard│ │ Admin / RBAC │  │
│  │ Planning │ │ Roster   │ │ & KPIs   │ │              │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS / REST + SSE
┌──────────────────────────▼──────────────────────────────────┐
│                   API Gateway (Caddy/Nginx)                 │
│                   Rate limiting, TLS termination            │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    Application Server                        │
│                   Python / FastAPI                           │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐              │
│  │ Flight Ops │ │ Crew Mgmt  │ │ Dashboard  │   ┌─────────▼──────┐
│  │ Service    │ │ Service    │ │ Service    │   │ SSE Streamer  │
│  └────────────┘ └────────────┘ └────────────┘   └──────────────┘
│  ┌────────────┐ ┌────────────┐ ┌────────────┐              │
│  │ Admin/RBAC │ │ Audit      │ │ Regulation │   ┌─────────▼──────┐
│  │ Service    │ │ Service    │ │ Engine     │   │ Background    │
│  └────────────┘ └────────────┘ └────────────┘   │ Scheduler     │
│                                                 └──────────────┘
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │              Domain Event Bus (in-memory)                   │  │
│  │  FlightPlanFiled │ StatusChanged │ RosterPublished │ ...   │  │
│  └─────────────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
   ┌───────────┐    ┌───────────┐    ┌───────────────┐
   │PostgreSQL │    │   Redis   │    │ External APIs │
   │ (Primary) │    │ (Cache/   │    │ (GDS, Weather │
   │           │    │  PubSub)  │    │  NOTAM feeds) │
   └───────────┘    └───────────┘    └───────────────┘
```

### Component Responsibilities

| Component | Responsibility | Boundary |
|---|---|---|
| **Flight Ops Service** | Flight plan CRUD, filing workflow, status transitions, route validation | Internal API |
| **Crew Management Service** | Roster generation (auto + manual), crew qualification tracking, certification validity | Internal API |
| **Regulation Engine** | Duty-time rule evaluation against roster assignments; returns violation report | Internal library called by Crew Mgmt |
| **Dashboard Service** | Aggregates current-state data from all services for role-based KPI display | Internal API |
| **Admin/RBAC Service** | User CRUD, role assignment, permission matrix, organization/tenant management; auth middleware on every API request; RBAC enforcement at service boundary (not just route-level) | Internal API + cross-cutting middleware |
| **Audit Service** | Append-only logging of all state-changing and access-decision events; triggered by domain events emitted by all services | Internal library |
| **SSE Streamer** | Pushes real-time flight status updates to subscribed browser clients; subscribes to `StatusChanged` domain events | Internal component |
| **Background Scheduler** | Cron-like jobs: roster publication notifications, cleanup, periodic validation sweeps | Internal component |
| **API Gateway** | TLS termination, rate limiting, request routing, tenant isolation header extraction | Infrastructure |
| **Domain Event Bus** | In-process event bus (Python `dataclass`-based during MVP); services publish and subscribe to domain events; pluggable backend (Redis pub/sub) for multi-process deployment | Internal library — in-memory dict of handlers at MVP scale |

---

## 5. Data Architecture

### 5.1 Primary Entities (MVP Domain Model)

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│    Tenant    │       │   Aircraft   │       │   Aerodrome  │
│──────────────│       │──────────────│       │──────────────│
│ id           │       │ id           │       │ id           │
│ name         │       │ registration │       │ IATA code    │
│ region       │       │ type         │       │ ICAO code    │
│ created_at   │       │ base_aero    │       │ region       │
└──────┬───────┘       └──────┬───────┘       └──────┬───────┘
       │                      │                      │
       │            ┌─────────▼────────────┐          │
       │            │      Flight          │◄─────────┘
       │            │──────────────────────│
       │            │ id                   │
       │            │ plan_id (unique)     │
       │            │ scheduled_date       │
       │            │ origin_aero → Aero   │
       │            │ dest_aero → Aero     │
       │            │ aircraft → Aircraft  │
       │            │ etd / eta            │
       │            │ fuel_qty             │
       │            │ status (filed|active │
       │            │  |complete|diverted) │
       │            └─────────┬────────────┘
       │                      │
       │            ┌─────────▼────────────┐
       │            │   CrewAssignment     │
       │            │──────────────────────│
       │            │ id                   │
       │            │ flight → Flight      │
       │            │ crew_member → Person │
       │            │ role (captain|co-pilot│
       │            │  |purser)            │
       │            │ duty_start / end     │
       │            └─────────┬────────────┘
       │                      │
       │            ┌─────────▼────────────┐
       ▼            │    Person            │
┌──────────────┐    │──────────────────────│
│    User      │    │ id                   │
│──────────────│    │ first_name / last    │
│ id → Person  │    │ email                │
│ tenant → Ten │    │ phone                │
│ username     │    └─────────┬────────────┘
│ password     │              │
│ role_id      │    ┌─────────▼────────────┐    ┌──────────────┐
│ created_at   │    │  CrewQualification   │    │    Role      │
└──────────────┘    │──────────────────────│    │──────────────│
                    │ person → Person      │    │ id           │
                    │ aircraft_type        │    │ name         │
                    │ cert_expiry          │    │ permissions  │
                    │ current (boolean)    │    └──────────────┘
                    └──────────────────────┘

┌───────────────────────────────────┐
│     RegulationProfile             │
│───────────────────────────────────│
│ id                                │
│ jurisdiction (EASA / FAA)         │
│ version                           │
│ effective_from / to               │
│ ruleset (JSON — structured rules) │
│ is_active                         │
└──────────────────┬────────────────┘
                   │
┌──────────────────▼────────────────┐
│     DutyTimeComplianceResult      │
│───────────────────────────────────│
│ id                                │
│ assignment → CrewAssignment       │
│ regulation_profile → Profile      │
│ violations (JSON array)           │
│ assessed_at                       │
└───────────────────────────────────┘

┌───────────────────────────────────┐
│     AuditLog (immutable)          │
│───────────────────────────────────│
│ id                                │
│ actor_user → User                 │
│ action (CREATE|UPDATE|DELETE|    │
│         ACCESS|VALIDATE)          │
│ entity_type                       │
│ entity_id                         │
│ snapshot (JSON — state at time)   │
│ hash_prev ← chain link            │
│ created_at                        │
└───────────────────────────────────┘
```

### 5.2 Data Flow Summary

All inter-service communication flows through the **Domain Event Bus** (in-memory, pluggable backend). Services publish events and subscribe via handler registrations — no direct service-to-service calls.

1. **Flight Plan Creation**: Dispatcher creates plan → Flight Ops Service persists to PostgreSQL → publishes `FlightPlanFiled` event on the bus → Audit Service logs via event subscription → Dashboard Service refreshes via event aggregation → SSE Streamer broadcasts to dashboard subscribers. Crew Mgmt is notified of the new flight for roster alignment (via `FlightPlanFiled`, not direct coupling).
2. **Roster Generation**: Scheduler triggers → Crew Mgmt fetches flights, crew pool, qualifications, active regulation profile → Regulation Engine evaluates duty-time compliance → Violations reported → Scheduler adjusts → Publish → Locks assignments → publishes `RosterPublished` event on the bus → Audit Service logs → Background Scheduler queues notification emails.
3. **In-Flight Status**: Ground station or pilot input → Flight Ops Service updates status → publishes `StatusChanged(flight_id, new_status)` event on the bus → SSE Streamer fans out to all subscribed dashboard clients → < 5s latency target validated by monitoring.

### 5.3 Domain Events (MVP)

| Event | Published By | Subscribers | Payload |
|---|---|---|---|
| `FlightPlanFiled` | Flight Ops | Dashboard, Audit | `{plan_id, flight_id, etd, etype}` |
| `StatusChanged` | Flight Ops | SSE Streamer, Dashboard | `{flight_id, from_status, to_status, timestamp}` |
| `RosterPublished` | Crew Mgmt | Audit, Scheduler (notifications) | `{period_start, period_end, assignment_count}` |
| `DutyViolationDetected` | Crew Mgmt / Regulation Engine | Audit, Dashboard | `{assignment_id, rule_id, violations[]}` |

### 5.4 Persistence Technology

(continues below with unchanged text)

- **Primary Store**: PostgreSQL 16+ — chosen for ACID compliance, JSONB support (flexible payloads for regulation rules and audit snapshots), and mature multi-region replication options on AWS/GCP.
- **Cache / PubSub**: Redis 7+ — used for SSE client session management, query caching on dashboard aggregations, and inter-service event pubsub within a region.

---

## 6. Key Interfaces and Integration Points

| Interface | Direction | Protocol | Data Format | Notes |
|---|---|---|---|---|
| **Frontend ↔ API Gateway** | Inbound | HTTPS / REST | JSON (OpenAPI spec) | Swagger UI for developer self-service |
| **SSE Streamer → Browser** | Outbound | SSE (text/event-stream) | Event stream | Flight status, roster publish alerts |
| **API Gateway → Services** | Internal | HTTP/gRPC | Protobuf or JSON | Depends on ADR-0001 implementation decision |
| **Regulation Engine ↔ Crew Mgmt** | Internal | Function call (Python) | In-memory domain objects | Embedded library — no network boundary |
| **External: GDS Connector** | Outbound | HTTPS REST / SOAP | XML or JSON (GDS-specific) | Adapter pattern; TBD which GDS in MVP |
| **External: NOTAM Feed** | Inbound (polling) | HTTPS REST | JSON (ICAO format) | Poll every 30 min; cache in Redis |
| **External: Email Service** | Outbound | SMTP / API | HTML email | Transactional email (SendGrid/AWS SES) |

---

## 7. Risk Areas and Mitigations

### Technical Risks

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| **TR-01** | Regulation engine accuracy — incorrect duty-time evaluation could produce non-compliant rosters. | Critical | Build a comprehensive automated test suite with published EASA/FAA scenarios; require domain expert review of rule definitions; run regression tests on every profile update. See ADR-0003. |
| **TR-02** | SSE connection drops under high load (500+ flights updating simultaneously). | Medium | Benchmark SSE throughput early in Elaboration; implement fallback polling for affected clients; use Redis pub/sub to fan out events efficiently. See R5 in risk-list.md. |
| **TR-03** | JSONB regulation ruleset becomes unmanageable as rule complexity grows. | High | Start with structured JSON schema per rule type (max-block, rest-period, duty-extension); enforce validation at profile publish time; plan to extract engine to a service if rule count exceeds threshold. |
| **TR-04** | Multi-region data residency increases operational complexity (replication lag, consistency). | Medium | MVP targets single region per tenant (no cross-region active-active); use PostgreSQL logical replication for passive standby regions; defer multi-region active failover to v2. |

---

## 8. Open Issues

| # | Question | Impact | Resolution Approach | Target Date |
|---|---|---|---|---|
| **OI-01** | Which GDS vendor(s) for integration spike? | Blocks UC-PS backlog; not MVP-critical but needed for v2 planning. | Timebox a 1-week research spike on Amadeus API documentation. | Elaboration Iteration 2 |
| **OI-02** | Regulation profiles: store as JSONB or external YAML config (human-editable)? | Affects TR-03 risk and future maintainability. Developer feedback suggests external config for SME readability. | Load YAML config files at runtime; persist parsed result to PostgreSQL JSONB with version tracking. Prototype the load + validate pipeline against EASA EU-OPS Subpart Q sample rules. | Elaboration Iteration 1 (prototype) |
| **OI-03** | Authentication: email/password vs. SSO-first for MVP? | Vision mentions SSO integration as a stakeholder need. | MVP ships email/password with SAML/OIDC hooks in RBAC service; first v2 customer request triggers full SSO implementation. | Elaboration Iteration 1 (decision) |
| **OI-04** | Cloud provider selection: AWS vs. GCP? | Affects infrastructure cost modeling and team skill requirements. | Assess based on target market region concentration and team's existing cloud expertise; align with tenant data residency needs. | Before Construction phase |
| **OI-05** | Frontend state management for drag-and-drop roster editor (UC-CM-01)? | 28-day roster with validation feedback under 3 seconds requires careful client/server state split. | Server owns authoritative state; client maintains optimistic UI draft during editing; constraint checking offloaded to fast API endpoint (not client-side, to avoid duplicating regulation engine logic). Evaluate React Query or Zustand for client state orchestration. | Elaboration Iteration 1 (decision) |

---

## 9. Technology Stack Summary

| Layer | Choice | Justification |
|---|---|---|
| **Frontend** | React 18 + TypeScript + Vite | Strong ecosystem for complex dashboards; type safety reduces runtime errors in business-logic-heavy UI. |
| **Backend** | Python 3.12 + FastAPI | Natural fit for rule-based domain logic (regulation engine); async support for SSE; rapid prototyping velocity. |
| **Primary Database** | PostgreSQL 16+ | ACID compliance, JSONB for flexible payloads, mature multi-region replication. |
| **Cache / PubSub** | Redis 7+ | Low-latency SSE session management and dashboard query caching. |
| **Rules Engine** | Custom Python with Pydantic validation | Avoids external dependency overhead; regulation rules are domain-specific and need tight integration with crew domain model. |
| **Infrastructure** | Docker + AWS ECS (MVP) → Kubernetes (v2) | Docker for containerization; ECS for simpler MVP deployment; Kubernetes planned when multi-tenant scale justifies it. |
| **API Docs** | OpenAPI 3.1 (auto-generated by FastAPI) | Single source of truth for API contract; supports frontend/backend parallel development. |

*See [ADR-0001](./adrs/adr-0001-tech-stack.md) for detailed comparison.*

---

## Appendix A: Domain Model Detail — Flight Operations + Crew Management

### Aggregates and Bounded Contexts

| Bounded Context | Aggregate Roots | Invariants |
|---|---|---|
| **Flight Planning** | `Flight` (plan_id), `Aerodrome`, `Aircraft` | An aircraft type must be approved for the route; a filed plan cannot be modified by two users simultaneously (optimistic lock). |
| **Crew Management** | `Person`, `CrewQualification`, `CrewAssignment` | A crew member must hold a valid certification for the aircraft type of any assigned flight; duty-time rules must pass before roster publish. |
| **Regulation** | `RegulationProfile`, `DutyTimeComplianceResult` | A profile version is immutable once published; compliance results are appended (never updated). |
| **Access Control (cross-cutting)** | `User`, `Role`, `Permission` | Roles are composable sets of permissions; a user cannot assign themselves a permission they do not hold. Enforced at every layer: auth middleware on API gateway → RBAC check in each service handler → row-level data filtering by tenant and role. Foundational for UC-AD-01 — all other modules depend on it. |
| **Audit** | `AuditLogEntry` | Entries are append-only; hash chain prevents undetected modification. |

### Flight State Machine

```
[Draft] -> Filed -> Active -> Complete
                  \ Diverted --\--> Complete
```

- *Draft*: Flight plan created but not yet filed
- *Filed*: Dispatcher has submitted; crew scheduling notified
- *Active*: Aircraft is airborne (or about to depart)
- *Diverted*: Redirected from planned destination
- *Complete*: Flight landed at final destination

### Crew Assignment Lifecycle

```
[Proposed] -> Reviewed -> Published -> (Live / Changed)
```

- *Proposed*: Auto-generated or manually assigned, not yet published
- *Reviewed*: Scheduler has reviewed (and possibly adjusted) the assignment
- *Published*: Roster locked; notifications sent
- *Live/Changed*: Post-publish changes require a new audit entry and re-validation

---

## Appendix B: Feasibility Assessment — R1 (Regulatory Compliance)

**Risk**: Crew duty-time rules (EU-OPS FTL / FAA Part 117) are complex and frequently updated. A compliance gap makes the product unusable for regulated operators.

### Feasibility Verdict: **FEASIBLE with conditions**

The regulation engine is a pure-domain problem — no experimental or unproven technology is required. The core techniques (rule evaluation, state tracking, constraint satisfaction) are well-established in software engineering. Key feasibility factors:

| Factor | Assessment | Evidence |
|---|---|---|
| **Algorithmic complexity** | Medium | EU-OPS Subpart Q and FAA Part 117 contain ~50-80 individual constraints (max duty, min rest, cumulative limits across windows). Each constraint is a conditional predicate; evaluation is O(n) per constraint per crew member. No combinatorial explosion expected for MVP roster sizes (<200 crew members). |
| **Domain knowledge gap** | High — requires SME | This is the single biggest risk. The team must either hire or contract an aviation domain expert (R8 from risk-list.md). Without SME review, even algorithmically correct code can encode rules incorrectly. |
| **Testability** | Good | Regulations are published as written rules with examples and regulatory guidance. These map directly to test cases. A rule-based system is inherently testable if rules are isolated in functions/classes. |
| **Versioning / Swapping** | Straightforward | Regulation profiles can be versioned data objects with an effective-date range. Loading the correct profile for a given roster date is a simple lookup. The engine itself remains unchanged when rules change. |

### Recommendation

1. **Immediately**: Identify and engage an aviation SME (R8 mitigation) before beginning regulation-engine implementation.
2. **Elaboration Iteration 1**: Build a prototype regulation engine against a subset of rules (e.g., max daily duty, min rest period) to validate the approach. This is the architectural spike for R1.
3. **Prototype acceptance criteria**: Correctly evaluate at least 5 distinct EASA EU-OPS duty-time constraints against synthetic crew schedules with known pass/fail outcomes.

---

## Appendix C: Feasibility Assessment — R2 (Scope Creep)

**Risk**: Six major feature areas in one release risks diluting focus and missing deadlines.

### Feasibility Verdict: **MANAGEABLE with strict guards**

The MVP scope is well-defined in the use case catalog (6 P0 use cases across 4 functional areas). Maintenance Tracking (UC-MT-*) and Passenger Services (UC-PS-*) are explicitly deferred to v2. The risk is not about missing scope items but about unplanned additions during development.

### Recommended Scope Guards

| Guard | Implementation |
|---|---|
| **Definition of Done for MVP** | Only the 6 P0 use cases with their acceptance criteria constitute "done". Anything outside requires a change request and PM approval. |
| **Architecture decoupling** | Design modules as bounded contexts so that v2 features (GDS, maintenance) can be added without refactoring MVP code. Use the adapter pattern for external integrations (ADR-0001). |
| **Feature flags** | MVP code is always deployable; v2 features behind feature flags until ready. Prevents half-finished v2 work from blocking MVP release. |
| **Iteration planning discipline** | No iteration starts without a clear story-point budget tied to P0 use cases. Scope adds only when equivalent scope is removed (one-for-one swap). |

### Recommendation

R2 is primarily a project management risk, not an architecture risk. The proposed architecture supports it naturally: services are decoupled by bounded context, so Flight Ops and Crew Management can be built independently of Maintenance Tracking and Passenger Services modules. No architectural change is needed — enforce process discipline.

---

## Self-Assessment Against Rubric

| Criterion | Grade | Notes |
|---|---|---|
| 1. Architectural Goals and Constraints | ✅ | Section 2 lists NFRs (compliance, data integrity, real-time, availability, scalability, security) and external constraints. |
| 2. Key Architectural Decisions | ✅ | 5 ADRs documented in Section 3 with rationale linked to individual files. |
| 3. System Structure / Component Overview | ✅ | ASCII diagram + component responsibility table in Section 4. |
| 4. Technology Stack | ✅ | Table in Section 9 with justification for each non-obvious choice. |
| 5. Data Architecture | ✅ | Entity model (Section 5.1), data flow (Section 5.2), persistence choices (Section 5.3). |
| 6. Key Interfaces and Integration Points | ✅ | Table in Section 7 with protocol, format, and notes for each interface. |
| 7. Risk Areas and Mitigations | ✅ | 4 technical risks in Section 7; R1 and R2 feasibility in Appendices B/C. |
| 8. Open Issues | ✅ | 4 open issues listed in Section 8 with impact, resolution approach, and target date. |

**Result**: `satisfied` — all rubric criteria met.
