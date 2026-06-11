# ADR-0001: Technology Stack Selection

| Field | Value |
|---|---|
| **Date** | 2026-06-11 |
| **Status** | Proposed |
| **Deciders** | Architect, Project Manager |
| **Consequences** | Determines development velocity, hiring requirements, infrastructure complexity, and long-term maintainability. |

---

## Context

AMS requires a technology stack that supports:
- Rapid prototyping (Elaboration phase needs early feedback)
- Complex rule-based domain logic (regulation engine)
- Real-time dashboard updates (SSE/WebSocket)
- ACID data integrity for safety-critical operations
- Cloud SaaS multi-region deployment
- Type safety for a business-logic-heavy application

## Decision

**Backend**: Python 3.12 + FastAPI
**Frontend**: React 18 + TypeScript + Vite
**Primary Database**: PostgreSQL 16+
**Cache / PubSub**: Redis 7+
**Infrastructure**: Docker + AWS ECS (MVP) → Kubernetes (v2)

## Rationale

### Backend: Python/FastAPI vs. alternatives

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **Python/FastAPI** (selected) | Rapid prototyping; natural fit for rule-based logic via Pydantic; async support for SSE; large data-processing ecosystem; team can share one language across backend + regulation engine | Perceived "slow" performance (not a concern at MVP scale — we're I/O bound, not CPU-bound); dynamic typing concerns (mitigated by Python 3.12 type hints + Pydantic) | **Selected** — best fit for the domain. The regulation engine is pure business logic; Python's readability makes rule encoding and SME review straightforward. |
| Go | Excellent performance; simple concurrency model; strong at I/O workloads (SSE) | Verbosity for complex domain models; no natural typing discipline (struct tags are less expressive than Pydantic); harder to prototype regulation rules quickly | Rejected — performance is not the bottleneck; domain logic complexity favors Python's expressiveness. |
| Java/Spring Boot | Enterprise maturity; strong typing; large ecosystem | Heavyweight for MVP; longer startup/deploy cycles; overkill for a small team building a first release | Rejected — violates R2 mitigation (scope creep control). Spring Boot adds 3-4x the boilerplate vs. FastAPI for equivalent functionality at MVP scale. |
| Node.js/TypeScript | One language across full stack; large ecosystem | Dynamic typing at runtime even with TS transpilation; weaker typing discipline than Pydantic validation for business rules | Rejected — we need stronger validation on domain objects (regulation rules) and a cleaner separation between API surface and business logic. |

### Frontend: React + TypeScript

React was selected over Vue or Svelte because:
- Larger ecosystem of data-grid, charting, and drag-and-drop components needed for complex roster UIs (drag-and-drop crew assignment is a key acceptance criterion)
- TypeScript provides compile-time type safety that catches mismatches between API contract and UI consumption
- Vite gives fast HMR for rapid iteration

### PostgreSQL with JSONB

PostgreSQL was selected over MySQL, CockroachDB, or document stores because:
- ACID guarantees are non-negotiable for crew assignments and flight plans
- JSONB columns store regulation rulesets and audit snapshots without schema changes
- Mature multi-region replication (AWS RDS Multi-AZ, read replicas)
- PostgreSQL's native `uuid` type fits the plan_id requirement in UC-FO-01

### Infrastructure: AWS ECS (MVP) → Kubernetes (v2)

ECS provides:
- Simpler operational burden for MVP (no kubectl mastery required)
- Built-in load balancing and auto-scaling
- Easy cost control for initial SaaS deployment
- Kubernetes is deferred to v2 when multi-tenant scale justifies the operational overhead

## Consequences

- **Positive**: Fast prototyping velocity; clear separation between API layer and business logic; regulation engine can be unit-tested in isolation; one language (Python) spans backend + domain logic.
- **Negative**: Python's GIL limits pure CPU throughput (mitigated by async I/O model); team may need to hire for React/TypeScript if not already possessed.
- **Risk mitigation**: Timebox a 2-day prototype of the regulation engine in Python during Elaboration Iteration 1 to validate that rule encoding feels natural to developers and SMEs.

## Testing Infrastructure

| Layer | Tool | Rationale |
|---|---|---|
| **Unit Tests** | `pytest` + `pytest-asyncio` | Standard Python test framework; async support for FastAPI route handlers |
| **Regulation Engine** | `hypothesis` (property-based testing) | Generate thousands of synthetic crew schedules to verify regulation rules hold under edge cases; essential for R1 compliance validation |
| **API Contract** | `pytest-httpx` (sync) / `httpx` async client | Verify REST endpoints match OpenAPI spec; no separate mock server needed |
| **Frontend Tests** | `@testing-library/react` + `vitest` | Component tests focused on user behavior, not implementation details |
| **E2E Smoke** | `playwright` (mvp), `cypress` (if richer交互 needed) | Browser-level smoke test of critical paths (flight plan filing, roster publish) |

The regulation engine's property-based testing is non-negotiable — example-based tests alone cannot cover the combinatorial space of duty-time windows (max duty × crew complement × time of day × cumulative periods).
