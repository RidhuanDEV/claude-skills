# 06. Uploads, Presigned URLs, LRO & Outbound Webhooks

## 1. Purpose & Activation Conditions
Design memory-safe direct-to-object-storage uploads, asynchronous Long-Running Operations (`202 Accepted`), and SSRF-safe signed outbound webhook dispatchers. Load when handling file uploads `> 1 MB`, async exports/AI jobs, or delivering webhooks to customer URLs.

## 2. Prerequisites
- Object storage bucket (S3 / Cloudflare R2 / MinIO) isolated from app webroot, durable job queue (`/shadow-concurrency`), and SSRF IP validation (`/shadow-sec`).

## 3. Technical Principles & Constraints
- **Direct Presigned Uploads (`> 1 MB`):** Never buffer multi-megabyte uploads in Node/Python app RAM before streaming to S3. Issue a short-lived (`<= 5–10m`) **presigned `PUT`/`POST` URL** bound to:
  1. Server-generated opaque UUID object key (`tenants/<tenantId>/uploads/<uuid>` — NEVER trust client filenames/paths -> prevents path traversal!),
  2. Strict `content-length-range` ceiling (e.g., `<= 25 MB`),
  3. Explicit allowed MIME types, followed by **asynchronous server-side magic-byte inspection** (and AV scan where regulated) before marking the asset `READY`.
  4. Serve downloads from a **separate sandbox domain** with `Content-Disposition: attachment` and `X-Content-Type-Options: nosniff` (blocks stored XSS from `.html`/`.svg` uploads!).
- **Long-Running Operations (`HTTP 202 Accepted`):** Any operation taking `> 2–5 seconds` (CSV/PDF export, bulk import, video render, batch AI inference) MUST return **`202 Accepted`** with `Location: /api/v1/jobs/:jobId`, `Retry-After: 2`, and `{ jobId, status: "QUEUED" }`. Transition deterministically `QUEUED -> PROCESSING -> COMPLETED | FAILED` scoped strictly to `tenant_id`.
- **Outbound Webhooks (Signed + SSRF-Protected + Retried):**
  1. Sign every delivery over `${timestampSec}.${rawBody}` using **dual-secret rotation-ready `HMAC-SHA256`** (`X-Webhook-Signature: t=...,v1_k1=...,v1_k2=...`).
  2. Enforce HTTPS-only destination URLs, resolve DNS at dispatch time, and **block all loopback/private/link-local IPs (`127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.169.254`, `::1`, `fc00::/7`, `fe80::/10`)** with `redirect: "manual"` to block SSRF!
  3. Dispatch asynchronously via durable outbox with exponential backoff, tight timeout (`<= 5–10s`), and circuit-breaking/auto-disable after prolonged `4xx`/`5xx` failure streaks.

## 4. Architecture & Implementation
```typescript
import crypto from 'node:crypto';

export interface ActiveWebhookSecret {
  readonly kid: string;
  readonly secret: string;
}

// Dual-secret rotation-ready HMAC-SHA256 header builder
export function buildWebhookSignatureHeader(
  rawBody: string,
  timestampSec: number,
  activeSecrets: readonly ActiveWebhookSecret[]
): string {
  if (activeSecrets.length === 0) {
    throw new Error('At least one active webhook signing secret is required');
  }
  const signedPayload = `${timestampSec}.${rawBody}`;
  const sigs = activeSecrets.map(({ kid, secret }) => {
    const mac = crypto.createHmac('sha256', secret).update(signedPayload, 'utf8').digest('hex');
    return `v1_${kid}=${mac}`;
  });
  return `t=${timestampSec},${sigs.join(',')}`;
}

export type MagicFileKind = 'png' | 'jpeg' | 'pdf' | 'unknown';

// Inspect actual file header bytes (never trust client Content-Type or file extension alone)
export function detectMagicFileKind(headerBytes: Uint8Array): MagicFileKind {
  if (headerBytes.length >= 4 && headerBytes[0] === 0x25 && headerBytes[1] === 0x50 && headerBytes[2] === 0x44 && headerBytes[3] === 0x46) {
    return 'pdf'; // %PDF
  }
  if (
    headerBytes.length >= 8 &&
    headerBytes[0] === 0x89 && headerBytes[1] === 0x50 && headerBytes[2] === 0x4e && headerBytes[3] === 0x47 &&
    headerBytes[4] === 0x0d && headerBytes[5] === 0x0a && headerBytes[6] === 0x1a && headerBytes[7] === 0x0a
  ) {
    return 'png';
  }
  if (headerBytes.length >= 3 && headerBytes[0] === 0xff && headerBytes[1] === 0xd8 && headerBytes[2] === 0xff) {
    return 'jpeg';
  }
  return 'unknown';
}
```

## 5. Platform / Vendor Variations
| Pattern | Recommended Tooling | Key Pitfall |
| :--- | :--- | :--- |
| **Presigned Uploads** | AWS S3 / Cloudflare R2 `createPresignedPost` (`content-length-range`) | Using presigned `PUT` without enforced `Content-Length` allows oversized uploads |
| **Resumable Large Uploads (`> 50 MB`)** | `tus` protocol / S3 Multipart Upload | Orphaned incomplete multipart parts inflate cloud storage bills — set S3 Lifecycle abort rule (`7 days`)! |
| **Outbound Webhook Platform** | Svix / Transactional Outbox + BullMQ/SQS | Sending webhooks inline inside the HTTP checkout request slows checkout to customer server latency |

## 6. Decision Matrix & Trade-Offs
| File Size / Latency | Pattern | Why |
| :--- | :--- | :--- |
| **Small JSON / `< 1 MB` Avatar** | Direct bounded multipart (`<= 1 MB`) + magic-byte check | Simple, single round-trip |
| **Files `> 1 MB` (PDF/Video/CSV)** | **Presigned Direct Upload** + async finalize | Protects app RAM, avoids reverse-proxy `413` / timeouts |
| **Operations `> 2–5s`** | **LRO (`202 Accepted` + `/jobs/:id`)** | Prevents `504 Gateway Timeout` & client retry storms |

## 7. Real Production Scenario
A SaaS app accepts `40 MB` inspection videos via Express `multer.memoryStorage()`. Four concurrent uploads spike heap usage by `320 MB`, triggering OOMKill restarts that drop active user sessions. Meanwhile, a customer sets their outbound webhook target to `http://169.254.169.254/latest/meta-data/iam/security-credentials/`, exposing cloud IAM credentials via SSRF. Moving uploads to presigned R2 URLs with `tus`/size bounds + magic-byte verification and locking outbound webhooks behind DNS-resolved private-IP blocking resolves both P0 incidents.

## 8. Failure Modes & Edge Cases
- **WRONG:** Trusting `file.mimetype === 'image/png'` sent by the browser (an attacker renames `xss.html` to `avatar.png` and sets `Content-Type: image/png`).
- **RIGHT:** Verify magic bytes (`detectMagicFileKind`) server-side and serve user files from a separate sandbox domain with `Content-Disposition: attachment` and `X-Content-Type-Options: nosniff`.
- **WRONG:** Returning `200 OK` on an async PDF export endpoint before the background worker has created the file.
- **RIGHT:** Return `202 Accepted` with `Location: /api/v1/jobs/:id`, polling status `QUEUED -> PROCESSING -> COMPLETED | FAILED`.

## 9. Testing & Verification
- Test negative upload & webhook cases: HTML file renamed `.png` -> rejected by `detectMagicFileKind`; oversized upload -> blocked; webhook URL `http://169.254.169.254/` or `http://[::1]/` -> rejected; dual-secret signature verifies with both old and new key during rotation window.

## 10. Operational Considerations
- Configure S3/R2 lifecycle rules to clean up unfinalized presigned uploads (`24h`) and incomplete multipart uploads (`7d`) so abandoned client uploads do not leak storage cost (`/shadow-finops`).

## 11. Authoritative References
- OWASP File Upload Cheat Sheet (`https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html`).
- Standard Webhooks Specification (`https://www.standardwebhooks.com/`).
- IETF RFC 9110 §15.3.3 — *`202 Accepted` Semantics*.

## 12. Limitations & When NOT to Use
- Presigned uploads require CORS configuration on the object-storage bucket and a 2-step client flow (`request-upload-url -> PUT -> finalize`); keep tiny `< 500 KB` form attachments simple unless concurrency warrants direct-to-S3.
