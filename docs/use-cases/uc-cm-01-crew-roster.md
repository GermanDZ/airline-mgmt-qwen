# Use Case — Generate Crew Roster

| Field | Value |
|---|---|
| **UC-ID** | UC-CM-01 |
| **Name** | Generate Crew Roster |
| **Priority** | P0 (MVP) |
| **Actor(s)** | Crew Scheduler |
| **Trigger** | Flight schedule published for a planning period (typically 28-day forward roster) |
| **Preconditions** | 1. User has crew scheduler role.<br>2. Flight schedule for target period exists in system.<br>3. Crew pool with valid certifications and qualifications is loaded. |

## Description
The Crew Scheduler generates a roster assigning available crew members to flights within the planning period, subject to qualification requirements (aircraft type ratings), certification validity, and duty-time regulations (EU-OPS / FAA Part 117). The system proposes assignments; the scheduler reviews and adjusts.

## Main Flow
1. Scheduler selects planning period and aircraft type group.
2. System retrieves: flight schedule, crew qualifications/certifications, current duty history, and applicable regulation profile.
3. System proposes crew-to-flight assignments prioritizing: certification validity, least seniority offset, minimum deadhead time.
4. System highlights conflicts (duty-time violations, missing certifications) in red.
5. Scheduler reviews proposed roster, adjusts manually where needed (drag-and-drop or select from dropdown).
6. System re-validates after each manual adjustment.
7. Scheduler publishes roster — system locks assignments and notifies affected crew via email notification.
8. Audit log records all changes with user identity and timestamps.

## Alternative Flows
- **A1: No valid crew for a flight** — System flags unassigned flights; scheduler must manually find coverage (e.g., stand-by, transfer from other base).
- **A2: Regulation change mid-planning** — If regulation profile is updated during roster generation, system re-runs validation and highlights newly violated assignments.
- **A3: Scheduler abandons draft** — Roster saved as draft with last-modified timestamp; scheduler can resume later.

## Postconditions
- Crew-to-flight assignments are locked for the planning period.
- Affected crew members receive notification (email).
- Flight operations module receives assigned crew names and positions.
- Duty-time compliance tracking (UC-CM-04) begins monitoring against published roster.

## Acceptance Criteria
- System generates a first-pass assignment for 90%+ of flights automatically within 2 minutes for a standard 7-day period.
- All duty-time regulation violations are flagged before publish; publishing with unresolved critical violations is blocked.
- Each manual adjustment triggers immediate re-validation (feedback within 3 seconds).
- Roster is published as a single atomic operation — all assignments visible simultaneously after publish.

## Acceptance Tests (Selected)
| # | Scenario | Expected Result |
|---|---|---|
| 1 | All crew have valid certifications, within duty limits | Zero violations; roster publishes successfully |
| 2 | One crew member exceeds daily duty limit | Assignment highlighted in red; publish blocked for that flight |
| 3 | No captain-certified crew for a type | Flight flagged as "unstaffed" after full auto-generation |
| 4 | Regulation profile updated after draft saved | Draft re-validated; new violations marked with badge |

## Related Use Cases
- UC-CM-02: Manage Crew Certifications (feeds qualification data)
- UC-CM-03: Handle Crew Replacement / Standby (post-publish changes)
- UC-CM-04: Track Duty-Time Compliance (consumes published roster)
- UC-FO-01: Create and File Flight Plan (source of flights to staff)
