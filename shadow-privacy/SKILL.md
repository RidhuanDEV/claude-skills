---
name: shadow-privacy
description: "Data Privacy & Regulatory Engineering (UU PDP & GDPR). Use when classifying Data Spesifik vs Umum (UU No. 27/2022 Pasal 4), building consent ledgers (Pasal 20), orchestrating multi-store DSAR/erasure & crypto-shredding, running DPIA/ROPA (Pasal 31/34), gating cross-border & AI transfers (Pasal 56), redacting PII logs, or planning 3x24h breach response (Pasal 46). Escalate legal opinions to counsel."
---

# Shadow Privacy (`/shadow-privacy`) — UU PDP (UU No. 27/2022) & GDPR Engineering Auditor

Use this skill whenever the **Monarch** designs or modifies schemas storing personal data, builds consent/DSAR/erasure flows, integrates cloud/analytics/LLM processors, scans for PII log leaks, or prepares for Staging UAT / Production Go-Live.

## 1. Core Privacy Engineering Principles & Non-Negotiables

1. **Statutory Classification & Lawful Basis (`UU PDP Pasal 4 & 20` / `GDPR Art. 6 & 9`):** Classify every field into **Data Spesifik (`Pasal 4(2)`**: health, biometrics, genetics, criminal, children, personal finance -> mandatory `AES-256-GCM`+KMS column encryption, RBAC, `0` raw logs, `Pasal 34` DPIA at scale) vs **Data Umum (`Pasal 4(3)`**: name, NIK, NPWP, phone, email, address). Record an explicit lawful basis (`CONSENT`, `CONTRACT`, `LEGAL_OBLIGATION`, `VITAL_INTEREST`, `PUBLIC_INTEREST`, `LEGITIMATE_INTEREST`) — never bundle optional marketing consent into mandatory ToS.
2. **Multi-Store DSAR & Synthetic Erasure Rehearsals (`Pasal 5–13, 42–44`):** Trace a synthetic subject (`synthetic: true`) across ALL independently inventoried stores (`expected_stores`: primary DB, search, cache, warehouse, 3rd-party processors, backups). Distinguish live deletion (`DELETED_LIVE`) from backup TTL (`PENDING_BACKUP_EXPIRY`) and statutory accounting holds (`Pasal 20(2)(c)`), require redacted processor receipts, and never put raw personal data into evidence manifests.
3. **Governance & Cross-Border Cascade (`Pasal 31, 34, 51–56`):** Maintain versioned ROPA, enforce pre-launch DPIA on high-risk/AI/biometric features, require signed DPAs + sub-processor approval, and enforce the exact 3-step `Pasal 56` cascade (`56(2)` adequacy -> `56(3)` binding safeguards/SCC -> `56(4)` explicit consent) + PII tokenization before offshore LLM/SaaS calls.
4. **Fail-Closed PII Log Redaction & 3x24h Breach Readiness (`Pasal 35–39, 46, 57`):** Strip raw `NIK`, `NPWP`, `BPJS`, `rekam_medis`, `nomor_rekening`, and tokens at logger & APM roots. Escalate suspected personal data breaches immediately to DPO/Legal so written notices satisfy the **3 x 24 hour (72h)** statutory window (`Pasal 46(2)`: exposed data, chronology, remediation; `Pasal 57`: up to `2%` annual revenue fine).
5. **Legal Escalation Boundary:** Automated scans and technical checklists provide engineering evidence, NOT formal legal certification; escalate statutory interpretation, DPAs, and official regulatory filings to DPO / qualified Legal Counsel.

## 2. Deterministic Privacy & Synthetic Erasure CLI

Run offline checks (`L0`/`L1`) before claiming `VERIFIED-LOCAL`:
```powershell
python "shadow-privacy/scripts/privacy_pdp_auditor.py" --scan .
python "shadow-privacy/scripts/privacy_pdp_auditor.py" --self-test
python "shadow-privacy/scripts/privacy_pdp_auditor.py" --assess-erasure path/to/synthetic_manifest.json
python -m unittest discover -s "shadow-privacy/tests" -v
```
For `--assess-erasure`, supply `synthetic: true`, an independently established `expected_stores` list of redacted system aliases, and `receipts` keyed by those aliases (evidence references only, zero raw PII). An absent processor receipt or retained archive keeps the rehearsal open until independently verified by store owners. Graded specialist scenarios live in [evaluations.md](evaluations.md) (8 scenarios).

## Reference Guide

Load **only** the 1–2 modules matching the active subtask (never load all 6 at once):

| Task / Scenario | Tier | Load Reference |
| :--- | :--- | :--- |
| UU PDP `Pasal 4(2)`/`4(3)` & GDPR classification, 6 lawful bases (`Pasal 20`) & field metadata registry | CORE | [references/01-uu-pdp-and-gdpr-classification-and-legal-basis.md](references/01-uu-pdp-and-gdpr-classification-and-legal-basis.md) |
| Granular consent ledger (`consent_records`), instant withdrawal (`Pasal 9`), guardian consent & minimization | CORE | [references/02-consent-lifecycle-and-minimization.md](references/02-consent-lifecycle-and-minimization.md) |
| Multi-store DSAR erasure, vendor receipts, backup TTLs, legal-hold coexistence & crypto-shredding | CORE | [references/03-dsar-multi-store-erasure-and-crypto-shredding.md](references/03-dsar-multi-store-erasure-and-crypto-shredding.md) |
| ROPA (`Pasal 31`), DPIA triggers (`Pasal 34`), processor DPAs (`Pasal 51–52`) & DPO criteria (`Pasal 53–54`) | ADVANCED | [references/04-dpia-ropa-and-vendor-processor-controls.md](references/04-dpia-ropa-and-vendor-processor-controls.md) |
| `Pasal 56` 3-step cross-border cascade, offshore cloud/LLM PII tokenization & `Pasal 10` AI profiling override | ADVANCED | [references/05-cross-border-transfers-and-ai-data-governance.md](references/05-cross-border-transfers-and-ai-data-governance.md) |
| Fail-closed PII log/APM redaction (`NIK`/`NPWP`/`rekam_medis`) & `Pasal 46` `3x24h` breach response runbook | OPERATIONAL | [references/06-breach-3x24h-response-and-pii-log-redaction.md](references/06-breach-3x24h-response-and-pii-log-redaction.md) |

Do not load unrelated references unnecessarily.
