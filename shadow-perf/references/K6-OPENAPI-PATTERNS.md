# K6-OPENAPI-PATTERNS — Production Load Testing for Pre-UAT Verification

Based on Grafana `k6` best practices and `@grafana/openapi-to-k6` patterns.

---

## 1. The 4 Pre-UAT Test Profiles

| Test Profile | Virtual Users (VUs) | Duration | Purpose Before UAT |
| :--- | :--- | :--- | :--- |
| **1. Smoke Test (`01-smoke.k6.js`)** | `1–5 VUs` | `1 min` | Verify scripts, auth tokens, and endpoints return `0%` 5xx errors under minimal load. |
| **2. Pre-UAT Load Test (`02-load-pre-uat.k6.js`)** | Expected UAT/Prod Peak (e.g. `50–200 VUs`) | `5–15 min` | Verify SLO thresholds (`p95 < 400ms`, `p99 < 900ms`, `error < 1%`) under realistic concurrent traffic. |
| **3. Stress / Spike Test (`03-stress-spike.k6.js`)** | `2x–3x Peak VUs` | `5–10 min` | Find the first bottleneck (DB connection pool, CPU, Redis, or Nginx worker limits) and verify graceful recovery. |
| **4. Soak Test (`04-soak.k6.js`)** | `80% Peak VUs` | `1–4 hours` | Detect memory leaks, unclosed DB connections, or disk-filling logs over time. |

---

## 2. Mandatory `k6` Authoring Rules

1. **Authenticate Once in `setup()` or Cache Token per VU**:
   - Do NOT hit `/auth/login` (which runs slow `bcrypt`/`argon2` hashing) on every single API iteration unless specifically load-testing the login endpoint! Obtain token(s) in `setup()` and pass `{ token }` to the `default` VU function.
2. **Use `SharedArray` to Prevent Artificial DB Cache Hits**:
   - Rotate across multiple user IDs, search keywords, and pagination offsets so the database buffer pool is tested realistically.
3. **Correlate Dynamic IDs (`POST` -> `GET` -> `PATCH`)**:
   - Capture the `id` returned by `POST` and pass it to subsequent `GET /resource/{id}` calls instead of hardcoding `id = 1`.
4. **Assert Both HTTP Status and Body Contract**:
   - An HTTP `200 OK` returning an HTML error page or `{"success": false}` is a failure — always validate JSON structure in `check()`.

```javascript
import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { SharedArray } from 'k6/data';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:3000';

export const options = {
  stages: [
    { duration: '1m', target: 20 },
    { duration: '3m', target: 50 },
    { duration: '1m', target: 0 },
  ],
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<400', 'p(99)<900'],
  },
};

export function setup() {
  const loginRes = http.post(
    `${BASE_URL}/api/v1/auth/login`,
    JSON.stringify({
      email: __ENV.TEST_EMAIL || 'qa@example.com',
      password: __ENV.TEST_PASSWORD || 'Password123!',
    }),
    { headers: { 'Content-Type': 'application/json' } }
  );
  const token = loginRes.status === 200 ? loginRes.json('data.accessToken') || loginRes.json('token') : '';
  return { token };
}

export default function (data) {
  const headers = {
    'Content-Type': 'application/json',
    ...(data.token ? { Authorization: `Bearer ${data.token}` } : {}),
  };

  group('01_Read_Browse_Endpoints', () => {
    const res = http.get(`${BASE_URL}/healthz`, { headers });
    check(res, {
      'status is 200': (r) => r.status === 200,
    });
  });

  sleep(Math.random() * 1.5 + 0.5);
}
```
