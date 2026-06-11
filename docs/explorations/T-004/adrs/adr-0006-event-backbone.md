# ADR-0006: Internal Domain Event Backbone

| Field | Value |
|---|---|
| **Date** | 2026-06-11 |
| **Status** | Proposed |
| **Deciders** | Architect, Developer |
| **Consequences** | Determines how tightly or loosely coupled services are; affects testing strategy and deployment flexibility. |

---

## Context

The use cases define implicit inter-service dependencies:
- UC-FO-01 (Flight Plan) postcondition: "System notifies Crew Scheduling and Flight Status tracking modules"
- UC-CM-01 (Crew Roster) postcondition: "Flight operations module receives assigned crew names and positions"
- UC-DR-01 (Dashboard) consumes aggregated data from multiple services

The initial architecture assumed direct service-to-service communication or shared state. The developer raised a valid concern: this tight coupling makes individual modules hard to test and prevents independent development. A domain event backbone decouples publishers from subscribers while preserving temporal ordering guarantees.

## Decision

An **in-memory Python event bus** using `dataclass`-based events during MVP, with a **pluggable Redis pub/sub backend** for multi-process deployment. The bus lives as an internal library component shared across all services within the same process. Services publish and subscribe via handler registrations — no direct calls between service modules.

## Rationale

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **In-memory event bus + pluggable backend** (selected) | Simple MVP implementation (50-100 LOC); zero deployment overhead; testable with synchronous dispatch; seamless upgrade to Redis pub/sub when multi-process; events are typed Python `dataclass` instances providing IDE autocomplete and type safety | In-process only — does not work across service boundaries in a microservice architecture; if the system is split into separate processes later, the bus must be replaced with Redis/NATS | **Selected** — MVP is a monolith (single FastAPI process). The pluggable backend ensures we are not locked in. Events typed as `dataclass` provide the same testing ergonomics as property-based test fixtures. |
| Redis pub/sub from day one | Works across processes; battle-tested | Adds an infrastructure dependency for MVP scale (100 users, single process); event delivery is at-least-once with no ordering guarantees without additional coordination | Rejected — adds operational complexity for a single-process deployment. The developer's concern is about *decoupling*, not multi-process communication, which can be achieved in-memory. |
| Message queue (RabbitMQ / Kafka) | Reliable delivery; replayability; horizontal scalability | Significant operational overhead (broker management); overkill for MVP; event replay requires additional tooling | Rejected — no business requirement for message persistence or replay at MVP scale. |
| Direct service calls | Simplest implementation; easy to debug | Tight coupling makes individual modules hard to unit test in isolation; changes to one service require deployment of both | Rejected — developer's valid concern. The cross-service dependencies described in use cases are *event-driven* by nature (one service "notifies" others), not request-response. |

### Event Bus Interface

```python
@dataclass
class FlightPlanFiled:
    plan_id: str
    flight_id: UUID
    etd: datetime
    aircraft_type: str

class EventBus:
    def publish(self, event: DomainEvent) -> None: ...
    def subscribe(self, event_type: type, handler: Callable) -> None: ...
```

### MVP Event Types

| Event | Publisher | Key Subscribers |
|---|---|---|
| `FlightPlanFiled` | Flight Ops Service | Dashboard (refresh), Audit (log), SSE Streamer (alert) |
| `StatusChanged(flight_id, from, to)` | Flight Ops Service | SSE Streamer (fan-out), Dashboard (update) |
| `RosterPublished(period, count)` | Crew Mgmt Service | Audit (log), Scheduler (email queue) |
| `DutyViolationDetected(assignment_id, violations)` | Regulation Engine | Audit (log), Dashboard (flag) |

## Consequences

- **Positive**: Each service can be tested independently by publishing events in tests and asserting handler behavior. The Flight Ops module does not need to "know" about the Crew Mgmt or Dashboard modules — it just publishes events.
- **Negative**: In-process bus limits the system to a single Python process at MVP scale. If we later split into microservices, the bus must be replaced with Redis/NATS (but the event types remain the same).
- **Testing benefit**: Events are typed `dataclass` instances — property-based testing tools (Hypothesis) can generate synthetic events for regression testing the regulation engine and audit log handler.

### Upgrade Path

```
MVP: EventBus (in-memory dict) → v2: RedisEventBus (pub/sub fan-out) → v3: KafkaEventBus (persistent replay)
Event type definitions never change — only the transport layer changes.
```

## Open Questions

- Should events include a `tenant_id` field from the start to support multi-tenancy? **Decision: yes** — all events will carry `tenant_id` as a mandatory field, even though MVP targets a single tenant. This avoids retrofitting when the second customer signs up.
- See OI-04 (cloud provider): the chosen cloud platform may influence the messaging choice for v2 multi-process deployment.
