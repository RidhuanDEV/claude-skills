# 06. Breach 3x24h Response & PII Log Redaction

## 1. Purpose & Activation Conditions
Prevent raw PII leakage across application logs, error trackers, and telemetry — and execute the statutory **3 x 24 hour (72-hour) Personal Data Breach Notification** workflow (`UU PDP Pasal 46 & 57`; `GDPR Art. 33–34`). Load when configuring structured logger redaction, scanning repos for PII leaks, or preparing/running breach incident runbooks.

## 2. Prerequisites
- Structured JSON logger (`BACKEND.md §12`), `shadow-privacy/scripts/privacy_pdp_auditor.py`, and security containment playbook (`shadow-sec` Module `08`).

## 3. Technical Principles & Constraints
- **Fail-Closed PII Log Redaction (`UU PDP Pasal 35–39`):**
  - NEVER print raw `NIK` (16-digit Kemendagri prefix), `NPWP`, `BPJS`, `rekam_medis`, `diagnosis`, `biometric`, `nomor_rekening`, `credit_card`, `password`, `token`, or full `Authorization`/`Cookie` headers into stdout logs, Sentry/APM spans, or analytics events.
  - Enforce redaction centrally at the **logger root configuration** (`pino` `redact.paths`, `structlog` processor, `slog.ReplaceAttr`) so individual developers cannot accidentally leak PII via `logger.info({ user })`.
  - When partial visibility is genuinely required for support triage, emit strictly deterministic masked formats (`3174********0001`, `r***@domain.com`, `****1234`) or opaque `user_id` UUIDs!
- **Statutory 3 x 24 Hour Breach Notification Clock (`UU PDP Pasal 46` / `GDPR Art. 33–34`):**
  - Upon failure of Personal Data Protection (unauthorized access, leak, exfiltration, or unlawful disclosure), Controller MUST deliver **written notification within `<= 3 x 24 hours` (72 hours)** to BOTH: (1) affected **Data Subjects**, and (2) the **PDP Authority** (*Lembaga PDP*).
  - Every written notice MUST contain at least 3 statutory elements (`Pasal 46 Ayat (2)`):
    1. **Exposed Personal Data (`huruf a`):** Exact categories and scope of affected personal data,
    2. **Time & Chronology (`huruf b`):** When and how the personal data was exposed,
    3. **Remediation & Recovery (`huruf c`):** Technical & organizational containment and mitigation steps taken by the Controller.
  - **Public Notice (`Pasal 46 Ayat (3)`):** In specific cases impacting public services and/or broad public interest, Controller MUST also notify the public!
- **Sanctions & Criminal Risk Awareness (`Pasal 57 & 65–70`):** Administrative sanctions include written warnings, temporary suspension, deletion/destruction orders, and **fines up to `2%` of annual revenue** (`Pasal 57(3)`). Unlawful acquisition/disclosure carries criminal imprisonment (`4–6` years) and corporate fines up to **10x** maximum criminal fine (`Pasal 70`).

## 4. Architecture & Implementation
```typescript
const NIK_PATTERN = /(?<![0-9a-fA-FxX-])(?:1[1-9]|21|3[1-6]|5[1-3]|6[1-5]|7[1-6]|8[1-2]|9[1-4])\d{14}(?![0-9a-fA-FxX-])/g;
const NPWP_PATTERN = /\b\d{2}\.\d{3}\.\d{3}\.\d-\d{3}\.\d{3}\b/g;

const REDACTED_KEYS = new Set([
  'password', 'authorization', 'cookie', 'token', 'secret',
  'nik', 'no_ktp', 'npwp', 'bpjs', 'rekam_medis', 'diagnosis',
  'biometric', 'nomor_rekening', 'bank_account', 'credit_card', 'card_number',
]);

export function redactPiiForLogs(value: unknown, depth = 0): unknown {
  if (depth > 8) return '[TRUNCATED_DEPTH]';
  if (typeof value === 'string') {
    return value
      .replace(NIK_PATTERN, (m) => `${m.slice(0, 4)}********${m.slice(-4)}`)
      .replace(NPWP_PATTERN, '**.***.***.*-***.***');
  }
  if (Array.isArray(value)) {
    return value.map((item) => redactPiiForLogs(item, depth + 1));
  }
  if (typeof value === 'object' && value !== null) {
    const clean: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value)) {
      clean[k] = REDACTED_KEYS.has(k.toLowerCase()) ? '[REDACTED_PII]' : redactPiiForLogs(v, depth + 1);
    }
    return clean;
  }
  return value;
}
```
Static repo PII & log-leak scan (`L0` read-only):
```powershell
python "shadow-privacy/scripts/privacy_pdp_auditor.py" --scan .
python "shadow-privacy/scripts/privacy_pdp_auditor.py" --self-test
```

## 5. Platform / Vendor Variations
| Timeline Milestone | Responsible Owner | Mandatory Deliverable (`Pasal 46`) |
| :--- | :--- | :--- |
| **`T+0h` to `T+4h` (Detect & Contain)** | Security + SRE (`/shadow-sec`, `/shadow-ops`) | Preserve forensic logs, stop active exfiltration (`L4`), start `72h` statutory timer |
| **`T+4h` to `T+24h` (Scope Impact)** | Engineering + Data + DPO | Exact subject count, exposed data categories (`Pasal 4(2)` vs `4(3)`), chronology |
| **`T+24h` to `T+60h` (Draft & Approve)** | DPO + Legal Counsel + Executive | Written notice covering `Pasal 46(2)` (a) data, (b) time/how, (c) remediation |
| **`<= T+72h` (Deliver & Monitor)** | DPO + Comms + Engineering | Deliver to PDP Authority + affected Data Subjects (+ public if `Pasal 46(3)`), patch & monitor |

## 6. Decision Matrix & Trade-Offs
| Incident Finding | Triggers 72h Notification Review? | First Technical Action |
| :--- | :---: | :--- |
| Public S3 bucket leaked 500 user `NIK` + `email` rows | **YES (Immediate DPO/Legal escalation)** | Lock bucket (`L4`), preserve access logs, quantify exact affected subjects |
| Unmasked `NIK` accidentally logged to internal private stdout log (no external access) | **Internal Incident — Assess with DPO** | Purge/rotate log index, deploy `redactPiiForLogs`, verify access logs |
| Synthetic dummy `NIK` in unit test fixture | No (ensure clearly marked synthetic) | Keep out of production paths |

## 7. Real Production Scenario
An e-KYC microservice crashes on a malformed PDF and prints the entire request payload (including raw 16-digit `NIK`, `NPWP`, and selfie base64) into Sentry and CloudWatch logs retained for 90 days. Running `privacy_pdp_auditor.py --scan .` catches `UU_PDP_PASAL_35_UNMASKED_PII_LOG` in CI; installing `redactPiiForLogs` at the logger & Sentry `beforeSend` hook + purging the polluted log slice eliminates ongoing PII exposure.

## 8. Failure Modes & Edge Cases
- **WRONG:** Redacting PII in `logger.info()` while forgetting Sentry/Datadog error-tracking breadcrumbs, HTTP access query strings, or crash dumps.
- **RIGHT:** Enforce fail-closed redaction across ALL 3 sinks: structured logger root, APM/error-tracker `beforeSend`, and reverse-proxy query-string sanitizer.
- **WRONG:** Delaying DPO/Legal escalation for 5 days `"until engineering finishes 100% of the root cause"` (misses the statutory 3x24h / 72-hour deadline!).
- **RIGHT:** Notify DPO/Legal immediately upon suspected breach (`T+0`–`4h`) so phased statutory notification can be issued cleanly within 72 hours.

## 9. Testing & Verification
- Run `python shadow-privacy/scripts/privacy_pdp_auditor.py --self-test` and unit-test `redactPiiForLogs` against synthetic `NIK` (`3174010101900001`), `NPWP` (`01.234.567.8-901.000`), and nested `{ patient: { rekam_medis: "..." } }` asserting zero raw PII survives.

## 10. Operational Considerations
- Run an annual 60-minute **72-Hour Breach Simulation Drill** jointly with Engineering, SRE, DPO, and Legal to verify subject-scoping SQL speed and communication templates before a real incident occurs.

## 11. Authoritative References
- UU PDP (UU No. 27 Tahun 2022) — Pasal 35–39, Pasal 46 (`3 x 24h` breach notice), Pasal 57 & 65–70.
- EU GDPR — Articles 32, 33, 34 (`72-hour` supervisory authority & subject notification).

## 12. Limitations & When NOT to Use
- Engineers own technical containment, log redaction, and accurate scope quantification — NEVER send official regulatory or public breach notices directly from engineering without DPO, Legal, and Executive sign-off.
