# 05. SSRF, Egress Control & File Upload Hardening

## 1. Purpose & Activation Conditions
Eliminate Server-Side Request Forgery (SSRF), cloud metadata credential theft, DNS-rebinding bypasses, and malicious file-upload execution/XSS. Load whenever backend code fetches user-influenced URLs (webhooks, link previews, PDF renderers, image proxies) or accepts user file uploads.

## 2. Prerequisites
- Outbound HTTP client supporting custom DNS/socket validation or dedicated egress proxy, plus isolated object storage (`shadow-api` Module `06`).

## 3. Technical Principles & Constraints
- **Defense-in-Depth Anti-SSRF Pipeline (Blocks All Classic Bypasses):**
  1. **Scheme & Userinfo Lock:** Allow strictly `https:` only (block `http:`, `file:`, `gopher:`, `ftp:`, `dict:`), and reject embedded credentials (`https://user@host`).
  2. **Explicit Host Allowlist When Bounded:** If the feature talks to a fixed set of providers, match exact lowercased hostnames against an immutable allowlist.
  3. **Upfront DNS Resolution (`all: true`) & Non-Global IP Blocklist:** Resolve ALL `A` and `AAAA` records and reject ANY non-global IP:
     - IPv4: `0.0.0.0/8`, `10.0.0.0/8`, `100.64.0.0/10` (CGNAT), `127.0.0.0/8` (loopback), `169.254.0.0/16` (AWS/GCP/Azure IMDS!), `172.16.0.0/12`, `192.168.0.0/16`, multicast/reserved.
     - IPv6: `::1`, `::`, `fc00::/7` (ULA), `fe80::/10` (link-local), and IPv4-mapped IPv6 `::ffff:0:0/96` (MUST unwrap to IPv4!).
     - Reject decimal/hex/octal obfuscations (`2130706433`, `0x7f000001`, `0177.0.0.1`) and internal cloud hostnames (`metadata.google.internal`).
  4. **Eliminate Redirect & TOCTOU DNS-Rebinding Bypasses:** Set `redirect: 'manual'` (or re-validate every hop against the exact same guard) AND connect directly to the validated IP (preserving TLS SNI `servername`) OR route untrusted egress through an isolated egress proxy with firewall rules blocking RFC 1918 & `169.254.169.254`!
  5. **Cloud IMDSv2 Enforcement (`/shadow-ops`):** Always enforce AWS **IMDSv2** (`HttpTokens=required`, hop limit `1`) so even a residual SSRF GET cannot steal EC2 IAM credentials.
- **File Upload Hardening (`OWASP ASVS v5.0.0-5.2.x`):**
  - Enforce hard size limit, verify **magic bytes** (never trust client `Content-Type` or extension), strip EXIF/metadata on images, store outside webroot under server-generated UUID keys, and serve from a separate sandbox domain with `Content-Disposition: attachment` + `X-Content-Type-Options: nosniff` (never render untrusted `.svg` or `.html` inline on the primary app origin!).

## 4. Architecture & Implementation
```typescript
import { lookup } from 'node:dns/promises';
import { isIP } from 'node:net';

function isForbiddenIpv4(ip: string): boolean {
  const parts = ip.split('.').map((n) => Number.parseInt(n, 10));
  if (parts.length !== 4 || parts.some((n) => Number.isNaN(n) || n < 0 || n > 255)) return true;
  const [a = -1, b = -1] = parts;
  return (
    a === 0 ||
    a === 10 ||
    a === 127 ||
    (a === 169 && b === 254) ||
    (a === 172 && b >= 16 && b <= 31) ||
    (a === 192 && b === 168) ||
    (a === 100 && b >= 64 && b <= 127)
  );
}

export function isForbiddenIpAddress(ip: string): boolean {
  const normalized = ip.trim().toLowerCase();
  if (isIP(normalized) === 4) return isForbiddenIpv4(normalized);
  if (normalized.startsWith('::ffff:')) return isForbiddenIpv4(normalized.slice(7));
  return (
    normalized === '::1' ||
    normalized === '::' ||
    normalized.startsWith('fe80:') ||
    normalized.startsWith('fc') ||
    normalized.startsWith('fd')
  );
}

export async function resolveAndValidateOutboundUrl(
  rawUrl: string,
  allowedHosts?: ReadonlySet<string>
): Promise<{ readonly url: URL; readonly pinnedIp: string }> {
  const parsed = new URL(rawUrl);
  if (parsed.protocol !== 'https:') throw new Error('SSRF_BLOCKED_PROTOCOL');
  if (parsed.username || parsed.password) throw new Error('SSRF_BLOCKED_USERINFO');
  const host = parsed.hostname.toLowerCase();
  if (allowedHosts && !allowedHosts.has(host)) throw new Error('SSRF_HOST_NOT_ALLOWED');

  const records = await lookup(host, { all: true });
  if (records.length === 0 || records.some((r) => isForbiddenIpAddress(r.address))) {
    throw new Error('SSRF_FORBIDDEN_DESTINATION_IP');
  }
  return { url: parsed, pinnedIp: records[0].address };
}
```
Offline SSRF regression test command:
```powershell
python "shadow-sec/scripts/appsec_control_verifier.py" --check-ssrf-url "https://2130706433/admin"
python "shadow-sec/scripts/appsec_control_verifier.py" --check-ssrf-url "https://partner.example/hook" --allow-host partner.example --resolved-ip "::ffff:169.254.169.254"
```

## 5. Platform / Vendor Variations
| High-Risk Feature | Classic SSRF / Upload Trap | Required Hardening |
| :--- | :--- | :--- |
| **HTML-to-PDF Renderers (Puppeteer/WeasyPrint/wkhtmltopdf)** | `<iframe src="http://169.254.169.254/...">` rendered inside headless browser! | Run renderer in network-isolated sandbox container (`--network=none` or egress proxy blocking private CIDRs) |
| **Image Proxy / Link Preview (`og:image`)** | `302 Found` redirect from public domain -> `http://127.0.0.1:6379` | Disable auto-redirects (`redirect: 'manual'`), re-validate each hop, cap max response bytes (`<= 5 MB`) & timeout (`<= 5s`) |
| **SVG Avatar Uploads** | Inline `<svg><script>...</script></svg>` executes Stored XSS on app domain | Reject SVG uploads for untrusted users (rasterize to WebP/PNG) OR serve exclusively from isolated sandbox domain |

## 6. Decision Matrix & Trade-Offs
| Egress Isolation Level | Blocks DNS Rebinding? | Operational Effort | When to Choose |
| :--- | :---: | :---: | :--- |
| **App-Level URL + DNS Check + IP Pinning** | Yes | Low–Medium | Baseline for every outbound webhook / fetcher |
| **Dedicated Egress Proxy / K8s NetworkPolicy** | **YES (Network-enforced)** | Medium | **Mandatory** for arbitrary user URL fetchers, headless PDF renderers & multi-tenant SaaS |

## 7. Real Production Scenario
A SaaS invoice builder renders customer-supplied HTML logos using headless Chromium on an AWS EC2 host running IMDSv1. A customer embeds `<img src="http://169.254.169.254/latest/meta-data/iam/security-credentials/prod-role">` and extracts full S3 credentials from the generated PDF. Enforcing IMDSv2 + running the PDF worker behind a private-CIDR-blocking egress proxy + validating URLs with `resolveAndValidateOutboundUrl` eliminates the entire exploit class.

## 8. Failure Modes & Edge Cases
- **WRONG:** Checking `!url.includes('localhost') && !url.startsWith('http://127.')` (bypassed by `http://2130706433/`, `http://[::1]/`, `http://0x7f000001/`, or a `302` redirect).
- **RIGHT:** Parse via standard URL parser, resolve all DNS records, check canonical IPv4/IPv6 ranges including `::ffff:` mapped addresses, pin the validated IP, and block unvalidated redirects.
- **WRONG:** Allowing `fetch()` with no response-body byte limit (attacker returns an infinite 10 GB gzip bomb exhausting worker RAM!).
- **RIGHT:** Stream response with a strict `maxBytes` abort controller and tight `5s` timeout.

## 9. Testing & Verification
- Run `python shadow-sec/scripts/appsec_control_verifier.py --self-test` and `python -m unittest discover -s shadow-sec/tests -v`.
- Verify negative SSRF vectors offline: `169.254.169.254`, `2130706433`, `0x7f000001`, `[::1]`, `[::ffff:169.254.169.254]`, `100.64.0.1`, `metadata.google.internal`, and `user:pass@host`.

## 10. Operational Considerations
- Log every `SSRF_FORBIDDEN_DESTINATION_IP` block as a high-signal security event (strong indicator of active attacker probing).

## 11. Authoritative References
- OWASP Server-Side Request Forgery Prevention Cheat Sheet (`https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html`).
- OWASP ASVS v5.0.0 — *V5 File Handling* & *V13 Configuration / Egress* (`https://asvs.owasp.org/`).

## 12. Limitations & When NOT to Use
- Application-level DNS validation alone still carries slight operational risk if a secondary library ignores custom socket pins; for high-risk arbitrary URL fetching, ALWAYS combine app guards with OS/VPC/NetworkPolicy egress filtering.
