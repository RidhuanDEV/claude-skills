# 04. DPIA, ROPA & Vendor/Processor Governance

## 1. Purpose & Activation Conditions
Establish auditable privacy governance artifacts required by **UU PDP (`Pasal 31, 34, 51–54`)** and **GDPR (`Art. 28, 30, 35, 37`)** — Record of Processing Activities (ROPA), Data Protection Impact Assessments (DPIA), Data Processing Agreements (DPA), sub-processor approval tracking, and DPO triggers. Load before launching high-risk features (biometrics, health/finance at scale, automated AI profiling) or onboarding new SaaS/cloud/LLM vendors.

## 2. Prerequisites
- Field-level privacy inventory (`01`) and list of every third-party processor/sub-processor receiving personal data.

## 3. Technical Principles & Constraints
- **ROPA (`UU PDP Pasal 31` / `GDPR Art. 30`):** Maintain a version-controlled `docs/privacy/ropa.yaml` mapping EVERY processing activity: `(activity_id, purpose, lawful_basis, data_categories, subject_categories, storage_stores, processors, retention_ttl, security_controls, owner)`.
- **Mandatory DPIA Triggers (`UU PDP Pasal 34` / `GDPR Art. 35`):** Require a documented **Data Protection Impact Assessment** BEFORE production rollout whenever a feature involves ANY of:
  1. Automated decision-making / profiling with legal or significant impact (credit scoring, fraud bans, automated hiring — `Pasal 10`),
  2. Processing **Data Spesifik (`Pasal 4(2)`)** at scale (health, biometrics, financial, children),
  3. Systematic large-scale monitoring of public/user behavior (CCTV/location tracking, behavioral profiling),
  4. Merging/matching datasets from multiple sources,
  5. Adopting **new high-risk technologies** (biometric liveness, facial recognition, LLM/GenAI processing personal data).
- **Processors & Sub-Processors (`Pasal 51–52` / `GDPR Art. 28`):** Every external vendor processing personal data on your behalf (cloud host, ESP, analytics SaaS, LLM API, payment gateway) requires a signed **DPA** enforcing purpose limitation, security safeguards, breach notification obligations, and **written Controller approval before onboarding sub-processors**.
- **DPO (Pejabat/Petugas Pelindung Data Pribadi — `Pasal 53–54`):** Flag mandatory DPO appointment whenever core activities involve: (a) public service delivery, (b) core large-scale regular systematic monitoring, OR (c) core large-scale processing of Specific or criminal personal data.

## 4. Architecture & Implementation
Machine-checkable ROPA entry (`docs/privacy/ropa.yaml`):
```yaml
version: "2026-11"
controller: "PT Example Teknologi Indonesia"
activities:
  - id: ACT-001-EKYC-ONBOARDING
    purpose: "Identity verification for regulated merchant onboarding"
    lawful_basis: LEGAL_OBLIGATION # UU PDP Pasal 20(2)(c) - AML/KYC
    data_classes:
      - GENERAL_PASAL_4_3   # NIK, full name
      - SPECIFIC_PASAL_4_2  # Biometric liveness embedding
    dpia_required: true
    dpia_ref: "docs/privacy/dpia/DPIA-001-ekyc.md"
    stores: ["primary_pg_id_region", "kms_vault_id"]
    processors:
      - name: "VerifiedEkycVendor"
        dpa_signed: true
        region: "ap-southeast-3 (Jakarta)"
        subprocessors_approved: true
    retention_days: 1825 # 5 years statutory AML retention
    security_controls: ["AES-256-GCM+KMS", "RBAC+Passkeys", "zero_log_pii"]
    owner: "identity-engineering"
```
Automated DPIA trigger evaluator:
```typescript
export interface FeaturePrivacyIntake {
  readonly processesSpecificDataAtScale: boolean;
  readonly automatedLegalImpactDecision: boolean;
  readonly systematicMonitoring: boolean;
  readonly usesNewBiometricOrAiOnPii: boolean;
  readonly dpiaDocumentRef: string | null;
}

export function checkDpiaGate(intake: FeaturePrivacyIntake): { readonly required: boolean; readonly blocked: boolean; readonly reasons: readonly string[] } {
  const reasons: string[] = [];
  if (intake.processesSpecificDataAtScale) reasons.push('UU_PDP_PASAL_34_SPECIFIC_DATA_AT_SCALE');
  if (intake.automatedLegalImpactDecision) reasons.push('UU_PDP_PASAL_34_AUTOMATED_PROFILING');
  if (intake.systematicMonitoring) reasons.push('UU_PDP_PASAL_34_SYSTEMATIC_MONITORING');
  if (intake.usesNewBiometricOrAiOnPii) reasons.push('UU_PDP_PASAL_34_NEW_HIGH_RISK_TECH');
  const required = reasons.length > 0;
  return { required, blocked: required && !intake.dpiaDocumentRef, reasons };
}
```

## 5. Platform / Vendor Variations
| Vendor Category | Must-Verify Before Production Integration |
| :--- | :--- |
| **LLM / GenAI APIs (OpenAI, Anthropic, Google)** | Zero-data-retention / no-training-on-API-data enterprise DPA + cross-border `Pasal 56` check (`05`) |
| **Analytics & Session Replay (PostHog, GA4, Mixpanel)** | Mask all inputs (`maskAllInputs`), disable PII autocapture, signed DPA, DSAR API wired (`03`) |
| **Cloud Infra (AWS Jakarta `ap-southeast-3`, GCP `asia-southeast2`)** | Confirm actual region residency of backups, logs, CDN caches, and support access |

## 6. Decision Matrix & Trade-Offs
| Feature Risk Profile | ROPA Update Needed? | DPIA Needed? | DPO / Legal Sign-Off |
| :--- | :---: | :---: | :---: |
| Minor UI layout tweak (zero new data) | No | No | No |
| New General Data field (e.g., delivery instructions) | **YES** | No | Engineering review |
| Biometric KYC, Health Records, AI Credit/Fraud Scoring | **YES** | **MANDATORY (`Pasal 34`)** | **Mandatory DPO + Legal** |

## 7. Real Production Scenario
A growth engineer pastes a new session-replay script and pipes customer support transcripts (containing `NIK` and bank account numbers) into an unapproved third-party AI summarization SaaS without a DPA, ROPA update, or DPIA. Quarterly vendor telemetry audit catches the outbound domains; blocking unapproved egress until DPA + PII redaction middleware + DPIA sign-off completes avoids `Pasal 51/56/57` regulatory exposure.

## 8. Failure Modes & Edge Cases
- **WRONG:** Onboarding a new SaaS/LLM vendor via developer credit card with click-through consumer ToS (no DPA, training-on-data enabled by default!).
- **RIGHT:** Gate all third-party PII processors through ROPA intake, signed DPA (zero training), sub-processor review, and cross-border transfer check (`05`).
- **WRONG:** Writing a DPIA *after* production launch just to check an audit box.
- **RIGHT:** Complete `checkDpiaGate` BEFORE engineering architecture freeze so privacy safeguards (pseudonymization, data minimization, human override) are built in by design.

## 9. Testing & Verification
- Lint `docs/privacy/ropa.yaml` in CI confirming every active third-party processor in `.env.example`/config has a corresponding ROPA entry with `dpa_signed: true`.

## 10. Operational Considerations
- Review ROPA and the vendor/sub-processor register every 6 months and whenever replacing a major vendor (ESP, analytics, cloud region, LLM provider).

## 11. Authoritative References
- UU PDP (UU No. 27 Tahun 2022) — Pasal 31 (ROPA), Pasal 34 (DPIA), Pasal 51–54 (Processors & DPO).
- ISO/IEC 27701:2019 — *Privacy Information Management System (PIMS)*.

## 12. Limitations & When NOT to Use
- Engineering ROPA/DPIA templates accelerate technical risk mapping, NOT legal sign-off; formal DPIA approval and DPA contract execution remain the responsibility of DPO and Legal Counsel.
