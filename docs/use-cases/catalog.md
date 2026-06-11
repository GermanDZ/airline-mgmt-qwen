# Use Case Catalog — Airline Management System

## Overview
This catalog lists all identified use cases organized by functional area. Two use cases are detailed (marked **Detailed**) for MVP scope; the rest are high-level descriptions suitable for v2+.

## 1. Flight Operations

| UC-ID | Use Case | Priority | Detail Level | Notes |
|---|---|---|---|---|
| UC-FO-01 | **Create and File Flight Plan** | P0 | **Detailed** | Core MVP use case |
| UC-FO-02 | Track In-Flight Status | P0 | **Detailed** | Core MVP use case |
| UC-FO-03 | Manage Delay / Diversion | P1 | High-level | Triggered by status events |
| UC-FO-04 | View Flight Manifest | P1 | High-level | Read-only, shared with Passenger Services |
| UC-FO-05 | NOTAM / Aerodrome Alert Feed | P2 | High-level | Informational only in v1 |

## 2. Crew Management

| UC-ID | Use Case | Priority | Detail Level | Notes |
|---|---|---|---|---|
| UC-CM-01 | Generate Crew Roster | P0 | **Detailed** | Core MVP use case |
| UC-CM-02 | Manage Crew Certifications | P1 | High-level | Required for roster validation |
| UC-CM-03 | Handle Crew Replacement / Standby | P1 | High-level | Linked to roster and flight ops |
| UC-CM-04 | Track Duty-Time Compliance | P0 | **Detailed** | Must validate against regulation profiles |

## 3. Maintenance Tracking

| UC-ID | Use Case | Priority | Detail Level | Notes |
|---|---|---|---|---|
| UC-MT-01 | Create Maintenance Work Order | P2 | High-level | Deferred to v2 |
| UC-MT-02 | Log Aircraft Defect | P2 | High-level | Deferred to v2 |
| UC-MT-03 | Manage Parts Inventory | P2 | High-level | Deferred to v2 |

## 4. Passenger Services

| UC-ID | Use Case | Priority | Detail Level | Notes |
|---|---|---|---|---|
| UC-PS-01 | Create / Modify PNR | P2 | High-level | Deferred to v2; may integrate with GDS |
| UC-PS-02 | Check-in Passenger | P2 | High-level | Deferred to v2 |
| UC-PS-03 | Rebook Passenger on Delayed Flight | P2 | High-level | Deferred to v2 |

## 5. Dashboard & Reporting

| UC-ID | Use Case | Priority | Detail Level | Notes |
|---|---|---|---|---|
| UC-DR-01 | View Operations Dashboard | P0 | **Detailed** | Role-based view of all active flights, crews, statuses |
| UC-DR-02 | Generate KPI Report | P1 | High-level | Scheduled or ad-hoc, exportable to PDF/CSV |

## 6. Administration

| UC-ID | Use Case | Priority | Detail Level | Notes |
|---|---|---|---|---|
| UC-AD-01 | Manage Users and Roles (RBAC) | P0 | High-level | Foundation for all other use cases |
| UC-AD-02 | View Audit Log | P1 | High-level | Required for compliance |

## Summary by Priority

| Priority | Count | Use Cases |
|---|---|---|
| P0 (MVP) | 6 | UC-FO-01, UC-FO-02, UC-CM-01, UC-CM-04, UC-DR-01, UC-AD-01 |
| P1 | 5 | UC-FO-03, UC-FO-04, UC-CM-02, UC-CM-03, UC-DR-02, UC-AD-02 |
| P2 | 6 | MT-01, MT-02, MT-03, PS-01, PS-02, PS-03, FO-05 |

**Total identified**: 20 use cases across 6 functional areas. **MVP scope (P0)**: 6 use cases.
