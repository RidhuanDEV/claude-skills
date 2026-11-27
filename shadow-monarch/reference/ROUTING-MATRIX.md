# Shadow Monarch Routing Matrix

> Moved verbatim from `shadow-monarch/SKILL.md` on 2026-11-27 to keep the always-loaded skill small. Load only the section the task needs.

### 1. Role & Domain Guides (with Companion Skill Auto-Load)

| Task / Role Domain | Reference | Auto-Load Companion Skill(s) |
|---|---|---|
| Core engineering mindset, code quality, abstraction discipline | `reference/CORE.md` | — (always active) |
| User Intent Boundary & Execution Approval Protocol (`L0`–`L4`, 7-part contract, sub-agent inheritance, `execution_approval_gate.py`) | `reference/EXECUTION-APPROVAL-PROTOCOL.md` | — (always active via orchestrator) |
| Official-First Project Initialization, Dependency Verification & SSO SDK Preservation (`official_first_verifier.py`) | `reference/OFFICIAL-FIRST-DEPENDENCY-POLICY.md` | `/shadow-bootstrap`, `/shadow-supplychain`, `/shadow-auth`, `/context7` |
| Codebase Intelligence & Convention Preservation: 10-facet discovery, convention profile, minimal change policy & drift prevention | `reference/CODEBASE-INTELLIGENCE.md` | `/shadow-quality` |
| Cross-Model Frontier Parity: unified instruction sync, pre-code checkpoints, deterministic `shadow_gate.py`, cross-model review & model routing | `reference/CROSS-MODEL-PARITY.md` | `/shadow-quality`, `/handoff` |
| Research & Standards Source Routing Policy (ISO/IEEE, NIST, OWASP, Context7, IEEE Xplore, ACM, Springer, ScienceDirect, Semantic Scholar/OpenAlex, arXiv preprint rules) | `reference/RESEARCH-SOURCE-POLICY.md` | `/shadow-doc`, `/context7` |
| Enterprise IT Consulting Core: Context-Aware Methodology, Evidence Provenance, Versioned Regulation Registry, Quantitative Decision & Cross-Skill Traceability | `reference/CONSULTING-INTELLIGENCE-CORE.md` | `/shadow-presales`, `/shadow-grc`, `/shadow-modernize`, `/shadow-pmo`, `/shadow-ea` |
| Shadow Monarch Token, Context & Subagent Execution Efficiency ("Mana Conservation") | `reference/TOKEN-EFFICIENCY.md` | `/handoff` (when context fills) |
| Backend Engineer: APIs, services, jobs, webhooks, realtime, async queues, structured field validation errors | [Backend guide](reference/BACKEND.md) | `/shadow-api`, `/shadow-auth`, `/shadow-concurrency`, `/shadow-realtime`, `/shadow-integrate`, `/shadow-cache` |
| Database Engineer / DBA: schemas, queries, ORM, migrations, transactions | `reference/DATABASE.md` | `/shadow-db` (introspect/ERD/DW), `/shadow-data` (migrations/backfills) |
| Frontend Engineer: UI logic, state, rendering, client data fetching, interactive states (`cursor: pointer`/hover/focus), theme-bound components, scrollbar styling, visible input limits and field-level errors | [Frontend guide](reference/FRONTEND.md) | `antislop`, `antislop-ui`, `antislop-layoutmobile`, `antislop-human`, `/modern-web-guidance`, `/shadow-cache`, `/shadow-browser` |
| UI/UX & Product Designer: design systems, layout, forms, accessibility | `reference/DESIGN.md` | `/shadow-design`, `/shadow-accessibility`, `antislop-human` |
| UI/UX, Visual Art Direction & Product Interface Knowledge Base v2 (ID): 43 bab panduan desain antarmuka, art direction, visual choreography, pola mobile/web, design system, audit rubrics & AI prompts | `reference/UI_UX_Design_Knowledge_Base_v2_Art_Direction_Web_Mobile_ID.md` | `/shadow-design`, `antislop-ui` |
| Brand illustrations, mascot variants, status artwork and SVG/Lottie handoff | [Mobile design workflow](reference/MOBILE-DESIGN.md) | `/shadow-illustration` |
| Narrated tutorial videos, GUI E2E click-throughs from scene files, tutorial updates after UI changes | [Frontend guide](reference/FRONTEND.md), `reference/sub-QA-AUTOMATION.md` | `/shadow-video`, `/shadow-browser` |
| Mobile UI, Vector Illustration & Lottie Motion Designer: SVG character/menu art, rigging, runtime state | `reference/MOBILE-DESIGN.md` | `/shadow-design`, `/shadow-mobile` |
| Mobile Architect: offline-first sync, lifecycle, deep links, mobile security | `reference/MOBILE.md` | `/shadow-mobile` |
| Refactoring Specialist: behavior-preserving extraction, characterization & cleanup | `reference/REFACTORING.md` | `/shadow-refactor`, `/shadow-quality`, `/shadow-modernize` (M&A/TCO) |
| Security Engineer / AppSec: auth, sessions, uploads, secrets, supply chain | `reference/SECURITY.md` | `/shadow-sec`, `/shadow-supplychain`, `/shadow-auth`, `/shadow-privacy` |
| Pentester, VAPT Auditor & DevSecOps: CVSS/VAPT reports, OWASP API/Mobile, WAF, Trivy/Semgrep, DFIR | `reference/SECOPS-PENTEST.md` | `/shadow-sec`, `/shadow-supplychain` |
| DevOps Engineer: Docker, Nginx, CI/CD, environment, Git diagnostics | `reference/DEVOPS.md` | `/shadow-ops`, `/shadow-git`, `/shadow-release`, `/shadow-bootstrap` |
| Cloud Architect, SRE & SysAdmin: Terraform/IaC, K8s/Helm, Linux/systemd, SLI/SLO, FinOps | `reference/CLOUD-SRE.md` | `/shadow-ops`, `/shadow-observe`, `/shadow-finops`, `/shadow-resilience` |
| Enterprise Integration & IAM Specialist: Kafka/RabbitMQ, Keycloak/OIDC/SAML, ERP/Payment Ledger | `reference/ENTERPRISE-INTEGRATION.md` | `/shadow-integrate`, `/shadow-concurrency`, `/shadow-auth` |
| QA Engineer: test strategy, regression coverage, flaky tests | `reference/TESTING.md` | `/shadow-test`, `/shadow-uat`, `/shadow-browser`, `/shadow-compat` |
| Incident Responder / Debugger: hypothesis falsification, bisect, races, heap/500 bugs | `reference/DEBUGGING.md` | `/shadow-debug`, `/shadow-maintain`, `/shadow-observe` |
| Principal / Solutions Architect: system design, domain boundaries, ADRs | `reference/ARCHITECTURE.md` | `/shadow-architect`, `/shadow-domain`, `/shadow-ea` (multi-app / SPBE) |
| Solutions Consultant & Pre-Sales: TOR/KAK, Technical Proposals, Server Sizing formulas, BoQ/RAB IT | `reference/PRESALES-PROPOSAL-KAK.md` | `/shadow-presales` |
| Code Reviewer / Auditor: code review, readiness assessments | `reference/CODE-REVIEW.md` | `/shadow-quality`, `/shadow-sec` |
| AI / LLM Engineer: structured outputs, tool-calling agents, streaming UX, prompts, RAG & LLM reliability | `reference/AI-LLM.md` | `/shadow-ai-eng` (build), `/shadow-search` (retrieval), `/shadow-eval` (faithfulness/safety), `/shadow-finops` |
| AI Agent & MCP Engineer: multi-agent orchestration, subagents, MCP servers/tools, guardrails | `reference/AGENTS-MCP.md` | `/shadow-ai-eng`, `/shadow-eval` |
| Product Manager (PM), System Analyst (SA) & BA: PRD/SRS/FSD, domain invariants, stories | `reference/PRODUCT-ANALYSIS.md` | `/shadow-discovery`, `/shadow-domain`, `/shadow-plan` |
| IT Project Manager (PMO), Scrum Master & GRC/Compliance: WBS, RAID, RFC/CR, SLA, UU PDP/ISO 27001 | `reference/IT-PMO-GOVERNANCE.md` | `/shadow-pmo`, `/shadow-grc`, `/shadow-privacy`, `/shadow-handover` |
| Technical Writer & Doc Engineer: source-driven `.md` → `.docx`/`.pdf` pipelines, SOP/Runbooks | `reference/DOCS-PIPELINE.md` | `/shadow-doc`, `antislop-copywriting` |
| Data Engineer & Automation: scripting, ETL, batch processing, CSV/Excel/JSON pipelines | `reference/DATA-AUTOMATION.md` | `/shadow-db`, `/shadow-data` |
| Data Analyst, BI, Analytics Engineer (`dbt`) & Classical ML: Star Schema, SQL KPIs, ML pipelines | `reference/DATA-ANALYTICS-ML.md` | `/shadow-db` |

### 1b. Sibling Skill Disambiguation Boundaries

| Pair | Load Skill A When... | Load Skill B When... |
|---|---|---|
| `/handoff` vs `/shadow-handover` | Saving/loading/merging **AI coding session memory** | Delivering **client BAST, Admin/User Manuals, credential transfer & ToT** |
| `/shadow-architect` vs `/shadow-ea` | Designing **one application** (C4, ADRs, Modular Monolith) | Mapping **multi-system portfolios, TOGAF 10, TIME or 6-Domain SPBE** |
| `/shadow-plan` vs `/shadow-pmo` | Breaking approved specs into **Sprints, Stories, Tasks** | Evaluating **contractual CRs, PERT+CPM+Monte Carlo P80, or EVM** |
| `/shadow-sec` vs `/shadow-privacy` vs `/shadow-grc` | **AppSec / STRIDE / OWASP ASVS / SAST** | **UU PDP / GDPR PII & consent** (`/shadow-privacy`); **COBIT / ISO 27001 SoA / SPBE / OJK GRC** (`/shadow-grc`) |
| `/shadow-data` vs `/shadow-db` | Writing **Expand-Contract app migrations, seeds, ACID tx** | **Live DB inspection, DBML/ERD, Star Schema DW, Pentaho** |
| `/shadow-test` vs `/shadow-eval` vs `/shadow-perf` | **Unit/integration/contract/property/mutation tests** (`/shadow-test`) | **RAG/LLM evals & red-teaming** (`/shadow-eval`); **Pre-UAT `k6`/`EXPLAIN` ONLY** (`/shadow-perf`) |
| `/shadow-browser` vs `/shadow-mobile` | **Web browser Playwright E2E & 375px overflow** | **iOS/Android/Flutter/RN MASVS, `PrivacyInfo.xcprivacy` & Store Gates** |
| `/shadow-debug` vs `/shadow-maintain` vs `/shadow-observe` | **Causal bug hypothesis falsification, bisect & repro proof** | **SLA/Harwat triage & RCA process** (`/shadow-maintain`); **SLI/SLO & OTel setup** (`/shadow-observe`) |
| `/shadow-refactor` vs `/shadow-modernize` vs `/shadow-quality` | **Characterization tests & behavior-preserving extraction** | **M&A due diligence & Strangler vs Rewrite TCO** (`/shadow-modernize`); **Static lint/gates** (`/shadow-quality`) |
| `/shadow-concurrency` vs `/shadow-integrate` vs `/shadow-realtime` | **Queues, outbox/inbox idempotency, CAS/locks & DLQ** | **HTTP/HMAC/payment adapters** (`/shadow-integrate`); **WebSocket/SSE resume & backpressure** (`/shadow-realtime`) |
| `/shadow-domain` vs `/shadow-discovery` | **Bounded contexts, aggregates & state invariants** | **Stakeholder PRD/SRS/BRD & Given/When/Then elicitation** (skip heavy DDD for simple CRUD) |
| `/shadow-search` vs `/shadow-eval` | **BM25/Indonesian analyzer, vector ANN, RRF & tenant ACL** | **LLM answer faithfulness, citation grounding & OWASP LLM safety** |
| `/shadow-supplychain` vs `/shadow-sec` vs `/shadow-release` | **CycloneDX/SPDX SBOM vs lockfile, typosquatting & SLSA** | **STRIDE/ASVS/SAST** (`/shadow-sec`); **SemVer changelog, migrations & deploy** (`/shadow-release`) |
| `/shadow-analytics` vs `/shadow-observe` | **Product event taxonomy, PostHog/GA4, PII-free telemetry & A/B SRM** | **Infra SLI/SLO, OTel traces, PromQL & structured app logs** (`/shadow-observe`) |
| `/shadow-email` vs `/shadow-integrate` | **Transactional HTML email (React Email/MJML), SPF/DKIM/DMARC, RFC 8058 & Mailpit** | **Payment gateways, HMAC webhooks, circuit breakers & external REST** (`/shadow-integrate`) |
| `/shadow-seo` vs `/shadow-illustration` | **JSON-LD Schema.org, sitemaps, `robots.txt`, `hreflang`, SSR crawlability & `llms.txt`** | **OG card image generation (Satori/Sharp), SVG mascots, Canvas/WebGL** (`/shadow-illustration`) |

### 2. Language & Backend/Core Framework Authoring Rules (`lang-*.md`)

| Stack | Reference |
|---|---|
| TypeScript, JavaScript, Node.js, NestJS, Express, React, Next.js | `reference/lang-TYPESCRIPT-NODE.md` |
| Go | `reference/lang-GO.md` |
| C#, .NET, ASP.NET Core, EF Core | `reference/lang-DOTNET.md` |
| Python, FastAPI, Django, Flask | `reference/lang-PYTHON.md` |
| Java, Kotlin, Spring Boot | `reference/lang-JAVA-KOTLIN.md` |
| PHP, Laravel | `reference/lang-PHP-LARAVEL.md` |
| Rust, tokio, axum | `reference/lang-RUST.md` |
| Dart, Flutter | `reference/lang-DART-FLUTTER.md` |
| C, Modern C++ (C++20/23), CMake, Embedded Firmware (ESP32/STM32/FreeRTOS), WebAssembly | `reference/lang-CPP-SYSTEMS.md` |

### 3. Sub-Task, Tooling & Specialized Stack Authoring Rules (`sub-*.md`)

| Sub-Task / Specialized Stack | Reference |
|---|---|
| Advanced RAG, Hybrid Search (RRF), Reranking, Vector DBs (`pgvector`/Qdrant/Milvus) & GraphRAG | `reference/sub-RAG-VECTOR-KNOWLEDGE.md` |
| AI/GPU Infrastructure, VRAM Sizing, `vLLM`/`SGLang`/`TGI`/`Ollama` Serving, K8s GPU & LLM Gateways (`LiteLLM`) | `reference/sub-AI-INFRA-SERVING.md` |
| LLM Fine-Tuning (`LoRA`/`QLoRA`/`DPO`/Unsloth), Dataset Curation, Guardrails & LLMOps (`Langfuse`/Phoenix) | `reference/sub-LLM-FINETUNING-LLMOps.md` |
| Vue 3/Nuxt 3, Angular Signals, Tailwind/Shadcn UI, React Native/Expo, Jetpack Compose, SwiftUI | `reference/sub-FRONTEND-MOBILE-STACKS.md` |
| PostgreSQL (JSONB/GIN/RLS/Partition/`pgvector`), Redis, Elasticsearch/OpenSearch, MongoDB | `reference/sub-DATA-STORES.md` |
| Playwright, Cypress, `k6`/`Locust` Load Tests, Bruno `.bru` API Tests, Test Case Matrix & UAT | `reference/sub-QA-AUTOMATION.md` |
| OpenAPI 3.1 YAML, DBML, Strict Mermaid Diagrams, `python-docx` & Node `docx` Generator Code | `reference/sub-SPECS-DOCX-CODE.md` |
| PowerShell (`.ps1`), Bash/POSIX Shell (`.sh`), `Makefile`, `Taskfile.yml`, `Justfile` | `reference/sub-SHELL-CLI-AUTOMATION.md` |
| OpenTelemetry (OTel), Prometheus (`PromQL`), Loki (`LogQL`), Grafana, `EXPLAIN ANALYZE` & Profiling | `reference/sub-OBSERVABILITY-PROFILING.md` |
| WebSockets, SSE, WebRTC, IoT (`MQTT`), Desktop (`Tauri`/`Electron`), Chrome Extensions (MV3) | `reference/sub-REALTIME-IOT-DESKTOP.md` |
| Indonesian Fintech & Gov (SNAP BI, QRIS/VA, TTE BSrE/e-Meterai, SatuSehat FHIR/BPJS, Tax PPN/PPh, Stock Lock) | `reference/sub-FINTECH-ID-ECOSYSTEM.md` |
| GIS & Geospatial (PostGIS SRID 4326, `GIST`, `ST_DWithin`, GeoJSON `[lng,lat]`, MapLibre/Leaflet, Vector Tiles, H3) | `reference/sub-GIS-GEOSPATIAL.md` |
| Computer Vision, Document OCR (e-KTP/Invoice), Biometrics/Liveness, Whisper Audio & Safe `ffmpeg` | `reference/sub-VISION-OCR-MEDIA.md` |

### 4. Full-Stack SDLC Orchestration & 59-Skill Shadow Army Matrix

`shadow-monarch` orchestrates 8 quality-gated SDLC stages plus Enterprise IT Consulting across all **59 skills** (returning work to the appropriate stage whenever a gate fails rather than forcing deployment). Use the table below and `skill_router.py --route` to pick the exact `1–4` skills + `recommended_playbooks`:

| Group | Slash Skill | Priority | Core Responsibility & Deliverable |
|---|---|---|---|
| **A. Discovery & Architecture** | `/shadow-discovery` | P0 | Requirement elicitation, FR/NFR, scope boundaries, Given/When/Then criteria & gap analysis |
| | `/shadow-architect` | P0 | System Design, C4 diagrams, ADRs, Modular Monolith vs Microservices & consistency models |
| | `/shadow-domain` | P1 | Bounded contexts, aggregate invariants, state transitions & anti-overengineering on CRUD |
| | `/shadow-plan` | P0 | Epic -> User Story -> Task breakdown, acyclic DAG (`sprint_dag_verifier.py`), DoR/DoD & `[APPROVAL-REQUIRED]` tagging |
| | `/shadow-bootstrap` | P0 | Zero-to-runnable project scaffold (strict TS/lint, env validation, DB/ORM, Docker dev, CI, seed) |
| | `/shadow-design` | P1 | Design system tokens, user flows, wireframe specs, 9-state component contracts & Human-AI UX |
| **B. App & Data Lifecycle** | `/shadow-auth` | P0 | AuthN/AuthZ, RBAC/ABAC, OAuth2/OIDC, SSO, refresh rotation, confused deputy & tenant isolation |
| | `/shadow-data` | P0 | Zero-downtime Expand-Contract migrations, isolation levels, outbox CDC & ACID integrity |
| | `/shadow-db` | P0 | Multi-DB introspect, DBML/ERD, Star Schema DW, planner `EXPLAIN`, MVCC & Pentaho (`shadow_db` MCP) |
| | `/shadow-api` | P0 | OpenAPI 3.1, RFC 9457 errors, idempotency, keyset pagination & live HTTP tests (`shadow_api` MCP) |
| | `/shadow-cache` | P1 | `TanStack Query`, Redis caching, coherency boundaries, jitter & tenant-scoped keys |
| | `/shadow-concurrency` | P0 | Async state machines, outbox/inbox idempotency, CAS/`SKIP LOCKED`, retries & poison DLQ |
| | `/shadow-realtime` | P1 | WebSocket/SSE `Last-Event-ID` resume, mid-session auth revocation & slow-consumer backpressure |
| | `/shadow-search` | P1 | Lexical BM25/Indonesian analyzer, vector ANN, hybrid RRF, `NDCG@K`, alias swap & ACL prefilter |
| | `/shadow-ai-eng` | P0 | Production AI/LLM/Agent systems: structured outputs, safe tool calling, streaming SSE UX, multi-provider gateways & MCP servers |
| | `/shadow-seo` | P1 | Technical SEO, XSS-safe JSON-LD Schema.org, dynamic sitemaps, `robots.txt`, `hreflang`, SSR crawlability & `llms.txt` |
| | `/shadow-email` | P1 | Transactional HTML email (React Email/MJML), SPF/DKIM/DMARC alignment, RFC 8058 one-click unsubscribe, suppression & Mailpit |
| | `/shadow-analytics` | P1 | Typed event taxonomy (PostHog/GA4/Mixpanel), UU PDP PII scrubbing, server-side conversion tracking & A/B SRM checks |
| | `/shadow-integrate` | P1 | Payment gateways, HMAC replay window, SMTP, reconciliation jobs & outbox handoff |
| | `/shadow-accessibility` | P2 | Deep WCAG 2.2 AA/AAA audit, keyboard focus traps, ARIA live regions & screen reader QA |
| | `/modern-web-guidance` | P0 | Baseline web platform APIs (`<dialog>`, Popover, `@container`, `:has()`, CWV) + React/Next.js waterfall/bundle/RSC perf |
| | `/shadow-illustration` | P2 | SVG/mascots, Canvas 2D/WebGL/GLSL procedural graphics, Sharp/Satori OG & icon pipelines, diagrams, CMYK print & Lottie/Rive |
| | `/shadow-video` | P2 | 4-mode video production: Playwright narrated tutorials, Remotion/Canvas motion clips, mobile demos, PR GIF/MP4 & LUFS audio |
| **C. Quality, UAT & Release** | `/shadow-quality` | P0 | Static analysis, architectural fitness rules, dead code cleanup, change-risk & drift gates |
| | `/shadow-debug` | P0 | Hypothesis falsification (>=2 hypotheses), `git bisect`, redacted timelines & red-before/green-after repro |
| | `/shadow-refactor` | P0 | Precedent discovery, Invariant Ledger, characterization tests & behavior-preserving extraction |
| | `/shadow-test` | P0 | Polyglot unit, integration, property-based, mutation, state-machine & contract tests (8+ languages) |
| | `/shadow-eval` | P0 | Retrieval-vs-LLM eval split, dataset versioning, judge calibration & OWASP LLM 2026 / Agentic Top 10 red-teaming |
| | `/shadow-sec` | P0 | STRIDE threat modeling, reachability triage, multi-hop authz & NIST SSDF / OWASP ASVS 5.0 |
| | `/shadow-supplychain` | P1 | CycloneDX/SPDX SBOM vs lockfile 1:1 check, typosquatting, pinned digests & SLSA provenance |
| | `/shadow-privacy` | P0 | UU PDP (UU No. 27/2022) & GDPR audit: personal data inventory, consent, DSAR, DPIA, cross-border & 3x24h breach readiness |
| | `/shadow-perf` | P0 | **Pre-UAT Gate ONLY**: Profile-first, variance-aware benchmarks, OpenAPI-to-`k6` & SQL `EXPLAIN ANALYZE` |
| | `/shadow-uat` | P0 | Requirement Traceability Matrix (RTM), Staging UAT scenarios, defect triage, evidence & sign-off |
| | `/shadow-release` | P0 | SemVer changelog, migration-before-code order, SBOM provenance gate & verified rollback |
| | `/shadow-compat` | P1 | Schema evolution compatibility matrix, semantic API diff, consumer contracts & sunset policy |
| | `/shadow-browser` | P0 | Real Chromium E2E UI verification & 375px mobile viewport overflow checks (`playwright` MCP) |
| | `/shadow-mobile` | P1 | OWASP MASVS v2.1.0 mobile hardening, iOS `PrivacyInfo.xcprivacy`, Android Play Integrity, signing & store gates |
| **D. Ops & Maintenance** | `/shadow-ops` | P0 | Immutable Docker/K8s, Nginx/Caddy, Linux `systemd`/PM2, CI/CD & backups (local OWASP/H5BP KB) |
| | `/shadow-observe` | P1 | SLI/SLO error budgets, multi-window burn alerts, OpenTelemetry trace/log correlation & triage |
| | `/shadow-finops` | P1 | FinOps Framework & FOCUS cost governance, K8s right-sizing, LLM prompt caching & thinking-token budgets |
| | `/shadow-resilience` | P1 | Automated DB backup restore drills (RPO/RTO proof), graceful degradation & fault isolation |
| | `/shadow-maintain` | P1 | Post-production Harwat/OMKT, SLA bug triage, hotfix + regression test workflow & blameless RCA |
| **E. Delivery & Collaboration** | `/shadow-handover` | P0 | Client BAST, source/SBOM inventory, secure credential transfer, Admin/User Manuals & ToT |
| | `/shadow-doc` | P0 | Generator-Agnostic Document Orchestrator (`doc_orchestrator.py`: repo-local first -> adapter -> Global AST v2.0/v2.1 engine fallback, 20 standardized SDLC templates / 26 type aliases, HTML/DOCX/PDF/XLSX/MD/ZIP + `build-manifest.json`) |
| | `/shadow-git` | P0 | Branching strategy detection, Git worktrees, parallel multi-agent isolation, independent feature integration, forward sync from `main`, `git merge-tree` conflict/semantic risk prediction & 6-point safe cleanup |
| | `/handoff` | P0 | Cross-agent AI session context compaction & resumption (`shadow_handoff` MCP) |
| | `/context7` | P0 | Real-time official library/framework documentation lookup (`context7` MCP) |
| | `/antislop` (+5 sub) | P0 | Always-on (`during` mode) UI, mobile layout, human accessibility, copywriting & code comment filter |
| **F. Enterprise IT Consulting** | `/shadow-presales` | P0 | Tender intelligence, 3-scenario workload capacity engineering, 3–5 yr TCO/NPV, Perpres 46/2025 RAB vs PPK HPS |
| | `/shadow-grc` | P0 | Risk-based audit lifecycle, COBIT 2019 (Capability vs Maturity), ISO 27001:2022 (Clauses 4–10 + 93 SoA), SPBE, POJK 11/2022 + PADK OJK 1/2026 |
| | `/shadow-pmo` | P0 | Contractual hierarchy CR triage, PERT + CPM + Monte Carlo (`P50/P80/P90`), EVM & BAST governance |
| | `/shadow-modernize` | P1 | 8-area technical due diligence, business-rule archaeology, multi-dimensional risk vector & Strangler vs Rewrite TCO |
| | `/shadow-ea` | P1 | TOGAF 10 ADM, explicit 6-Domain SPBE crosswalk (`Perpres 132/2022`), TIME portfolio rationalization & ABB/SBB |

For other stacks use `reference/CORE.md` plus applicable domain references and verified ecosystem documentation.
Framework-specific examples do not transfer unchanged to another framework. Resolve conflicting
reference guidance through the verified implementation, installed version, and task requirements.
Use specialized artifact, product-documentation, or platform skills when their actual workflow applies.

