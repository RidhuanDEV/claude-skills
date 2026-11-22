# 08. Incident Containment & Coordinated Patching

## 1. Purpose & Activation Conditions
Execute disciplined, evidence-preserving security incident containment, blast-radius scoping, credential rotation, and regression-locked patching when a live vulnerability or secret/endpoint leak is discovered. Load during active security incidents (e.g., exposed internal endpoint in JS bundle, leaked `.env` key, active IDOR exploitation, or zero-day CVE).

## 2. Prerequisites
- Read-only access to edge/WAF/app access logs (`shadow-observe`), credential inventory (`06`), and explicit `L4` approval before mutating production infrastructure, WAF rules, or live credentials.

## 3. Technical Principles & Constraints
- **6-Step Containment & Recovery Sequence (Contain First, Preserve Evidence, Fix Root Cause):**
  1. **Verify & Scope Blast Radius (`T+0` — `L0` Read-Only):** Confirm exact vulnerability (`file:line` / route), affected tenants/records, and whether active exploitation occurred in access/audit logs (`status=200`, unusual IPs/volumes, unexpected exports). **NEVER destroy forensic logs during containment!**
  2. **Immediate Edge/App Containment (`L4` Approved):** Block or disable the exposed route at WAF/Nginx/feature-flag kill-switch immediately if active exploitation is possible (e.g., `return 403` on `/internal/*` at ingress while preserving admin VPN access).
  3. **Revoke & Rotate Compromised Credentials (`L4` Approved):** For ANY secret pushed to Git, leaked in logs, or exposed via SSRF/bundle: rotate DB passwords, API keys, JWT signing keys (remove compromised `kid` from JWKS immediately!), and revoke affected user sessions!
  4. **Check Statutory Breach Notification Clock (`/shadow-privacy`):** If personal data exposure is confirmed or suspected, immediately trigger the **UU PDP Pasal 46 (`3 x 24h` / 72-hour)** & GDPR Art. 33 breach notification triage workflow with Legal/DPO!
  5. **Root-Cause Patch + Regression Lock (`L1` Verified):** Fix the underlying server control (e.g., add AuthN/AuthZ + tenant scoping on backend route, NOT merely hiding the URL in frontend JS!), write a failing-before / passing-after negative security test, and deploy via `/shadow-release`.
  6. **Blameless Postmortem & Structural Prevention (`/shadow-maintain`):** Add a permanent CI guard (SAST rule, secret scanner, route-policy check, or CSP check) so the entire class of bug cannot recur.

## 4. Architecture & Implementation
```nginx
# Emergency Edge Containment Example (Requires L4 Production Approval before applying)
# Immediately block external internet access to accidentally exposed /internal/ routes while backend patch ships
location ^~ /internal/ {
    deny all;
    return 403;
}
```
Structured Security Incident Containment Checklist Schema:
```typescript
export interface SecurityIncidentRecord {
  readonly incidentId: string;
  readonly discoveredAtIso: string;
  readonly severity: 'SEV1_ACTIVE_EXPLOIT' | 'SEV2_EXPOSED_NO_CONFIRMED_EXPLOIT' | 'SEV3_CONTAINED_LOW';
  readonly exposureVector: string;
  readonly forensicLogsPreserved: boolean;
  readonly containmentAction: string;
  readonly credentialsRotated: readonly string[];
  readonly personalDataImpacted: boolean;
  readonly uuPdp72hClockStartedAtIso: string | null;
  readonly regressionTestPath: string;
  readonly permanentCiGuardAdded: string;
}
```

## 5. Platform / Vendor Variations
| Incident Archetype | First Containment Action | Common Fatal Mistake |
| :--- | :--- | :--- |
| **Internal Endpoint Found in Frontend JS Bundle** | Block route at WAF/edge + add server AuthN/AuthZ middleware immediately | Only removing the URL string from the frontend repo (backend route stays wide open!) |
| **`.env` / API Key Pushed to Git** | Revoke & rotate keys at provider immediately + audit provider billing/access logs | Running `git revert` or force-pushing without rotating the compromised key |
| **Cross-Tenant IDOR Exploited** | Hotfix tenant query predicate / kill-switch endpoint + query access logs for cross-tenant hits | Assuming `"only 1 user noticed"` without checking historical access logs |
| **Compromised JWT Signing Key** | Publish fresh `kid_v2`, remove compromised `kid_v1` from JWKS, revoke active refresh families | Waiting for natural `exp` expiry while attacker mints infinite admin tokens |

## 6. Decision Matrix & Trade-Offs
| Signal Observed | Action Priority | Escalation Required |
| :--- | :--- | :--- |
| Active unauthorized data exfiltration in logs | **Immediate Containment + Credential Rotation** | Monarch (`L4`), Incident Commander, Legal/DPO (`UU PDP 72h`) |
| Exposed vulnerability in staging/prod with zero log evidence of abuse | **Urgent Containment + Root-Cause Patch (`< 24h`)** | Monarch (`L4` for prod hotfix) + Security Review |
| Vulnerability caught pre-release on feature branch (never deployed, no prod secrets) | **Block Merge + Fix + Regression Test** | PR Reviewer (no breach notification needed) |

## 7. Real Production Scenario
A security researcher reports that `/api/internal/admin-export` has no auth check and its path is hardcoded in the minified React bundle. Instead of panicking and only stripping the string from React, the team executes the 6-step runbook: (1) snapshots Nginx access logs for the past 30 days confirming only 2 researcher hits and 0 bulk exfiltrations, (2) obtains `L4` approval to block `/api/internal/*` at Nginx immediately, (3) adds mandatory server-side AuthN + `admin` RBAC + `tenant_id` scoping on the backend handler (`/shadow-auth`), (4) removes the internal endpoint reference from frontend code, (5) adds a `401`/`403` policy-matrix regression test, and (6) adds a CI bundle-scanner gate checking that `/internal/` never appears in public build artifacts.

## 8. Failure Modes & Edge Cases
- **WRONG:** Restarting or deleting compromised containers/pods before exporting access logs, memory/process state, and audit trails (destroys forensic evidence needed for RCA and UU PDP Pasal 46 reporting!).
- **RIGHT:** Snapshot and preserve immutable logs/evidence BEFORE restarting or rotating workloads.
- **WRONG:** Making unauthorized production firewall/IAM/key-rotation mutations autonomously without Monarch `L4` confirmation.
- **RIGHT:** Prepare exact verified containment commands, state blast radius and rollback plan clearly, and execute upon explicit `L4` authorization.

## 9. Testing & Verification
- Rehearse incident containment quarterly via a 30-minute tabletop exercise (`"Leaked API key in PR"` and `"Exposed unauth endpoint"`); confirm `MTTR < 30 min` and clear escalation owners.

## 10. Operational Considerations
- Maintain a clear `SECURITY.md` disclosure policy (`security@company.com`, safe-harbor terms, PGP key if applicable) so external researchers report issues responsibly instead of publishing zero-days publicly.

## 11. Authoritative References
- NIST SP 800-61 Rev. 3 — *Incident Response Recommendations and Considerations for Cybersecurity Risk Management* (`https://csrc.nist.gov/pubs/sp/800/61/r3/final`).
- NIST Cybersecurity Framework (CSF) 2.0 — *Respond (`RS`) & Recover (`RC`)* (`https://www.nist.gov/cyberframework`).
- UU PDP (UU No. 27 Tahun 2022) — Pasal 46 (`3 x 24h` breach notification).

## 12. Limitations & When NOT to Use
- Security engineering containment does NOT replace formal legal breach-notification counsel or law-enforcement forensics in a major ransomware/extortion compromise; escalate immediately to DPO, Legal, and specialized DFIR responders.
