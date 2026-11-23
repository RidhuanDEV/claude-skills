# 01. Severity-SLA Triage, Evidence Preservation & Safe Containment

## 1. Purpose & Activation Conditions
Use this playbook during active post-production incidents (`SEV1`/`P0` through `SEV4`/`P3`) to classify customer impact, preserve volatile forensic evidence BEFORE restarting or mutating runtime state, evaluate whether rollback is data-compatible, and restore service safely without amplifying blast radius.

Activate this playbook when:
- Production experiences an outage, elevated `5xx` rate, login/payment blockage, data corruption, or severe latency degradation.
- Deciding between immediate rollback to a previous release artifact, feature-flag containment, traffic shedding, or forward-fix patching.
- Coordinating Incident Command communications, SLA response clocks, and handoff into deep root-cause diagnosis (`/shadow-debug`).

## 2. Prerequisites
- Read-only observability telemetry (`requestId` logs, metrics, burn-rate alerts, recent deploy SHA) via `/shadow-observe`.
- Explicit release history and DB schema/queue compatibility knowledge (`/shadow-release`, `/shadow-data`).
- Incident Commander / Monarch approval (`L4`) before executing any production mutation (rollback, traffic cutover, writer pause, or hotfix deployment).

## 3. Technical Principles & Constraints
1. **Restore Customer Impact Before Code Refactors**: During active `SEV1`/`SEV2` incidents, stabilize service via the fastest **verified reversible control** (feature flag off, config revert, or compatible rollback). Never spend 45 minutes refactoring code while users are completely blocked.
2. **Preserve Volatile Evidence Before Bouncing Processes**: Never blindly restart pods/containers first. Capture recent error logs, active DB lock/connection metrics, queue depths, and (if safe) a heap/thread snapshot BEFORE restarting, or you permanently erase the root cause trail.
3. **Compatibility-Checked Rollback Gate (Never Blindly Roll Back)**: Before rolling back to the last known good artifact, verify **3 compatibility invariants**:
   - **Schema Compatibility**: Can the older artifact read/write the current database schema without crashing on new NOT NULL columns or renamed enums?
   - **Data Compatibility**: Have live production writes created rows/formats the older artifact cannot deserialize?
   - **Queue/Event Compatibility**: Are in-flight messages or outbox events readable by the older worker version?
   If **any** check fails, **DO NOT blind-rollback**; instead contain via feature flag, pause the faulty writer/consumer cleanly, and prepare a surgical forward fix (`test_incident_rollback_gate.py`).
4. **Explicit Owner, Abort Condition & Recovery Signal**: Every mitigation step MUST record its owner, concrete abort condition (when to stop if mitigation worsens errors), and measurable customer recovery signal (`5xx < 0.5%` for 5 consecutive minutes).
5. **Production PII Access Guardrail**: Never download unmasked live production PII dumps to local developer workstations during triage — diagnose via sanitized `requestId` structured logs and anonymized reproduction fixtures (`/shadow-privacy`).

## 4. Architecture & Implementation
### Severity Classification & SLA Response Matrix
| Severity | Customer & Business Impact | Triage / Ack SLA | Mitigation Target | Mandatory Governance Trail |
| :--- | :--- | :--- | :--- | :--- |
| **`P0 / SEV1`** | Total outage, auth/payment blocked, active security/PII breach | `< 15 min` | `< 1–2 hours` | Incident Lead + Evidence Snapshot + Blameless RCA `< 48h` + Regression Test |
| **`P1 / SEV2`** | Core workflow degraded for cohort, severe latency/error spike, no easy workaround | `< 30 min` | `< 4–8 hours` | Containment/Hotfix + Blameless RCA + Regression Test |
| **`P2 / SEV3`** | Scoped defect with documented safe operational workaround | `< 4 business hrs` | `< 3–5 days` | Scoped patch + Regression Test in next scheduled release |
| **`P3 / SEV4`** | Cosmetic UI glitch, minor copy polish, preventive hygiene | Next grooming | Monthly Harwat | Tracked in Harwat/OMKT monthly backlog |

### Strict TypeScript Rollback Compatibility Gate
```typescript
export interface RollbackCompatibilityInput {
  readonly incidentId: string;
  readonly severity: 'SEV1' | 'SEV2' | 'SEV3' | 'SEV4';
  readonly evidencePreserved: boolean;
  readonly oldArtifactReadsCurrentSchema: boolean;
  readonly oldArtifactReadsCurrentWrites: boolean;
  readonly oldArtifactReadsQueuedEvents: boolean;
  readonly featureFlagAvailable: boolean;
  readonly commanderApproved: boolean;
}

export type MitigationAction =
  | 'HOLD_PRESERVE_EVIDENCE'
  | 'HOLD_COMMANDER_APPROVAL'
  | 'EXECUTE_COMPATIBLE_ROLLBACK'
  | 'CONTAIN_VIA_FLAG_AND_FORWARD_FIX'
  | 'PAUSE_AFFECTED_WRITER_AND_FORWARD_FIX';

export function decideIncidentMitigation(
  input: RollbackCompatibilityInput,
): { readonly action: MitigationAction; readonly reason: string } {
  if (!input.evidencePreserved) {
    return {
      action: 'HOLD_PRESERVE_EVIDENCE',
      reason: 'Capture logs, metrics, and impact timestamp before mutating production state.',
    };
  }
  if (!input.commanderApproved) {
    return {
      action: 'HOLD_COMMANDER_APPROVAL',
      reason: 'Production rollback/containment requires explicit Incident Commander / Monarch L4 approval.',
    };
  }
  const fullyCompatible =
    input.oldArtifactReadsCurrentSchema &&
    input.oldArtifactReadsCurrentWrites &&
    input.oldArtifactReadsQueuedEvents;

  if (fullyCompatible) {
    return {
      action: 'EXECUTE_COMPATIBLE_ROLLBACK',
      reason: 'Previous artifact verified compatible with current schema, writes, and queued events.',
    };
  }
  if (input.featureFlagAvailable) {
    return {
      action: 'CONTAIN_VIA_FLAG_AND_FORWARD_FIX',
      reason: 'Rollback incompatible with live writes/schema/queue; disable feature flag and ship forward fix.',
    };
  }
  return {
    action: 'PAUSE_AFFECTED_WRITER_AND_FORWARD_FIX',
    reason: 'Rollback incompatible and no flag exists; pause affected writer cleanly to stop corruption and ship forward fix.',
  };
}
```

## 5. Platform / Vendor Variations
- **Stateless Web / API Containers (Kubernetes / ECS / PM2)**: Compatible artifact rollback is usually fast (`< 2 min`) when DB migrations follow Expand-Contract (`/shadow-data`); watch out for changed Redis session/cache serialization keys (`/shadow-cache`).
- **Event-Driven & Queue Workers (BullMQ / RabbitMQ / SQS / Kafka)**: Check dead-letter queues and schema evolution before rolling workers back; pausing a single faulty consumer group often stops cascade failures safely while preserving queued jobs.
- **Indonesian Regulated Financial / Government Operations (OJK / SPBE / UU PDP)**: If a `SEV1` incident involves confirmed or suspected personal data exposure, immediately activate the UU PDP Pasal 46 `3x24` hour breach-notification clock with `/shadow-privacy` & `/shadow-sec`.

## 6. Decision Matrix & Trade-Offs
| Containment Option | Speed to Restore | Risk Profile | Best Fit |
| :--- | :--- | :--- | :--- |
| **Feature Flag Kill-Switch** | Seconds (`< 30s`) | Lowest risk; zero deploy churn | Newly released feature behind runtime flag |
| **Verified Compatible Rollback** | Minutes (`2–5m`) | Low ONLY if schema/write/queue compatibility verified | Recent deploy regression with expand-only migration |
| **Pause Faulty Writer / Shed Load** | Minutes (`1–3m`) | Partial degradation, stops data corruption immediately | Incompatible schema/queue preventing rollback |
| **Direct Surgical Forward Fix** | Tens of minutes | Medium; requires failing regression test first | Persistent logic/data bug unaffected by rollback |

## 7. Real Production Scenario
**Context:** Twenty minutes after deploying `v2.8.0` (which added a new `PARTIAL_REFUND` enum value written to PostgreSQL and emitted to the settlement queue), checkout error rates spiked to `14%` (`SEV1`).
**Near-Miss Avoided:** An engineer proposed immediately rolling back to `v2.7.9`. Running the 3-point compatibility check revealed `v2.7.9` crashed on deserializing the `18` `PARTIAL_REFUND` queue messages already emitted!
**Safe Resolution:** The team captured error traces and queue metrics, obtained Incident Commander approval, toggled the `checkout_partial_refund_v2` feature flag OFF (stopping new bad traffic in 12 seconds), quarantined the 18 messages cleanly, and shipped a 9-line forward fix with a regression test 35 minutes later.

## 8. Failure Modes & Edge Cases
- **WRONG (Blindly restarting pods or rolling back without checking schema/queue compatibility):** Restarting crashed containers immediately (wiping forensic evidence) and rolling back an app version that cannot parse live queue events—turning a `14%` degradation into a `100%` crash loop.
  **RIGHT:** Snapshot logs/metrics first, evaluate `oldArtifactReadsCurrentSchema/Writes/QueuedEvents`, and contain via feature flag or writer pause whenever rollback is incompatible.
- **WRONG (Treating one log line as proven root cause):** Seeing `ECONNRESET` in a single log entry and guessing *"Redis is broken"* without structured causal diagnosis.
  **RIGHT:** Stabilize customer impact first, then hand off structured `requestId` traces and reproduction evidence to `/shadow-debug` for falsifiable root-cause confirmation.

## 9. Testing & Verification
- Run `python -m unittest discover -s shadow-maintain/tests -v` (`test_incident_rollback_gate.py` verifies compatibility-checked rollback vs containment decision logic).
- Confirm every incident drill exercises evidence capture, explicit rollback compatibility verification, and measurable recovery criteria.

## 10. Operational Considerations
- Maintain a live incident timeline (`UTC` and `Asia/Jakarta` WIB) capturing exact timestamps for Detection, Triage, Escalation, Mitigation Applied, and Verified Recovery so SLA compliance and monthly Harwat reporting remain audit-ready.

## 11. Authoritative References
- **NIST SP 800-61 Rev. 3** — *Incident Response Recommendations and Considerations for Cybersecurity Risk Management*.
- **Google SRE Book / Workbook** — *Managing Incidents & Emergency Response (Mitigation before deep diagnosis)*.
- **ISO/IEC/IEEE 14764:2022** — *Software Engineering — Software Life Cycle Processes — Maintenance*.

## 12. Limitations & When NOT to Use
- **Do NOT use** `/shadow-maintain` for deep code-level debugging methodology (bisecting race conditions, heap profiling, hypothesis falsification) — delegate causal diagnosis to `/shadow-debug`.
- **Do NOT use** for setting up OTel tracing, Prometheus metrics, or SLO burn-rate alert rules from scratch — route to `/shadow-observe`.
