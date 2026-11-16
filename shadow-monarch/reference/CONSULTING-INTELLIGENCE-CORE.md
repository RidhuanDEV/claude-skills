# CONSULTING-INTELLIGENCE-CORE — Shared Foundation for Enterprise IT Consulting

Use this module alongside `/shadow-presales`, `/shadow-grc`, `/shadow-modernize`, `/shadow-pmo`, and `/shadow-ea` so every consulting engagement operates as one evidence-linked, audit-defensible advisory system rather than disconnected document generators.

---

## 1. Seven Shared Consulting Capabilities

1. **Context-Aware Methodology Selection (`consulting-core/industry_packs.json`)**:
   - Identify `org_type` (`GOVERNMENT_SPBE`, `BANKING`, `FINTECH`, `BUMN`, `GENERAL_ENTERPRISE`) and `engagement_type` (`PRESALES`, `ADVISORY`, `ASSESSMENT`, `AUDIT_ASSURANCE`, `DUE_DILIGENCE`, `PMO_DELIVERY`, `ARCHITECTURE`) before selecting frameworks.
   - Never blindly apply COBIT, TOGAF, or private-sector rules without checking sector applicability and access boundaries.
2. **Evidence & Provenance Engine (`schemas/engagement_bundle.schema.json`)**:
   - Every non-trivial finding must bind to `evidence_refs[]` pointing to `evidence_registry[]` (`evidence_id`, `source_type`, `source_path`, `collected_at`, `method`, `integrity_hash`) plus explicit `confidence` (`HIGH`/`MEDIUM`/`LOW`) and `limitations[]`.
3. **Versioned Regulatory Knowledge Engine (`regulations_registry.json`)**:
   - Always check `effective_date`, `supersedes`, and `verification_status` before citing a regulation.
   - Example: In Indonesian commercial banking, **PADK OJK No. 1 Tahun 2026** (effective **1 March 2026**) implements **POJK 11/POJK.03/2022** and revokes **SEOJK 21/SEOJK.03/2017**; citing the revoked SEOJK as active control fails Hard Gate `HG1`.
   - Respect copyrighted standards (`ISO/IEC 27001:2022`, `COBIT 2019`, `TOGAF 10`): map controls and methodology legitimately without reproducing proprietary full text.
4. **Quantitative Decision & Uncertainty Engine**:
   - Separate deterministic formulas from LLM judgment. Output `conservative`, `expected`, and `stress` scenarios, explicit `assumption_register[]`, sensitivity sweeps, and MCDA trade-offs instead of unverified single point estimates.
5. **Cross-Skill Traceability**:
   - Connect outputs across skills under one `engagement_id`: `EA (SYS-*, EA-*) -> Modernize (MOD-*, DEC-*) -> GRC (GRC-*, CTRL-*) -> Presales (REQ-*, TCO-*) -> PMO (WBS-*, CR-*)`.
6. **Professional Judgment & Human Escalation Gates**:
   - Never cross statutory or professional boundaries autonomously:
     - Never approve or set official **HPS** on behalf of **PPK** (`Perpres 46/2025`).
     - Never issue official **ISO 27001 Certification** or **SPBE/OJK Regulatory Sign-Off** from an advisory self-assessment.
     - Never issue a binding legal determination on **Paid Change Request (CR)** liability without contract/legal counsel & CCB approval.
7. **Independent Adversarial Review & Non-Compensable Competency Scorecard**:
   - Every deliverable runs a dual-pass check (`Consultant` + `Independent Reviewer`) and is scored across 6 weighted dimensions (threshold >= `90/100`) plus **5 Non-Compensable Hard Gates** (`HG1`–`HG5`) enforced by:
     ```powershell
     python "shadow-monarch/consulting-core/scripts/consulting_core.py" --self-test
     python "shadow-monarch/consulting-core/scripts/consulting_core.py" --check-regulations --sector BANKING --cite PADK-OJK-1-2026
     python "shadow-monarch/consulting-core/scripts/consulting_core.py" --validate-bundle path/to/bundle.json
     ```
