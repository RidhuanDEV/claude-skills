---
name: shadow-sec
description: "Application & SDLC Security Engineering Specialist. Use when performing STRIDE threat modeling, OWASP ASVS 5.0 & NIST SSDF audits, SQLi/OS-injection/XSS/CSP/CORS/SSRF hardening, AES-256-GCM/KMS secrets review, SAST/CVE reachability triage, or security incident containment. Do NOT use for UU PDP privacy (/shadow-privacy), auth implementation (/shadow-auth), or COBIT/OJK GRC (/shadow-grc)."
---

# Shadow Sec (`/shadow-sec`) — SDLC Security, Threat Modeling & OWASP ASVS 5.0 Auditor

Use this skill whenever the **Monarch** performs STRIDE threat modeling, AppSec code/PR reviews, SDLC Stage 4 & Stage 6 security gates, injection/SSRF/CSP/CORS/crypto hardening, CVE reachability triage, or security incident containment.

## 1. Core Security Audit Principles & Non-Negotiables

1. **Trust-Boundary STRIDE & Multi-Hop AuthZ:** Model every trust boundary (`Client -> Edge -> App -> Worker -> DB/Egress`), audit PR attack-surface diffs, and inspect multi-hop authorization chains (Gateway -> Internal Worker confused deputy). Delegate auth implementation to `/shadow-auth`, SBOM/SLSA attestations to `/shadow-supplychain`, UU PDP to `/shadow-privacy`, and COBIT/ISO 27001/OJK GRC to `/shadow-grc`.
2. **Verifiable Standards Only (Zero Fabricated IDs):** Map findings to exact adopted **OWASP ASVS v5.0.0 (`v5.0.0-C.S.R`)** and **NIST SSDF (`SP 800-218`)** controls. When an exact control mapping cannot be verified against the official catalog, report the technical finding clearly and mark `control_id: UNVERIFIED` — never fabricate IDs or claim formal certification.
3. **Structural Defenses Over Blacklists:** Enforce parameterized SQL (`$1`), shell-less `execFile` (`shell: false`), canonical path containment (`+ path.sep`), per-request nonce CSP + exact-origin CORS (`Vary: Origin`), HTTPS + upfront DNS-resolved anti-SSRF blocking all non-global IPv4/IPv6 (`169.254.169.254`, `2130706433`, `[::1]`, `::ffff:`), and `AES-256-GCM` with fresh 96-bit nonces + AAD + KMS `kid` rotation.
4. **Reachability-First Triage & Official-First Checks:** Prioritize CVEs by `runtime x reachable x untrusted input / KEV`; flag unverified npm lookalike swaps for local SDKs (`file:../sdk/sso-client`) and endpoints trusting frontend `username`.
5. **Strict `L0`–`L4` Approval Boundary:** Static SAST, STRIDE, and offline verification are `L0_READ_ONLY` / `L1_SAFE_VERIFICATION`. Active DAST/fuzzing against live services (`L3`) and production WAF/secret rotation/containment (`L4`) **NEVER** run without explicit Monarch approval.

## 2. Deterministic Verification CLI & Scenario Benchmarks

Run offline checks (`L0`/`L1`, zero outbound network calls) before claiming `VERIFIED-LOCAL`:
```powershell
python "shadow-sec/scripts/appsec_control_verifier.py" --self-test
python "shadow-sec/scripts/appsec_control_verifier.py" --check-security-headers path/to/headers.json
python "shadow-sec/scripts/appsec_control_verifier.py" --check-ssrf-url "https://partner.example/hook" --allow-host partner.example --resolved-ip "93.184.216.34"
python "shadow-sec/scripts/appsec_control_verifier.py" --check-finding-report path/to/findings.json
python -m unittest discover -s "shadow-sec/tests" -v
```
Graded specialist scenarios live in [evaluations.md](evaluations.md) (10 scenarios covering exposed internal endpoints in JS bundles, SSRF obfuscation bypasses, credentialed CORS reflection, ECB/hardcoded keys, CVE reachability triage, and unauthorized live-pentest refusal).

## Reference Guide

Load **only** the 1–2 modules matching the active subtask (never load all 8 at once):

| Task / Scenario | Tier | Load Reference |
| :--- | :--- | :--- |
| STRIDE threat modeling, trust boundaries, multi-hop confused deputy & PR attack-surface diffs | CORE | [references/01-stride-threat-modeling-and-trust-boundaries.md](references/01-stride-threat-modeling-and-trust-boundaries.md) |
| Verifiable OWASP ASVS v5.0.0 (`V1`–`V17`) & NIST SSDF (`SP 800-218`) control catalog & reporting | CORE | [references/02-owasp-asvs-5-and-nist-ssdf-catalog.md](references/02-owasp-asvs-5-and-nist-ssdf-catalog.md) |
| SQLi, NoSQL, OS command injection (`execFile`), path traversal, prototype pollution & ReDoS | CORE | [references/03-injection-and-input-boundary-defenses.md](references/03-injection-and-input-boundary-defenses.md) |
| Nonce CSP, exact-origin CORS (`Vary: Origin`), HSTS, XSS output encoding & safe rich text | CORE | [references/04-browser-security-csp-cors-and-csrf.md](references/04-browser-security-csp-cors-and-csrf.md) |
| DNS-resolved anti-SSRF (IPv4/IPv6/decimal/IMDSv2), egress proxies & magic-byte upload sandboxing | ADVANCED | [references/05-ssrf-egress-and-file-upload-hardening.md](references/05-ssrf-egress-and-file-upload-hardening.md) |
| `AES-256-GCM` AEAD + AAD + KMS `kid` rotation, blind indexes & zero-secret Git/CI hygiene | ADVANCED | [references/06-secrets-kms-and-cryptography-architecture.md](references/06-secrets-kms-and-cryptography-architecture.md) |
| Reachability-first CVE/SCA triage, SAST CI rules, `/shadow-supplychain` handoff & `L3` DAST gate | OPERATIONAL | [references/07-sast-dast-and-supply-chain-reachability.md](references/07-sast-dast-and-supply-chain-reachability.md) |
| 6-step security incident containment, forensic log preservation, key rotation & UU PDP 72h handoff | OPERATIONAL | [references/08-incident-containment-and-coordinated-patching.md](references/08-incident-containment-and-coordinated-patching.md) |

Do not load unrelated references unnecessarily.
