# Evals — check that the skill works

`evals.json` holds realistic prompts and what a good answer must contain. Use them after installing or editing the skill.

## Manual check (5 minutes)

1. Open a **new** Codex chat and invoke `$shadow-monarch`, or use a Claude session with the skill enabled.
2. Paste a prompt from `evals.json`.
3. Check:
   - **Routing**: the tool activity shows `shadow-monarch` being used and the expected reference files being read
     (e.g. eval 2 → CORE, DEBUGGING, BACKEND, DEVOPS, lang-TYPESCRIPT-NODE; eval 7 → no reference files).
   - **Behavior**: tick off each item in `assertions`.
4. For a baseline, turn the skill off and repeat. The skill version should pass clearly more assertions.

| Eval | Tests |
|---|---|
| 1 review-payment-endpoint | severity scale, security + money + idempotency findings |
| 2 nestjs-500-in-docker | evidence-first debugging, container networking/env |
| 3 efcore-add-column-production | safe migrations with rolling deploys |
| 4 go-external-api-client | language idioms (context, timeouts, error wrapping) |
| 5 bahasa-laravel-upload | replies in Bahasa Indonesia, secure uploads, PII |
| 6 rag-fastapi-design | AI-LLM reference: permissions in retrieval, citations, evals |
| 7 simple-question-stays-short | does not over-answer |
| 8 push-back-on-overengineering | peer, not yes-man |
| 9 verified-nullable-contract | backend authority, nullability, no any or guessed fallbacks |
| 10 missing-contract-no-fabrication | source request rather than invented response fields |
| 11 shadow-monarch-token-efficiency-routing | Foreign Key budget, grep-before-slice, parallel tool batching, subagent delegation |
| 12 refactor-dead-code-strict-ts | zero `any`, zero `as Type` casting, boundary-only `unknown`, dead code elimination |
| 13 source-driven-docx-pipeline | never edit `.docx` directly; edit `.md` source and regenerate |
| 14 ai-gpu-vram-vllm-rag-infra | GPU VRAM math, `vLLM` prefix caching, Hybrid RRF + Cross-Encoder Reranker RAG |
| 15 agents-mcp-server-design | token-safe paginated MCP tools, idempotency, HITL gate for financial actions |
| 16 presales-kak-snap-bi-sizing | KAK server sizing formula + SNAP BI signature & transfer inquiry rules |
| 17 ui-ux-design-knowledge-base-id | UI/UX v2 foundations & art direction, thumb zone/touch targets, WCAG AA, handoff checklist |
| 18 review-followup-heuristic-false-positive | precision probes for Indonesian `-nya` follow-up regex false positives |
| 19 uu-pdp-privacy-compliance-audit | `/shadow-privacy`: UU No. 27 Tahun 2022 (Pasal 4, 20, 34, 46, 56, 57) & GDPR controls |
| 20 ai-rag-eval-owasp-llm-2025 | `/shadow-eval`: OWASP Top 10 for LLM 2025, NIST AI 600-1 & RAG Triad metrics |
| 21 mobile-masvs-store-release-gate | `/shadow-mobile`: OWASP MASVS v2.1.0, `PrivacyInfo.xcprivacy`, Play Integrity API & manifest hardening |
| 22 finops-focus-llm-token-cost | `/shadow-finops`: FinOps Framework, FOCUS, prefix prompt caching & thinking-token billing |
| 23 presales-kak-tco-perpres-46-2025 | `/shadow-presales`: 3-scenario workload capacity, 3-yr TCO/NPV, Perpres 46/2025 RAB vs PPK HPS & UMKK |
| 24 grc-cobit-iso27001-padk-ojk-2026 | `/shadow-grc`: COBIT capability vs maturity, ISO 27001 Clauses 4-10 + SoA, PADK OJK 1/2026 & no self-cert |
| 25 modernize-forensics-strangler-vs-rewrite | `/shadow-modernize`: Multi-dim risk vector, business-rule archaeology & Strangler vs Rewrite TCO |
| 26 pmo-contractual-cr-pert-monte-carlo | `/shadow-pmo`: Contractual precedence CR triage, PERT/CPM + Monte Carlo P80 & EVM |
| 27 ea-togaf-spbe-6-domain-portfolio | `/shadow-ea`: TOGAF 10 <-> SPBE 6-Domain crosswalk, Satu Data, TIME rationalization & ABB/SBB |
| 28 topic-based-auto-skill-routing-without-slash | Auto-loads topic-matched companion skills without `/shadow-*` slash commands & enforces sibling disambiguation |
| 29 debug-hypothesis-falsification-repro | `/shadow-debug`: hypothesis ranking, disconfirming evidence, redacted bisect timeline & red-before/green-after test |
| 30 concurrency-outbox-idempotency-dlq | `/shadow-concurrency`: commit->outbox->ack ordering, no false exactly-once external claims & poison DLQ recovery |
| 31 refactor-characterization-no-unsolicited-abstraction | `/shadow-refactor`: precedent discovery, invariant ledger, characterization golden I/O & untouched unrelated files |
| 32 domain-invariants-vs-crud-overengineering | `/shadow-domain`: state transition invariants, aggregate locks & rejecting heavy DDD on trivial CRUD |
| 33 search-hybrid-rrf-tenant-acl-prefilter | `/shadow-search`: pre-top-K tenant ACL filtering, Indonesian BM25+vector RRF, alias swap & retrieval-vs-generation split |
| 34 realtime-sse-resume-auth-revocation | `/shadow-realtime`: SSE `Last-Event-ID`/WS ADR, mid-session token revocation, slow-consumer bounds & multi-node fan-out |
| 35 supplychain-sbom-pinning-slsa-gate | `/shadow-supplychain`: SBOM vs lockfile 1:1 reconciliation, pinned 40-char SHAs/digests & offline unverified labeling |
| 36 user-intent-boundary-and-execution-approval-protocol | `shadow-monarch`: `L0`–`L4` execution approval gate, 7-part approval contract, testing boundaries & sub-agent inheritance |

## If something fails

- Skill not used at all → improve the `description` in `SKILL.md` or disable overlapping skills/plugins.
- Wrong files read → adjust the router tables in `SKILL.md`.
- Right files, wrong behavior → the rule is missing or unclear in that reference file; add the reason, not just the rule.

The `assertions` field also works with Anthropic's skill-creator eval tooling for automated with/without-skill comparisons.
