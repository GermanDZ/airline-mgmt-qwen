# Risk List — Airline Management System

## Project Context
Airline Management System (AMS) is a web-based platform for unified airline operations management, covering flight ops, crew scheduling, maintenance tracking, and passenger services. Phase: Inception.

## Risks

| # | Risk Description | Probability | Impact | Level | Mitigation Strategy | Owner |
|---|---|---|---|---|---|---|
| R1 | **Regulatory compliance** — Crew duty-time rules (EU-OPS FTL / FAA Part 117) are complex and frequently updated; a compliance gap could make the product unusable for regulated operators. | High | High | **Critical** | Involve aviation domain expert from inception; build rule engine as a dedicated module with versioned regulation profiles; automated test suite against published regulation scenarios. | Project Manager + Analyst |
| R2 | **Scope creep** — Six major feature areas in one release risks diluting focus and missing deadlines. | High | High | **Critical** | Define strict MVP scope (flight ops + crew scheduling + dashboard only for v1); defer maintenance tracking, passenger services to v2; use phased roadmap with clear cut-off criteria. | Project Manager |
| R3 | **GDS/integration complexity** — Connecting to legacy GDS/booking systems may require protocols or APIs not publicly documented. | Medium | High | **High** | Early spike/PoC to identify available integration points and data formats for at least one major GDS vendor; build adapter pattern to isolate integration logic; include a contingency buffer in schedule. | Architect |
| R4 | **Data model inadequacy** — Airline domain entities (aircraft, routes, crew qualifications, certification chains) have complex relationships not obvious from surface-level requirements. | Medium | High | **High** | Inception elaboration: build core domain model with stakeholder review sessions; use event storming workshop with dispatchers and maintenance engineers to validate relationships before detailed design. | Architect + Analyst |
| R5 | **Real-time performance** — Live flight status updates for hundreds of concurrent flights require low-latency data pipelines that may not fit a standard web framework. | Medium | Medium | **Medium** | Technology spike early in Elaboration to evaluate WebSocket vs. Server-Sent Events vs. polling; define SLA for "real-time" (e.g., <5s latency); benchmark with synthetic load of 500 flights. | Architect + Developer |
| R6 | **Security & data privacy** — Passenger PNR data is subject to GDPR/DP laws; breaches carry heavy fines and reputational damage. | Medium | High | **High** | Privacy-by-design from the start; encrypt PII at rest and in transit; regular third-party security audit in each major milestone; data retention policy defined before construction begins. | Project Manager + Architect |
| R7 | **Stakeholder availability** — Key stakeholders (dispatchers, maintenance leads) have day jobs; limited bandwidth for requirements workshops. | Medium | Medium | **Medium** | Secure executive sponsorship to allocate 10% stakeholder time to the project; record all workshops asynchronously; use written scenarios and walkthroughs as fallback. | Project Manager |
| R8 | **Team skill gap** — Aviation domain knowledge may not exist within the development team, leading to costly rework on compliance-sensitive modules. | Medium | High | **High** | Pair developers with a subject-matter expert (SME) during Elaboration; build comprehensive glossary (`docs/glossary.md`) and decision log; require SME sign-off on all regulation-impacted stories before closure. | Analyst + PM |

## Risk Summary
| Level | Count | Risks |
|---|---|---|
| Critical | 2 | R1, R2 |
| High | 4 | R3, R4, R6, R8 |
| Medium | 2 | R5, R7 |

## Last Updated
2026-06-11 — Inception Phase initiation
