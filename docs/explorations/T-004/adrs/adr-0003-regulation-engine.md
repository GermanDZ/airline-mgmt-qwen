# ADR-0003: Regulation Engine — Embedded Rule Engine with Versioned Profiles

| Field | Value |
|---|---|
| **Date** | 2026-06-11 |
| **Status** | Proposed |
| **Deciders** | Architect, Project Manager |
| **Consequences** | Determines whether the compliance engine can be developed quickly, tested rigorously, and maintained without external dependencies. Directly addresses R1 (regulatory compliance). |

---

## Context

UC-CM-01 (Generate Crew Roster) requires the system to validate crew assignments against duty-time regulations before allowing roster publication. The use case specifies evaluation against "EU-OPS / FAA Part 117" profiles. These regulations contain:
- Maximum daily duty periods (varies by crew complement)
- Minimum rest periods between duties
- Cumulative limits (e.g., max hours in 7 days, 30 days, 365 days)
- Conditions for extensions and reductions
- Jurisdiction-specific rules

The regulation profile must be versioned — when a regulation is updated, existing rosters should remain valid against the profile that was active at publication time, while new rosters use the latest profile.

## Decision

**An embedded Python rule engine with Pydantic validation**, using **versioned regulation profiles loaded from external configuration files (JSON/YAML) and persisted as `JSONB`** in PostgreSQL. The engine is a clearly separated library module within the Crew Management Service, not a standalone service. Profiles are defined as editable external config — not embedded in code.

## Rationale

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **Embedded Python + Pydantic** (selected) | Tight integration with domain model; no network boundary = fast evaluation (<1ms per rule); Pydantic models provide validation and type safety for rule definitions; SME-friendly — Python reads like pseudocode; easy to unit test individual rules | Rule definitions live in data (JSONB), not code — must enforce schema; engine versioning needs care when regulation formats change | **Selected** — best fit for MVP timeline. The regulation engine is pure domain logic; embedding it avoids deployment complexity while enabling rapid iteration during Elaboration. |
| Drools / jBPM | Mature rules engines; graphical rule editors; excellent for complex business rules | Java-only (mismatch with Python backend); heavy dependency (adds 50MB+ to build); over-engineering for MVP; harder to unit test in isolation | Rejected — adds JVM dependency and operational complexity. The ~50-80 regulation constraints at MVP scale are simple conditional predicates, not complex rule-chaining scenarios. |
| OPA (Open Policy Agent) | Generic policy engine; Rego language; works as sidecar or embedded | Rego has a steep learning curve for SMEs; policy-as-code is powerful but overkill here; integration overhead with FastAPI | Rejected — best suited for infrastructure/security policies, not business-domain rule evaluation. SME review would be difficult with Rego syntax. |
| Standalone microservice (Rust/Go) | Independent deployment; language agility | Adds network boundary; requires inter-service communication for every roster validation; overkill for MVP scale | Rejected — the regulation engine is called synchronously during roster generation, not at query-time scale. A separate service adds latency and operational complexity for no MVP benefit. |

### Rule Representation Format

Regulation rules will be stored as JSON objects with a fixed schema:

```json
{
  "rule_id": "EU-OPS-FTL-MAX-DUTY-DAY",
  "type": "max_block",
  "jurisdiction": "EASA",
  "value": 9.0,
  "unit": "hours",
  "conditions": {
    "crew_complement": {"min": 2, "max": 4}
  },
  "description": "Maximum duty period: 9 hours for 2-4 crew complement"
}
```

This structure supports the five rule categories needed for EU-OPS Subpart Q:
1. **max_block** — maximum duty/flight time
2. **min_rest** — minimum rest between duties
3. **cumulative_max** — max hours across a window (7d, 30d, 365d)
4. **duty_extension** — conditions under which duty can be extended
5. **reduction_factor** — modifiers based on time-of-day, circadian factors

### Evaluation Flow

```
CrewMgmtService.assign_crew(flight_id, crew_id, role)
    -> DutyTimeEngine.evaluate(assignment, active_profile)
        -> For each rule in profile.ruleset:
            if rule.applies_to(assignment):
                result = rule.check(value)
                if result.violated:
                    violations.append(result)
        -> return ComplianceResult(violations=violations)
```

## Consequences

- **Positive**: Fast development — rules are data, not code; SMEs can review JSON structures directly; unit tests map one-to-one to regulation clauses; zero deployment overhead.
- **Negative**: If rule count grows beyond ~200 or evaluation becomes a bottleneck (unlikely at MVP scale), extraction to a dedicated service is needed. Schema drift between engine versions and stored JSONB rulesets requires migration strategy.
- **Risk mitigation for R1**: Build an automated test suite where each regulation clause has at least 3 test cases (pass, fail, boundary). Run all tests on every profile update. Require SME sign-off before deploying a new rule version to production.

## Testing Strategy

The regulation engine requires **property-based testing** (`hypothesis`) in addition to example-based tests, because duty-time rule violation space is combinatorial:

| Test Type | Scope | Tool | Example |
|---|---|---|---|
| **Example-based** | Canonical regulatory scenarios from EASA/FAA guidance documents | `pytest` | "2-crew flight of 10 hours → 1 violation" |
| **Property-based** | Rules hold across synthetic crew schedules with randomized parameters | `hypothesis` | "For any combination of duty_start, crew_count, flight_duration: the max_duty rule either passes or fails consistently" |
| **Compliance regression** | Full profile evaluation against historical roster data to detect regressions on profile updates | `pytest` + `json` fixtures | Run all EASA EU-OPS rules against last month's synthetic roster after a profile version bump |

### Architecture for Testability

The rule engine is designed with clear I/O boundaries:
```python
class RegulationEngine:
    def evaluate(self, assignments: list[CrewAssignment], profile: RegulationProfile) -> ComplianceResult
    # Pure function: same input → same output, no side effects, no DB access
```

This allows testing the engine in isolation with synthetic `CrewAssignment` and `RegulationProfile` objects — no database, no HTTP server needed. The `hypothesis` strategy can generate these objects directly.
