# Technical Forensics, Business-Rule Archaeology & Migration Economics

## 1. The 8 Technical Due Diligence Areas

| Area | Primary Evidence Sources | Key Risks Evaluated |
|---|---|---|
| **1. Code & Dependencies** | Lockfiles (`package-lock.json`, `composer.lock`, `go.sum`, `requirements.txt`), runtime configs | EOL runtimes/frameworks, transitive CVE blast radius, cyclic complexity hotspots |
| **2. Architecture** | Module/package dependency graph, shared DB tables, circular imports | Tight coupling, god services, hidden synchronous RPC chains |
| **3. Data** | DDL migrations, triggers, stored procedures, orphan foreign keys, reconciliation scripts | Missing referential integrity, split-brain writes, unstructured legacy BLOBs/JSON |
| **4. Operations** | Deployment pipelines, SLO/SLA metrics, incident logs, backup/restore drills | Manual FTP/SSH deploys, single points of failure, lack of distributed correlation |
| **5. Security** | AuthN/AuthZ middleware, secret scanning, OWASP ASVS controls, audit trails | Hardcoded secrets, IDOR, outdated TLS/crypto, unpinned supply chain |
| **6. Business** | Transaction throughput/value, downtime cost/hour, vendor lock-in clauses | High revenue-per-hour blast radius, proprietary vendor licensing traps |
| **7. Modernization Strategy** | TIME (`Tolerate/Invest/Migrate/Eliminate`) & 6R/7R (`Retain`, `Rehost`, `Replatform`, `Refactor`, `Rearchitect`, `Replace`, `Retire`) | Strangler Fig seams, CDC dual-write vs read-replica migration, rollback readiness |
| **8. Economics** | Build effort, coexistence/dual-run infra, data cleansing, cutover & shadow-run cost | Full Rewrite "Second-System" overrun risk vs incremental Refactor payback |

---

## 2. Multi-Dimensional Risk Vectors & Anti-Bias Rules

Never collapse technical due diligence into a single uncalibrated "Tech Debt = 72/100" number. Maintain a **Risk Vector**:
$$\vec{R} = (r_{\text{code}}, r_{\text{arch}}, r_{\text{data}}, r_{\text{ops}}, r_{\text{sec}}, r_{\text{business}}), \quad \text{each } r_i \in [0, 5] \text{ paired with } \text{Confidence}_i \in \{\text{HIGH}, \text{MEDIUM}, \text{LOW}\}$$

### Why "No Tests" Does Not Equal "Full Rewrite"
If a legacy system exhibits:
- **High Business-Rule Complexity / Undocumented Domain Logic**, AND
- **Stable Production Operations / Low Incident Rate**, AND
- **Low Automated Test Coverage**:
A **Full Rewrite** risks severe **business-rule loss** and dual-system synchronization drift. The safer engineering sequence is **Business-Rule Archaeology -> Characterization Tests (Golden I/O Snapshots) -> Strangler Fig Incremental Extraction**.

---

## 3. Business-Rule Archaeology Protocol

1. **Database Constraints & Stored Logic**: Extract every `CHECK`, `UNIQUE`, `TRIGGER`, `FUNCTION`, and `VIEW`.
2. **Code Hotspots & Branching**: Map high-churn financial/eligibility/tax calculation files (`git log --stat`).
3. **Behavioral Ground Truth**: Compare production API responses, DB rows, and batch CSV exports against outdated specs to identify undocumented edge cases before extracting a bounded context.
