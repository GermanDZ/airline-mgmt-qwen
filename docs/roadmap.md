# Project Roadmap

## T-001: Initialize OpenUP Project Structure
**Status**: completed
**Priority**: high
**Description**: Initial project setup and documentation structure
**Iteration**: 0 (inception)

## T-002: Define Project Vision
**Status**: completed
**Priority**: high
**Description**: Created vision document defining scope, stakeholders, and business case for Airline Management system
**Iteration**: 0 (inception)

## T-003: Identify Key Use Cases
**Status**: completed
**Priority**: high
**Description**: 20 use cases catalogued across 6 functional areas; 2 detailed (MVP): UC-FO-01 Flight Plan, UC-CM-01 Crew Roster
**Iteration**: 0 (inception)

## T-004: Assess Technical Feasibility
**Status**: completed
**Priority**: medium
**Description**: Architecture baseline, domain model, regulation engine approach, tech stack decisions for MVP scope. 6 ADRs created covering tech stack, data model, regulation engine, real-time updates, audit logging, event backbone.
**Iteration**: 1 (elaboration)

## T-005: Document Risks and Mitigations
**Status**: completed
**Priority**: high
**Description**: Created risk list with 8 identified risks; 2 critical (regulatory compliance, scope creep), 4 high
**Iteration**: 0 (inception)

## T-006: Create Initial Project Plan
**Status**: completed
**Priority**: high
**Description**: Comprehensive construction plan with 5 sprints, ~126 story points, 14-week timeline. Key dependency: SME engagement for regulation engine (Sprint 2) before construction starts.
**Iteration**: 2 (planning)
**PR**: [#1](https://github.com/GermanDZ/airline-mgmt-qwen/pull/1)

## Inception Summary (Iteration 0)
- Vision document: complete (docs/vision.md)
- Risk list: 8 risks identified, 2 critical (docs/risk-list.md)
- Use cases: 20 catalogued, 2 detailed for MVP
- MVP scope: Flight Ops + Crew Mgmt + Dashboard + Admin (6 P0 use cases)

## Elaboration Summary (Iteration 1)
- Task: T-004 Technical Feasibility Assessment — completed
- Architecture: 5 bounded contexts, 6 ADRs
- Tech stack confirmed: Python/FastAPI + React/TS + PostgreSQL + Redis + AWS ECS
- Risks assessed: R1 (FEASIBLE with SME), R2 (MANAGEABLE)

## Planning Summary (Iteration 2 — Completed)
- Task: T-006 Initial Project Plan — completed
- Deliverable: Construction plan with 5 sprints, ~126 story points, 14-week timeline
- Key dependency: SME engagement required before Sprint 2 (regulation engine)

## T-007: Construction Sprint 0 — Foundation Scaffolding
**Status**: in-progress
**Priority**: high
**Description**: Project scaffolding: FastAPI backend + React frontend + PostgreSQL DB schema (Alembic), GitHub Actions CI/CD pipeline, authentication service skeleton (JWT + RBAC model), audit logging infrastructure, OpenAPI contract definition. Foundation for all subsequent sprints.
**Phase**: construction, Iteration 3
**Team**: openup-construction-team-t007 (developer + tester)
