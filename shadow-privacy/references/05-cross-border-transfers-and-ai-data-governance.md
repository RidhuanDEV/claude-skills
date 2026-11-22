# 05. Cross-Border Transfers & AI Data Governance

## 1. Purpose & Activation Conditions
Enforce Indonesia **UU PDP Pasal 56** and **GDPR Chapter V (`Art. 44–49`)** safeguards before transmitting personal data to offshore cloud regions, SaaS analytics, ESPs, or third-party LLM APIs — combined with PII tokenization/redaction for AI workloads. Load whenever integrating non-Indonesian cloud/LLM/SaaS endpoints or reviewing international data flows.

## 2. Prerequisites
- Signed vendor DPA (`04`), inventory of outbound endpoints and regions, and PII redaction layer (`06`).

## 3. Technical Principles & Constraints
- **UU PDP Pasal 56 — Mandatory 3-Tier Cross-Border Transfer Cascade (Strict Order!):** Before transferring personal data outside the jurisdiction of the Republic of Indonesia, a Controller MUST satisfy the statutory sequence in strict descending order:
  1. **Tier 1 — Adequacy (`Pasal 56 Ayat (2)`):** Destination country has equal or higher level of personal data protection than Indonesia (confirm latest government/PDP Authority adequacy determination via Legal/DPO — never assume!), OR
  2. **Tier 2 — Adequate & Binding Safeguards (`Pasal 56 Ayat (3)`):** If Tier 1 is not met, put in place adequate and binding contractual/organizational safeguards (e.g., Standard Contractual Clauses / Binding Corporate Rules / DPA security & enforceability clauses verified by Legal), OR
  3. **Tier 3 — Explicit Data Subject Consent (`Pasal 56 Ayat (4)`):** ONLY if neither Tier 1 nor Tier 2 is met, obtain explicit informed consent from the Data Subject specifically covering the cross-border transfer!
- **LLM & GenAI Personal Data Protection:**
  - **Minimize & Pseudonymize BEFORE Outbound LLM Calls:** Strip or tokenize `NIK`, `NPWP`, `full_name`, `email`, `phone`, `nomor_rekening`, and `rekam_medis` into opaque placeholders (`[SUBJECT_1]`, `[ACCOUNT_1]`) before sending prompts to external LLM APIs, re-hydrating locally on response if needed!
  - **Contractual Zero-Training & Zero-Retention:** Use enterprise/API tiers with explicit **zero training on customer prompts/outputs** and minimal retention (`0–30d` abuse-monitoring only, or regional inference endpoints like `ap-southeast` / self-hosted open-weights inside Indonesia when regulated data cannot leave!).
  - **Automated Decision Safeguard (`Pasal 10`):** Whenever an AI/LLM model produces decisions with legal or significant impact (loan approval, claim denial, account suspension), store model rationale metadata and enforce a mandatory **Human-in-the-Loop (HITL) objection & review workflow**.

## 4. Architecture & Implementation
```typescript
export type CrossBorderMechanism =
  | 'IN_COUNTRY_NO_TRANSFER'
  | 'PASAL_56_2_ADEQUACY'
  | 'PASAL_56_3_BINDING_SAFEGUARDS_SCC'
  | 'PASAL_56_4_EXPLICIT_CONSENT'
  | 'UNVERIFIED_NONE';

export interface OutboundTransferConfig {
  readonly processorName: string;
  readonly destinationRegion: string;
  readonly carriesPersonalData: boolean;
  readonly piiTokenizedBeforeEgress: boolean;
  readonly mechanism: CrossBorderMechanism;
  readonly dpaZeroTrainingConfirmed: boolean;
  readonly legalCounselReviewed: boolean;
}

export function evaluateCrossBorderTransferGate(
  cfg: OutboundTransferConfig
): { readonly allowed: boolean; readonly blockers: readonly string[] } {
  if (!cfg.carriesPersonalData || cfg.mechanism === 'IN_COUNTRY_NO_TRANSFER') {
    return { allowed: true, blockers: [] };
  }
  const blockers: string[] = [];
  if (cfg.mechanism === 'UNVERIFIED_NONE') {
    blockers.push(`PASAL_56_BLOCKED: '${cfg.processorName}' (${cfg.destinationRegion}) lacks lawful cross-border transfer basis.`);
  }
  if (!cfg.dpaZeroTrainingConfirmed) {
    blockers.push(`DPA_MISSING: Confirm signed DPA & zero-training clause for '${cfg.processorName}'.`);
  }
  if (!cfg.legalCounselReviewed) {
    blockers.push(`LEGAL_REVIEW_REQUIRED: Escalate cross-border transfer to '${cfg.destinationRegion}' for DPO/Legal verification.`);
  }
  if (!cfg.piiTokenizedBeforeEgress) {
    blockers.push(`DATA_MINIMIZATION_WARNING: Strip/tokenize raw PII (NIK/NPWP/medical/account) before transmitting to '${cfg.processorName}'.`);
  }
  return { allowed: blockers.length === 0, blockers };
}
```

## 5. Platform / Vendor Variations
| Deployment Choice | Cross-Border Risk | Best Fit |
| :--- | :---: | :--- |
| **In-Country Cloud (`AWS Jakarta ap-southeast-3`, `GCP Jakarta asia-southeast2`)** | **Zero transfer** (verify backups, CDN, & support access stay local too!) | Government SPBE, banking/fintech, healthcare (`rekam_medis`) |
| **Offshore SaaS / LLM API + Pseudonymization + SCC/DPA** | Controlled (`Pasal 56(3)`) | General SaaS analytics, support, & non-sensitive AI features |
| **Self-Hosted Open-Weights LLM Inside Indonesian VPC** | **Zero transfer** | Regulated health/gov/financial AI pipelines where raw Specific Data cannot exit Indonesia |

## 6. Decision Matrix & Trade-Offs
| Data Sensitivity | Send Raw to US/EU LLM API? | Recommended Architecture |
| :--- | :---: | :--- |
| **Public Docs / Non-Personal Knowledge Base** | Allowed (standard API) | Standard enterprise API + zero-training DPA |
| **General PII (`name`, `email`, `phone`, `NIK`)** | **NO (Strip/Tokenize First!)** | Local PII redactor/tokenizer -> offshore LLM API (`Pasal 56(3)` + DPA) |
| **Regulated Specific Data (`rekam_medis`, `biometrics`, banking core)** | **NO** | In-country VPC / Jakarta cloud region + explicit DPIA (`Pasal 34`) & regulatory sign-off |

## 7. Real Production Scenario
A hospital startup builds a clinical summary assistant by posting raw patient records (`NIK`, `full_name`, `diagnosis`, lab values) directly to a US-hosted LLM API without a DPA, without `Pasal 56` legal assessment, and without PII redaction. Pre-launch privacy audit flags `Pasal 4(2)` Specific Data, missing `Pasal 34` DPIA, and `Pasal 56` cross-border violation. Moving inference to an in-country VPC (or stripping all direct identifiers before egress + signing enterprise zero-retention DPA + DPIA sign-off with Legal/DPO) brings the design into alignment.

## 8. Failure Modes & Edge Cases
- **WRONG:** Assuming `"our database is in Jakarta"` means zero cross-border transfers while Sentry error stacks, PostHog events, Resend emails, and OpenAI prompts ship raw PII to US servers!
- **RIGHT:** Audit EVERY outbound HTTP/SDK destination (`logs`, `APM`, `analytics`, `email`, `LLM`, `backups`) in the cross-border transfer register.
- **WRONG:** Relying solely on `Pasal 56(4)` consent without first evaluating `Pasal 56(2)` adequacy and `Pasal 56(3)` binding contractual safeguards (or hiding transfer consent inside generic ToS).
- **RIGHT:** Follow the exact statutory cascade (`56(2) -> 56(3) -> 56(4)`) with Legal/DPO review.

## 9. Testing & Verification
- Unit-test your outbound LLM/APM redaction middleware with synthetic `NIK` (`3174...`), `NPWP`, `email`, `phone`, and `nomor_rekening`; assert `0` raw identifiers exist in captured outbound HTTP payloads.

## 10. Operational Considerations
- Monitor implementing regulations (*Peraturan Pemerintah* / PDP Authority guidance) for updated Indonesian adequacy lists and sector-specific data localization rules (e.g., OJK / Kemenkes / Komdigi).

## 11. Authoritative References
- UU PDP (UU No. 27 Tahun 2022) — Pasal 10 (Automated Profiling) & Pasal 56 (Cross-Border Data Transfer).
- EU GDPR — Chapter V (`Articles 44–49`) & EDPB Recommendations on Supplementary Measures.

## 12. Limitations & When NOT to Use
- Simple regex PII masking before LLM calls can miss unstructured identifiers in free-text clinical/legal notes (e.g., `"Bapak Andi di Jl. Sudirman No. 12"`). For sensitive unstructured text, prefer in-country processing or dedicated NER redaction + human review rather than claiming regex masking alone makes data non-personal!
