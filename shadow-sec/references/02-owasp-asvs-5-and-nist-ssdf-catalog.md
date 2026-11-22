# 02. OWASP ASVS 5.0 & NIST SSDF (SP 800-218) Control Catalog

## 1. Purpose & Activation Conditions
Map concrete security findings and SDLC release gates accurately to **NIST SSDF (SP 800-218)** and **OWASP ASVS v5.0.0** without fabricating control numbers or claiming unverified compliance. Load when executing SDLC Stage 4/6 security reviews, audit traceability tables, or formal AppSec reports.

## 2. Prerequisites
- Adopted assurance target level (ASVS **Level 2** default for production/enterprise apps; **Level 3** for critical financial, healthcare, or government systems).

## 3. Technical Principles & Constraints
- **Verifiable Citation Discipline (Zero Fabricated IDs):** Before citing any ASVS or NIST SSDF requirement ID in a report, confirm the exact adopted release (`ASVS v5.0.0`, `NIST SP 800-218 v1.1`) and verify the exact control number and requirement text. If a catalog mapping cannot be verified against the official text, report the technical vulnerability clearly and mark the control ID **`UNVERIFIED`** rather than guessing!
- **NIST SSDF (`PO`, `PS`, `PW`, `RV`) SDLC Mapping:** Security spans preparation (`PO`), source/artifact protection (`PS`), secure engineering (`PW`), and vulnerability response (`RV`) — never treat security as a single pre-launch scan.
- **OWASP ASVS v5.0.0 Structure:** Organizes verification across 17 chapters (`V1`–`V17`, citation format `v5.0.0-C.S.R`), covering encoding/sanitization (`V1`), validation (`V2`), web frontend/browser security (`V3`), API/web services (`V4`), file handling (`V5`), authn (`V6`), sessions (`V7`), authorization (`V8`), self-contained tokens (`V9`), OAuth/OIDC (`V10`), cryptography (`V11`), secure comms (`V12`), configuration/egress (`V13`), data protection (`V14`), secure coding/supply chain (`V15`), logging/error handling (`V16`), and WebRTC (`V17`).
- **Scope Separation:** Delegate formal COBIT/ISO 27001/POJK/SPBE governance audits to `/shadow-grc` and UU PDP statutory privacy reviews to `/shadow-privacy`.

## 4. Architecture & Implementation
### NIST SSDF (SP 800-218) x Shadow Army SDLC Matrix
| Practice Group | Practice ID | Shadow Army SDLC Stage & Owner | Verifiable Technical Artifact |
| :--- | :--- | :--- | :--- |
| **Prepare (`PO`)** | `PO.1`, `PO.3` | Toolchain & baseline guardrails (`shadow-monarch`, `/shadow-bootstrap`) | Strict compiler flags, `.gitignore`, pre-commit secret guard |
| **Protect (`PS`)** | `PS.1`, `PS.2`, `PS.3` | Source integrity, secrets & release provenance (`/shadow-git`, `/shadow-supplychain`, `/shadow-release`) | Zero secrets in Git history, pinned CI digests, SBOM & signed tags |
| **Produce (`PW`)** | `PW.1`, `PW.4`, `PW.7`, `PW.8` | Threat model (`/shadow-sec`), Auth (`/shadow-auth`), Code review & negative testing (`/shadow-test`) | STRIDE table, parameterized SQL, `0` reachable critical CVEs, 401/403 IDOR tests |
| **Respond (`RV`)** | `RV.1`, `RV.2`, `RV.3` | Post-prod monitoring, triage, hotfix & RCA (`/shadow-observe`, `/shadow-maintain`) | CVE patch SLA, regression test per security fix, blameless RCA |

### OWASP ASVS v5.0.0 Core Verification Matrix (Level 2 Baseline)
| Control Area | ASVS v5.0.0 Focus | Codebase Verification Check |
| :--- | :--- | :--- |
| **Injection & Encoding** | `V1` (`v5.0.0-1.2.x`) | Parameterized SQL (`$1`), `execFile` (`shell: false`), strict output encoding |
| **Validation & Business Logic** | `V2` | Strict DTO allowlists (`Zod`/`Pydantic`), server-side price/state validation |
| **Browser Security** | `V3` (`v5.0.0-3.4.x`) | Nonce CSP, `frame-ancestors 'none'`, exact CORS allowlist, `nosniff` |
| **API & Files** | `V4`, `V5` (`v5.0.0-5.2.x`) | Bounded pagination, rate limits, magic-byte upload check, sandbox download domain |
| **AuthN, Sessions & AuthZ** | `V6`, `V7`, `V8` (`v5.0.0-8.2.1`) | Argon2id, `HttpOnly`/`Secure` cookies, refresh family revocation, tenant `WHERE` + RLS |
| **Crypto, Comms & Config** | `V11`, `V12`, `V13`, `V14` | `AES-256-GCM` + KMS, TLS 1.2+/1.3 + HSTS, anti-SSRF DNS guard, `Cache-Control: no-store` |
| **Supply Chain & Logging** | `V15`, `V16` | Committed lockfiles, reachable CVE triage, generic RFC 9457 errors, redacted audit logs |

```powershell
# Verify structured ASVS/SSDF finding schema & two-tenant control test
python "shadow-sec/scripts/appsec_control_verifier.py" --self-test
python -m unittest discover -s "shadow-sec/tests" -v
```

## 5. Platform / Vendor Variations
| Assurance Target | Applicable Context | Additional Rigor Required |
| :--- | :--- | :--- |
| **ASVS Level 1** | Low-risk static / non-sensitive sites | Basic automated checks + zero critical injection/XSS |
| **ASVS Level 2 (Default)** | Standard SaaS, B2B, e-commerce, PII apps | Full authentication/session hardening, tenant isolation, KMS encryption, SSRF/CSP guards |
| **ASVS Level 3** | Banking/fintech (POJK), healthcare, government critical infra | Phishing-resistant Passkeys/FIDO2, HSM/KMS envelope crypto, formal threat model, independent pentest |

## 6. Decision Matrix & Trade-Offs
| Situation | Correct Reporting Behavior |
| :--- | :--- |
| Exact ASVS v5.0.0 control verified | Cite `ASVS-5.0 v5.0.0-C.S.R` + observed `file:line` + concrete patch |
| Exact sub-requirement ID uncertain | Report the exact technical vulnerability & CWE, mark ASVS sub-ID `UNVERIFIED` |
| Client asks for `"ISO/ASVS certification"` from an AI scan | **REFUSE certification claim** — clarify AI audit is internal technical readiness evidence only |

## 7. Real Production Scenario
An automated security report cited ASVS 4.0 chapter numbers (`V12 Files`, `V4 Access Control`) mixed with fabricated `V4.9.9` sub-IDs while claiming `"ASVS 5.0 Level 2 Compliant"`. An external assessor rejected the report immediately because ASVS 5.0 reorganized chapters (`V5 Files`, `V8 Authorization`, `V16 Logging`) and `V4.9.9` didn't exist. Enforcing version-pinned `v5.0.0-C.S.R` lookups with explicit `UNVERIFIED` fallback restored assessor trust completely.

## 8. Failure Modes & Edge Cases
- **WRONG:** Mixing ASVS 4.0 and ASVS 5.0 chapter numbers arbitrarily or claiming `"100% OWASP ASVS compliant"` after a 5-minute grep scan.
- **RIGHT:** State exact adopted version (`ASVS v5.0.0`), enumerate tested controls vs `NOT_RUN` controls, and tie every finding to verifiable `file:line` evidence.
- **WRONG:** Leaving `control_id` empty or omitting concrete remediation code in audit findings.
- **RIGHT:** Enforce the 5-part structured finding format (`severity`, `control_id`, `location`, `impact`, `remediation`) checked by `appsec_control_verifier.py`.

## 9. Testing & Verification
- Run `python shadow-sec/scripts/appsec_control_verifier.py --check-finding-report <findings.json>` and `python -m unittest discover -s shadow-sec/tests -v`.

## 10. Operational Considerations
- Re-check official OWASP ASVS and NIST SSDF minor revisions semi-annually; pin the exact adopted release string inside your team's security policy doc.

## 11. Authoritative References
- OWASP Application Security Verification Standard (ASVS) v5.0.0 (`https://asvs.owasp.org/`).
- NIST Special Publication 800-218 — *Secure Software Development Framework (SSDF)* (`https://csrc.nist.gov/pubs/sp/800/218/final`).
- MITRE CWE Top 25 Most Dangerous Software Weaknesses (`https://cwe.mitre.org/`).

## 12. Limitations & When NOT to Use
- Static code checklists cannot replace authorized runtime penetration testing or organizational GRC governance audits (`/shadow-grc`); present static findings honestly as technical pre-assessment evidence.
