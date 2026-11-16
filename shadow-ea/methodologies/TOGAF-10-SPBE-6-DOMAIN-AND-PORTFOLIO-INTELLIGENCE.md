# TOGAF 10, SPBE 6-Domain Crosswalk & IT Portfolio Intelligence Methodology

## 1. Explicit Crosswalk: TOGAF 10 ADM (4 Domains) <-> Indonesian SPBE (6 Domains)

Under **Perpres Nomor 95 Tahun 2018** and **Perpres Nomor 132 Tahun 2022**, Indonesian government enterprise architecture mandates **6 distinct domains** rather than collapsing Security and Public Services into Application/Technology:

| SPBE Domain (`Perpres 95/2018` & `132/2022`) | TOGAF 10 Mapping | Mandatory Artifacts & Standards |
|---|---|---|
| **1. Arsitektur Proses Bisnis** | `Phase B — Business Architecture` | Value streams, cross-agency BPMN workflows, elimination of redundant bureaucratic steps |
| **2. Arsitektur Data dan Informasi** | `Phase C — Data Architecture` | **Satu Data Indonesia (`Perpres 39/2019`)**: Data Standards, Metadata, Interoperability specs, Master/Reference Data ownership |
| **3. Arsitektur Infrastruktur SPBE** | `Phase D — Technology Architecture` | Pusat Data Nasional (PDN) / Cloud / Hybrid topology, network zoning, DR/RPO/RTO |
| **4. Arsitektur Aplikasi SPBE** | `Phase C — Application Architecture` | Shared vs specific application catalog, API Gateway, duplicate app consolidation |
| **5. Arsitektur Keamanan SPBE** | Cross-cutting (`Phase A-G` Security Viewpoint) | BSSN cryptographic/TTE compliance, IAM, SOC telemetry, UU PDP data protection |
| **6. Arsitektur Layanan SPBE** | `Phase B/C — Business Service Catalog` | Citizen/business/ASN service portals, omnichannel SLA, integrated life-event services |

---

## 2. Application Portfolio Management (TIME Classification)

Evaluate every system across **Business Value (1–5)** vs **Technical & Security Health (1–5)**:
- **`INVEST` (High Business Value, High/Moderate Tech Health)**: Flagship platforms receiving strategic feature & resilience investment.
- **`MIGRATE` (High Business Value, Low Tech Health)**: Business-critical legacy cores handed to `/shadow-modernize` for **Strangler Fig** or **Phased Modernization**.
- **`TOLERATE` (Low/Stable Business Value, Acceptable Health)**: Maintain at minimum OPEX until scheduled retirement without major new investment.
- **`ELIMINATE` (Low Business Value or Redundant Duplicate, Low Health)**: Retire and consolidate data into surviving `INVEST` system of record.

---

## 3. Architecture Building Blocks (ABB) vs Solution Building Blocks (SBB)

- **ABB (Vendor-Neutral)**: Defines *what* capability, contract, NFR, and compliance rule is required (e.g., *"Event-driven transactional ledger with immutable audit log and 99.95% availability"*).
- **SBB (Concrete Implementation)**: Defines *which* concrete technology fulfills the ABB (e.g., *"PostgreSQL 16 HA + Outbox Worker + OpenTelemetry"*), allowing `/shadow-presales` to evaluate multiple vendors fairly against the same ABB.

---

## 4. Architecture Governance & Design Authority

1. Maintain **Architecture Principles**, **Technology Standards Catalog** (`Approved`, `Contain/Legacy`, `Retired`), and **Architecture Decision Records (`ADR`)**.
2. Conduct **Architecture Compliance Reviews** at project gates (`Discovery`, `Pre-Procurement`, `Pre-UAT`) issuing `COMPLIANT`, `CONDITIONALLY_COMPLIANT_WITH_DISPENSATION`, or `NON_COMPLIANT`.
