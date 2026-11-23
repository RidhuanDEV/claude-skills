# 01. Indonesia 6-Domain SPBE (`Perpres 95/2018 & 132/2022`) & Satu Data (`Perpres 39/2019`)

## 1. Purpose & Activation Conditions
Use this playbook when authoring, auditing, or aligning **Arsitektur SPBE (Sistem Pemerintahan Berbasis Elektronik)** blueprints for Indonesian ministries, agencies, or regional governments (`K/L/PD`). Standard 4-domain enterprise architecture frameworks omit two mandatory statutory SPBE domains in Indonesia; this playbook enforces full **6-Domain SPBE compliance** paired with **Satu Data Indonesia (`Perpres 39/2019`)** data ownership and `SPLP` interoperability.

Activate this playbook when:
- Designing or reviewing an Indonesian public-sector enterprise architecture blueprint (`org_type: "GOVERNMENT_SPBE"`).
- Validating all 6 SPBE domains and Satu Data `Wali Data` ownership via `shadow-ea/scripts/ea_portfolio_engine.py --analyze-portfolio`.
- Mapping legacy siloed government applications into unified national/regional shared services (`Aplikasi Umum` vs `Aplikasi Khusus`, `SPLP` API integration).

## 2. Prerequisites
- Agency organizational mandate, existing application catalog (`SYS-*`), business-process inventory (`Probis`), and regulatory anchor (`Perpres 95/2018`, `Perpres 132/2022`, `Perpres 39/2019`).
- Deep companion methodology: [`../methodologies/TOGAF-10-SPBE-6-DOMAIN-AND-PORTFOLIO-INTELLIGENCE.md`](../methodologies/TOGAF-10-SPBE-6-DOMAIN-AND-PORTFOLIO-INTELLIGENCE.md) & [`../playbooks/EA-BLUEPRINT-AND-PORTFOLIO-TEMPLATES.md`](../playbooks/EA-BLUEPRINT-AND-PORTFOLIO-TEMPLATES.md).

## 3. Technical Principles & Constraints
1. **All 6 SPBE Domains Are Mandatory (Never Truncate to 4 TOGAF Domains)**:
   Every Indonesian government EA blueprint (`Perpres 95/2018` & `Perpres 132/2022`) MUST explicitly model ALL 6 domains:
   1. **`PROSES_BISNIS`** (Arsitektur Proses Bisnis — aligned to `Probis` & agency mandate)
   2. **`DATA_DAN_INFORMASI`** (Arsitektur Data & Informasi — aligned to **Satu Data Indonesia `Perpres 39/2019`**)
   3. **`INFRASTRUKTUR_SPBE`** (Arsitektur Infrastruktur — Pusat Data Nasional `PDN` / Intra-Gov Network / SPLP)
   4. **`APLIKASI_SPBE`** (Arsitektur Aplikasi — prioritizing `Aplikasi Umum` shared national services over redundant `Aplikasi Khusus` silos)
   5. **`KEAMANAN_SPBE`** (Arsitektur Keamanan — BSSN alignment, Indeks KAMI, IAM/SSO, encryption, CSIRT, UU PDP)
   6. **`LAYANAN_SPBE`** (Arsitektur Layanan — citizen/G2C, G2B, G2G, G2E service portals & measurable SLA outcomes)
   Omitting `KEAMANAN_SPBE` or `LAYANAN_SPBE` causes immediate compliance failure in `ea_portfolio_engine.py` and KemenPANRB SPBE evaluations!
2. **Satu Data Indonesia (`Perpres 39/2019`) 4-Principle Interoperability**:
   Every data entity in `DATA_DAN_INFORMASI` MUST specify:
   - **Standar Data** (canonical schema, format, taxonomy)
   - **Metadata Baku** (standardized descriptive/structural metadata)
   - **Interoperabilitas Data** (API exchange via `SPLP` — Sistem Penghubung Layanan Pemerintah — never manual WhatsApp/email CSV swaps!)
   - **Kode Referensi & Data Induk** + explicit **Wali Data / Data Owner** (`data_owner != "UNASSIGNED"` and clear `Produsen Data` vs `Wali Data` accountability).
3. **Zero Unjustified Silo Duplication (`Aplikasi Umum` First)**:
   Flag redundant departmental applications (`ABSEN-SILO`, `SURAT-UNIT-X`) that duplicate shared national/agency capabilities for consolidation via TIME rationalization (`03-time-portfolio-rationalization-and-arb-governance.md`).
4. **TOGAF 4-Domain <-> SPBE 6-Domain Crosswalk**:
   When collaborating with multinational consultants or BUMN teams fluent in TOGAF 10, publish an explicit mapping table showing how `KEAMANAN_SPBE` elevates security from a crosscutting concern into a first-class statutory domain and how `LAYANAN_SPBE` anchors citizen-facing service outcomes directly to `PROSES_BISNIS`.

## 4. Architecture & Implementation
### Mandatory TOGAF 4-Domain <-> SPBE 6-Domain Crosswalk
| SPBE Statutory Domain (`Perpres 132/2022`) | Closest TOGAF 10 Alignment | Mandatory Statutory Artifacts | Collaborating Skill |
| :--- | :--- | :--- | :--- |
| `1. PROSES_BISNIS` | Business Architecture | Peta Proses Bisnis (`RAD` / Level 1–4), Value Streams | `/shadow-discovery` |
| `2. DATA_DAN_INFORMASI` | Data Architecture | Daftar Data, `Wali Data`, Kode Referensi, Satu Data Metadata | `/shadow-db`, `/shadow-privacy` |
| `3. INFRASTRUKTUR_SPBE` | Technology Architecture | PDN/Cloud Topology, Jaringan Intra, `SPLP` Penghubung | `/shadow-ops`, `/shadow-presales` |
| `4. APLIKASI_SPBE` | Application Architecture | Katalog `Aplikasi Umum` vs `Khusus`, TIME Rationalization | `/shadow-modernize` |
| `5. KEAMANAN_SPBE` | Crosscutting Security *(Elevated to First-Class Domain!)* | BSSN Indeks KAMI map, IAM/SSO, CSIRT, UU PDP Controls | `/shadow-grc`, `/shadow-sec` |
| `6. LAYANAN_SPBE` | Business Service Catalog *(Elevated to First-Class Domain!)* | Katalog Layanan G2C/G2B/G2G/G2E, Omni-Channel Portal, SLAs | `/shadow-design` |

### Strict TypeScript 6-Domain SPBE & Satu Data Validator
```typescript
export const REQUIRED_SPBE_DOMAINS = [
  'PROSES_BISNIS',
  'DATA_DAN_INFORMASI',
  'INFRASTRUKTUR_SPBE',
  'APLIKASI_SPBE',
  'KEAMANAN_SPBE',
  'LAYANAN_SPBE',
] as const;

export type SpbeDomain = (typeof REQUIRED_SPBE_DOMAINS)[number];

export interface SpbeSystemEntry {
  readonly systemId: string;
  readonly dataOwner: string;
  readonly usesSplpOrStandardApi: boolean;
}

export function auditSpbeCompliance(
  coveredDomains: readonly string[],
  systems: readonly SpbeSystemEntry[],
): { readonly compliant: boolean; readonly gaps: readonly string[] } {
  const gaps: string[] = [];
  const coveredSet = new Set(coveredDomains);
  for (const domain of REQUIRED_SPBE_DOMAINS) {
    if (!coveredSet.has(domain)) {
      gaps.push(`MISSING_SPBE_DOMAIN:${domain}`);
    }
  }
  for (const sys of systems) {
    if (sys.dataOwner.trim() === '' || sys.dataOwner.trim().toUpperCase() === 'UNASSIGNED') {
      gaps.push(`SATU_DATA_MISSING_WALI_DATA:${sys.systemId}`);
    }
    if (!sys.usesSplpOrStandardApi) {
      gaps.push(`INTEROP_MANUAL_SILO:${sys.systemId}`);
    }
  }
  return { compliant: gaps.length === 0, gaps };
}
```

### Deterministic Verification Command (`ea_portfolio_engine.py`)
```powershell
python "shadow-ea/scripts/ea_portfolio_engine.py" --analyze-portfolio path/to/spbe_portfolio.json
```

## 5. Platform / Vendor Variations
- **Central Ministries (`Kementerian / Lembaga`)**: Align `Aplikasi Umum` integration directly to national shared services (e.g., `SRIKANDI`, `SIASN`, `SAKTI`, `INA-Digital` / `SPLP Nasional`) and register metadata with `data.go.id` (Satu Data Portal).
- **Provincial / Municipal Governments (`Pemda`)**: Focus on consolidating redundant `OPD` (Dinas) bespoke apps into one shared regional super-service portal backed by a centralized `Diskominfo` Wali Data & SPLP gateway.

## 6. Decision Matrix & Trade-Offs
| Public-Sector Architecture Choice | SPBE Score & Governance Impact | Delivery Trade-Off |
| :--- | :--- | :--- |
| **Reuse `Aplikasi Umum` + `SPLP` API integration** | High SPBE compliance; eliminates redundant maintenance budget | Requires aligning local agency process quirks to national standard |
| **Build Bespoke `Aplikasi Khusus` per Dinas** | Penalizes SPBE consolidation score; creates permanent data silos | Faster isolated kickoff but causes long-term integration & Harwat sprawl |

## 7. Real Production Scenario
**Context:** A provincial government commissioned an Enterprise Architecture Masterplan (`Peta Rencana SPBE`). The initial consultant draft copied a generic 4-domain TOGAF template, omitting `KEAMANAN_SPBE` and `LAYANAN_SPBE`, and listed `47` agency apps with `data_owner: "UNASSIGNED"`.
**Correction:** Running `ea_portfolio_engine.py --analyze-portfolio` flagged both missing statutory domains and 11 duplicate attendance/correspondence silos across Dinas units. Adding explicit `KEAMANAN_SPBE` (aligned with `/shadow-grc` Indeks KAMI) and `LAYANAN_SPBE`, assigning `Diskominfo` / `BKD` `Wali Data` owners, and proposing SPLP consolidation raised the agency's SPBE Architecture audit readiness cleanly.

## 8. Failure Modes & Edge Cases
- **WRONG (Delivering a 4-domain TOGAF blueprint for an Indonesian ministry omitting `KEAMANAN_SPBE` and `LAYANAN_SPBE`, or leaving `data_owner = UNASSIGNED`):** Fails statutory Perpres 132/2022 & Perpres 39/2019 SPBE evaluations.
  **RIGHT:** Model all 6 SPBE domains explicitly, assign named `Wali Data` owners, and specify `SPLP`/API interoperability for every cross-agency exchange.
- **WRONG (Designing a single microservice's internal controllers using 6-Domain SPBE):** Over-engineers single-app architecture.
  **RIGHT:** Route single-application design to `/shadow-architect`; reserve `/shadow-ea` for multi-system institutional blueprints.

## 9. Testing & Verification
- Run `python shadow-ea/scripts/ea_portfolio_engine.py --self-test` (`8/8` probes) and `--analyze-portfolio <portfolio.json>` verifying zero missing SPBE domains (`org_type: "GOVERNMENT_SPBE"`).
- Export formal `ARCHITECTURE_REPORT` blueprints via `shadow-doc/scripts/doc_orchestrator.py` (`adapt_pmo_or_ea_payload`).

## 10. Operational Considerations
- Synchronize `Arsitektur SPBE` updates annually with the agency's `Peta Rencana SPBE` (5-year roadmap) and budget clearance cycle (`Bappenas` / `KemenPANRB` / `Diskominfo` clearance).

## 11. Authoritative References
- **Perpres Nomor 95 Tahun 2018** — *Sistem Pemerintahan Berbasis Elektronik (SPBE)*.
- **Perpres Nomor 132 Tahun 2022** — *Arsitektur Sistem Pemerintahan Berbasis Elektronik Nasional (6 Domain)*.
- **Perpres Nomor 39 Tahun 2019** — *Satu Data Indonesia*.

## 12. Limitations & When NOT to Use
- **Do NOT use** `/shadow-ea` for single-application C4 container/component design or Monolith vs Microservices decisions — route to `/shadow-architect`.
- **Do NOT use** `/shadow-ea` for formal Indeks KAMI BSSN control fieldwork testing — coordinate security assurance with `/shadow-grc`.
