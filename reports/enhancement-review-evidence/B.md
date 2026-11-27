# Grader B: 15 backend/data/AI skills (read-only review, 2026-11-26)

Repo: `D:\Ridhuan Ngoding Moment\SKILL` @ `1dbe3b5` (clean). I modified no repo files. The probe fixtures are in `C:/Users/Ridhuan/AppData/Local/Temp/claude/e80b2dfa48902dc8/c0b822e3-f9e8-41c6-a8c8-050edf286e4e/scratchpad/probesB/`.

## Global runs
`python -B -m unittest discover -s tests -q` was run in each skill dir. All 15 suites passed, as follows: api 3, auth 4, cache 6, concurrency 2, data 4, db 3, integrate 1, realtime 7 (19.7s), search 9, domain 3, ai-eng 2, eval 6 (39.7s), analytics 4, architect 1, bootstrap 4.
Link check over each skill's `**/*.md`: 0 broken markdown links. One unresolvable backtick path: `shadow-bootstrap/references/02-official-cli-generators-and-staging-adoption.md` cites `scripts/official_first_verifier.py`. The file is actually in `shadow-monarch/scripts`.
Provenance scan (URL count / "last verified" dates):
- api 21/0, auth 19/0, cache **0**/0, concurrency 7/0, data 12/0
- db 10/0, integrate 4/0, realtime **0**/0, search 5/0, domain 3/1
- ai-eng 9/1, eval 9/0, analytics 31/0, architect **0**/0, bootstrap **0**/0

No skill has a consistent "last verified" date.

## Prior-review defect re-probes (requested)
| Defect | Probe | Observed | Status |
|---|---|---|---|
| shadow-eval empty sample -> perfect | `--score-rag [{}]` | `INCOMPLETE`, gate_passed=False, all metrics `None`, exit 1 | **FIXED** |
| | `--score-rag []` | `INCOMPLETE` "Expected a non-empty samples array" | FIXED |
| | `[{"tenant_id":"t","retrieved_chunks":[]}]` | `INCOMPLETE` "answerable requires non-empty allowed labels" | FIXED |
| (residual) | single abstain-only or isolation-only sample | `PASS`, gate_passed=True, recall/citation/claim_support all `None`, exit 0 | residual MEDIUM |
| shadow-search duplicate doc -> Recall 2.0 / NDCG 1.63 | `d1` x3, grade d1=3, k=3 | Recall 1.0, MRR 1.0, NDCG 1.0, `duplicate_hits_at_k=2` | **FIXED** |
| | empty judgments + empty results | `FAIL`, `INSUFFICIENT_EVIDENCE` | FIXED |
| | `deleted_or_revoked:"false"` | `FAIL INVALID_INPUT` (must be boolean) | FIXED |
| | other-tenant doc at rank 3 > k=2 | `FAIL` ACL violation (checked beyond K) | FIXED (good) |
| shadow-realtime string flags + empty events pass | five `"false"` flags + `events:[]` (legacy) | `INCOMPLETE`, exit 1 | **FIXED** |
| | v2 with `events:[]` | `FAIL` "Trace needs a nonempty events array" | FIXED |
| | `trace_version:"2"` | `FAIL` Unsupported trace_version | FIXED |
| | minimal valid trace (1 deliver) | `INCOMPLETE`, missing resume/replay/revocation/queue | FIXED |
| shadow-bootstrap forces DB/OpenAPI/infra on offline CLI | `preview_scaffold.py X --profile cli` | `PREVIEW` deliverables = `[command entry point, exit-code and stdout smoke test]`, no DB/API | **FIXED** |
| | non-empty target | `REVIEW_EXISTING`, deliverables `[]`, exit 1 | FIXED |

Other prior-review items: shadow-auth 401-vs-403/404 **FIXED** (ref 08:13 now separates the anonymous 401 case, and the verifier requires `unauth_401`). shadow-cache idempotency fingerprint **FIXED** (SKILL.md:64, ref 04:16). shadow-db ETL honesty **FIXED** (SKILL.md:15 "File generation alone does NOT verify execution"). shadow-architect ADR-by-scope **FIXED** (SKILL.md:33). shadow-integrate provider-capability gate **PARTIALLY FIXED** (SKILL.md:14, but the tool still has a binding gap; see below).

## New defects found by fresh probes (same defect class the prior review flagged in realtime: boolean truthiness)
| Skill | Probe | Observed | Severity |
|---|---|---|---|
| shadow-auth | `{"deny_by_default":true,"routes":[{"path":"/api/admin/export","public":"false","privileged":true}]}` | `passed: true`, errors `[]`. A privileged route with no server auth passes because `bool("false")` is True (`auth_policy_verifier.py:88`) | **CRITICAL** (false PASS on a security gate) |
| shadow-concurrency | all safety flags `"false"`, `max_attempts:3` | `PASS`, `delivery_guarantee: AT_LEAST_ONCE_WITH_IDEMPOTENT_DEDUP` (`concurrency_invariant_checker.py:24-29` uses `bool()`). The "simulation" only re-reads declared flags. | **CRITICAL** (false PASS) |
| shadow-analytics | guardrail `{"regressed":"true"}` | `SHIP_CANDIDATE`, passed=True (`analytics_experiment_verifier.py` guardrail loop uses `is True`, so the string is silently ignored) | **CRITICAL** (false ship verdict) |
| shadow-analytics | 10000 vs 10600 at 50/50 with `srm_alpha:0` | `SHIP_CANDIDATE`. The caller can disable the SRM gate (`:209`, no bounds check). The same data at default alpha gives `BLOCKED_SRM`, p=2.9e-5 | HIGH |
| shadow-cache | `{"pattern":"prod:tenant_{t}:orders:v1:{id}","persistent_structure":"false"}` with no TTL | `PASS` (`cache_policy_verifier.py:59` `bool()` skips the TTL rule) | HIGH |
| shadow-integrate | UNKNOWN op, inquiry `verified:true`, same op id, `account:"OTHER"`, `amount_minor:999` | `RECORD_CONFIRMED`. `reconcile_unknown.py:19-22` never compares account/amount, although SKILL.md:14 requires that binding | HIGH (money) |
| shadow-api | problem+json whose `detail` holds a raw PG `duplicate key value violates unique constraint "users_email_key"` plus a `node_modules/pg/lib/client.js:526` path | `passed: true` (`api_contract_verifier.py:21-23` leak regex is too narrow) | MEDIUM |
| shadow-db | `alter table orders alter column email set not null;` (no lock_timeout) | not flagged (only CREATE INDEX/FK flagged) | MEDIUM |
| shadow-db | `-- SET lock_timeout = 3s;` (comment) + FK NOT VALID | `passed: true`, no warning: a comment satisfies the check | MEDIUM |

---

### shadow-api
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 3 | 3 | 3 | 2 | 3 | 3 | 2 | 2.75 | MEDIUM |

Strengths
- Step 0 ownership discovery (Code-First vs Contract-First, a stop gate on generic doc requests) is concrete and operable (SKILL.md:10-16).
- The standards it cites are correct: RFC 9457, RFC 9745 `Deprecation: @<unix>`, RFC 8594 `Sunset`. RateLimit headers are honestly labeled an IETF draft (ref 07:10).
- 10 scenario evals with must/must-not columns (evaluations.md).

Gaps
- MEDIUM: the problem+json leak oracle misses common ORM/driver messages (PG `violates unique constraint`, `ER_DUP_ENTRY`, Sequelize, `node_modules` paths). The probe passes at `scripts/api_contract_verifier.py:21-23`.
- MEDIUM: only 3 unit tests. The `--check-breaking-diff` recall is untested against enum narrowing and optional-to-required response changes (tests/test_api_contract_verifier.py).
- LOW: outbound webhooks (SKILL.md:3) overlap shadow-integrate, and neither description sets a boundary for them.
- LOW: no "last verified" dates on the 21 URLs (references/*).

Prior-review defect status: ALREADY GOOD previously. The host-conversation eval it suggested is still not present (N/A).
Upgrade actions:
1. Broaden `LEAK_PATTERNS` using the OWASP Error Handling Cheat Sheet and add precision/recall probes for PG/MySQL/Prisma/Sequelize/file paths.
2. Add breaking-diff fixtures per the oasdiff rule catalogue.
3. Add `last_verified` dates to RFC 9457/9745/8594 citations.

Test/self-test run: `python -B -m unittest discover -s tests -q` -> 3 OK. Probe described above -> false `passed: true`.

### shadow-auth
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 3 | 2 | 3 | 1 | 3 | 3 | 2 | 2.38 | **BAD** (critical tool defect) |

Strengths
- Senior-level content: refresh-token family reuse revocation, dummy-hash anti-enumeration, Zookie consistency, HMAC-digested API keys (SKILL.md:12-16; evaluations AUTH-EVAL-05/08/09).
- The 401/403/404 matrix is now correctly separated (references/08-audit-trails-and-auth-security-testing.md:13-16).

Gaps
- **CRITICAL**: `--check-policy-matrix` returns `passed: true` for a privileged admin route with no server auth when `"public":"false"` (`scripts/auth_policy_verifier.py:88` `bool(r.get("public", False))`).
- HIGH (D3): it claims ASVS 5.0 but cites ASVS 4.0.3 chapter numbers. Examples: "ASVS 5.0 (V2)" Authentication (ref 01:4, 01:90), "ASVS V2.4" password storage (ref 01:10), "ASVS V3" sessions (ref 03:10), "ASVS 5.0 V7/V16" logging (ref 08:82). In ASVS 5.0, V2 is Validation & Business Logic, V6 Authentication, V7 Session Management, V11 Cryptography and V16 Logging (verified against github.com/OWASP/ASVS/5.0/en).
- MEDIUM: OAuth 2.1 is presented as a normative standard ("Deprecated & FORBIDDEN (OAuth 2.1)", ref 02:89), but it is still an IETF draft. RFC 9700 (OAuth 2.0 Security BCP) is the normative source and is cited only once (ref 02:109).
- MEDIUM (D1): router probe "rotate JWT signing keys" -> none (orchestrator measurement), although ref 04 covers exactly this.
- LOW: no dated provenance.

Prior-review defect status: 401-vs-403/404 conflation **FIXED** (ref 08:13; verifier requires `unauth_401`).
Upgrade actions:
1. Replace every `bool(x.get(...))` with strict `type(x) is bool` validation (fail INVALID_INPUT) and add string-flag precision probes.
2. Remap all ASVS references to ASVS 5.0.0 IDs (V6.x, V7.x, V8.x, V9.x, V10.x, V11.4).
3. Label OAuth 2.1 as draft-ietf-oauth-v2-1 and anchor to RFC 9700 / RFC 9449 / RFC 7636.
4. Add JWKS rotation keywords to the router.

Test/self-test run: unittest -> 4 OK. Probe `au1.json` -> `{"passed": true, "errors": []}`.

### shadow-cache
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 3 | 3 | 2 | 2 | 3 | 2 | 1 | 2.25 | MEDIUM |

Strengths
- The idempotency contract now covers the fingerprint, an auth recheck before replay, and lost-ack reconciliation (SKILL.md:62-66).
- `tests/test_idempotency.py` exercises real competing connections and changed payloads, not just declarations (SKILL.md:72).

Gaps
- HIGH: `cache_policy_verifier.py:59` `bool(entry.get("persistent_structure"))` makes `"false"` skip the TTL rule. A TTL-less tenant key returns `PASS`.
- MEDIUM (D4): no ordered workflow or deliverable contract. The skill is a list of rules (SKILL.md:27-66).
- MEDIUM (D7): the inline TS code block and idempotency rules are duplicated across shadow-api (SKILL.md:21), shadow-concurrency and shadow-cache (SKILL.md:60-66). The ownership is unclear.
- MEDIUM (D1): router probe "our redis cache returns other tenant data" -> none.
- LOW: SKILL.md:50 says `private, no-store` on all authenticated routes, but evaluations CACHE-EVAL-03 permits `private, no-cache` + ETag. The two are inconsistent.
- HIGH (D8): zero URLs across SKILL and refs. RFC 9111, RFC 9110 and the Fastly/Cloudflare surrogate-key docs are not cited.

Prior-review defect status: idempotency fingerprint **FIXED** (SKILL.md:64; ref 04:16).
Upgrade actions:
1. Use strict boolean typing in the verifier.
2. Cite RFC 9111 (HTTP Caching), RFC 5861 (stale-while-revalidate), the TanStack Query v5 docs and the Redis key-eviction docs, with dates.
3. Make shadow-concurrency the single idempotency owner and link to it.
4. Add an ordered 5-step workflow and a deliverable template.

Test/self-test run: unittest -> 6 OK. Probe `k1.json` -> `PASS, violation_count 0`.

### shadow-concurrency
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 3 | 3 | 2 | 1 | 2 | 3 | 2 | 2.38 | **BAD** (critical tool defect) |

Strengths
- Correct non-claims: no unassisted exactly-once, commit->outbox->dispatch->ack, fencing tokens with the Kleppmann rationale (SKILL.md:13-16; CONC-EVAL-05).
- Right-sizing guidance (Postgres SKIP LOCKED before Kafka; CONC-EVAL-07).

Gaps
- **CRITICAL**: `--verify-workflow` with all safety flags set to `"false"` returns `PASS` / `AT_LEAST_ONCE_WITH_IDEMPOTENT_DEDUP` (`scripts/concurrency_invariant_checker.py:24-29`).
- HIGH (D5): the "replay simulation" (`:43-54`) is a deterministic function of the declared booleans. It cannot observe a real crash-before-ack, so it is tautological. The prior review's "integration fixture" recommendation is not implemented (only 2 unit tests).
- MEDIUM (D4): no ordered workflow or output contract in SKILL.md (only 4 invariants plus links to the methodology/playbook).
- MEDIUM (D6): no approval-level guidance for DLQ replay or purge, or for broker config changes on shared infra.
- LOW: "<500 jobs/s" for Postgres SKIP LOCKED (SKILL.md:16) is unsourced.

Prior-review defect status: rated ALREADY GOOD previously. The truthiness class found in realtime is **present here and STILL OPEN**.
Upgrade actions:
1. Use strict boolean typing and probes for string/missing flags.
2. Replace the declaration simulation with a trace-based checker (like realtime v2) or a SQLite crash-before-ack fixture (like shadow-data's `test_expand_backfill.py`).
3. Cite the Postgres `SKIP LOCKED` docs and the RabbitMQ/Kafka delivery-semantics docs with dates.

Test/self-test run: unittest -> 2 OK. Probe `c1.json` -> `PASS`.

### shadow-data
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 3 | 3 | 3 | 3 | 4 | 3 | 2 | 2.88 | MEDIUM |

Strengths
- Correct PG lock semantics (VALIDATE takes SHARE UPDATE EXCLUSIVE, ref 02:15/57) and the `CHECK ... NOT VALID -> VALIDATE -> SET NOT NULL` (PG12+) recipe (ref 01:52, ref 02:31-42).
- The explicit L1-vs-L4 boundary for destructive DDL / `migrate reset` (SKILL.md:16; DATA-EVAL-08) is strong.
- `test_expand_backfill.py` is a real SQLite simulation of legacy-writer drift.

Gaps
- HIGH (D1): router probe "migrate column email to NOT NULL in 50M row table" -> none, although this skill holds the exact recipe.
- MEDIUM: the contract-phase consumer inventory and owner (prior-review suggestion) is mentioned only as "0 legacy consumers verified" (SKILL.md:12). No required output fields.
- MEDIUM: the verifier does not lint DDL (that tool is in shadow-db), and `SET NOT NULL` is not caught by either tool.
- LOW: no dated provenance (12 URLs).

Prior-review defect status: contract-phase evidence **PARTIALLY FIXED** (SKILL.md:12 requires 0 consumers + L4, but no reader/writer list contract).
Upgrade actions:
1. Add NOT NULL / rename / type-change keywords to the router.
2. Add a `contract_readiness` schema (readers, writers, adoption evidence, owner) to `--check-migration-phases`.
3. Cite the PostgreSQL 16/17 ALTER TABLE lock docs with dates.

Test/self-test run: unittest -> 4 OK; `--self-test` OK.

### shadow-db
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 3 | 3 | 3 | 2 | 4 | 3 | 2 | 2.75 | MEDIUM |

Strengths
- Fail-closed unknown host (`BLOCKED_UNKNOWN_ENVIRONMENT`) with L4 for any mutation (SKILL.md:13; DB-EVAL-07).
- An honest ETL claim: draft artifacts are not verification (SKILL.md:15; DB-EVAL-08).
- Correct specifics: `(SELECT auth.uid())` InitPlan, `SET search_path=''` on SECURITY DEFINER, PgBouncer >=1.21 `max_prepared_statements` (ref 05:10).

Gaps
- MEDIUM: the DDL verifier misses `ALTER COLUMN ... SET NOT NULL` (full scan under ACCESS EXCLUSIVE). The probe `d1.sql` flagged only the index and FK.
- MEDIUM: a `SET lock_timeout` inside a SQL comment satisfies the lock_timeout check (probe `d2.sql` -> passed, no warning). There is no comment stripping in `scripts/sql_migration_safety_verifier.py`.
- MEDIUM (D1): router probes "why is this query slow EXPLAIN" -> none. "bikin ERD dari database postgres" -> shadow-db, but with the RLS playbook instead of ref 06.
- LOW: only 3 unit tests. There is no RLS policy fixture with `auth.uid()` unwrapped inside a function body.

Prior-review defect status: ETL evidence levels **FIXED** (SKILL.md:15).
Upgrade actions:
1. Strip SQL comments before regex.
2. Add rules for SET NOT NULL, ALTER TYPE, and ADD COLUMN with a volatile default (PG docs "ALTER TABLE" lock table).
3. Route EXPLAIN/ERD keywords to refs 03 and 06.

Test/self-test run: unittest -> 3 OK. Probes as above.

### shadow-integrate
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 3 | 3 | 3 | 2 | 3 | 3 | 2 | 2.63 | MEDIUM |

Strengths
- UNKNOWN-state discipline: never mark a timeout FAILED; replay only inside a verified provider dedup window (SKILL.md:14; INT-EVAL-02).
- SNAP BI specifics are correct: unique daily `X-EXTERNAL-ID`, minified-body SHA-256 in the string-to-sign (INT-EVAL-06).

Gaps
- HIGH: `reconcile_unknown.py:19-22` returns `RECORD_CONFIRMED` for an inquiry with a different account and amount. It checks only `operation_id` + `verified`, which contradicts SKILL.md:14 ("verifying identical account/operation/tx/amount").
- MEDIUM (D5): 1 unit test; the self-test is 13 hand-asserted cases with no schema validation of `state`/`inquiry`.
- MEDIUM (D1): router "set up stripe webhook signature check" -> playbook 04 instead of 02 (HMAC webhooks).
- LOW (D8): only 4 URLs. No links to the Stripe webhook docs, Midtrans notification docs, or the SNAP BI spec version/date.

Prior-review defect status: provider-capability gate **FIXED in text** (SKILL.md:14, 25). Tool binding is **STILL OPEN** (amount/account).
Upgrade actions:
1. Require and compare `account`, `amount_minor`, `currency`, `provider_tx_id` on inquiry; anything else -> MANUAL_RECONCILIATION.
2. Cite the SNAP BI (ASPI) standard version, the Stripe "Verify webhook signatures" page, and Midtrans HTTP notification docs with dates.
3. Fix the routing keyword for webhook signature -> ref 02.

Test/self-test run: unittest -> 1 OK. Probe `i1.json` -> `{"next_action": "RECORD_CONFIRMED"}`.

### shadow-realtime
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 3 | 3 | 3 | 3 | 3 | 3 | 1 | 2.75 | MEDIUM |

Strengths
- The v2 trace verifier is now a real state machine with strict types, INCOMPLETE vs FAIL, and required coverage of resume, replayed duplicate, post-revocation block, queue, and cross-node (`scripts/realtime_transport_verifier.py:38-180`).
- Honest scope note: "A passing trace is evidence for the supplied sequence only" (SKILL.md:57).

Gaps
- HIGH (D8): zero URLs. RFC 6455, the WHATWG HTML SSE section (`Last-Event-ID`), RFC 8441, and MQTT 5.0 are not cited.
- MEDIUM: `blocked` events are self-reported by the trace author. Nothing ties them to a dispatcher log, so a fabricated trace can PASS (SKILL.md:59 warns against this, but no check enforces it).
- LOW: SKILL.md puts the Reference Guide (lines 11-23) before the workflow, and section 3 (lines 50-59) is dense prose. D7 is acceptable.
- LOW: no approval levels for load/reconnect-storm tests (should map to L3).

Prior-review defect status: string flags + empty events **FIXED** (probes r1-r4 above).
Upgrade actions:
1. Add dated citations: RFC 6455, WHATWG HTML §9.2 SSE, RFC 7692 (permessage-deflate), MQTT 5.0 OASIS.
2. Require a `source` field (broker/dispatcher/client) per event and reject `blocked` without a dispatcher source.

Test/self-test run: unittest -> 7 OK (19.7s).

### shadow-search
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 3 | 3 | 3 | 3 | 3 | 3 | 2 | 2.88 | MEDIUM |

Strengths
- The metrics are now correct: dedup with `duplicate_hits_at_k`, ideal-DCG at the same K, a distinct-positive denominator, and ACL checks across the full list, not just top-K (`scripts/search_relevance_acl_gate.py:80-120`).
- Honest limits: tenant match does not prove a pre-top-K filter (SKILL.md:51). Segment and paired comparison discipline (SKILL.md:45-53).
- Correct engine facts: `max_result_window` 10,000, PIT + `search_after`, RRF k=60.

Gaps
- MEDIUM: without `allowed_document_ids`, the ACL check is tenant equality only. The gate can PASS with no permission-scope evidence and gives no warning (`:89`).
- MEDIUM: `evals/compare_search_indexes.py` (ref 04:38) lives at the repo root, outside the skill, so the skill is not self-contained.
- LOW (D8): 5 URLs, undated. No Lucene/OpenSearch version is pinned for analyzer claims.

Prior-review defect status: Recall 2.0 / NDCG 1.63 and empty-query PASS **FIXED**.
Upgrade actions:
1. Emit `acl_evidence: TENANT_ONLY` and WARN/INCOMPLETE when there is no allowed-ID snapshot.
2. Cite TREC/`trec_eval` NDCG definitions and OpenSearch 2.x/3.x docs with dates.

Test/self-test run: unittest -> 9 OK.

### shadow-domain
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 3 | 3 | 3 | 2 | 3 | 3 | 2 | 2.75 | MEDIUM |

Strengths
- An anti-overengineering rule and STOP/escalate on policy conflicts (SKILL.md:13-14; DOMAIN-EVAL-02/03).
- Concrete invariants: closed FSM, maker-checker, CAS `version`, fail-closed ACL (SKILL.md:15-16).

Gaps
- MEDIUM: `domain_invariant_verifier.py:43` `bool(tx.get("expected_allowed", True))` has the same truthiness class (`"false"` becomes True).
- MEDIUM (D5): 3 unit tests. The verifier checks declared models, not code.
- LOW: the prior-review suggestion (policy-change handoff with owner and effective date) is not present in evaluations.md.
- LOW (D8): 3 URLs, 1 date.

Prior-review defect status: ALREADY GOOD previously. Suggested enhancements are still not implemented (N/A).
Upgrade actions:
1. Use strict boolean typing.
2. Add an effective-dated policy scenario.
3. Cite Evans/Vernon and Fowler articles with dates.

Test/self-test run: unittest -> 3 OK; `--self-test` OK.

### shadow-ai-eng
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 3 | 3 | 2 | 2 | 3 | 3 | 2 | 2.63 | MEDIUM |

Strengths
- Correct trust boundaries: no LLM-supplied `tenantId`/`rawSql`, HITL + idempotency on mutating tools, and MCP stdout kept JSON-RPC-only (SKILL.md:12-15).
- A clean sibling boundary to shadow-search, shadow-eval and shadow-finops (SKILL.md:16).

Gaps
- MEDIUM (D4): no ordered workflow or deliverable contract, only non-negotiables plus references.
- MEDIUM (D5): 2 unit tests. The checks are config-declaration based (`--check-tool-spec`, `--check-prompt-layout`).
- LOW (D3): `thinking_budget` (SKILL.md:13) is vendor-specific naming. Anthropic uses `thinking.budget_tokens`, so the skill should state the provider mapping or defer to `/context7`.
- LOW: no dates on model/API claims, which change fast.

Prior-review defect status: N/A (not covered).
Upgrade actions:
1. Add a 5-step workflow (contract -> gateway -> tools/HITL -> streaming -> eval handoff).
2. Pin the MCP spec revision (modelcontextprotocol.io, 2025-06-18 or later) and per-provider structured-output docs with dates.

Test/self-test run: unittest -> 2 OK; `--self-test` all passed.

### shadow-eval
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 3 | 3 | 3 | 3 | 4 | 3 | 2 | 2.88 | MEDIUM |

Strengths
- The OWASP LLM Top 10 2025 IDs are correctly mapped (LLM05 Improper Output Handling, LLM07 System Prompt Leakage, LLM08 Vector & Embedding; ref 05:18-25). NIST AI 600-1 is cited correctly.
- The L1 vs L3 boundary for paid live sweeps and honest `NOT_RUN` reporting (SKILL.md:16; EVAL-SCEN-08).
- The scorer now has typed samples, duplicate-ID rejection, and grounded claims requiring citation ⊆ allowed (`scripts/ai_eval_gate.py:110-180`).

Gaps
- MEDIUM: a dataset with only abstain or isolation samples returns `PASS` with no answerable coverage (probes e4/e5, exit 0). There is no minimum-coverage gate in `score_rag_dataset` (`:213-247`).
- MEDIUM: legacy (untyped) answerable rows PASS with `claim_support: None`, so faithfulness is unmeasured but the gate passes (probe e6).
- MEDIUM (D1): the description has no "Do NOT use" clause (SKILL.md:3), unlike siblings.
- LOW: it references `evals/compare_search_indexes.py` (SKILL.md:28), which lives outside the skill.

Prior-review defect status: empty sample -> perfect score **FIXED** (probes e1-e3 -> INCOMPLETE).
Upgrade actions:
1. Require >=1 answerable sample with judged claims for `PASS`, otherwise `INSUFFICIENT_EVIDENCE`.
2. Add a "Do NOT use for retrieval tuning (/shadow-search) or runtime build (/shadow-ai-eng)" clause.
3. Date-stamp the OWASP GenAI 2025 / NIST AI 600-1 citations.

Test/self-test run: unittest -> 6 OK (39.7s).

### shadow-analytics
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 4 | 3 | 3 | 1 | 2 | 3 | 3 | 2.75 | **BAD** (critical tool defect) |

Strengths
- The deepest knowledge in the set: Assignment vs Exposure, SRM at alpha 0.001 as a hard block, Delta Method for ratio metrics, pre-assignment-only CUPED, mSPRT/GST, switchbacks, DiD/SCM/RDD (SKILL.md:12-15; 15 refs, 13 evals).
- The best provenance of the 15 (31 URLs).

Gaps
- **CRITICAL**: a blocking guardrail with `"regressed":"true"` is silently ignored, giving `SHIP_CANDIDATE` (probe a3). The `is True` check discards non-bool values without INVALID_INPUT.
- HIGH: `srm_alpha` is caller-controlled with no bounds (`scripts/analytics_experiment_verifier.py:209`). `srm_alpha:0` disables the SRM gate and gives `SHIP_CANDIDATE` on data that otherwise returns `BLOCKED_SRM` (probe a2). This defeats the "BLOCK regardless" rule in SKILL.md:14.
- MEDIUM: `assignment_exposure_separated` is checked only when explicitly `False`. If it is missing, the check passes silently.
- MEDIUM (D6): multi-vendor DSAR deletion calls (PostHog/GA4/Mixpanel) are irreversible but carry no L4 or approval marker (SKILL.md:13).
- LOW: no "last verified" dates.

Prior-review defect status: N/A.
Upgrade actions:
1. Validate every flag strictly and reject unknown types.
2. Clamp `srm_alpha` to [1e-6, 0.01] and require a justification field for overrides (Kohavi et al., *Trustworthy Online Controlled Experiments*, ch. 21).
3. Mark vendor DSAR deletion execution as L4.
4. Add dates to citations.

Test/self-test run: unittest -> 4 OK. Probes a1 (BLOCKED_SRM, correct), a2/a3 (false SHIP_CANDIDATE).

### shadow-architect
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 3 | 2 | 3 | 1 | 3 | 3 | 1 | 2.38 | MEDIUM |

Strengths
- Decision-scope calibration (inline answers for reversible local changes, ADR for shared contracts and deployment) fixes the prior defect (SKILL.md:33; ref 01:18).
- Brownfield preservation with a precedence hierarchy and a clean `/shadow-ea` boundary (SKILL.md:39; ARCH-EVAL-07).

Gaps
- HIGH (D5): there are no scripts. `tests/test_boundary_levels.py:5-30` defines the function it tests inside the test file, so it verifies nothing the skill ships (a tautology).
- MEDIUM (D3): the extraction thresholds "25+ engineer release contention" and "> 10x scaling divergence" (SKILL.md:30) are presented as rules with no source. The 5x revisit trigger (ref 01:68) is also unsourced.
- HIGH (D8): zero URLs. C4 (c4model.com), Mermaid C4 syntax, the Nygard ADR format, and *Building Evolutionary Architectures* (fitness functions) are not cited.
- LOW: `evals/decision-trials.md` is listed in the Reference Guide (SKILL.md:23) as a "load" item for agents, which mixes grader material with runtime context.

Prior-review defect status: ADR-by-scope **FIXED** (SKILL.md:33).
Upgrade actions:
1. Ship a small `topology_decision_checker.py` that consumes a decision record, and test that.
2. Label the thresholds as heuristics with sources (Team Topologies; Fowler "MonolithFirst").
3. Add dated citations.

Test/self-test run: unittest -> 1 OK (tautological).

### shadow-bootstrap
| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | Avg | Grade |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 2 | 3 | 3 | 2 | 3 | 3 | 1 | 2.50 | MEDIUM |

Strengths
- Profiles plus opt-in capabilities. A CLI gets 0 infrastructure deliverables, and a non-empty target gives `REVIEW_EXISTING` with exit 1 (`scripts/preview_scaffold.py:8-41`).
- Sibling-staging adoption for generators that might clobber `.git` (SKILL.md:31).

Gaps
- MEDIUM: there is drift between SKILL and tool. SKILL.md:36 makes config validation, a structured logger and SIGTERM shutdown mandatory for `http`, but the `http` preview deliverables are only `[request handler, exercise one documented request]` unless `--capability configuration/telemetry` is passed (`preview_scaffold.py:12`).
- MEDIUM (D5): preview never inspects parent monorepo manifests or nested `.git`, which SKILL.md:28 says to check. It is purely manual.
- MEDIUM (D2): thin depth. 3 references, and it does not name the version-specific generator flags it relies on.
- HIGH (D8): zero URLs. Unresolvable path `scripts/official_first_verifier.py` (`references/02-official-cli-generators-and-staging-adoption.md`; the real path is `shadow-monarch/scripts/official_first_verifier.py`).

Prior-review defect status: forced DB/OpenAPI/infra on an offline CLI **FIXED** (probe output above).
Upgrade actions:
1. Make `http` default-include configuration and telemetry, or soften SKILL.md:36.
2. Add parent-manifest and `.git` detection to preview.
3. Cite the official generator docs (vite.dev, nextjs.org create-next-app, docs.astral.sh/uv, go.dev/ref/mod) with dates.
4. Fix the path.

Test/self-test run: unittest -> 4 OK. Probes: cli PREVIEW, existing REVIEW_EXISTING.

---

## Summary table
| Skill | Avg | Grade | Top gap |
|---|---|---|---|
| shadow-api | 2.75 | MEDIUM | leak regex misses raw PG errors/paths -> false PASS |
| shadow-auth | 2.38 | BAD | `"public":"false"` -> privileged route passes with no auth; ASVS 5.0 IDs wrong |
| shadow-cache | 2.25 | MEDIUM | string flag skips TTL rule; 0 citations; no workflow |
| shadow-concurrency | 2.38 | BAD | string flags -> PASS "AT_LEAST_ONCE_WITH_IDEMPOTENT_DEDUP"; tautological sim |
| shadow-data | 2.88 | MEDIUM | router misses NOT NULL migration; no contract-readiness schema |
| shadow-db | 2.75 | MEDIUM | SET NOT NULL unflagged; commented lock_timeout counts |
| shadow-integrate | 2.63 | MEDIUM | reconcile ignores account/amount -> RECORD_CONFIRMED |
| shadow-realtime | 2.75 | MEDIUM | 0 citations; self-reported `blocked` events |
| shadow-search | 2.88 | MEDIUM | tenant-only ACL evidence passes silently |
| shadow-domain | 2.75 | MEDIUM | truthiness in verifier; thin tests |
| shadow-ai-eng | 2.63 | MEDIUM | no ordered workflow; declaration-only checks |
| shadow-eval | 2.88 | MEDIUM | abstain/isolation-only dataset PASSes with no answer coverage |
| shadow-analytics | 2.75 | BAD | `"regressed":"true"` ignored and `srm_alpha:0` bypass -> SHIP_CANDIDATE |
| shadow-architect | 2.38 | MEDIUM | test checks its own inline function; 0 citations |
| shadow-bootstrap | 2.50 | MEDIUM | http preview omits SKILL-mandated config/logging/shutdown; 0 citations |

## Cross-cutting observations
1. **The truthiness defect was fixed in realtime only, not across the set.** `bool(x.get(...))` or silent `is True` handling still turns string flags into false PASS verdicts in auth (CRITICAL), concurrency (CRITICAL), analytics (CRITICAL), cache (HIGH) and domain (MEDIUM). A shared strict-typing helper plus a repo-wide string-flag probe in CI would close this whole class.
2. **Most verifiers check declarations, not observations.** They check JSON flags the agent writes itself (concurrency, ai-eng, cache, domain, architect test), so the agent can mark its own homework as passing. Only realtime v2, search, eval, data (SQLite) and cache `test_idempotency.py` exercise observed behavior. Readiness claims built on the declaration checkers should be capped at IMPLEMENTED.
3. **Provenance is the weakest dimension (D8).** No skill keeps a consistent "last verified" date. Four skills (cache, realtime, architect, bootstrap) cite zero URLs. shadow-auth claims ASVS 5.0 but uses 4.0.3 chapter numbers, and calls OAuth 2.1 a standard. Router gaps also hurt D1 for auth, cache, data, db and integrate.
