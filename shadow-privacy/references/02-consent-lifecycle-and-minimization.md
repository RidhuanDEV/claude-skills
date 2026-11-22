# 02. Consent Lifecycle & Data Minimization

## 1. Purpose & Activation Conditions
Implement verifiable, granular, withdrawable consent lifecycles (`UU PDP Pasal 20–26` & `Pasal 9`; `GDPR Art. 7`) and privacy-by-design data minimization across registration, preference centers, and downstream messaging/analytics pipelines. Load when designing consent modals, preference tables, or child/guardian onboarding flows.

## 2. Prerequisites
- Lawful basis classification (`01-uu-pdp-and-gdpr-classification-and-legal-basis.md`) separating mandatory contractual fields from optional consent-based purposes.

## 3. Technical Principles & Constraints
- **Valid Consent Invariants (`UU PDP Pasal 21–24`):**
  - Must be **explicit, affirmative, purpose-specific, and documented** (`written` or recorded electronically). Pre-ticked checkboxes, forced bundling ("agree to marketing ads to use basic app"), or hidden fine print are **INVALID**.
  - Must be presented in clear, accessible **Bahasa Indonesia** (when targeting Indonesian subjects) explaining controller identity, purpose, data categories, retention period, and withdrawal rights (`Pasal 5 & 21`).
- **Immutable Consent Ledger:** Never overwrite a boolean `users.marketing_opt_in = false` without history! Append/maintain verifiable proof: `(subject_id, purpose_code, lawful_basis, policy_version, granted_at, withdrawn_at, source_channel, evidence_hash)`.
- **Instant Withdrawal Propagation (`Pasal 9`):** Withdrawing consent MUST be as easy as granting it and MUST synchronously halt non-essential processing (marketing emails `/shadow-email`, client/server behavioral tracking `/shadow-analytics`, AI profiling).
- **Special Protection for Children & Persons with Disabilities (`Pasal 25–26`):** Require verifiable parent/guardian consent (plus age-gating where applicable) before processing children's personal data.
- **Data Minimization (`Pasal 16(2)(c)` / `GDPR Art. 5(1)(c)`):** Collect ONLY fields strictly necessary for the declared purpose (do NOT ask for `NIK`, `mother_maiden_name`, or `religion` on a newsletter or basic e-commerce signup!).

## 4. Architecture & Implementation
```sql
-- Immutable-proof PostgreSQL Consent Ledger (UU PDP Pasal 20-24 & Pasal 9)
CREATE TABLE consent_records (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  subject_id      UUID NOT NULL,
  purpose_code    TEXT NOT NULL,        -- e.g. 'marketing_email', 'analytics_behavioral', 'ai_credit_scoring'
  lawful_basis    TEXT NOT NULL CHECK (lawful_basis IN ('CONSENT', 'CONTRACT', 'LEGAL_OBLIGATION', 'VITAL_INTEREST', 'PUBLIC_INTEREST', 'LEGITIMATE_INTEREST')),
  policy_version  TEXT NOT NULL,
  granted_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  withdrawn_at    TIMESTAMPTZ,
  source_channel  TEXT NOT NULL,        -- e.g. 'web_signup', 'mobile_preference_center'
  evidence_hash   TEXT NOT NULL,        -- SHA-256 of rendered notice text + timestamp + subject_id
  guardian_id     UUID,                 -- Required when subject is minor (Pasal 25)
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_consent_active ON consent_records (subject_id, purpose_code)
  WHERE withdrawn_at IS NULL;
```
Server-side purpose gate before invoking optional processing:
```typescript
export interface ActiveConsentRecord {
  readonly purposeCode: string;
  readonly policyVersion: string;
  readonly withdrawnAtIso: string | null;
}

export function hasValidActiveConsent(
  records: readonly ActiveConsentRecord[],
  requiredPurpose: string,
  minPolicyVersion?: string
): boolean {
  return records.some((r) => {
    if (r.purposeCode !== requiredPurpose || r.withdrawnAtIso !== null) return false;
    if (minPolicyVersion && r.policyVersion < minPolicyVersion) return false;
    return true;
  });
}
```

## 5. Platform / Vendor Variations
| Processing Channel | Withdrawal Enforcement Hook | Pitfall to Watch |
| :--- | :--- | :--- |
| **Marketing Email (`/shadow-email`)** | RFC 8058 `POST` + preference center sets `withdrawn_at` + HMAC suppression tombstone | Worker sends queued campaign without re-checking `withdrawn_at` at dispatch |
| **Product Analytics (`/shadow-analytics`)** | Runtime consent gate halts SDK capture & clears persistent cookies on withdrawal | Tag manager loads third-party pixel before consent state resolves |
| **Automated Profiling (`Pasal 10`)** | Opt-out / human-review override flag (`requires_human_review = true`) | Scoring pipeline ignores `objection_recorded` flag during batch re-runs |

## 6. Decision Matrix & Trade-Offs
| Consent UI Pattern | Legal Validity (`UU PDP` / `GDPR`) | UX Clarity | Verdict |
| :--- | :---: | :---: | :--- |
| **Unchecked Granular Toggles per Purpose** | **Valid** | High | **Mandatory standard** |
| **Pre-Ticked Marketing Checkbox** | **INVALID** | Deceptive | **FORBIDDEN** |
| **Single Bundled `"Accept ToS + Marketing + Third-Party Ads"`** | **INVALID** | Poor | **FORBIDDEN** |

## 7. Real Production Scenario
A fintech onboarding form uses a single pre-checked checkbox `"Saya setuju dengan Syarat & Ketentuan serta menerima penawaran mitra pihak ketiga"` and stores only a single `users.agreed = true` boolean. When a customer disputes receiving partner telemarketing calls under UU PDP `Pasal 9 & 22`, the company has zero proof of which notice version was shown or when consent was granted/withdrawn. Replacing it with unbundled opt-in checkboxes + `consent_records` ledger + instant withdrawal propagation resolves compliance exposure.

## 8. Failure Modes & Edge Cases
- **WRONG:** Storing consent state ONLY in browser `localStorage` without persisting proof on the backend (erased when user switches devices or clears browser cache!).
- **RIGHT:** Persist authenticated user consent decisions in server-side `consent_records` synced across devices, using browser storage only for anonymous pre-login banners.
- **WRONG:** Requiring users to email customer support and wait 14 days just to withdraw marketing consent that took 1 click to enable.
- **RIGHT:** Provide self-service 1-click consent withdrawal in preferences + RFC 8058 unsubscribe.

## 9. Testing & Verification
- E2E test: create user with `marketing_email: false` -> verify marketing enqueue is blocked -> grant consent -> verify `consent_records` row with `policy_version` and `evidence_hash` -> withdraw consent -> assert `withdrawn_at` set and next dispatch blocked immediately.

## 10. Operational Considerations
- Version privacy notice text cleanly (`policy_version: "2026-11-v2"`). Whenever a new processing purpose is added, request fresh explicit consent strictly for the new purpose rather than silently grandfathering old users.

## 11. Authoritative References
- UU PDP (UU No. 27 Tahun 2022) — Pasal 5, 9, 16, 20–26.
- EU GDPR — Articles 5(1)(c), 7, 8 (`https://eur-lex.europa.eu/eli/reg/2016/679/oj`).

## 12. Limitations & When NOT to Use
- Never ask for consent when processing is actually mandatory under `LEGAL_OBLIGATION` or `CONTRACT` — offering an illusory opt-out that the user cannot actually refuse violates transparency and breaks `Pasal 20` clarity.
