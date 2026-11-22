# 09. ESP Integration & Failover

## 1. Purpose & Activation Conditions
Design vendor-neutral Email Service Provider (ESP) adapters, evaluate Amazon SES vs Resend vs Postmark vs SendGrid, and implement safe multi-ESP failover without causing duplicate sends or DMARC breakage. Load when selecting an ESP, migrating providers, or engineering high-availability email failover.

## 2. Prerequisites
- Domain authentication (`02-authentication-and-domain-security.md`), transactional `EmailProviderPort` (`03-transactional-email-architecture.md`), and durable outbox/queue (`05-queue-and-reliability-engineering.md`).

## 3. Technical Principles & Constraints
- **Failover Safety Rule (Zero Duplicate Ambiguity):** NEVER automatically fail over to a secondary ESP after an **ambiguous post-submit network timeout** (`ETIMEDOUT` / `ECONNRESET` after the HTTP `POST` body was transmitted) — the primary ESP may have already accepted and sent the email. Fail over ONLY when:
  1. Primary circuit breaker is `OPEN` (preventing submission before sending), OR
  2. Primary returns a deterministic **pre-accept failure** (`401/403` auth failure, `503 Service Unavailable`, `429` quota exhausted, or TCP `ECONNREFUSED` before request dispatch).
- **Pre-Warmed, Pre-Aligned Secondary DNS:** A cold secondary ESP cannot take over mid-incident unless its DKIM selectors, SPF/custom `Return-Path` subdomain, webhook endpoints, and suppression sync are already configured and verified in production BEFORE an outage.
- **Unified Suppression Sync:** If a user hard-bounces or complains on ESP-A, ESP-B does NOT know unless your **application owns the canonical `email_suppressions` table** and checks it before calling any adapter.
- **Stream Separation Across Providers:** Many high-reliability teams run fast transactional mail on Postmark/Resend/SES Dedicated and marketing campaigns on a separate subdomain + ESP pool so a marketing complaint spike never degrades OTP latency.

## 4. Architecture & Implementation
```typescript
export type ProviderFailureKind = 'pre_accept_retryable' | 'ambiguous_timeout' | 'permanent_4xx';

export interface ProviderSendResult {
  readonly ok: boolean;
  readonly provider: string;
  readonly providerMessageId?: string;
  readonly failureKind?: ProviderFailureKind;
  readonly statusCode?: number;
}

export interface EmailProviderAdapter {
  readonly name: string;
  send(message: NormalizedEmailPayload): Promise<ProviderSendResult>;
}

export interface NormalizedEmailPayload {
  readonly idempotencyKey: string;
  readonly from: string;
  readonly to: readonly string[];
  readonly subject: string;
  readonly html: string;
  readonly text: string;
  readonly headers: Readonly<Record<string, string>>;
}

export interface CircuitBreakerState {
  isOpen(providerName: string): boolean;
  recordSuccess(providerName: string): void;
  recordPreAcceptFailure(providerName: string): void;
}

export async function sendWithSafeFailover(
  payload: NormalizedEmailPayload,
  primary: EmailProviderAdapter,
  secondary: EmailProviderAdapter,
  breaker: CircuitBreakerState
): Promise<ProviderSendResult> {
  if (!breaker.isOpen(primary.name)) {
    const first = await primary.send(payload);
    if (first.ok) {
      breaker.recordSuccess(primary.name);
      return first;
    }
    if (first.failureKind === 'ambiguous_timeout' || first.failureKind === 'permanent_4xx') {
      // Do NOT blindly dispatch to secondary on ambiguous timeout (duplicate risk) or invalid recipient 4xx
      return first;
    }
    breaker.recordPreAcceptFailure(primary.name);
  }

  // Primary breaker is OPEN or failed deterministically before acceptance -> route to secondary
  const fallback = await secondary.send(payload);
  if (fallback.ok) {
    breaker.recordSuccess(secondary.name);
  }
  return fallback;
}
```

## 5. Platform / Vendor Variations
| ESP | Primary Strength | Cost Model (Approx.) | Watch-Out / Constraint |
| --- | --- | --- | --- |
| **Amazon SES** | Ultra-low cost (`~$0.10/1k`), IAM security, AWS-native VPC/SNS | Pay-per-send + dedicated IP fee | Starts in sandbox; requires manual SNS/SQS setup for bounces & complaints; strict account-level suspension on `> 5%` bounce / `> 0.1%` complaint |
| **Postmark** | Fastest transactional p95 latency, strict anti-spam pools, built-in Message Streams | Tiered monthly volume | Strictly enforces transactional vs broadcast stream separation (good discipline, blocks abuse quickly) |
| **Resend** | Modern DX, React Email native, built-in `Idempotency-Key` header | Tiered monthly volume | Verify custom `Return-Path` & DKIM alignment; check regional data residency if regulated |
| **SendGrid** | Mature enterprise API, marketing + transactional suites | Tiered monthly volume | Shared IP pools can suffer noisy-neighbor reputation unless using Dedicated IP + strict stream separation |

## 6. Decision Matrix & Trade-Offs
| Architecture | Availability | Complexity | Cost | When to Choose |
| --- | --- | --- | --- | --- |
| **Single ESP + Durable Outbox** | 99.9%+ (queues absorb brief blips) | Low | Lowest | Most startups & SMEs (`< 500k` emails/mo) |
| **Split-Stream (ESP-A Tx + ESP-B Marketing)** | High isolation | Medium | Low–Medium | Any growing SaaS sending both OTPs and newsletters |
| **Active-Passive Multi-ESP Failover** | 99.99% (survives regional ESP outage) | High (dual DNS, dual webhooks, canary traffic) | Medium–High | Mission-critical fintech/auth where 15-min OTP outage breaches SLA |

## 7. Real Production Scenario
A fintech platform configures Amazon SES as primary and Postmark as passive failover for OTPs. When an AWS us-east-1 SES latency spike causes HTTP timeouts at 3s, the naive failover code immediately sends every timed-out request to Postmark. Both ESPs deliver different 6-digit OTP codes 4 seconds apart, invalidating the first code in Redis just as users type it and breaking logins for 18,000 customers. Refactoring to a circuit breaker (`5xx`/connection-refused triggers `OPEN` for 60s; ambiguous timeouts are NOT double-dispatched and reuse the same active OTP token inside idempotency window) resolves the duplicate-OTP storm.

## 8. Failure Modes & Edge Cases
- **WRONG:** Keeping a secondary ESP idle for 12 months with unverified DKIM/SPF and no canary sends, then flipping traffic during an outage (`550 DMARC fail` + cold-IP throttling).
- **RIGHT:** Send `1%`–`5%` canary traffic (or weekly automated health probes) through the secondary ESP so DNS alignment, credentials, webhooks, and IP reputation stay continuously verified.
- **WRONG:** Relying on ESP-hosted suppression lists as the sole source of truth during provider migration.
- **RIGHT:** Maintain application-owned `email_suppressions` synchronized from all ESP webhooks so switching ESPs never re-sends to previously bounced or complained recipients.

## 9. Testing & Verification
- Chaos-test the failover adapter in unit/integration tests:
  1. Primary returns `503` -> secondary invoked and succeeds.
  2. Primary throws `ambiguous_timeout` -> secondary is **NOT** invoked (prevents duplicate email).
  3. Primary returns `422 invalid recipient` -> secondary is **NOT** invoked.
- Run DNS alignment check (`email_deliverability_verifier.py --check-dns`) against BOTH primary and secondary `Return-Path`/DKIM configurations before launch.

## 10. Operational Considerations
- Normalize provider webhooks into a single internal schema (`email.accepted`, `email.delivered`, `email.bounced_hard`, `email.bounced_soft`, `email.complained`, `email.deferred`) with `provider` tag so observability dashboards work seamlessly across ESP switches.
- Store provider credentials per environment with rotation runbooks; never reuse production API keys in staging.

## 11. Authoritative References
- AWS SES Developer Guide — *Monitoring & Configuration Sets* (`https://docs.aws.amazon.com/ses/latest/dg/monitor-sending-activity.html`).
- Postmark Documentation — *Message Streams Architecture* (`https://postmarkapp.com/message-streams`).
- Resend API Documentation — *Idempotency Keys* (`https://resend.com/docs/api-reference/introduction`).

## 12. Limitations & When NOT to Use
- Do NOT build multi-ESP active-passive failover for early-stage products with low volume; a single reliable ESP + durable outbox + retry backoff solves 99% of transient failures without doubling DNS and webhook maintenance.
- Failover cannot cure domain-level blocklisting (`d=brand.com` reputation collapse); only fixing list hygiene, authentication, and abuse stops domain-level blocks.
