# Multi-Protocol API Architecture, Uploads, LRO & Outbound Webhooks

## 1. Core Concepts
Production APIs extend beyond synchronous CRUD JSON into **graph projections (GraphQL)**, **low-latency binary contracts (gRPC/ConnectRPC)**, **direct-to-object-storage uploads (Presigned URLs)**, **asynchronous Long-Running Operations (HTTP `202 Accepted`)**, and **cryptographically signed outbound webhooks**.

## 2. Technical Rules & Protocol Selection Matrix

| Protocol / Pattern | Choose When | Mandatory Senior Rules |
| :--- | :--- | :--- |
| **REST (OpenAPI 3.1)** | Public/partner APIs, cacheable resources, standard CRUD | RFC 9457 `application/problem+json`, `Idempotency-Key` on `POST`, keyset pagination (`after`, `limit <= 100`). |
| **GraphQL** | Complex UI views needing variable field subsets across relations | Per-request **DataLoader** batching (0 N+1), max query depth (`<= 7`) + cost limits, persisted queries, field-level AuthZ. |
| **gRPC / Protobuf** | High-throughput internal service-to-service RPC & streaming | Never reuse deleted field numbers; enforce `buf breaking` in CI; require per-call deadlines & W3C `traceparent`. |
| **Presigned Upload** | Files `> 1 MB` (images, PDFs, videos, CSV imports) | Client uploads straight to S3/R2 via short-lived presigned `PUT`/`POST`; backend verifies magic bytes, size ceiling, and AV scan asynchronously. |
| **LRO (`202 Accepted`)** | Operations taking `> 2–5s` (exports, batch jobs, AI generation) | Return `202` + `Location: /api/v1/jobs/:id` + `Retry-After`; track `QUEUED -> PROCESSING -> COMPLETED | FAILED`. |

## 3. Implementation Examples
```ts
// 1. Outbound Webhook HMAC-SHA256 Signing (Dual-Secret Rotation Ready)
import crypto from 'node:crypto'

export function buildWebhookSignatureHeader(
  rawBody: string,
  timestampSec: number,
  activeSecrets: ReadonlyArray<{ readonly kid: string; readonly secret: string }>,
): string {
  const signedPayload = `${timestampSec}.${rawBody}`
  const sigs = activeSecrets.map(({ kid, secret }) => {
    const mac = crypto.createHmac('sha256', secret).update(signedPayload, 'utf8').digest('hex')
    return `v1_${kid}=${mac}`
  })
  return `t=${timestampSec},${sigs.join(',')}`
}

// 2. RFC 9457 Problem Details Builder (Zero Stack-Trace Leak)
export function buildProblemJson(status: number, title: string, detail: string, instance: string, requestId: string) {
  return {
    type: `https://httpstatuses.com/${status}`,
    title,
    status,
    detail,
    instance,
    requestId,
  }
}
```

## 4. Best Practices
- Resolve outbound webhook destination hostnames and **block private/link-local IPs (`10.0.0.0/8`, `127.0.0.0/8`, `169.254.169.254`, `172.16.0.0/12`, `192.168.0.0/16`, `::1`)** at connection time to prevent SSRF.
- Serve user-uploaded files from a separate sandbox domain with `Content-Disposition: attachment` and `X-Content-Type-Options: nosniff`.

## 5. Anti-patterns (WRONG vs RIGHT)
- **WRONG:** Buffering a 50MB file upload in Node/Python process RAM before forwarding it to S3, or trusting `req.file.mimetype` without checking magic bytes.
- **RIGHT:** Issue a presigned S3/R2 upload URL with strict `content-length-range` and inspect magic bytes on the uploaded object header.
- **WRONG:** Returning `200 OK` on an asynchronous export before the worker actually finishes generating the file.
- **RIGHT:** Return `202 Accepted` with `{ jobId, status: "QUEUED" }` and transition to `COMPLETED` only after worker verification.

## 6. Production Considerations
- Test webhook receivers and senders against duplicate delivery, out-of-order timestamps (`|now - t| > 300s` rejected), and secret rotation overlap windows.
