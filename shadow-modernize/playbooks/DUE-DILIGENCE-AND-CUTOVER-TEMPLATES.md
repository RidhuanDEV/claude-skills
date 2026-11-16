# Due Diligence & Phased Cutover Templates

## 1. System Archaeology Report
- **System ID & Scope** (`SYS-*` linked from `/shadow-ea`)
- **Runtime, Framework & Lockfile Inventory** (with `SHA-256` manifest hashes)
- **Undocumented Business Rules Discovered** (DB triggers, cron jobs, hardcoded tax/fee exceptions)
- **Access Limitations** (what was NOT measured: prod logs, load metrics, DB row counts).

## 2. Multi-Dimensional Technical Risk Register
| Risk ID | Dimension (`Code/Arch/Data/Ops/Sec/Business`) | Severity (`CRITICAL..LOW`) | Score (0–5) | Evidence Confidence | Evidence Ref (`EVD-*`) | Remediation |
|---|---|---|---:|---|---|---|

## 3. Modernization Business Case (3–5 Year TCO Comparison)
| Option | Build Cost | Coexistence / Dual-Run Cost | Ops + Support (3–5 Yr) | Risk-Adjusted Expected Delay Cost | Total Risk-Adjusted TCO | Recommendation |
|---|---:|---:|---:|---:|---:|---|

## 4. Phased Cutover & Rollback Playbook
Define **Shadow Traffic -> Canary % -> Dual-Write Reconciliation Checksum -> Cutover Window -> Instant DNS/Feature-Flag Rollback Trigger** (strict RPO/RTO bounds).
