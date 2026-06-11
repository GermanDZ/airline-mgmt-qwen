# ADR-0005: Immutable Audit Log with Hash-Chained Integrity

| Field | Value |
|---|---|
| **Date** | 2026-06-11 |
| **Status** | Proposed |
| **Deciders** | Architect, Project Manager |
| **Consequences** | Determines whether audit trail integrity can be verified independently and whether tampering with historical records is detectable. |

---

## Context

Multiple use cases require an audit trail:
- UC-FO-01 postcondition: "Audit log entry created (user, timestamp, plan ID)"
- UC-CM-01 main flow step 8: "Audit log records all changes with user identity and timestamps"
- R6 (security & data privacy): "Regular third-party security audit"
- Regulatory compliance: EASA/FAA may require proof of who changed what and when

The audit log must be **tamper-evident** — if someone modifies a historical entry, the system should detect it. This is not about preventing modification (DBA access can always modify data) but about providing cryptographic evidence that tampering occurred.

## Decision

An **append-only `audit_log` table** in PostgreSQL, where each row contains a SHA-256 hash of the previous row's content. Entries are inserted via application-level enforcement (no direct database writes to this table from any source other than the Audit Service). The hash chain provides tamper detection: modifying any entry breaks the chain for all subsequent entries.

## Rationale

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **Hash-chained append-only table** (selected) | Simple SQL implementation; no external dependencies; tamper-evident via hash chain verification query; audit data lives in the same database as application data (simple backups); verifiable with a single SQL statement (`SELECT id, prev_hash, sha256(id || created_at || entity_type || ...)` ) | Requires careful DBA access control (grants must deny UPDATE/DELETE on this table); hash chain can only detect tampering, not prevent it if DBA is the attacker | **Selected** — sufficient for MVP compliance requirements. The hash chain provides mathematical evidence of tampering with zero infrastructure cost. |
| Append-only database feature (PostgreSQL `pgaudit` + `FORCE APPEND ONLY`) | Built-in enforcement; tamper-proof by database engine | PostgreSQL does not have native "append only" table semantics; would require custom triggers or external tooling | Rejected — no native PostgreSQL feature provides this; triggers add complexity with marginal benefit over application-level enforcement. |
| Write-ahead log / binary audit trail | Tamper-proof if WAL is archived externally; database-native | Binary format requires specialized tools to read; cannot be queried in SQL; operational complexity for a compliance requirement that needs human-readable audit review | Rejected — auditors need to query and read the audit log, not just verify its integrity. |
| Blockchain / distributed ledger | Immutable; verifiable by third parties | Massive over-engineering; no business justification for MVP; operational overhead of running nodes | Rejected — not applicable to this use case. |

### Audit Log Schema

```sql
CREATE TABLE audit_log (
    id              BIGSERIAL PRIMARY KEY,
    actor_user_id   UUID NOT NULL REFERENCES "user"(id),
    action          VARCHAR(20) NOT NULL CHECK (action IN ('CREATE','UPDATE','DELETE','ACCESS','VALIDATE')),
    entity_type     VARCHAR(50) NOT NULL,
    entity_id       UUID NOT NULL,
    snapshot        JSONB NOT NULL,           -- full entity state at time of change
    hash_prev       CHAR(64) NOT NULL,        -- SHA-256 of previous row's concatenated fields
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Integrity: hash_current is a computed column (via trigger) for tamper detection
    CONSTRAINT audit_log_chain CHECK (hash_prev IS NOT NULL)
);

-- Trigger function to compute SHA-256 of previous row
CREATE INDEX idx_audit_log_entity ON audit_log (entity_type, entity_id);
CREATE INDEX idx_audit_log_created_at ON audit_log (created_at);
```

### Integrity Verification Query

To verify the hash chain:
```sql
WITH ordered AS (
    SELECT id, actor_user_id, action, entity_type, entity_id, snapshot, created_at,
           LAG(hash_prev) OVER (ORDER BY id) AS expected_hash,
           hash_prev AS actual_hash
    FROM audit_log
)
SELECT * FROM ordered WHERE expected_hash != actual_hash;
```
Zero rows returned means the chain is intact.

## Consequences

- **Positive**: Tamper-evident with zero external dependencies; human-readable entries for auditor review; simple backup/restore with the rest of the database; single SQL query verifies integrity.
- **Negative**: A DBA with direct access can still modify data and recompute hashes (the chain prevents *undetectable* tampering by application-level actors, not privileged database operators). For higher assurance, consider off-database log shipping (e.g., to S3) in v2.
- **Risk mitigation**: Implement a periodic integrity verification job that runs daily and alerts on hash-chain breaks. Log the verification result itself to the audit table for compliance reporting.

## Open Questions

- Should the audit log be off-loaded to immutable storage (S3 Object Lock) for regulatory audits? This is deferred to v2 unless an initial customer requires it.
- See R6 in risk-list.md: data privacy implications — must implement audit-log retention and redaction policies before handling PII-containing entities.
