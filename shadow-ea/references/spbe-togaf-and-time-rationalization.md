# Indonesia 6-Domain SPBE, TOGAF 10 ADM & TIME Portfolio Rationalization Playbook

> Use this playbook when architecting multi-system enterprise IT portfolios (`TOGAF 10 ADM`), Indonesia **6-Domain SPBE (`Perpres 95/2018` & `132/2022`) + Satu Data (`Perpres 39/2019`)**, classifying **TIME** duplicate-application rationalization, or separating **ABB** vs **SBB** building blocks.

## 1. Core Concepts
Enterprise Architecture prevents duplicate government/enterprise systems, fragmented data silos, and vendor lock-in:
- **4 TOGAF Domains vs 6 Mandatory SPBE Domains:** Standard TOGAF (`Business`, `Data`, `Application`, `Technology`) drops two mandatory statutory SPBE domains in Indonesia (**`Keamanan SPBE`** & **`Layanan SPBE`**). Public-sector blueprints MUST map all **6 SPBE Domains**.
- **Vendor-Neutral ABB vs Concrete SBB:** Define vendor-neutral capability requirements (**Architecture Building Blocks — ABB**, e.g., *"OIDC Identity Broker & SPLP API Gateway"*) BEFORE naming candidate vendor/OSS implementations (**Solution Building Blocks — SBB**).

## 2. Technical Rules & Decision Matrix

| Framework / Classification | Axis / Domain Mapping | Mandatory Decision Rule |
| :--- | :--- | :--- |
| **Indonesia 6-Domain SPBE** (`Perpres 95/2018 & 132/2022`) | `PROSES_BISNIS`, `DATA_DAN_INFORMASI` (`Perpres 39/2019` Satu Data), `INFRASTRUKTUR_SPBE`, `APLIKASI_SPBE`, `KEAMANAN_SPBE`, `LAYANAN_SPBE` | All 6 required for `GOVERNMENT_SPBE`; specify Interoperability (`SPLP`), Metadata & Referensi Data |
| **TIME Quadrant (`INVEST`)** | `business_value >= 3.5` AND `tech_health >= 3.0` | Fund strategic roadmap & API exposure |
| **TIME Quadrant (`MIGRATE`)** | `business_value >= 3.5` AND `tech_health < 3.0` | Modernize incrementally (`/shadow-modernize` Strangler Fig) or consolidate |
| **TIME Quadrant (`TOLERATE` / `ELIMINATE`)** | `bv < 3.5`: Tolerate (`th >= 3.0`) or Eliminate (`th < 3.0`, or redundant duplicate `bv < 4.0`) | Flag duplicate capabilities for consolidation (`EA-DUP-*`) |

## 3. Implementation Examples

### 6-Domain SPBE & Portfolio JSON Input (`scripts/ea_portfolio_engine.py`)
```json
{
  "org_type": "GOVERNMENT_SPBE",
  "spbe_domains_covered": [
    "PROSES_BISNIS", "DATA_DAN_INFORMASI", "INFRASTRUKTUR_SPBE",
    "APLIKASI_SPBE", "KEAMANAN_SPBE", "LAYANAN_SPBE"
  ],
  "applications": [
    { "system_id": "SIMPEG-CORE", "name": "HRIS Terintegrasi", "business_capability": "Civil Servant Lifecycle", "business_value": 4.5, "tech_health": 3.8, "data_owner": "BKD" },
    { "system_id": "ABSEN-SILO", "name": "Unit Attendance Legacy", "business_capability": "Civil Servant Lifecycle", "business_value": 2.9, "tech_health": 1.8, "data_owner": "Dinas-X" }
  ],
  "abb_sbb_gaps": [
    { "abb_id": "ABB-API-GW-01", "capability": "SPLP Compliant API Gateway", "candidate_sbb": "Kong / APISIX (Vendor-Neutral Evaluation)" }
  ]
}
```
```powershell
python "shadow-ea/scripts/ea_portfolio_engine.py" --analyze-portfolio portfolio.json
```

## 4. Best Practices
- Pair every **Satu Data Indonesia (`Perpres 39/2019`)** application mapping with an explicit **Wali Data / Data Owner** (`data_owner != "UNASSIGNED"`), standardized kode referensi, and API exchange standard rather than manual CSV emails.
- Feed TIME consolidation findings (`MIGRATE`/`ELIMINATE`) cleanly downstream to `/shadow-modernize` (due diligence), `/shadow-presales` (infrastructure consolidation TCO), and `/shadow-pmo` (multi-year transition schedule).

## 5. Anti-Patterns (`WRONG` vs `RIGHT`)
- **WRONG (Vendor-locked ABB blueprints & 4-domain SPBE truncation):** Writing proprietary product names directly inside vendor-neutral ABB blueprints, or omitting `KEAMANAN_SPBE` and `LAYANAN_SPBE` on Indonesian government EA blueprints.
  **RIGHT:** Separate vendor-neutral `abb_id` requirements from evaluated `candidate_sbb` options, and validate all 6 SPBE domains explicitly via `ea_portfolio_engine.py`.
- **WRONG (Using `/shadow-ea` for single-application microservice/class design):** Generating C4 container internals of a single CRUD backend using enterprise SPBE frameworks.
  **RIGHT:** Delegate single-application architecture to `/shadow-architect`; reserve `/shadow-ea` for multi-system portfolios, SPBE/TOGAF blueprints, and TIME rationalization.

## 6. Production Considerations
- **Document Boundary:** Export formal `ARCHITECTURE_REPORT` blueprints exclusively through `shadow-doc/scripts/doc_orchestrator.py` (`adapt_pmo_or_ea_payload`) so SPBE/TIME matrices render consistently across `.docx`/`.pdf` deliverables.
