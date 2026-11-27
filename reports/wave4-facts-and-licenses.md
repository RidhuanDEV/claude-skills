# Wave 4: Facts and license hygiene

27 November 2026 · **Gate: `PASS`** · **Readiness: `VERIFIED-LOCAL`**

| Exit criterion ([enhancement-review §7](enhancement-review.md)) | Result | Evidence |
| --- | --- | --- |
| A dated registry for standards, thresholds and legal citations | **15 facts**, each with source URL, publisher, `verified_on` and `review_by` | [facts-registry.json](../shadow-monarch/reference/facts-registry.json) |
| 0 overdue `review_by` dates | **0** | `facts_registry_check.py --repo .` passes. With `--today 2027-02-27` it fails exactly the 3 facts due on 2027-02-26 (MCP, OAuth 2.1, SSDF) |
| 0 conflicting fact values | **0** | One registry is the source of truth; duplicate IDs fail the schema check |
| Fix every row in §4.4 | **0 stale-fact findings** across 535 content files (39 at the start) | Checker scan |
| Every vendored file carries a license notice | **9/9** files, each with a notice, a `LICENSES.md` and a SHA-256 lock | [test_vendor_provenance.py](../evals/test_vendor_provenance.py) |
| 0 broken links | **0** relative links broken in any SKILL.md | [test_skill_content_contracts.py](../evals/test_skill_content_contracts.py); external URLs not checked (below) |

## Facts registry and checker

[facts_registry_check.py](../shadow-quality/scripts/facts_registry_check.py) uses only the standard library. It fails on:
- a schema error, duplicate ID or invalid date;
- a `review_by` date that has passed;
- a `stale_pattern` found on a line that does not explain the old fact (`allow_context`), for example "RFC 7489" without saying it is obsolete;
- a missing fact that a skill must mention (`required_in`), for example ASI01 in shadow-eval and shadow-ai-eng.

Vendored upstream text is reported as skipped rather than rewritten.

Each stale pattern has recall and precision probes in [test_facts_registry.py](../shadow-quality/tests/test_facts_registry.py), 14 facts in total. Examples of lines that must **not** be flagged:
- "SLSA v1.0/v1.2";
- "CycloneDX 1.5+";
- "MASVS v2.1.0";
- "font-size: 18px";
- "initialize the database";
- the deliberate "WRONG: mixing ASVS 4.0 and 5.0" counterexample.

The first scan's precision check found 4 such false positives, which were fixed before the gate was used.

## Drift fixed

| Fact | Files | Change |
| --- | --- | --- |
| OWASP Top 10 for LLM 2025 → **2026** | shadow-eval (SKILL, evaluations, refs 01/02/04/05, `ai_eval_gate.py`), shadow-ai-eng refs 01–06, finops, search, monarch, README, evals | Edition updated and every cited ID remapped (for example LLM06 Excessive Agency → LLM03, LLM05 Improper Output Handling → LLM10). 2025 LLM07 System Prompt Leakage has no same-named 2026 entry and is marked "confirm" |
| OWASP Agentic Top 10 (ASI01–ASI10), previously missing | shadow-eval ref 05 §4.1, shadow-ai-eng ref 02 §3.1 | Each ASI item is mapped to an existing probe or control |
| MCP 2026-07-28 (stateless) | shadow-ai-eng ref 06 | The stdio test uses `server/discover`; the `initialize` handshake is kept only for 2025-11-25 servers |
| DMARC RFC 9989, `pct` removed | shadow-email ref 10 and verifier fixture | RFC 7489 is marked obsolete |
| Postmaster v1 reputation retired | shadow-email refs 06/10 | Warm-up gate now uses v2 Compliance Status plus spam rate < 0.1% |
| OAuth 2.1 is still a draft | shadow-auth (SKILL, refs 02/03), ai-eng ref 06, monarch SECURITY/ENTERPRISE-INTEGRATION | Labelled draft-ietf-oauth-v2-1, with baseline RFC 9700 |
| ASVS 5.0.0 chapters | shadow-auth refs 01/03/06/08 | V6 Authentication, V7 Session, V8 Authorization, V11 Crypto; sections the registry does not pin are marked "verify before citing" |
| WebAuthn Level 3 | shadow-auth ref 05 | Recommendation of 2026-08-25 noted |
| Play target API 36 | shadow-mobile ref 03 | `targetSdk` and `compileSdk` 36; existing apps ≥ 35 |
| WCAG large text | antislop R-25, antislop-human | 24px regular or 18.66px bold (previously "18px+") |
| SVGO v4 | shadow-illustration | `preset-default` keeps `viewBox` and `<title>`; the unverified `svgo --check` flag is replaced with a re-run-and-diff step |
| CycloneDX 1.7 / SPDX 3.0.1 / SLSA 1.2 | shadow-supplychain ref 01, shadow-handover ref 01 | Current versions plus the 1.5+ minimum |
| Stale test descriptions | shadow-auth refs 06:99, 08:76 | They now describe the current offline policy-gate tests |

## Licenses

- **shadow-ops vendor:**
  - 5 OWASP cheat sheets: **CC BY-SA 4.0**. Each carries attribution, a license link, a source link and a modification notice.
  - 3 H5BP nginx configs: MIT, Copyright (c) H5BP.
- **shadow-test vendor:** the Goldberg testing guide, MIT, Copyright (c) 2019 Yoni Goldberg.
- **Locks:** each folder has a `LICENSES.md` with the upstream license text, and a `VENDOR.json` with the source, license and SHA-256. The SHA-256 is computed on LF content, so the lock also holds on `autocrlf` checkouts; tested by simulation.
- **Root notices:** [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md). The README license section now states that the MIT grant covers only original content and excludes the CC BY-SA files.
- **Falsification:** changing one byte in a vendored file makes `test_vendor_provenance.py` fail; the test passes again once the file is restored.

## Side fix

On Windows, Python `write_text` writes CRLF. Earlier patch scripts had converted 83 LF files to CRLF. All of them are back to LF (files that were already CRLF in `HEAD` were left as they were). Git now shows 0 CRLF warnings.

## Verification

| Check | Result |
| --- | --- |
| `facts_registry_check.py --repo .` | PASS, 15 facts, 535 files, 0 findings |
| Skill suites | 533 tests, 0 failures |
| `evals` (incl. content contracts and vendor provenance) | 89 OK |
| Node: perf / video | 13 / 7 pass |
| `skill_router.py --self-test` | 154/154 |
| Wave 2 regression on set M | exit 0 |
| Description audit | PASS, 7,909 characters |

## Not measured

- External links (URL reachability). lychee would make network calls and is a new tool, so it was not added.
- Upstream revision of the vendored files. It was not recorded when they were vendored; the files are pinned by hash and should be re-checked against the source.
- The `shadow-design` main pack (`ai-product-designer-skill-pack`) has **no recorded license**. The owner must confirm before publishing.
- Facts outside the registry's 15 entries. Other skills still contain unregistered versions and thresholds (for example Perpres 46/2025 thresholds and price tables). The registry is the mechanism; covering everything is ongoing work.
- Renamed rule IDs in `ai_eval_gate.py` (`LLM07_*` → `LLM08_*`, `LLM05_*` → `LLM10_*`, `LLM06_*` → `LLM03_*`). Repo-internal consumers were checked; external consumers were not.
- No independent adversarial review of the content edits.
