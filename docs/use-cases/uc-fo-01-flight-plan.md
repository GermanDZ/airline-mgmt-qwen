# Use Case — Create and File Flight Plan

| Field | Value |
|---|---|
| **UC-ID** | UC-FO-01 |
| **Name** | Create and File Flight Plan |
| **Priority** | P0 (MVP) |
| **Actor(s)** | Flight Dispatcher |
| **Trigger** | New flight schedule published or existing flight modified |
| **Preconditions** | 1. User has dispatcher role with flight planning permission.<br>2. Aircraft assignment exists for the scheduled route.<br>3. Latest aerodrome and en-route NOTAMs are available in system (read-only). |

## Description
The Flight Dispatcher creates a flight plan specifying aircraft, route, fuel requirements, alternate airports, and estimated times. The plan is reviewed against basic constraints (aircraft type compatibility, route availability) and filed into the system for execution.

## Main Flow
1. Dispatcher selects a scheduled flight from the roster.
2. System displays aircraft assignment, route waypoints, and latest NOTAMs for origin/destination/alternates.
3. Dispatcher reviews or adjusts aircraft registration (if multiple options available).
4. Dispatcher enters or confirms estimated times (ETD, ETA, EON, EOS).
5. Dispatcher calculates or confirms fuel quantity (base fuel + contingency + alternate).
6. System validates: aircraft type matches route restrictions, NOTAMs flagged for selected aerodromes are displayed (non-blocking).
7. Dispatcher submits — system records the flight plan with a unique plan ID and status "filed".
8. System notifies Crew Scheduling and Flight Status tracking modules.

## Alternative Flows
- **A1: Validation fails** — Aircraft type not approved for route; dispatcher must select different aircraft or request temporary approval from Operations Director.
- **A2: NOTAM blocks aerodrome** — Dispatcher selects alternate airport; system re-routes calculation if needed.
- **A3: Duplicate plan exists** — System alerts dispatcher and offers to merge changes into existing active plan.

## Postconditions
- Flight plan is recorded with status "filed".
- Crew scheduling module receives assigned aircraft and times.
- Flight Status tracking module creates a flight event record for real-time updates.
- Audit log entry created (user, timestamp, plan ID).

## Acceptance Criteria
- Dispatcher can create a flight plan in under 5 minutes for a standard domestic route.
- System prevents filing when critical NOTAMs are unacknowledged by dispatcher.
- Flight plan is visible to all relevant modules within 10 seconds of filing.
- Every filed plan is auditable: creator, timestamp, data version at time of filing.

## Related Use Cases
- UC-FO-02: Track In-Flight Status (consumes filed plan)
- UC-CM-01: Generate Crew Roster (receives aircraft/times)
- UC-CM-04: Track Duty-Time Compliance (uses dispatched times for duty window calculation)
