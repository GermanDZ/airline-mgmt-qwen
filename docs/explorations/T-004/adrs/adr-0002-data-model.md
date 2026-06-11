# ADR-0002: Primary Data Store and Modeling Approach

| Field | Value |
|---|---|
| **Date** | 2026-06-11 |
| **Status** | Proposed |
| **Deciders** | Architect, Project Manager |
| **Consequences** | Determines how regulation rules are stored, how audit trails are enforced, and how easily the data model evolves as scope grows. |

---

## Context

AMS domain entities have complex relationships: aircraft types must be approved for routes, crew members need type-specific certifications, duty-time rules vary by jurisdiction and version, and every state change must be auditable. The risk-list identifies R4 (data model inadequacy) as a High-severity risk. The MVP requires supporting ~10 entity types with clear relational boundaries, plus flexible storage for regulation ruleset definitions.

## Decision

**PostgreSQL 16+ as the sole primary data store**, using:
- Relational tables for structured entities (users, flights, crew assignments)
- `JSONB` columns for variable-length payloads (regulation rulesets, audit snapshots)
- UUID primary keys throughout
- A single database per tenant at MVP scale

**Object-Relational Mapping**: SQLAlchemy 2.0+ with declarative mappings and async engine.
**Migration Tooling**: Alembic for schema versioning and migrations.

## Rationale

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **PostgreSQL** (selected) | ACID compliance; `JSONB` for flexible payloads without schema migration; mature multi-region replication; native `uuid`; excellent OLAP capabilities for dashboard queries | Multi-region active-active requires third-party tools at MVP; large binary blobs not ideal | **Selected** — best balance of relational integrity and flexibility. The JSONB columns solve the regulation ruleset problem (ADR-0003) without introducing a second database. |
| MySQL 8 | Mature; good performance for simple OLTP workloads | Weaker JSON support (JSON functions exist but less expressive than PostgreSQL's); no native `uuid` type; multi-region replication less mature | Rejected — we need stronger JSON querying for regulation rules and audit snapshots. |
| CockroachDB | Distributed SQL with automatic sharding | Younger ecosystem; operational complexity for MVP; cost overhead not justified at 100-user scale | Rejected — over-engineering for MVP. |
| MongoDB + separate relational store | Flexible schemas; good document modeling | Two databases = two failure domains; transaction support across stores is limited (not available in most configs); increases operational complexity | Rejected — adds unnecessary infrastructure complexity. Regulation rules and compliance results don't need a document store's flexibility — PostgreSQL JSONB handles them well. |

### Use of `JSONB` for Specific Entities

| Entity | Column | Content | Why JSONB |
|---|---|---|---|
| `RegulationProfile.ruleset` | `JSONB` | Structured rule definitions (type, condition, threshold) | Rules evolve; schema changes require no migration — only data version bump |
| `AuditLog.snapshot` | `JSONB` | Full entity state at time of change | Variable-width snapshots; queryable for audit review |
| `DutyTimeComplianceResult.violations` | `JSONB` | Array of violation objects (rule_id, severity, description) | Each assessment produces a variable number of violations |

### Why Not Event Sourcing?

Event sourcing was considered because:
- It naturally provides an audit trail
- It supports replaying regulation rules against historical data

However, for MVP scale (100 users, <500 active flights), event sourcing adds complexity that is not yet justified. The append-only `AuditLog` table with hash-chain integrity provides sufficient traceability. Event sourcing can be introduced in v2 if the replay requirement becomes critical (e.g., regulatory audits requiring full state history).

## Object-Relational Mapping

**SQLAlchemy 2.0+** with async engine (`asyncpg` dialect), declarative base, and `Mapped` type annotations.

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **SQLAlchemy 2.0+** (selected) | Mature; native JSONB support via `sqlalchemy.dialects.postgresql.JSONB`; integrates with Alembic out of the box; declarative `Mapped` annotations provide type safety; async engine pairs with FastAPI | Some learning curve for complex relationships (e.g., many-to-many crew certifications) | **Selected** — ecosystem standard; tight integration with Alembic and Pydantic (SQLAlchemy's ORM-extras pattern or manual mapping to Pydantic models at API boundaries). |
| Tortoise ORM | Native async from the ground up; Django-like syntax | Smaller ecosystem; weaker JSONB query support; less mature multi-tenant patterns | Rejected — we need strong JSONB queries for regulation rules and audit snapshots. |
| Ormar (async SQLAlchemy wrapper) | Pydantic-native models as the source of truth; auto-generates SQLAlchemy metadata | Extra abstraction layer can cause subtle bugs when SQLAlchemy features are needed; less community support | Rejected — keep ORM and validation layers distinct (SQLAlchemy for persistence, Pydantic for API boundary). This reduces coupling if we ever need to swap ORM. |

## Database Migration Strategy

**Alembic** as the migration tool, paired with SQLAlchemy's declarative base.

| Consideration | Approach |
|---|---|
| **Schema migrations** | Alembic auto-generates initial migration from SQLAlchemy models; manual edits for complex operations (triggers, indexes) |
| **JSONB column changes** | `ALTER TABLE ... ALTER COLUMN ruleset TYPE JSONB USING ruleset::jsonb` — tested before applying to production |
| **Data migrations** | Alembic `upgrade/downgrade` hooks can run Python logic (e.g., backfill hash values for audit log, migrate regulation profiles) |
| **Migration review** | Every generated migration must be reviewed by at least one developer before application |
| **Zero-downtime deployments** | Deploy migrations that are backward-compatible first; use feature flags where schema changes could break running instances |

### Migration Workflow

```
1. Developer modifies SQLAlchemy model → `alembic revision --autogenerate -m "add crew_qualification_table"`
2. Review generated migration script for correctness (indexes, constraints, data safety)
3. Apply to dev: `alembic upgrade head`
4. Test: run suite of integration tests against migrated schema
5. Merge: PR gate requires successful CI migration test step
```

## Consequences

- **Positive**: Single data store reduces operational complexity; ACID guarantees all safety-critical workflows; JSONB columns allow regulation rules to evolve without migrations. SQLAlchemy + Alembic provides predictable, version-controlled migration process.
- **Negative**: Multi-region active-active requires waiting for CockroachDB or PostgreSQL logical replication with conflict resolution (deferred to v2).
- **Risk mitigation**: Build the core domain model (Flight, CrewAssignment, RegulationProfile) as a conceptual ER diagram in Elaboration Iteration 1 and review it with dispatchers and crew schedulers to validate R4 risk assumption.
