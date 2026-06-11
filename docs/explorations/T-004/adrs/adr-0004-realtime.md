# ADR-0004: Real-Time Update Mechanism — Server-Sent Events

| Field | Value |
|---|---|
| **Date** | 2026-06-11 |
| **Status** | Proposed |
| **Deciders** | Architect, Project Manager |
| **Consequences** | Determines how in-flight status updates reach dashboards; affects latency targets and browser compatibility requirements. |

---

## Context

UC-FO-02 (Track In-Flight Status) requires that when a flight's status changes (e.g., "active" → "diverted"), all relevant dashboard users see the update within seconds. The risk-list identifies R5 (real-time performance) as Medium severity, noting that "live flight status updates for hundreds of concurrent flights require low-latency data pipelines."

The acceptance criteria state: "Flight plan is visible to all relevant modules within 10 seconds of filing" (UC-FO-01). This implies a push-based notification system rather than client polling.

## Decision

**Server-Sent Events (SSE)** as the primary real-time mechanism for MVP, with **Redis pub/sub** as the fan-out layer and **WebSocket** reserved for future interactive features (drag-and-drop roster adjustment, collaborative flight plan editing).

## Rationale

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **SSE + Redis pub/sub** (selected) | Native browser support (no library needed); single-direction push (sufficient for status updates); built-in reconnection, event IDs, and retry semantics; simple to implement with FastAPI + Redis; lower server resource usage than WebSockets | One-way communication (server → client); no message acknowledgment from clients; not suitable for bidirectional interaction | **Selected** — the MVP real-time requirement is unidirectional: server pushes status changes to dashboards. SSE matches this perfectly and has less operational overhead than WebSockets. |
| WebSockets | Full-duplex; message acknowledgment; binary support | More complex lifecycle management (connection drops, heartbeat); higher memory per connection; browser polyfills needed for older browsers | **Deferred** — bidirectional interaction is not required in MVP. Reserve for v2 features like real-time collaborative editing or pilot-ground chat. |
| Long Polling | Universal browser compatibility | High latency (~1s round-trip minimum); excessive HTTP overhead; poor UX compared to push-based solutions | Rejected — the 5-second real-time target with hundreds of flights makes polling impractical and wasteful. |
| GraphQL Subscriptions | Type-safe subscriptions; integrates with existing GraphQL API | Requires full GraphQL stack (schema, resolvers, subscription server); adds significant complexity for a simple status-update use case | Rejected — GraphQL is not needed in MVP. The REST + SSE combination is simpler and sufficient. |

### Architecture

```
StatusChangeEvent (internal)
    -> SSEStreamer.publish(flight_id, event_data)
        -> redis.PUBLISH("flight_status", json_payload)  # fan-out within region
            -> All SSE connections subscribed to channel receive event
                -> Browser EventSource receives and updates DOM
```

- The SSE Streamer maintains a Redis subscriber per active flight. When a flight status changes, it publishes the event once to Redis pub/sub.
- All browser clients connected via SSE to that flight's channel receive the event simultaneously.
- SSE connections are long-lived HTTP connections managed by FastAPI (`StreamingResponse` with `text/event-stream` MIME type).

### Expected Performance

| Metric | Target | Measurement Approach |
|---|---|---|
| Server → Redis publish latency | < 1ms | Local benchmark |
| Redis fan-out to connected clients | < 5ms | Redis `PUBSUB NUMCONN` monitoring + synthetic test |
| Client-side DOM update after event receipt | < 100ms (browser dependent) | Browser DevTools Performance tab |
| End-to-end latency (status change → dashboard visible) | < 5 seconds | Acceptance criteria; validated by automated load test with 500 flights |

## Consequences

- **Positive**: Simple implementation (<200 lines of FastAPI code for the SSE streamer); low memory per connection (~10KB vs. ~50KB for WebSocket); native browser support eliminates JavaScript dependencies.
- **Negative**: No client acknowledgment — if a browser disconnects during an update, there is no guarantee it received the last event (mitigated by SSE's built-in reconnection with last-event-ID). Not suitable for bidirectional interaction.
- **Risk mitigation**: Benchmark SSE + Redis pub/sub with 500 concurrent connections in Elaboration Iteration 1 (technical spike for R5). If throughput is insufficient, evaluate WebSocket as the v2 upgrade path.

## Open Questions

- None at MVP scope. Revisit in v2 when interactive features require bidirectional communication.
