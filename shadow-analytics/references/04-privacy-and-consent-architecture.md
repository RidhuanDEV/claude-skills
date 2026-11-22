# 04. Privacy & Consent Architecture

## 1. Purpose & Activation Conditions
Architect legally compliant product analytics under Indonesia **UU PDP (UU No. 27/2022)** and **GDPR/ePrivacy**: consent gating before SDK initialization, data minimization, PII redaction, retention TTLs, and **end-to-end multi-vendor DSAR erasure**. Load when integrating consent banners, scrubbing PII, or designing user data deletion workflows across warehouse and analytics vendors.

## 2. Prerequisites
- Inventory of EVERY analytics, session-replay, attribution, and messaging vendor receiving user identifiers or event payloads (e.g., Warehouse, PostHog, GA4, Mixpanel, Sentry, Resend/SES).
- Legal classification of data categories and retention windows (`/shadow-privacy`).

## 3. Technical Principles & Constraints
- **Consent-First Execution Gate:** Do NOT load persistent marketing/analytics cookies or emit non-essential tracking before valid consent where required by jurisdiction (GDPR/ePrivacy opt-in; UU PDP Pasal 20 explicit legal basis & withdrawal). Support granular categories (`necessary`, `analytics`, `marketing`) and immediate runtime opt-out without page reload.
- **Data Minimization & Zero Sensitive PII:** Never send `email`, `phone`, `nik`, `npwp`, `date_of_birth`, medical/biometric attributes (UU PDP *Data Spesifik*), free-text form inputs, or query-string tokens into analytics events or session replay DOM captures. Mask all `<input>` and sensitive containers by default in session replay (`maskAllInputs: true`).
- **End-to-End Multi-Vendor DSAR Orchestration (CRITICAL):**
  - Deleting rows from a local warehouse mapping table (`DELETE FROM analytics_identity_map WHERE user_id = ...`) **DOES NOT fulfill UU PDP or GDPR Right to Erasure** when third-party vendors (PostHog, GA4, Mixpanel, ESPs) retain copies of user profiles and event histories!
  - True DSAR compliance requires an **asynchronous DSAR Orchestrator** that:
    1. Purges/pseudonymizes user identity links and PII-bearing records in the local warehouse & backups/retention policy,
    2. Invokes **each configured vendor's official deletion API** (PostHog Person Delete API, GA4 User Deletion API, Mixpanel GDPR Deletion API, ESP contact deletion) and records signed job IDs + completion timestamps,
    3. Enforces bounded raw-event TTLs (`90–365 days` for granular clickstreams; aggregated cohort rollups kept anonymously),
    4. Retains ONLY a minimal keyed `HMAC-SHA256` opt-out/suppression tombstone where legally required to prevent re-contacting an erased user.

## 4. Architecture & Implementation
```typescript
export type ConsentCategory = 'necessary' | 'analytics' | 'marketing';

export interface ConsentState {
  readonly policyVersion: string;
  readonly updatedAtIso: string;
  readonly granted: Readonly<Record<ConsentCategory, boolean>>;
}

export interface VendorErasureAdapter {
  readonly vendorName: string;
  readonly slaDays: number;
  requestUserDeletion(userId: string, requestId: string): Promise<{ readonly externalJobId: string }>;
}

export interface DsarErasureReceipt {
  readonly requestId: string;
  readonly userIdHash: string;
  readonly warehousePurgedAt: string;
  readonly vendorJobs: readonly { readonly vendor: string; readonly externalJobId: string; readonly slaDays: number }[];
}

export async function executeEndToEndDsarErasure(
  userId: string,
  userIdHash: string,
  requestId: string,
  purgeWarehouse: (uid: string) => Promise<void>,
  vendors: readonly VendorErasureAdapter[]
): Promise<DsarErasureReceipt> {
  if (vendors.length === 0) {
    throw new Error('DSAR orchestrator must explicitly enumerate configured third-party vendors (pass explicit empty-vendor audit only if none exist).');
  }
  await purgeWarehouse(userId);
  const warehousePurgedAt = new Date().toISOString();

  const vendorJobs: { readonly vendor: string; readonly externalJobId: string; readonly slaDays: number }[] = [];
  for (const adapter of vendors) {
    const res = await adapter.requestUserDeletion(userId, requestId);
    vendorJobs.push({
      vendor: adapter.vendorName,
      externalJobId: res.externalJobId,
      slaDays: adapter.slaDays,
    });
  }

  return { requestId, userIdHash, warehousePurgedAt, vendorJobs };
}
```

## 5. Platform / Vendor Variations
| Vendor | Official DSAR Erasure Mechanism | Retention / SLA Nuance |
| --- | --- | --- |
| **PostHog** | `DELETE /api/projects/:id/persons/:id/?delete_events=true` | Async ClickHouse mutation; verify completion & disable person profiles for anonymous cookieless mode if desired |
| **Google Analytics 4** | User Deletion API (`userDeletionRequest` by `userId` or `clientId`) + Data Retention setting (`2` or `14` months) | Deletion propagates within days; Consent Mode v2 controls cookieless pings |
| **Mixpanel** | GDPR Data Deletion API (`POST /api/app/data-pipelines/v1/gdpr/deletion`) | Queues erasure for up to 60 days; requires `distinct_id` list |
| **Self-Hosted Warehouse (Postgres/ClickHouse/BigQuery)** | Partitioned TTL + identity-map crypto-shredding / row delete | Avoid rewriting petabytes per user: separate identity lookup + crypto-shred per-user key OR scheduled batch `DELETE` within SLA |

## 6. Decision Matrix & Trade-Offs
| Tracking Mode (When Analytics Consent Denied) | Privacy Compliance | Funnel / Experiment Utility | Implementation Effort |
| --- | --- | --- | --- |
| **Strict No-Track (Zero Client Events)** | Maximum | None for unconsented users (bias risk if opt-in is low) | Low |
| **Cookieless Aggregate Server Metrics** | High (no client storage, no cross-session ID) | Pageview & server-side order counts intact; no multi-session retention | Medium |
| **Consent-Gated Full Analytics + Server Truth** | High (compliant in ID/EU) | Full funnels for consented cohort + 100% revenue truth on server | Medium (Recommended) |

## 7. Real Production Scenario
During a UU PDP / ISO 27701 readiness audit, an engineering team demonstrates their DSAR script: `DELETE FROM analytics_identity_map WHERE user_id = $1`. The auditor checks PostHog and GA4 and immediately finds the erased customer's full behavioral timeline, device history, and custom traits still searchable by `user_id` and `anonymous_id`. The audit fails. Implementing `executeEndToEndDsarErasure` wired to PostHog, GA4, and ESP deletion APIs — plus validating coverage in CI with `analytics_experiment_verifier.py --check-dsar-plan` — closes the compliance gap permanently.

## 8. Failure Modes & Edge Cases
- **WRONG:** Deleting only the local warehouse lookup table and claiming `"DSAR complete"` while PostHog, Mixpanel, and GA4 retain full user profiles.
- **RIGHT:** Orchestrate verified deletion calls across EVERY downstream vendor holding the user's identifiers and log immutable erasure receipts (containing only hashed `user_id`).
- **WRONG:** Logging full `window.location.href` when URLs contain `?email=...`, `?token=...`, or `?reset_code=...`, leaking credentials and PII into analytics vendors.
- **RIGHT:** Strip sensitive query parameters in an edge/client sanitizer middleware BEFORE any event leaves the browser or proxy.

## 9. Testing & Verification
- Run `python shadow-analytics/scripts/analytics_experiment_verifier.py --check-dsar-plan <dsar_plan.json>` in CI; fail the build if any configured vendor in the app lacks a wired deletion adapter or exceeds SLA.
- Verify consent revocation in E2E: toggle `analytics: false`, trigger actions, assert zero outbound requests to `/ingest` or vendor domains and analytics cookies cleared.

## 10. Operational Considerations
- Audit vendor list quarterly: marketing teams frequently add pixels via Tag Managers without informing engineering, creating shadow PII leaks and unmapped DSAR surfaces.
- Keep UU PDP `3x24h` response and breach notification readiness aligned with `/shadow-privacy`.

## 11. Authoritative References
- Undang-Undang No. 27 Tahun 2022 tentang Pelindungan Data Pribadi (UU PDP) — Pasal 4, 8, 20, 46.
- EU GDPR — Article 17 (*Right to Erasure*) & Article 25 (*Data Protection by Design*).
- PostHog Privacy & GDPR Documentation (`https://posthog.com/docs/privacy/gdpr-compliance`).
- Google Analytics 4 — *User Deletion API* (`https://developers.google.com/analytics/devguides/config/userdeletion/v3`).

## 12. Limitations & When NOT to Use
- Technical privacy controls do not replace formal Legal/DPO review of your Privacy Policy, Data Processing Agreements (DPAs), and cross-border transfer bases (`UU PDP Pasal 56`).
- Do NOT use irreversible anonymization on legally mandated financial/tax records (which must be retained per statutory accounting law under separate legal basis, isolated from product analytics).
