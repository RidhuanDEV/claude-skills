#!/usr/bin/env python3
"""
Shadow Monarch Topic-Based Skill Router, Decision Record Emitter & Description Auditor (skill_router.py)

Supports:
1. `--audit-descriptions`: verifies every skill in the repo has a valid `Use when...`
   natural-language trigger clause and stays within <= 500 chars.
2. `--route "<prompt>"`: deterministically maps natural-language EN/ID tasks to a
   structured §2.2 Router Decision Record (`primary_skill`, `supporting_skills`,
   `risk_review_skills`, `excluded_skills`, `required_permissions`, `prohibited_actions`)
   plus backward-compatible keys (`companion_skills`, `always_on_ui_skills`, `reference_modules`),
   enforcing 3-layer progressive loading and sibling disambiguation.
3. `--self-test`: executes audit + 52-skill precision/recall & §5.1/§5.3 negative-trigger probes.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SKIP_ROOT_DIRS = {"evals", "mcp-servers", "reports", "docs", "scripts", "node_modules"}

USE_WHEN_RE = re.compile(r"\buse\s+(?:only\s+)?when\b", re.IGNORECASE)
CODE_REVIEW_RE = re.compile(
    r"\b(?:(?:only\s+review|hanya\s+(?:review|tinjau))\s+(?:(?:this|the)\s+)?(?:API|endpoint|webhook|handler|kode|code|diff|PR)\b|"
    r"code\s+review|PR\s+review|review\s+(?:(?:this|the)\s+)?(?:PR|code|diff|changes|kode|webhook(?:\s+handler)?|endpoint(?:\s+handler)?)|(?:audit|tinjau)\s+kode)\b",
    re.IGNORECASE,
)
READ_ONLY_SCOPE_RE = re.compile(
    r"\b(?:secara\s+read[- ]only|read[- ]only\s*\(\s*jangan\s+ubah\s+file|"
    r"only\s+(?:inspect|review)\b[^\n]*\bread[- ]only)\b",
    re.IGNORECASE,
)
LOAD_TEST_DENIAL_RE = re.compile(
    r"\b(?:tidak\s+menyetujui|do\s+not\s+approve|(?:jangan|do\s+not)\s+(?:jalankan|run))\s+"
    r"(?:k6|(?:a\s+)?(?:load|stress|soak)\s+test)\b",
    re.IGNORECASE,
)
QUOTED_LOG_RE = re.compile(
    r"```[\s\S]*?```|"
    r"(?:\b(?:log|error|stderr|stdout|paste|output|stack\s*trace|traceback)\s*[:=]\s*)(?:\"[^\"]*\"|'[^']*')|"
    r"\"[^\"]*(?:failed|timeout|exception|traceback|stack\s*trace|/shadow-[a-z-]+)[^\"]*\"|"
    r"'[^']*(?:failed|timeout|exception|traceback|stack\s*trace|/shadow-[a-z-]+)[^']*'",
    re.IGNORECASE,
)
NEGATED_CLAUSE_RE = re.compile(
    r"\b(?:jangan|tidak\s+perlu|tanpa|do\s+not|don't|without|skip|no)\s+"
    r"(?:jalankan\s+|run\s+|lakukan\s+|do\s+)?(?:load\s*test(?:ing)?|stress\s*test(?:ing)?|soak\s*test(?:ing)?|"
    r"k6|playwright|e2e|benchmark|mutat\w*|edit\w*|write\w*)\b",
    re.IGNORECASE,
)
API_DOCS_GENERIC_RE = re.compile(
    r"\b(?:buat(?:kan)?|create|add|tambahkan|document|dokumentasi(?:kan)?|update|sync)\s+"
    r"(?:the\s+)?(?:API\s+doc(?:s|umentation)?|dokumentasi\s+API)\b",
    re.IGNORECASE,
)
API_DOCS_EXPLICIT_FORMAT_RE = re.compile(
    r"\b(?:openapi|swagger|postman|bruno|scalar|redoc|insomnia|asyncapi|graphql\s+sdl|protobuf)\b",
    re.IGNORECASE,
)

# Ordered by domain specificity so primary ownership resolves cleanly before general helpers.
ROUTING_RULES: list[dict[str, Any]] = [
    {
        "skill": "handoff",
        "layer": "task",
        "references": ["TOKEN-EFFICIENCY.md"],
        "include": re.compile(
            r"\b(?:lanjut\s+handoff|load\s+handoff|merge\s+handoff|session\s+handoff|context\s+(?:full|penuh|compaction)|simpan\s+sesi)\b",
            re.IGNORECASE,
        ),
        "exclude": re.compile(
            r"\b(?:BAST|serah\s+terima\s+klien|admin\s+manual|operator\s+manual|training\s+of\s+trainers)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-handover",
        "layer": "risk",
        "references": ["DOCS-PIPELINE.md", "IT-PMO-GOVERNANCE.md"],
        "include": re.compile(
            r"\b(?:BAST|berita\s+acara\s+serah\s+terima|serah\s+terima\s+(?:klien|proyek)|admin\s+manual|operator\s+manual|training\s+of\s+trainers|ToT|"
            r"credential\s+transfer\s+manifest|operator\s+handover|access\s+cutover|client\s+handover)\b",
            re.IGNORECASE,
        ),
        "exclude": re.compile(r"\b(?:lanjut\s+handoff|load\s+handoff|session\s+handoff)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-presales",
        "layer": "task",
        "references": ["PRESALES-PROPOSAL-KAK.md", "CONSULTING-INTELLIGENCE-CORE.md"],
        "include": re.compile(
            r"\b(?:KAK|TOR|RFP|tender|aanwijzing|bid/no-bid|RAB|BoQ|HPS|TKDN|BMP|PDN|UMKK|Perpres\s*46|"
            r"server\s*sizing|capacity\s*sizing|workload\s+sizing|3[- ]scenario\s+(?:sizing|capacity)|3[- ]year\s*TCO|NPV|price[- ]estimation\s+for\s+tender)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-grc",
        "layer": "risk",
        "references": ["IT-PMO-GOVERNANCE.md", "CONSULTING-INTELLIGENCE-CORE.md"],
        "include": re.compile(
            r"\b(?:COBIT|ISO\s*(?:/IEC\s*)?27001|Statement\s+of\s+Applicability|SoA|Annex\s+A|Indeks\s+KAMI|BSSN|"
            r"POJK\s*11|PADK\s*OJK|SEOJK\s*21/2017|PPJTI|Design\s+Effectiveness|Operating\s+Effectiveness|"
            r"audit\s+(?:TI|IT|workpaper)|governance\s+assurance)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-modernize",
        "layer": "task",
        "references": ["REFACTORING.md", "CONSULTING-INTELLIGENCE-CORE.md"],
        "include": re.compile(
            r"\b(?:technical\s+due\s+diligence|strangler\s+fig|business[- ]rule\s+archaeology|refactor\s+vs\s+rewrite|"
            r"coexistence\s+cost|EOL\s+runtime|legacy\s+modernization|dual[- ]run\s+TCO|full\s+rewrite\s+vs|monolith\s+modernization)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-pmo",
        "layer": "task",
        "references": ["IT-PMO-GOVERNANCE.md", "CONSULTING-INTELLIGENCE-CORE.md"],
        "include": re.compile(
            r"\b(?:contract\s+change\s+request|change\s+request|paid\s+CR|scope\s+creep|Change\s+Control\s+Board|PERT|critical\s+path|CPM|"
            r"monte\s+carlo|merge\s+bias|contractual\s+precedence|P80|earned\s+value|EVM|CPI|SPI|EAC\s+forecast|RAID\s+log|laporan\s+(?:pendahuluan|antara|akhir))\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-ea",
        "layer": "risk",
        "references": ["ARCHITECTURE.md", "CONSULTING-INTELLIGENCE-CORE.md"],
        "include": re.compile(
            r"\b(?:TOGAF|enterprise\s+architecture|arsitektur\s+SPBE|6\s+domain\s+SPBE|SPBE\s+6[- ]domain|"
            r"Perpres\s*95/2018|Perpres\s*132|Perpres\s*39/2019|Satu\s+Data|TIME\s+(?:matrix|portfolio)|application\s+rationalization|ABB|SBB|capability\s+heatmap)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-debug",
        "layer": "task",
        "references": ["DEBUGGING.md", "CODEBASE-INTELLIGENCE.md"],
        "include": re.compile(
            r"\b(?:returns?\s+500|HTTP\s*500|500\s+errors?|random\s+500|\b500\b\s+(?:di|in|on)\s+\w+|"
            r"diagnos(?:e|ing)\s+[^\n]{0,40}\b(?:bug|error|500|failure|crash)|intermittent\s+(?:500|bug|failure|error)|"
            r"database\s+deadlock|deadlock|root[- ]cause|stack\s+trace|memory\s+leak|heap\s+leak|heap\s+snapshot|"
            r"flamegraph|pprof|clinic\.js|CPU\s+profiling|goroutine\s+leak|OOMKilled|flaky\s+test|"
            r"git\s+bisect|repro\s+bug|race\s+(?:condition|symptom)|production\s+bug|"
            r"(?:ada|fix|perbaiki)\s+bug\b|sering\s+timeout|tidak\s+(?:mengirim|berfungsi|bekerja)\s+\w+)\b",
            re.IGNORECASE,
        ),
        "exclude": re.compile(r"\b(?:typo[- ]only|only\s+typo|README\s+typo|pure\s+formatting)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-concurrency",
        "layer": "task",
        "references": ["BACKEND.md", "ENTERPRISE-INTEGRATION.md"],
        "include": re.compile(
            r"\b(?:duplicat(?:ed?|es)\s+(?:notification|email|webhook|charge)|emails?\s+duplicated|after\s+retries?|"
            r"worker\s+retry|outbox|inbox\s+dedup|poison\s+DLQ|dead[- ]letter|crash[- ]before[- ]ack|optimistic\s+lock|"
            r"CAS\s+version|queue\s+semantics|Redis\s+vs\s+queue|saga\s+(?:orchestrat|choreograph|compensat)|"
            r"fencing\s+token|distributed\s+lock|Redlock|BullMQ|RabbitMQ|Kafka|NATS\s+JetStream|Temporal\s+workflow|"
            r"token\s+bucket|rate\s+limit(?:ing|er)\s+algorithm)\b",
            re.IGNORECASE,
        ),
        "exclude": re.compile(r"\b(?:SMTP\s+250|Postmaster\s+Tools|email\s+header\s+injection)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-refactor",
        "layer": "task",
        "references": ["REFACTORING.md", "CODEBASE-INTELLIGENCE.md"],
        "include": re.compile(
            r"\b(?:refactor\s+(?:old|legacy|module|feature|service|controller|handler|component|helper|function|kode|code|class|[a-z0-9_-]+\s+(?:service|module|handler|controller|component))|"
            r"refactoring\s+(?:legacy|module|service)|behavior\s+unchanged|characterization\s+test|Golden\s+Master\s+test|seam\s+extraction|"
            r"branch[- ]by[- ]abstraction|semantic\s+equivalence|incremental\s+refactor|behavior[- ]preserving|extract\s+seam|safe\s+refactor)\b",
            re.IGNORECASE,
        ),
        "exclude": re.compile(
            r"\b(?:contract\s+change\s+request|paid\s+CR|pure\s+formatting\s+refactor|formatting[- ]only|prettier\s+only)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-domain",
        "layer": "task",
        "references": ["ARCHITECTURE.md", "PRODUCT-ANALYSIS.md"],
        "include": re.compile(
            r"\b(?:bounded\s+contexts?|aggregate\s+(?:roots?|invariants?)|domain\s+events?|anti[- ]corruption\s+layers?|ubiquitous\s+language|"
            r"finite\s+state\s+machine|state\s+machine\s+(?:transition|table|workflow)|maker[- ]checker|four[- ]eyes\s+approval|"
            r"complex\s+(?:approvals?|cancellations?|state\s+machines?)(?:\s+and\s+cancellations?)?|state\s+transition\s+invariants?|"
            r"business\s+invariants?|value\s+objects?|invarian\s+(?:domain|state)|DDD)\b",
            re.IGNORECASE,
        ),
        "exclude": re.compile(
            r"\b(?:pure\s+formatting\s+refactor|formatting[- ]only|trivial\s+CRUD|simple\s+CRUD)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-search",
        "layer": "task",
        "references": ["sub-RAG-VECTOR-KNOWLEDGE.md", "DATA-ANALYTICS-ML.md"],
        "include": re.compile(
            r"\b(?:search\s+relevance|relevansi\s+pencarian|BM25|lexical\s+search|vector\s+ANN|hybrid\s+(?:RRF|search)|reciprocal\s+rank\s+fusion|"
            r"cross[- ]encoder\s+rerank|NDCG@|MRR@|Recall@\d+|zero[- ]downtime\s+alias|Indonesian\s+analyzer|search_after|PIT\s+pagination|"
            r"retrieval\s+ACL\s+prefilter|tenant\s+ACL\s+pre[- ]filter|searchDocumentsForTenant|Meilisearch|Typesense|OpenSearch|pgvector|Qdrant|HNSW)\b",
            re.IGNORECASE,
        ),
        "exclude": re.compile(r"\b(?:Context\s+Recall\s*,?\s*(?:dan|and)\s*.*prompt\s+injection)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-realtime",
        "layer": "task",
        "references": ["sub-REALTIME-IOT-DESKTOP.md", "BACKEND.md"],
        "include": re.compile(
            r"\b(?:realtime\s+(?:notification|transport|dashboard|disconnect)|WebSocket|Server[- ]Sent\s+Events|SSE|"
            r"EventSource|Last[- ]Event[- ]ID|slow[- ]consumer\s+backpressure|mid[- ]connection\s+(?:auth|revocation)|"
            r"pub/sub\s+fan[- ]out|socket\s+reconnect|WebRTC|STUN/TURN|WebTransport|MQTT|CRDT|Yjs|Automerge|"
            r"collaborative\s+edit(?:ing|or))\b",
            re.IGNORECASE,
        ),
        "exclude": re.compile(r"\b(?:duplicat(?:ed?|es)\s+(?:notification|email)|emails?\s+duplicated\s+after\s+retries)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-supplychain",
        "layer": "task",
        "references": ["SECURITY.md", "SECOPS-PENTEST.md"],
        "include": re.compile(
            r"\b(?:transitive\s+dependency|CycloneDX|SPDX|SBOM|SLSA\s+(?:provenance|v?1\.[012])|lockfile\s+integrity|typosquat|dependency\s+confusion|"
            r"pin(?:ned)?\s+(?:SHA|digest)|SHA\s+pin(?:ning)?|GitHub\s+Actions\s+pin|Cosign|Sigstore|in-toto|verify-attestation|"
            r"provenance\s+attestation|vulnerability\s+waiver|floating\s+:latest|supply[- ]chain\s+(?:audit|integrity|waiver))\b",
            re.IGNORECASE,
        ),
        "exclude": re.compile(r"\b(?:price[- ]estimation\s+for\s+tender|KAK|TOR|RAB|HPS)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-privacy",
        "layer": "risk",
        "references": ["SECURITY.md", "IT-PMO-GOVERNANCE.md"],
        "include": re.compile(
            r"\b(?:UU\s*PDP|UU\s*(?:No\.?\s*)?27\s*(?:Tahun\s*)?2022|GDPR|DPIA|ROPA|DSAR|data\s+(?:spesifik|pribadi)|cross[- ]border\s+transfer|PII\s+(?:redaction|masking)|NIK\s+log|kebocoran\s+data|erasure[-_]tombstones|legal[-_ ]?hold|3\s*x\s*24)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-ai-eng",
        "layer": "task",
        "references": ["AI-LLM.md", "AGENTS-MCP.md"],
        "include": re.compile(
            r"\b(?:structured\s+outputs?|tool[- ]calling\s+agent|function\s+calling|LLM\s+(?:gateway|streaming|copilot|feature|app)|"
            r"AI\s+(?:agent|copilot|assistant|workflow|gateway)|build\s+(?:an?\s+)?MCP\s+server|buat\s+MCP\s+server|"
            r"MCP\s+(?:server|tool\s+schema)|token\s+streaming|semantic\s+cach(?:e|ing)|prompt\s+versioning|context\s+compaction)\b",
            re.IGNORECASE,
        ),
        "exclude": re.compile(
            r"\b(?:RAG\s*(?:eval|triad|faithfulness)|red[- ]team|OWASP\s*LLM|tagihan\s+cloud|FOCUS\s+spec)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-eval",
        "layer": "risk",
        "references": ["AI-LLM.md", "sub-RAG-VECTOR-KNOWLEDGE.md"],
        "include": re.compile(
            r"\b(?:RAG\s*(?:eval|triad|faithfulness)|answer\s+(?:faithfulness|groundedness)|LLM[- ]as[- ]a[- ]judge|OWASP\s*LLM|NIST\s*AI\s*600-1|prompt\s+injection|red[- ]team\s+LLM|precision\s+probe|recall\s+probe|golden\s+dataset)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-finops",
        "layer": "risk",
        "references": ["CLOUD-SRE.md", "sub-AI-INFRA-SERVING.md"],
        "include": re.compile(
            r"\b(?:FinOps|FOCUS\s+spec|cloud\s+(?:cost|bill|tagihan)|token\s+(?:cost|budget)|prompt\s+caching|thinking\s+token|K8s\s+(?:cost|right[- ]sizing)|egress\s+cost)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-mobile",
        "layer": "task",
        "references": ["MOBILE.md", "sub-FRONTEND-MOBILE-STACKS.md"],
        "include": re.compile(
            r"\b(?:OWASP\s*MASVS|PrivacyInfo\.xcprivacy|Play\s+Integrity|targetSdkVersion|AndroidManifest|App\s+Store\s+Connect|Play\s+Console|\.aab|Universal\s+Links|App\s+Links|assetlinks\.json|apple-app-site-association|Flutter\s+release|React\s+Native\s+signing)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-perf",
        "layer": "risk",
        "references": ["sub-OBSERVABILITY-PROFILING.md", "sub-QA-AUTOMATION.md"],
        "include": re.compile(
            r"\b(?:pre[- ]UAT\s+(?:perf|load)|k6\s+load|load\s+test|stress\s+test|spike\s+test|EXPLAIN\s+ANALYZE|query\s+profiling|bottleneck\s+audit)\b",
            re.IGNORECASE,
        ),
        "exclude": re.compile(
            r"^(?!.*\b(?:pre[- ]?UAT|k6|EXPLAIN\s+ANALYZE)\b).*\b(?:build|implement|create|buat|tambah)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    },
    {
        "skill": "shadow-api",
        "layer": "task",
        "references": ["BACKEND.md", "sub-SPECS-DOCX-CODE.md"],
        "include": re.compile(
            r"\b(?:REST\s+API|API\s+(?:endpoint|documentation)|dokumentasi\s+API|backend\s+endpoint|endpoint\s+backend|"
            r"endpoint\s+(?:Express|FastAPI|NestJS|Hono|Laravel|Go|REST)|\b(?:GET|POST|PUT|PATCH|DELETE)\s+/[a-z0-9_/:.-]+|"
            r"OpenAPI|openapi\.yaml|Swagger|Postman|Bruno|\.bru\b|Scalar|Redoc|Insomnia|TypeSpec|"
            r"HTTP\s+(?:route|controller)|GraphQL\s+(?:schema|contract)|AsyncAPI|gRPC\s+contract|RFC\s*9457|"
            r"tRPC|multipart\s+upload|presigned\s+URL|tus\s+resumable|S3\s+multipart|cursor\s+pagination)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-auth",
        "layer": "task",
        "references": ["SECURITY.md", "BACKEND.md"],
        "include": re.compile(
            r"\b(?:login|authentication|AuthN|AuthZ|RBAC|ABAC|ReBAC|OpenFGA|SpiceDB|Zanzibar|Passkeys?|WebAuthn|FIDO2|"
            r"MFA|TOTP|OAuth2|OIDC|SSO|mTLS|DPoP|API\s+key\s+(?:lifecycle|rotation)|JWT\s+refresh|session\s+rotation|"
            r"tenant\s+isolation|multi[- ]tenant\s+auth|confused\s+deputy)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-db",
        "layer": "task",
        "references": ["DATABASE.md", "DATA-ANALYTICS-ML.md"],
        "include": re.compile(
            r"\b(?:inspect\s+(?:live\s+)?database|DBML|ERD|schema\s+diff|Star\s+Schema|Data\s+Warehouse|Pentaho|\.ktr|\.kjb|"
            r"read[- ]only\s+query|MVCC\s+bloat|query\s+planner|ETL\s+dari\s+SQLite\s+ke\s+PostgreSQL|database\s+deadlock|"
            r"PgBouncer|transaction\s+pooling|SQLite\s+WAL|MongoDB|TimescaleDB|ClickHouse|connection\s+pool\s+sizing|"
            r"Row[- ]Level\s+Security|\bRLS\b\s+(?:policy|policies|index)|auth\.uid\(\)|SECURITY\s+DEFINER|Supabase\s+(?:Postgres|RLS|index))\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-data",
        "layer": "task",
        "references": ["DATABASE.md", "sub-DATA-STORES.md"],
        "include": re.compile(
            r"\b(?:database\s+migration|ETL\s+dari\s+SQLite\s+ke\s+PostgreSQL|Expand[- ]Contract|zero[- ]downtime\s+migration|backfill|"
            r"deterministic\s+seed|bulk\s+(?:import|export)|ACID\s+lock|isolation\s+anomal|database\s+deadlock|"
            r"Debezium|CDC\s+pipeline|online\s+DDL|pg_repack|gh-ost|NOT\s+VALID\s+constraint|CONCURRENTLY\s+index)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-cache",
        "layer": "task",
        "references": ["FRONTEND.md", "sub-DATA-STORES.md"],
        "include": re.compile(
            r"\b(?:TanStack\s+Query|SWR|Redis\s+cach|cache\s+stampede|singleflight|request\s+coalescing|Bloom\s+filter|"
            r"negative\s+cach(?:e|ing)|CDN\s+cach(?:e|ing)|Surrogate-Key|ETag\s+cach|optimistic\s+UI|Idempotency[- ]Key|"
            r"stale[- ]while[- ]revalidate|cache\s+coherency)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-integrate",
        "layer": "task",
        "references": ["ENTERPRISE-INTEGRATION.md", "sub-FINTECH-ID-ECOSYSTEM.md"],
        "include": re.compile(
            r"\b(?:payment\s+gateway|SNAP\s+BI|Midtrans|Xendit|Stripe|QRIS|webhook|webhook\s+replay|HMAC\s+signature|"
            r"Transactional\s+Outbox|circuit\s+breaker|reconciliation\s+job|provider\s+inquiry|"
            r"third[- ]party\s+API\s+(?:retry|timeout|integration)|WhatsApp\s+gateway|SMTP|emails?\s+duplicated)\b",
            re.IGNORECASE,
        ),
        "exclude": re.compile(r"\b(?:SMTP\s+250|Postmaster\s+Tools|email\s+header\s+injection)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-email",
        "layer": "task",
        "references": ["BACKEND.md", "ENTERPRISE-INTEGRATION.md"],
        "include": re.compile(
            r"\b(?:React\s+Email|MJML|transactional\s+email|email\s+(?:template|deliverability|bounce|suppression|rendering|outbox)|"
            r"SPF|DKIM|DMARC|BIMI|MTA-STS|TLS-RPT|RFC\s*8058|List-Unsubscribe(?:-Post)?|one[- ]click\s+unsubscribe|"
            r"Outlook\s+VML|Gmail\s+102\s*KB|IP\s+warm[- ]?up|Mailpit|Resend|Postmark|Amazon\s+SES|SendGrid|"
            r"SMTP\s+250|Postmaster\s+Tools|DSN\s+bounce|email\s+header\s+injection)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-seo",
        "layer": "task",
        "references": ["FRONTEND.md"],
        "include": re.compile(
            r"\b(?:technical\s+SEO|\bSEO\b|JSON-LD|Schema\.org|sitemap\.xml|robots\.txt|hreflang|canonical\s+URL|"
            r"crawl\s+budget|redirect\s+chain|domain\s+migration\s+SEO|ccTLD|X-Robots-Tag|llms\.txt|crawlabilit\w*|rich\s+snippets?|OpenGraph\s+meta|"
            r"CrUX|Search\s+Console|keyword\s+cannibalization|faceted\s+navigation|programmatic\s+SEO|AI\s+search\s+visibility)\b",
            re.IGNORECASE,
        ),
        "exclude": re.compile(r"\b(?:OG\s+card\s+Satori|generate\s+OG\s+image)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-analytics",
        "layer": "task",
        "references": ["FRONTEND.md", "DATA-ANALYTICS-ML.md"],
        "include": re.compile(
            r"\b(?:product\s+analytics|event\s+taxonomy|tracking\s+plan|PostHog|GA4|Google\s+Analytics|Mixpanel|Amplitude|"
            r"Plausible|Sample\s+Ratio\s+Mismatch|\bSRM\b|CUPED|power\s+analysis|A/B\s+(?:test(?:ing)?|experiment)|"
            r"funnel\s+tracking|identity\s+stitching|cohort\s+retention|North\s+Star\s+Metric|"
            r"Difference[- ]in[- ]Differences|\bDiD\b|causal\s+inference|Synthetic\s+Control|mSPRT|delta\s+method|"
            r"sequential\s+testing|assignment\s+vs\s+exposure|switchback\s+experiment)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-sec",
        "layer": "risk",
        "references": ["SECURITY.md", "SECOPS-PENTEST.md"],
        "include": re.compile(
            r"\b(?:STRIDE|threat\s+model|OWASP\s*ASVS|NIST\s*SSDF|VAPT|SAST|DAST|secret\s+scan|SQL\s+injection|SQLi|"
            r"IDOR|SSRF|XSS|CSRF|CSP|CSP\s+nonce|HSTS|CORS|security\s+headers|path\s+traversal|169\.254\.169\.254|"
            r"BOLA|broken\s+access|clickjacking|kerentanan|celah\s+keamanan|audit\s+keamanan|transitive\s+dependency|attack[- ]surface)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-browser",
        "layer": "risk",
        "references": ["FRONTEND.md", "sub-QA-AUTOMATION.md"],
        "include": re.compile(
            r"\b(?:Playwright|browser\s+E2E|375px|mobile\s+viewport\s+overflow|console\s+error\s+in\s+browser|UI\s+click[- ]through|"
            r"visual\s+regression|toHaveScreenshot|HAR\s+recording|Playwright\s+trace|storageState)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-video",
        "layer": "task",
        "references": ["FRONTEND.md", "sub-QA-AUTOMATION.md", "sub-VISION-OCR-MEDIA.md"],
        "include": re.compile(
            r"\b(?:video\s+tutorial|tutorial\s+video|narasi\s+TTS|TTS\s+narration|narrated\s+video|video-pipeline|"
            r"rekam(?:an)?\s+layar|screen\s+recording|Azure\s+(?:AI\s+)?Speech|kartu\s+judul|title\s+cards?|"
            r"video\s+panduan|Remotion|programmatic\s+video|motion\s+product\s+video|mobile\s+app\s+demo\s+video|"
            r"docs\s+GIF|LUFS\s+loudness)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-illustration",
        "layer": "task",
        "references": ["MOBILE-DESIGN.md", "DESIGN.md"],
        "include": re.compile(
            r"\b(?:product\s+illustration|ilustrasi\s+(?:SVG|produk|maskot|onboarding|status|canvas|isometric)|mascot|maskot|"
            r"onboarding\s+(?:art|illustration)|status\s+artwork|SVG\s+(?:character|mascot|illustration|icon\s+system)|"
            r"Lottie\s+(?:motion|handoff|animation)|Rive\s+animation|HTML5\s+canvas|WebGL|Three\.js|GLSL\s+shader|"
            r"procedural\s+(?:art|visual)|OG\s+card|Satori|spritesheet|favicon\s+(?:set|pack)|PWA\s+icons?|"
            r"isometric\s+diagram|CMYK\s+print|banner\s+cetak)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "modern-web-guidance",
        "layer": "task",
        "references": ["FRONTEND.md"],
        "include": re.compile(
            r"\b(?:modern[- ]web[- ]guidance|popover\s+API|anchor\s+positioning|container\s+quer(?:y|ies)|"
            r"@container|:has\(|:user-valid|view\s+transitions?\s+API|scroll[- ]driven\s+animations?|"
            r"content-visibility|fetchpriority|core\s+web\s+vitals|native\s+<dialog>|"
            r"async\s+waterfalls?|barrel\s+imports?|React\.cache|RSC\s+(?:serialization|performance|bundle)|react-best-practices)\b",
            re.IGNORECASE,
        ),
        "exclude": re.compile(r"\b(?:SQL\s+query|Dockerfile|GitHub\s+Actions|CI/CD\s+pipeline)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-accessibility",
        "layer": "risk",
        "references": ["DESIGN.md", "UI_UX_Design_Knowledge_Base_v2_Art_Direction_Web_Mobile_ID.md"],
        "include": re.compile(
            r"\b(?:WCAG|screen\s+reader|ARIA\s+live|aria-label|aria-describedby|focus\s+trap|"
            r"keyboard\s+navigation|tab\s+order|kontras\s+warna|color\s+contrast|aksesibilitas|lansia\s+contrast|"
            r"i18n|internationalization|RTL\s+layout|ICU\s+MessageFormat|pseudo[- ]localization)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-design",
        "layer": "task",
        "references": ["DESIGN.md", "UI_UX_Design_Knowledge_Base_v2_Art_Direction_Web_Mobile_ID.md"],
        "include": re.compile(
            r"\b(?:design\s+system|wireframe|UI/UX|user\s+flow|thumb\s+zone|design\s+token|komponen\s+UI|antarmuka|interview-script|task[- ]usability)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-test",
        "layer": "task",
        "references": ["TESTING.md", "sub-QA-AUTOMATION.md"],
        "include": re.compile(
            r"\b(?:unit\s+test|integration\s+test|contract\s+test|Vitest|Jest|Pytest|Pest|PHPUnit|JUnit|xUnit|regression\s+test|property[- ]based\s+test|mutation\s+test|characterization\s+test)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-quality",
        "layer": "risk",
        "references": ["CODE-REVIEW.md", "CROSS-MODEL-PARITY.md"],
        "include": re.compile(
            r"\b(?:static\s+analysis|lint|typecheck|dead\s+code|cyclomatic\s+complexity|shadow_gate|"
            r"fitness\s+function|architectural\s+fitness|ESLint\s+boundary|noUncheckedIndexedAccess|strict\s+tsconfig|convention\s+drift|"
            r"pure\s+formatting\s+refactor|formatting[- ]only)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-git",
        "layer": "task",
        "references": ["DEVOPS.md"],
        "include": re.compile(
            r"\b(?:git\s+merge-tree|merge\s+conflict|git\s+worktree|sync\s+branch|pull\s+branch|branching\s+strategy)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-doc",
        "layer": "task",
        "references": ["DOCS-PIPELINE.md", "sub-SPECS-DOCX-CODE.md"],
        "include": re.compile(
            r"\b(?:document\s+generator|document\s+engine|doc_orchestrator|build_doc\.py|(?:regenerasi|regenerate)\s+(?:output\s+)?(?:dokumen|document)|export\s+(?:to\s+)?(?:docx|pdf|html|xlsx)|render\s+(?:handover|grc|presales|pmo|architecture)\s+(?:report|document|proposal)|build-manifest|\.docx|\.xlsx|Canonical\s+AST|generate\s+document|SRS\s+doc|SDD\s+doc|reference_verifier)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-discovery",
        "layer": "task",
        "references": ["PRODUCT-ANALYSIS.md"],
        "include": re.compile(
            r"\b(?:elicit\s+requirement|PRD|SRS|BRD|stakeholder\s+mapping|Given/When/Then|acceptance\s+criteria|"
            r"NFR\s+(?:table|spec|quantif|engineering)|non[- ]functional\s+requirements?|requirements?\s+(?:discovery|elicitation|gap))\b",
            re.IGNORECASE,
        ),
        "exclude": re.compile(r"\b(?:KAK|tender|RAB|HPS|paid\s+CR)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-architect",
        "layer": "task",
        "references": ["ARCHITECTURE.md"],
        "include": re.compile(
            r"\b(?:C4\s+diagram|ADR|Architecture\s+Decision\s+Record|modular\s+monolith|microservices\s+vs\s+monolith|"
            r"module\s+boundar(?:y|ies)|topology\s+selection|system\s+architecture|architecture\s+for\s+a\s+new\s+app(?:lication)?)\b",
            re.IGNORECASE,
        ),
        "exclude": re.compile(r"\b(?:TOGAF|SPBE|6\s+domain|application\s+portfolio|TIME\s+matrix)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-plan",
        "layer": "task",
        "references": ["PRODUCT-ANALYSIS.md", "IT-PMO-GOVERNANCE.md"],
        "include": re.compile(r"\b(?:epic|user\s+story|sprint\s+task|DoR|DoD|task\s+breakdown|vertical\s+slic(?:e|ing)|sprint\s+planning|story\s+decomposition)\b", re.IGNORECASE),
        "exclude": re.compile(r"\b(?:paid\s+CR|monte\s+carlo|EVM|CPI|SPI)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-bootstrap",
        "layer": "task",
        "references": ["OFFICIAL-FIRST-DEPENDENCY-POLICY.md", "CORE.md", "DEVOPS.md"],
        "include": re.compile(
            r"\b(?:scaffold\s+new\s+project|scaffold\s+(?:a\s+)?(?:new\s+)?(?:service|CLI|library|worker|app)|greenfield\s+(?:project|service|app|CLI)|"
            r"from\s+scratch|from\s+zero|init\s+repository|bootstrap\s+(?:a\s+)?(?:new\s+)?project|buat\s+proyek\s+baru|"
            r"(?:initialize|create|start|buat)\s+(?:a\s+)?new\s+[^\n]{0,30}\b(?:project|app)|create-next-app|create\s+vite)\b",
            re.IGNORECASE,
        ),
        "exclude": re.compile(r"\b(?:technical\s+due\s+diligence|legacy\s+(?:codebase|module|feature)|refactor)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-uat",
        "layer": "risk",
        "references": ["sub-QA-AUTOMATION.md"],
        "include": re.compile(
            r"\b(?:Staging\s+UAT|UAT\s+scenario|Berita\s+Acara\s+UAT|UAT\s+sign[- ]off|UAT\s+defect\s+triage|UAT\s+exit\s+gate|"
            r"tim\s+QA\s+melaporkan|Requirement\s+Traceability\s+Matrix|RTM|client\s+sign[- ]off)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-release",
        "layer": "risk",
        "references": ["DEVOPS.md", "CLOUD-SRE.md"],
        "include": re.compile(
            r"\b(?:production\s+(?:release|deploy)|SemVer|changelog|rollback\s+runbook|kriteria\s+rollback\s+aman|feature\s+flag\s+rollout|"
            r"kill[- ]switch\s+(?:flag|feature\s+flag)|canary\s+cohort|pre[- ]flight\s+release|release\s+checklist|deployment\s+rollback|roll\s+forward\s+vs\s+rollback)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-compat",
        "layer": "risk",
        "references": ["BACKEND.md", "FRONTEND.md"],
        "include": re.compile(
            r"\b(?:backward\s+compatib|dependency\s+upgrade|breaking\s+change|cross[- ]browser\s+matrix|behavior\s+unchanged|schema\s+evolution|"
            r"RFC\s*9745|RFC\s*8594|Deprecation\s+header|Sunset\s+header|410\s+Gone|deprecat(?:e|ing)\s+(?:an?\s+)?(?:API|endpoint|route)|"
            r"consumer[- ]driven\s+contract|tolerant\s+reader|API\s+versioning)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-ops",
        "layer": "task",
        "references": ["DEVOPS.md", "CLOUD-SRE.md"],
        "include": re.compile(
            r"\b(?:Docker|Dockerfile|Kubernetes|Nginx|Caddy|systemd|PM2|CI/CD|GitHub\s+Actions|GitLab\s+CI|canary\s+rollout|blue[- ]green|secret\s+rotation|"
            r"orphan(?:ed)?\s+(?:MCP|process(?:es)?)|proses\s+(?:MCP|yatim)|leftover\s+(?:dev\s+server|process(?:es)?)|dev\s+server\s+(?:nyangkut|sisa)|"
            r"resource_cleanup|port\s+conflict|bersihkan\s+proses)\b",
            re.IGNORECASE,
        ),
        "exclude": re.compile(r"\b(?:Redis\s+vs\s+queue\s+semantics|queue\s+semantics\s+vs\s+Redis)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-observe",
        "layer": "risk",
        "references": ["sub-OBSERVABILITY-PROFILING.md", "CLOUD-SRE.md"],
        "include": re.compile(
            r"\b(?:SLI|SLO|error\s+budget|OpenTelemetry|OTel|Prometheus|PromQL|Loki|Grafana|distributed\s+tracing|"
            r"traceparent|structured\s+log(?:ger|ging)?|pino|winston|structlog|log/slog|correlation\s+id|"
            r"X-Request-Id|wide[- ]event\s+log|returns?\s+500|random\s+500)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-resilience",
        "layer": "risk",
        "references": ["CLOUD-SRE.md"],
        "include": re.compile(
            r"\b(?:disaster\s+recovery|restore\s+drill|RPO|RTO|chaos\s+engineering|backup\s+restore|bulkhead\s+(?:isolation|pattern|semaphore|pool)|"
            r"graceful\s+degradation|feature\s+shedding|load\s+shedding|stale[- ]cache\s+fallback|business\s+continuity|fault\s+injection)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-maintain",
        "layer": "task",
        "references": ["DEBUGGING.md", "IT-PMO-GOVERNANCE.md"],
        "include": re.compile(
            r"\b(?:post[- ]production|Harwat|OMKT|postmortem|blameless\s+RCA|hotfix\s+SLA|"
            r"incident\s+triage|SEV[1-4]\s+incident|5[- ]Why\s+RCA|fault[- ]tree\s+RCA|preventive\s+maintenance)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "context7",
        "layer": "task",
        "references": [],
        "include": re.compile(r"\b(?:latest\s+(?:library|framework|SDK)\s+docs|Context7|breaking\s+API\s+in\s+v\d+)\b", re.IGNORECASE),
    },
]

# Contextual co-activation bundles for §5.1 multi-skill ownership pairs without forcing false positives.
CO_ACTIVATION_MAP: dict[str, dict[str, list[str]]] = {
    "shadow-debug": {"supporting": ["shadow-test"], "risk": []},
    "shadow-refactor": {"supporting": ["shadow-test"], "risk": ["shadow-compat", "shadow-quality"]},
    "shadow-concurrency": {"supporting": ["shadow-test"], "risk": []},
    "shadow-domain": {"supporting": ["shadow-test"], "risk": []},
    "shadow-search": {"supporting": ["shadow-db"], "risk": ["shadow-eval"]},
    "shadow-realtime": {"supporting": ["shadow-auth", "shadow-concurrency", "shadow-observe"], "risk": []},
    "shadow-supplychain": {"supporting": [], "risk": ["shadow-sec", "shadow-release"]},
    "shadow-pmo": {"supporting": ["shadow-architect"], "risk": []},
    "shadow-architect": {"supporting": ["shadow-domain"], "risk": ["shadow-sec"]},
}

LANGUAGE_REF_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(?:TypeScript|Node\.js|Express|NestJS|Hono|Next\.js)\b", re.IGNORECASE), "lang-TYPESCRIPT-NODE.md"),
    (re.compile(r"\b(?:Golang|\bGo\b\s+(?:service|API|backend|server|worker))\b", re.IGNORECASE), "lang-GO.md"),
    (re.compile(r"\b(?:Python|FastAPI|Django|Flask|Pytest)\b", re.IGNORECASE), "lang-PYTHON.md"),
    (re.compile(r"\b(?:Laravel|PHP|Pest|PHPUnit)\b", re.IGNORECASE), "lang-PHP-LARAVEL.md"),
    (re.compile(r"\b(?:Spring\s+Boot|Kotlin|Java\b|JUnit)\b", re.IGNORECASE), "lang-JAVA-KOTLIN.md"),
    (re.compile(r"\b(?:ASP\.NET|C#|EF\s+Core|\.NET\b)\b", re.IGNORECASE), "lang-DOTNET.md"),
    (re.compile(r"\b(?:Rust|tokio|axum|cargo)\b", re.IGNORECASE), "lang-RUST.md"),
    (re.compile(r"\b(?:Flutter|Dart\b)\b", re.IGNORECASE), "lang-DART-FLUTTER.md"),
    (re.compile(r"\b(?:C\+\+|CMake|FreeRTOS|ESP32|STM32)\b", re.IGNORECASE), "lang-CPP-SYSTEMS.md"),
    (re.compile(r"\b(?:MCP\s+server|subagent|multi[- ]agent)\b", re.IGNORECASE), "AGENTS-MCP.md"),
    (re.compile(r"\b(?:PostGIS|GeoJSON|MapLibre|Leaflet|geospatial)\b", re.IGNORECASE), "sub-GIS-GEOSPATIAL.md"),
    (re.compile(r"\b(?:LoRA|QLoRA|fine[- ]tun|Unsloth|Langfuse)\b", re.IGNORECASE), "sub-LLM-FINETUNING-LLMOps.md"),
    (re.compile(r"\b(?:PowerShell|\.ps1|Makefile|Justfile|Taskfile)\b", re.IGNORECASE), "sub-SHELL-CLI-AUTOMATION.md"),
]

UI_ANTISLOP_RE = re.compile(
    r"\b(?:UI|frontend|halaman|landing\s+page|CSS|Tailwind|React|Next\.js|Vue|Svelte|Angular|shadcn|"
    r"component|komponen|card|dropdown|dialog|drawer|table|tabel|tabs|sidebar|header|footer|input|select|"
    r"badge|toast|popover|tooltip|accordion|theme|styling|form|modal|navbar|dashboard|tombol|button|layout|"
    r"mobile\s+responsive)\b",
    re.IGNORECASE,
)
COPYWRITING_RE = re.compile(
    r"\b(?:copywriting|microcopy|headline|CTA|call[- ]to[- ]action|pesan\s+error|UX\s+writing|product\s+prose)\b",
    re.IGNORECASE,
)
CODE_COMMENT_RE = re.compile(
    r"\b(?:code\s+comments?|komentar\s+kode|clean(?:up)?\s+comments?|rapikan\s+(?:code\s+)?comments?)\b",
    re.IGNORECASE,
)
TYPO_ONLY_RE = re.compile(
    r"\b(?:typo[- ]only\b|fix\s+(?:a\s+)?(?:small\s+)?typo\s+(?:in\s+)?[^\n]{0,40}(?:README|\.(?:md|txt))|"
    r"perbaiki\s+typo\s+(?:di\s+)?[^\n]{0,40}(?:README|\.(?:md|txt))|only\s+typo)\b",
    re.IGNORECASE,
)
TRIVIAL_FACT_RE = re.compile(r"^\s*(?:apa\s+itu|what\s+is|berapa|bagi\s+benchmark|knp|kenapa)\b", re.IGNORECASE)
NON_TRIVIAL_INCIDENT_RE = re.compile(
    r"\b(?:API|error|500|40[0-9]|timeout|crash|bug|gagal|production|staging|DB|database|server|query|endpoint|"
    r"slow|lambat|tagihan|cost|token|cloud|K8s)\b",
    re.IGNORECASE,
)
PROD_ACCESS_UNAUTH_RE = re.compile(
    r"\b(?:production\s+data\s+access\s+required\s+but\s+not\s+authorized|no\s+prod(?:uction)?\s+(?:DB|data)\s+access|akses\s+produksi\s+belum\s+diizinkan)\b",
    re.IGNORECASE,
)


def audit_descriptions(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    """Audit all skill SKILL.md frontmatter descriptions for explicit 'Use when...' triggers."""
    skill_dirs = sorted(
        [p for p in repo_root.iterdir() if p.is_dir() and not p.name.startswith(".") and p.name not in SKIP_ROOT_DIRS],
        key=lambda p: p.name,
    )

    missing_use_when: list[str] = []
    oversized_desc: list[dict[str, Any]] = []
    missing_frontmatter: list[str] = []

    for sdir in skill_dirs:
        sfile = sdir / "SKILL.md"
        if not sfile.is_file():
            missing_frontmatter.append(sdir.name)
            continue
        txt = sfile.read_text(encoding="utf-8")
        m = re.search(r"^---\s*\n(.*?)\n---", txt, re.DOTALL)
        if not m:
            missing_frontmatter.append(sdir.name)
            continue
        desc = ""
        for line in m.group(1).splitlines():
            if line.startswith("description:"):
                desc = line[len("description:") :].strip().strip('"').strip("'")
                break
        if not USE_WHEN_RE.search(desc):
            missing_use_when.append(sdir.name)
        if len(desc) > 500:
            oversized_desc.append({"skill": sdir.name, "length": len(desc)})

    passed = (
        len(skill_dirs) > 0
        and len(missing_frontmatter) == 0
        and len(missing_use_when) == 0
        and len(oversized_desc) == 0
    )
    return {
        "total_skills": len(skill_dirs),
        "missing_frontmatter": missing_frontmatter,
        "missing_use_when_trigger": missing_use_when,
        "oversized_descriptions_gt_500": oversized_desc,
        "all_passed": passed,
    }


def get_known_skill_names(repo_root: Path = REPO_ROOT) -> set[str]:
    return {
        p.name
        for p in repo_root.iterdir()
        if p.is_dir() and not p.name.startswith(".") and p.name not in SKIP_ROOT_DIRS and (p / "SKILL.md").is_file()
    }


def _strip_non_authoritative_signals(prompt: str) -> str:
    """Remove fenced/quoted log snippets and explicit negated tool clauses before topic matching."""
    cleaned = QUOTED_LOG_RE.sub(" ", prompt)
    cleaned = NEGATED_CLAUSE_RE.sub(" ", cleaned)
    return cleaned


def _compute_disclosure_metrics(
    companion_skills: list[str],
    always_on_ui: list[str],
    reference_modules: list[str],
    is_trivial: bool,
) -> dict[str, Any]:
    loaded_paths: list[str] = []
    total_bytes = 0
    for skill in [*companion_skills, *always_on_ui]:
        skill_file = REPO_ROOT / skill / "SKILL.md"
        if skill_file.exists():
            loaded_paths.append(f"{skill}/SKILL.md")
            total_bytes += skill_file.stat().st_size
    for ref in reference_modules:
        ref_file = REPO_ROOT / "shadow-monarch" / "reference" / ref
        if ref_file.exists():
            loaded_paths.append(f"shadow-monarch/reference/{ref}")
            total_bytes += ref_file.stat().st_size
    return {
        "trivial_fast_path": is_trivial,
        "loaded_skill_count": len(companion_skills) + len(always_on_ui),
        "loaded_ref_count": len(reference_modules),
        "estimated_loaded_bytes": total_bytes,
        "loaded_paths": loaded_paths,
    }


def route_prompt(
    prompt: str,
    max_companion_skills: int = 4,
    task_id: str = "TASK-AUTO",
    repo_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Route a natural-language task prompt to required skills, references & §2.2 Decision Record."""
    stripped = prompt.strip()
    signal_text = _strip_non_authoritative_signals(stripped)
    known_skills = get_known_skill_names()

    mentions = re.findall(r"(?<![\w/.:])[/\$]([a-z][a-z0-9-]+)(?![\w/-])", signal_text.lower())
    explicit_skills = [skill for skill in mentions if skill in known_skills]
    unquoted = QUOTED_LOG_RE.sub(" ", stripped)
    is_code_review = bool(CODE_REVIEW_RE.search(signal_text) or READ_ONLY_SCOPE_RE.search(unquoted))
    is_load_test_denied = bool(LOAD_TEST_DENIAL_RE.search(unquoted))
    is_unit_test_only = bool(re.search(r"\b(?:unit\s+tests?|Vitest|Jest|Pytest|Pest|PHPUnit|JUnit|xUnit)\b", signal_text, re.IGNORECASE))
    blocked_by_scope = (
        {"shadow-browser", "shadow-perf"} if is_code_review or is_unit_test_only else set()
    )

    if is_load_test_denied:
        blocked_by_scope.add("shadow-perf")

    matched_ordered: list[str] = []
    matched_task: list[str] = []
    matched_risk: list[str] = []
    matched_refs: list[str] = []
    excluded_records: list[dict[str, str]] = []

    is_typo_only = bool(TYPO_ONLY_RE.search(signal_text)) and not explicit_skills
    is_definitional_query = bool(re.match(r"^\s*(?:apa\s+itu|what\s+is|what\s+does)\b", signal_text, re.IGNORECASE))
    is_trivial_fact = (
        bool(TRIVIAL_FACT_RE.match(signal_text))
        and not explicit_skills
        and (is_definitional_query or not NON_TRIVIAL_INCIDENT_RE.search(signal_text))
    )

    for sl in explicit_skills:
        if sl in blocked_by_scope:
            continue
        if sl not in matched_ordered:
            matched_ordered.append(sl)
        if sl not in matched_task:
            matched_task.append(sl)

    if not is_typo_only:
        for rule in ROUTING_RULES:
            sname = rule["skill"]
            if sname not in known_skills or sname in blocked_by_scope:
                continue
            if rule["include"].search(signal_text) or (sname == "shadow-quality" and is_code_review):
                excl = rule.get("exclude")
                if excl and excl.search(signal_text):
                    excluded_records.append(
                        {"skill": sname, "reason": "Excluded by sibling disambiguation or negative trigger boundary."}
                    )
                    continue
                target_bucket = matched_risk if rule.get("layer") == "risk" else matched_task
                if sname not in matched_ordered:
                    matched_ordered.append(sname)
                if sname not in matched_task and sname not in matched_risk:
                    target_bucket.append(sname)

    always_on_ui: list[str] = []
    if not is_typo_only:
        if UI_ANTISLOP_RE.search(signal_text):
            for ui_skill in ("antislop", "antislop-ui", "antislop-layoutmobile", "antislop-human", "modern-web-guidance"):
                if ui_skill in known_skills and ui_skill not in matched_ordered and ui_skill not in always_on_ui:
                    always_on_ui.append(ui_skill)
        if COPYWRITING_RE.search(signal_text) and "antislop-copywriting" in known_skills:
            if "antislop" not in always_on_ui and "antislop" in known_skills:
                always_on_ui.append("antislop")
            if "antislop-copywriting" not in always_on_ui:
                always_on_ui.append("antislop-copywriting")
        if CODE_COMMENT_RE.search(signal_text) and "antislop-code" in known_skills:
            if "antislop-code" not in always_on_ui:
                always_on_ui.append("antislop-code")

    # Guard against accidental shadow-perf loading during routine implementation
    if "shadow-perf" not in matched_ordered and "shadow-perf" not in blocked_by_scope and re.search(r"\b(?:build|implement|create|buat|tambah)\b", signal_text, re.IGNORECASE):
        excluded_records.append(
            {"skill": "shadow-perf", "reason": "Strict Pre-UAT gate only; excluded during routine implementation."}
        )

    is_trivial = (is_typo_only or is_trivial_fact) and len(matched_ordered) == 0 and len(always_on_ui) == 0
    if is_typo_only:
        excluded_records.append(
            {"skill": "shadow-architect/shadow-sec/shadow-browser", "reason": "Negative trigger §5.3: typo-only README edit uses Layer 1 minimal safeguards."}
        )

    primary_skill = matched_ordered[0] if matched_ordered else "shadow-monarch"

    for skill in sorted(blocked_by_scope):
        excluded_records.append({"skill": skill, "reason": "Execution skill is outside the requested scope."})

    excluded_names = {entry["skill"] for entry in excluded_records}
    if primary_skill in CO_ACTIVATION_MAP and not is_trivial:
        bundle = CO_ACTIVATION_MAP[primary_skill]
        for sup in bundle["supporting"]:
            if sup in known_skills and sup != primary_skill and sup not in excluded_names and sup not in matched_ordered:
                matched_ordered.append(sup)
                matched_task.append(sup)
        for rsk in bundle["risk"]:
            if rsk in known_skills and rsk != primary_skill and rsk not in excluded_names and rsk not in matched_ordered:
                matched_ordered.append(rsk)
                matched_risk.append(rsk)

    if not is_trivial and re.search(r"\b(?:ridhuan-sso|sso-client|SSO\s+SDK)\b", stripped, re.IGNORECASE):
        if "shadow-auth" in known_skills and primary_skill != "shadow-auth":
            if "shadow-auth" in matched_ordered:
                matched_ordered.remove("shadow-auth")
            matched_ordered.insert(1 if matched_ordered else 0, "shadow-auth")
            if "shadow-auth" not in matched_task:
                matched_task.append("shadow-auth")

    companion_skills = matched_ordered[:max(1, max_companion_skills)]
    supporting_skills = [skill for skill in companion_skills if skill != primary_skill and skill in matched_task]
    risk_review_skills = [skill for skill in companion_skills if skill != primary_skill and skill in matched_risk]
    for skill in companion_skills:
        for rule in ROUTING_RULES:
            if rule["skill"] == skill:
                for reference in rule.get("references", []):
                    if reference not in matched_refs:
                        matched_refs.append(reference)

    if not is_trivial and any(s in always_on_ui for s in ("antislop-ui", "antislop-human", "modern-web-guidance")):
        if "FRONTEND.md" not in matched_refs:
            matched_refs.append("FRONTEND.md")

    if not is_trivial and (companion_skills or always_on_ui):
        for lang_re, lang_ref in LANGUAGE_REF_RULES:
            if len(matched_refs) >= 4:
                break
            if lang_re.search(signal_text) and lang_ref not in matched_refs:
                matched_refs.append(lang_ref)
                break

    if not is_trivial and not matched_refs and companion_skills:
        matched_refs.append("CORE.md")

    # Attach Official-First policy for new-project scaffolding, dependency adoption, or SSO/SDK integration
    is_official_first_task = bool(
        re.search(
            r"\b(?:scaffold|new\s+project|from\s+scratch|from\s+zero|buat\s+proyek\s+baru|create-next-app|create\s+vite|"
            r"npm\s+install|add\s+package|tambah\s+library|dependency|ridhuan-sso|sso-client|file:\.\./sdk|SSO\s+SDK)\b",
            stripped,
            re.IGNORECASE,
        )
    )
    if not is_trivial and is_official_first_task and "OFFICIAL-FIRST-DEPENDENCY-POLICY.md" not in matched_refs:
        matched_refs.insert(0, "OFFICIAL-FIRST-DEPENDENCY-POLICY.md")
    unauth_prod = bool(PROD_ACCESS_UNAUTH_RE.search(stripped))
    required_perms = ["read_repository"]
    if not is_code_review and not is_trivial:
        required_perms.append("run_local_tests")
    if unauth_prod:
        required_perms.append("explicit_prod_read_approval_missing_stop_at_safe_plan")

    if is_code_review:
        intent_mode = "code_review"
        max_auto_level = "L0_READ_ONLY"
    elif is_unit_test_only:
        intent_mode = "unit_test"
        max_auto_level = "L1_SAFE_VERIFICATION"
    elif primary_skill == "shadow-debug":
        intent_mode = "debug"
        max_auto_level = "L1_SAFE_VERIFICATION"
    elif primary_skill == "shadow-perf":
        intent_mode = "perf_optimization"
        max_auto_level = "L1_SAFE_VERIFICATION"
    elif primary_skill in {"shadow-data", "shadow-db"}:
        intent_mode = "db_fix"
        max_auto_level = "L1_SAFE_VERIFICATION"
    elif primary_skill in {"shadow-design", "shadow-accessibility", "modern-web-guidance", "shadow-illustration"} or (
        primary_skill == "shadow-monarch" and always_on_ui
    ):
        intent_mode = "ui_implementation"
        max_auto_level = "L1_SAFE_VERIFICATION"
    elif matched_ordered:
        intent_mode = "feature_implementation"
        max_auto_level = "L1_SAFE_VERIFICATION"
    else:
        intent_mode = "general"
        max_auto_level = "L0_READ_ONLY" if is_trivial else "L1_SAFE_VERIFICATION"

    prohibited_actions = [
        "write_production_db",
        "push_remote",
        "global_home_install_without_approval",
        "touch_external_docker_containers",
        "expand_scope_or_upgrade_subagent_level",
    ]
    if intent_mode == "code_review":
        prohibited_actions.extend(["write_or_modify_source_files", "run_mutating_commands"])
    if is_load_test_denied:
        prohibited_actions.append("run_explicitly_denied_load_test")
    if intent_mode in {"debug", "unit_test", "ui_implementation"}:
        prohibited_actions.append("stress_or_load_test_without_l3_approval")

    activation_reason = (
        f"Layer 1 minimal edit only ({'typo-only' if is_typo_only else 'trivial query'})."
        if is_trivial
        else (
            f"Primary owner `{primary_skill}` selected via topic/intent signal"
            + (f"; paired with supporting {supporting_skills}" if supporting_skills else "")
            + (f"; risk gates {risk_review_skills}" if risk_review_skills else "")
            + "."
        )
    )

    ctx = repo_context or {}
    has_active_api_doc_gen = bool(ctx.get("has_active_generator", False))
    readme_summary_only = bool(ctx.get("readme_summary_only", False))
    asks_generic_api_docs = bool(API_DOCS_GENERIC_RE.search(signal_text)) and not bool(
        API_DOCS_EXPLICIT_FORMAT_RE.search(signal_text)
    )
    requires_api_docs_decision = asks_generic_api_docs and readme_summary_only and not has_active_api_doc_gen

    final_refs = [] if is_trivial else matched_refs[:4]
    disclosure_metrics = _compute_disclosure_metrics(companion_skills, always_on_ui, final_refs, is_trivial)

    denied_actions = ["load_test", "stress_test", "soak_test"] if is_code_review or is_load_test_denied else []
    if is_code_review:
        denied_actions.append("broad_e2e")

    decision_record = {
        "task_id": task_id,
        "intent": stripped,
        "primary_skill": primary_skill,
        "supporting_skills": supporting_skills,
        "risk_review_skills": risk_review_skills,
        "activation_reason": activation_reason,
        "excluded_skills": excluded_records,
        "required_permissions": required_perms,
        "prohibited_actions": prohibited_actions,
        "disclosure_metrics": disclosure_metrics,
        "permission_policy": {
            "intent_mode": intent_mode,
            "max_auto_level": max_auto_level,
            "approval_required_levels": ["L2_SCOPE_EXPANSION", "L3_RESOURCE_INTENSIVE", "L4_HIGH_IMPACT"],
            "unknown_environment_policy": "FAIL_CLOSED",
        },
        "user_input_policy": {
            "channel": "INTERACTIVE_IF_AVAILABLE",
            "trigger": "MATERIAL_UNRESOLVED_DECISION_OR_REQUIRED_APPROVAL",
            "wait_before_dependent_work": True,
            "repeat_resolved_questions": False,
            "requires_user_decision": requires_api_docs_decision,
            "question_topic": "api_docs_format" if requires_api_docs_decision else None,
            "stop_before_write": requires_api_docs_decision,
        },
        "subagent_policy": {
            "inherit_parent_scope": True,
            "max_permission_level": max_auto_level,
            "denied_actions": denied_actions,
            "allow_scope_expansion": False,
            "allow_level_upgrade": False,
            "orchestrator_recommendation_is_authorization": False,
            "enforcer": "shadow-monarch/scripts/execution_approval_gate.py",
        },
    }

    return {
        "prompt": prompt,
        "core_orchestrator": "shadow-monarch",
        "companion_skills": companion_skills,
        "always_on_ui_skills": always_on_ui,
        "reference_modules": final_refs,
        "excluded_skills": excluded_records,
        "disclosure_metrics": disclosure_metrics,
        "routing_decision": decision_record,
    }


def run_self_test() -> dict[str, Any]:
    """Run description audit + §5.1 / §5.3 / legacy precision & recall routing probes."""
    audit = audit_descriptions()
    known_skills = get_known_skill_names()
    results: list[dict[str, Any]] = [
        {
            "probe": "AUDIT-1: All 59 SKILL.md have 'Use when...' triggers & <=500 chars",
            "passed": audit["all_passed"] and audit["total_skills"] >= 59,
            "details": audit,
        }
    ]

    # (name, prompt, must_include_skills, must_exclude_skills, expected_primary_optional)
    probes: list[tuple[str, str, list[str], list[str], str | None]] = [
        (
            "RECALL-1: Indonesian KAK & RAB under Perpres 46/2025 (no slash)",
            "Tolong buatkan perhitungan server sizing dan estimasi RAB proyek pemerintah dari KAK ini sesuai Perpres 46 Tahun 2025 dan TKDN.",
            ["shadow-presales"],
            ["shadow-perf", "shadow-ea"],
            "shadow-presales",
        ),
        (
            "RECALL-2: Banking GRC audit PADK OJK 1/2026 & COBIT/ISO 27001 (no slash)",
            "Lakukan readiness assessment ISO 27001 Clauses 4-10, SoA 93 kontrol, COBIT 2019, dan PADK OJK 1/2026 untuk bank umum.",
            ["shadow-grc"],
            ["shadow-perf", "shadow-privacy"],
            "shadow-grc",
        ),
        (
            "RECALL-3: UU PDP personal data classification & 3x24h breach (no slash)",
            "Audit tabel pasien yang menyimpan NIK dan rekam medis agar sesuai UU PDP Pasal 4, DPIA, cross-border transfer, dan notifikasi kebocoran data 3x24 jam.",
            ["shadow-privacy"],
            ["shadow-perf"],
            "shadow-privacy",
        ),
        (
            "RECALL-4: Legacy system technical due diligence (no slash)",
            "Lakukan technical due diligence pada legacy codebase PHP ini untuk melihat apakah lebih tepat Strangler Fig atau Full Rewrite.",
            ["shadow-modernize"],
            ["shadow-bootstrap", "shadow-perf"],
            "shadow-modernize",
        ),
        (
            "RECALL-5: Mid-project Paid CR vs Defect + PERT/Monte Carlo P80 (no slash)",
            "Klien minta fitur baru di tengah jalan, tolong evaluasi ini defect atau Paid CR lalu hitung ulang jadwal PERT, CPM, dan Monte Carlo P80.",
            ["shadow-pmo"],
            ["shadow-plan", "shadow-discovery"],
            "shadow-pmo",
        ),
        (
            "RECALL-6: Government 6-domain SPBE + Satu Data + TIME portfolio (no slash)",
            "Petakan portofolio aplikasi kementerian ke dalam 6 domain SPBE Perpres 132/2022, Satu Data, matriks TIME, dan ABB vs SBB.",
            ["shadow-ea"],
            ["shadow-architect"],
            "shadow-ea",
        ),
        (
            "RECALL-7: Single-app C4 & Modular Monolith design (no slash)",
            "Rancang C4 diagram dan ADR untuk memutuskan Modular Monolith vs Microservices pada satu sistem ERP baru.",
            ["shadow-architect"],
            ["shadow-ea"],
            "shadow-architect",
        ),
        (
            "RECALL-8: RAG evaluation + prompt injection red-team (no slash)",
            "Evaluasi kualitas RAG chatbot kami menggunakan metrics Faithfulness, Context Recall, dan uji red-team OWASP LLM prompt injection.",
            ["shadow-eval"],
            ["shadow-perf", "shadow-search"],
            "shadow-eval",
        ),
        (
            "RECALL-9: Mobile App Store PrivacyInfo.xcprivacy + Play Integrity (no slash)",
            "Siapkan build release Flutter untuk App Store Connect dan Play Console: cek PrivacyInfo.xcprivacy, Play Integrity API, dan assetlinks.json.",
            ["shadow-mobile"],
            ["shadow-browser"],
            "shadow-mobile",
        ),
        (
            "RECALL-VIDEO-1: Narrated tutorial video with Indonesian TTS (no slash)",
            "Buat video tutorial modul pengajuan usulan dengan narasi TTS Bahasa Indonesia dan subtitle SRT dari aplikasi staging.",
            ["shadow-video"],
            ["shadow-mobile", "shadow-perf"],
            "shadow-video",
        ),
        (
            "NEG-VIDEO-1: 375px layout check stays with shadow-browser (no slash)",
            "Jalankan Playwright browser E2E untuk cek mobile viewport overflow 375px di halaman checkout.",
            ["shadow-browser"],
            ["shadow-video"],
            "shadow-browser",
        ),
        (
            "RECALL-10: Cloud & LLM Token FinOps spike (no slash)",
            "Kenapa tagihan cloud K8s dan token LLM melonjak bulan ini? Cek prompt caching, thinking token budget, dan skema FOCUS.",
            ["shadow-finops"],
            ["shadow-perf"],
            "shadow-finops",
        ),
        (
            "RECALL-11: Backend REST API + Auth RBAC + DB migration (no slash)",
            "Buat endpoint REST API login dengan RBAC multi-tenant, OpenAPI 3.1, dan zero-downtime database migration Expand-Contract.",
            ["shadow-api", "shadow-auth", "shadow-data"],
            ["shadow-perf"],
            "shadow-api",
        ),
        (
            "RECALL-12: AI session resume ('lanjut handoff') vs client BAST",
            "lanjut handoff sesi kemarin ya, lanjutkan implementasi endpoint.",
            ["handoff"],
            ["shadow-handover"],
            "handoff",
        ),
        (
            "RECALL-13: Client BAST handover & manuals",
            "Siapkan dokumen BAST serah terima proyek ke klien lengkap dengan Admin Manual dan Training of Trainers.",
            ["shadow-handover"],
            ["handoff"],
            "shadow-handover",
        ),
        (
            "RECALL-14: Pre-UAT k6 load testing & EXPLAIN ANALYZE (explicit Pre-UAT)",
            "Fitur sudah selesai, sekarang jalankan Pre-UAT k6 load test dari openapi.yaml dan SQL EXPLAIN ANALYZE profiling.",
            ["shadow-perf"],
            [],
            "shadow-perf",
        ),
        (
            "S51-1: API returns 500 randomly -> shadow-debug owns root cause (no slash)",
            "Our checkout API returns 500 randomly under concurrency with misleading stack trace.",
            ["shadow-debug", "shadow-observe", "shadow-test"],
            ["shadow-perf"],
            "shadow-debug",
        ),
        (
            "S51-2: Refactor old feature behavior unchanged -> shadow-refactor (no bootstrap)",
            "Refactor old billing module so behavior unchanged using characterization tests.",
            ["shadow-refactor", "shadow-compat", "shadow-quality"],
            ["shadow-bootstrap", "shadow-perf"],
            "shadow-refactor",
        ),
        (
            "S51-3: Emails duplicated after retries -> shadow-concurrency (no shadow-realtime)",
            "Emails duplicated after retries when queue workers crash before ack.",
            ["shadow-concurrency", "shadow-integrate", "shadow-test"],
            ["shadow-realtime", "shadow-perf"],
            "shadow-concurrency",
        ),
        (
            "S51-4: Complex approvals & cancellation -> shadow-domain",
            "Model complex approvals and cancellation state transition invariants across bounded contexts.",
            ["shadow-domain", "shadow-test"],
            ["shadow-perf"],
            "shadow-domain",
        ),
        (
            "S51-5: Search relevance poor (BM25/hybrid RRF) -> shadow-search",
            "Search relevance poor with Indonesian slang on BM25 and hybrid RRF; tune NDCG@10 and retrieval ACL prefilter.",
            ["shadow-search", "shadow-db", "shadow-eval"],
            ["shadow-perf"],
            "shadow-search",
        ),
        (
            "S51-6: Realtime notifications disconnect -> shadow-realtime",
            "Realtime notifications disconnect on mobile clients; fix SSE Last-Event-ID resume and slow-consumer backpressure.",
            ["shadow-realtime", "shadow-auth", "shadow-concurrency", "shadow-observe"],
            ["shadow-perf"],
            "shadow-realtime",
        ),
        (
            "S51-7: Unsafe transitive dependency -> shadow-supplychain",
            "Audit unsafe transitive dependency, generate CycloneDX SBOM against lockfile, check typosquatting and SLSA provenance.",
            ["shadow-supplychain", "shadow-sec", "shadow-release"],
            ["shadow-perf"],
            "shadow-supplychain",
        ),
        (
            "S51-8: Database deadlock diagnosis -> shadow-debug",
            "Investigate production PostgreSQL database deadlock before tuning indexes.",
            ["shadow-debug", "shadow-data", "shadow-db"],
            ["shadow-perf"],
            "shadow-debug",
        ),
        (
            "S51-9: Architecture for new app -> shadow-architect (not shadow-ea)",
            "Design C4 architecture for a new application with domain invariants.",
            ["shadow-architect", "shadow-domain", "shadow-sec"],
            ["shadow-ea"],
            "shadow-architect",
        ),
        (
            "S51-10: Contract change request -> shadow-pmo (not shadow-refactor)",
            "Evaluate this client contract change request before touching code.",
            ["shadow-pmo"],
            ["shadow-refactor", "shadow-perf"],
            "shadow-pmo",
        ),
        (
            "NEG-1 (§5.3): Typo-only README edit skips heavy skills & antislop",
            "Typo-only README edit: fix spelling of 'installation'.",
            [],
            ["shadow-architect", "shadow-sec", "shadow-browser", "antislop"],
            "shadow-monarch",
        ),
        (
            "NEG-2 (§5.3): Pure formatting refactor skips shadow-domain & shadow-data",
            "Run a pure formatting refactor on src/helpers without changing domain or storage.",
            ["shadow-quality"],
            ["shadow-domain", "shadow-data", "shadow-refactor"],
            "shadow-quality",
        ),
        (
            "NEG-3 (§5.3): Redis vs queue semantics routes to shadow-concurrency, NOT shadow-ops",
            "Should we use Redis vs queue semantics for idempotent background job delivery?",
            ["shadow-concurrency"],
            ["shadow-ops", "shadow-realtime"],
            "shadow-concurrency",
        ),
        (
            "NEG-4 (§5.3): Price estimation for tender routes to shadow-presales, NOT shadow-supplychain",
            "We need price-estimation for tender RAB submission under Perpres 46.",
            ["shadow-presales"],
            ["shadow-supplychain", "shadow-ea"],
            "shadow-presales",
        ),
        (
            "NEG-5 (§5.3): Unauthorized prod access stops at permission boundary",
            "API returns 500 randomly; production data access required but not authorized.",
            ["shadow-debug"],
            ["shadow-perf"],
            "shadow-debug",
        ),
        (
            "PRECISION-1: Normal UI React feature coding auto-loads antislop & blocks shadow-perf",
            "Buat halaman dashboard React dan Tailwind dengan form login dan modal konfirmasi.",
            ["shadow-auth", "antislop"],
            ["shadow-perf", "shadow-presales", "shadow-grc"],
            None,
        ),
        (
            "PRECISION-2: Trivial factual question loads 0 companion skills & 0 references",
            "Apa itu HTTP status code 429?",
            [],
            ["shadow-perf", "shadow-api", "shadow-grc", "shadow-presales"],
            "shadow-monarch",
        ),
        (
            "INTENT-1: Code review enforces L0_READ_ONLY and blocks file modifications",
            "Please do a code review on the auth PR diff.",
            ["shadow-quality"],
            ["shadow-perf", "shadow-refactor"],
            None,
        ),
        (
            "INTENT-2: Unit test request excludes broad E2E (shadow-browser) and load testing (shadow-perf)",
            "Write unit tests with pytest for our discount helper.",
            ["shadow-test"],
            ["shadow-browser", "shadow-perf"],
            "shadow-test",
        ),
        (
            "INTENT-3: Debugging intent bounds to L1 local repro and blocks stress testing (shadow-perf)",
            "Diagnose this 500 error in local checkout API.",
            ["shadow-debug"],
            ["shadow-perf"],
            "shadow-debug",
        ),
        (
            "OFFICIAL-1: Greenfield project initialization loads shadow-bootstrap + OFFICIAL-FIRST-DEPENDENCY-POLICY.md",
            "Initialize a new React + Vite project using the official generator without writing boilerplate manually.",
            ["shadow-bootstrap"],
            ["shadow-perf"],
            "shadow-bootstrap",
        ),
        ("Bootstrap plain request", "Bootstrap a new project for an offline CLI.", ["shadow-bootstrap"], ["shadow-perf"], "shadow-bootstrap"),
        ("Bootstrap CSS existing project", "Adjust Bootstrap CSS spacing in existing project.", [], ["shadow-bootstrap"], None),
        (
            "OFFICIAL-2: ridhuan-sso SDK integration loads shadow-auth + OFFICIAL-FIRST-DEPENDENCY-POLICY.md",
            "Integrate existing ridhuan-sso (file:../sdk/sso-client) SDK into our backend app.",
            ["shadow-auth"],
            ["shadow-perf"],
            "shadow-auth",
        ),
        (
            "DOC-ENGINE-1: Multi-format GRC export with generator discovery routes shadow-doc + shadow-grc",
            "Audit ISO 27001 controls and export the GRC assessment report to docx and html using our document generator.",
            ["shadow-doc", "shadow-grc"],
            ["shadow-perf"],
            None,
        ),
        (
            "API-DISCOVERY-1: API documentation ownership routes to shadow-api",
            "Temukan source of truth dokumentasi API dan identifikasi generator yang dipakai.",
            ["shadow-api"],
            ["shadow-perf", "shadow-bootstrap"],
            "shadow-api",
        ),
        (
            "API-DISCOVERY-2: Generic source of truth question avoids API discovery",
            "What does source of truth mean?",
            [],
            ["shadow-api"],
            None,
        ),
        (
            "SCOPE-1: Unit tests mentioning excluded E2E and load checks stay in scope",
            "Write unit tests for the helper with pytest. Skip Playwright E2E and Pre-UAT k6 load tests.",
            ["shadow-test"],
            ["shadow-browser", "shadow-perf"],
            "shadow-test",
        ),
        (
            "SCOPE-2: Code review referencing performance reports stays read-only",
            "Review the code diff for the changes linked to the Pre-UAT k6 load test and Playwright E2E report.",
            ["shadow-quality"],
            ["shadow-browser", "shadow-perf"],
            "shadow-quality",
        ),
        (
            "SCOPE-2EN: Explicit endpoint review mentioning a forbidden load test",
            "Only review this API endpoint; do not run a load test",
            ["shadow-quality"], ["shadow-perf", "shadow-browser"], None,
        ),
        (
            "SCOPE-2ID: Review-only endpoint in Indonesian",
            "Hanya tinjau endpoint API ini, jangan jalankan load test",
            ["shadow-quality"], ["shadow-perf", "shadow-browser"], None,
        ),
        (
            "SCOPE-3: A backticked dollar-prefixed skill is an explicit selection",
            "Gunakan `$shadow-api` untuk audit ini.",
            ["shadow-api"],
            ["shadow-perf"],
            "shadow-api",
        ),
        (
            "SCOPE-4: URL path is not an explicit skill selection",
            "Check the literal URL /shadow-api/status in this note.",
            [],
            ["shadow-api"],
            "shadow-monarch",
        ),
        (
            "UI-CRAFT-1: Component + button loads antislop-human, modern-web-guidance & FRONTEND.md",
            "Tolong buatkan component card dan button primary sesuai theme aplikasi.",
            ["antislop", "antislop-ui", "antislop-human", "modern-web-guidance"],
            ["shadow-perf"],
            "shadow-monarch",
        ),
        (
            "UI-CRAFT-2: Indonesian dropdown/tabel component triggers UI bundle",
            "Buatkan komponen dropdown filter dan tabel transaksi.",
            ["antislop-human", "modern-web-guidance"],
            ["shadow-perf"],
            "shadow-monarch",
        ),
        (
            "UI-CRAFT-3: SVG mascot illustration routes to shadow-illustration",
            "Tolong buatkan ilustrasi SVG maskot onboarding untuk halaman welcome.",
            ["shadow-illustration"],
            ["shadow-perf"],
            "shadow-illustration",
        ),
        (
            "UI-CRAFT-4: Copywriting and code comments route antislop-copywriting & antislop-code",
            "Perbaiki copywriting headline CTA dan rapikan code comments di halaman checkout.",
            ["antislop-copywriting", "antislop-code"],
            ["shadow-perf"],
            "shadow-monarch",
        ),
        (
            "DEBUG-ID-1: Indonesian 'Kenapa...' production 500/timeout routes shadow-debug (never trivial)",
            "Kenapa API checkout kita sering timeout dan 500 di production?",
            ["shadow-debug"],
            ["shadow-perf"],
            "shadow-debug",
        ),
        (
            "QUOTE-1: Quoted user requirement is NOT stripped as log",
            'User bilang "buatkan endpoint REST API login dengan RBAC"',
            ["shadow-api", "shadow-auth"],
            ["shadow-perf"],
            "shadow-api",
        ),
        (
            "PERF-PREUAT-1: Explicit 'Buat script k6 load test Pre-UAT' routes shadow-perf",
            "Buat script k6 load test untuk Pre-UAT staging dari openapi.yaml.",
            ["shadow-perf", "shadow-api"],
            [],
            "shadow-perf",
        ),
        (
            "API-BRUNO-1: Bruno .bru update and Indonesian Express endpoint route shadow-api + shadow-observe",
            "Update koleksi Bruno orders.bru dan buat endpoint Express POST /orders dengan structured logger pino.",
            ["shadow-api", "shadow-observe"],
            ["shadow-perf"],
            "shadow-api",
        ),
        (
            "SEC-WEB-1: XSS/CSRF/CSP/CORS audit routes shadow-sec",
            "Audit celah XSS, CSRF, CSP, dan CORS pada aplikasi web ini.",
            ["shadow-sec"],
            ["shadow-perf"],
            "shadow-sec",
        ),
        (
            "REFACTOR-GEN-1: Normal service refactor routes shadow-refactor",
            "Refactor checkout service untuk memisahkan kalkulasi pajak.",
            ["shadow-refactor"],
            ["shadow-perf"],
            "shadow-refactor",
        ),
        (
            "AI-ENG-1: Production LLM tool-calling agent & MCP server routes shadow-ai-eng",
            "Build an MCP server and tool-calling agent with structured outputs and token streaming.",
            ["shadow-ai-eng"],
            ["shadow-perf", "shadow-eval"],
            "shadow-ai-eng",
        ),
        (
            "ILLUS-CANVAS-1: HTML5 Canvas / WebGL procedural art & Satori OG card routes shadow-illustration",
            "Buatkan ilustrasi canvas WebGL procedural visual dan generator OG card Satori.",
            ["shadow-illustration"],
            ["shadow-perf"],
            "shadow-illustration",
        ),
        (
            "VIDEO-REMOTION-1: Remotion programmatic product video & LUFS audio routes shadow-video",
            "Buat programmatic video dengan Remotion dan normalisasi LUFS loudness untuk rilis produk.",
            ["shadow-video"],
            ["shadow-perf"],
            "shadow-video",
        ),
        (
            "AUTH-PASSKEY-1: Passkeys WebAuthn & OpenFGA ReBAC routes shadow-auth",
            "Implementasikan login Passkeys WebAuthn FIDO2 dan authorization ReBAC memakai OpenFGA.",
            ["shadow-auth"],
            ["shadow-perf"],
            "shadow-auth",
        ),
        (
            "REALTIME-WEBRTC-1: WebRTC SFU & CRDT Yjs collaborative editing routes shadow-realtime",
            "Rancang collaborative editing memakai CRDT Yjs dan panggilan WebRTC STUN/TURN.",
            ["shadow-realtime"],
            ["shadow-perf"],
            "shadow-realtime",
        ),
        (
            "A11Y-I18N-1: i18n ICU MessageFormat & RTL layout routes shadow-accessibility",
            "Tambahkan dukungan i18n ICU MessageFormat dan RTL layout pada aplikasi web ini.",
            ["shadow-accessibility"],
            ["shadow-perf"],
            "shadow-accessibility",
        ),
        (
            "COMPAT-RFC-1: RFC 9745 Deprecation & RFC 8594 Sunset routes shadow-compat",
            "Add RFC 9745 Deprecation header, RFC 8594 Sunset header, and 410 Gone retirement for legacy route.",
            ["shadow-compat"],
            ["shadow-perf"],
            "shadow-compat",
        ),
        (
            "INTEGRATE-CB-1: Stripe webhook replay & circuit breaker reconciliation routes shadow-integrate",
            "Implement Stripe webhook replay check and provider inquiry reconciliation job with circuit breaker.",
            ["shadow-integrate"],
            ["shadow-perf"],
            "shadow-integrate",
        ),
        (
            "SUPPLY-COSIGN-1: SLSA v1.2 Cosign Sigstore & GitHub Actions SHA pinning routes shadow-supplychain",
            "Verify SLSA v1.2 provenance attestation using Cosign Sigstore and enforce GitHub Actions SHA pinning.",
            ["shadow-supplychain", "shadow-sec", "shadow-release"],
            ["shadow-perf"],
            "shadow-supplychain",
        ),
        (
            "DOMAIN-FSM-1: Finite state machine & maker-checker invariants route shadow-domain",
            "Model finite state machine transition table with maker-checker approval business invariants.",
            ["shadow-domain", "shadow-test"],
            ["shadow-perf"],
            "shadow-domain",
        ),
        (
            "RESILIENCE-BH-1: Bulkhead semaphore & graceful degradation route shadow-resilience",
            "Implement bulkhead semaphore isolation, stale-cache fallback, and graceful degradation for export jobs.",
            ["shadow-resilience"],
            ["shadow-perf"],
            "shadow-resilience",
        ),
        (
            "RELEASE-CANARY-1: Canary cohort bucketing & kill-switch rollback route shadow-release",
            "Design deterministic canary cohort bucketing with kill-switch flag and deployment rollback plan.",
            ["shadow-release"],
            ["shadow-perf"],
            "shadow-release",
        ),
        (
            "MAINTAIN-RCA-1: SEV1 triage & 5-Why RCA postmortem route shadow-maintain",
            "Run SEV1 incident triage and write a 5-Why RCA postmortem with regression hotfix checklist.",
            ["shadow-maintain"],
            ["shadow-perf"],
            "shadow-maintain",
        ),
        (
            "DB-POOL-1: PgBouncer transaction pooling & TimescaleDB sizing route shadow-db",
            "Configure PgBouncer transaction pooling and connection pool sizing for PostgreSQL and TimescaleDB.",
            ["shadow-db"],
            ["shadow-perf"],
            "shadow-db",
        ),
        (
            "DATA-CDC-1: Debezium CDC & online DDL CONCURRENTLY route shadow-data",
            "Set up Debezium CDC pipeline and online DDL with CONCURRENTLY index and NOT VALID constraint.",
            ["shadow-data"],
            ["shadow-perf"],
            "shadow-data",
        ),
        (
            "SEARCH-VEC-1: pgvector HNSW & Meilisearch hybrid search route shadow-search",
            "Build hybrid search with pgvector HNSW and Meilisearch for Indonesian catalog.",
            ["shadow-search", "shadow-db", "shadow-eval"],
            ["shadow-perf"],
            "shadow-search",
        ),
        (
            "BROWSER-VIS-1: Playwright visual regression & HAR trace route shadow-browser",
            "Add Playwright visual regression toHaveScreenshot and HAR recording trace for checkout.",
            ["shadow-browser"],
            ["shadow-perf"],
            "shadow-browser",
        ),
        (
            "GRC-OJK-1: DE vs OE banking PPJTI PADK OJK 1/2026 replacing SEOJK 21/2017 routes shadow-grc",
            "Audit Design Effectiveness vs Operating Effectiveness for banking PPJTI under POJK 11/2022 and PADK OJK 1/2026 replacing SEOJK 21/2017.",
            ["shadow-grc"],
            ["shadow-perf"],
            "shadow-grc",
        ),
        (
            "OPS-CLEANUP-1: Orphan MCP & leftover dev server audit routes shadow-ops (never shadow-perf)",
            "Cek proses MCP yatim dan matikan dev server sisa yang nyangkut tanpa menyentuh proyek lain.",
            ["shadow-ops"],
            ["shadow-perf"],
            "shadow-ops",
        ),
        (
            "OPS-CLEANUP-2: Port conflict & resource_cleanup routes shadow-ops (never shadow-perf)",
            "Run resource_cleanup audit to inspect port conflict and orphaned processes safely.",
            ["shadow-ops"],
            ["shadow-perf"],
            "shadow-ops",
        ),
        (
            "SEO-1: JSON-LD Schema.org, sitemap.xml, robots.txt & hreflang route shadow-seo",
            "Implement XSS-safe JSON-LD Schema.org, dynamic sitemap.xml, robots.txt, and reciprocal hreflang for our Next.js catalog.",
            ["shadow-seo"],
            ["shadow-perf", "shadow-illustration"],
            "shadow-seo",
        ),
        (
            "EMAIL-1: SPF/DKIM/DMARC, RFC 8058 List-Unsubscribe-Post & React Email on Mailpit route shadow-email",
            "Configure SPF, 2048-bit DKIM, DMARC alignment, RFC 8058 List-Unsubscribe-Post, and React Email templates tested on Mailpit.",
            ["shadow-email"],
            ["shadow-perf"],
            "shadow-email",
        ),
        (
            "ANALYTICS-1: PostHog event taxonomy, PII scrubbing & A/B SRM check route shadow-analytics (not shadow-observe)",
            "Design a typed PostHog event taxonomy tracking plan with PII scrubbing and A/B test Sample Ratio Mismatch check.",
            ["shadow-analytics"],
            ["shadow-perf", "shadow-observe"],
            "shadow-analytics",
        ),
        (
            "MWG-REACT-1: Async waterfalls, barrel imports & React.cache RSC optimization route modern-web-guidance",
            "Eliminate async waterfalls, remove barrel imports, and optimize RSC serialization with React.cache in Next.js.",
            ["modern-web-guidance"],
            ["shadow-perf"],
            "modern-web-guidance",
        ),
        (
            "DB-RLS-1: Supabase Postgres RLS (SELECT auth.uid()) & SECURITY DEFINER route shadow-db",
            "Optimize Supabase Postgres RLS policies using (SELECT auth.uid()), composite indexes, and hardened SECURITY DEFINER RPC.",
            ["shadow-db"],
            ["shadow-perf"],
            "shadow-db",
        ),
        (
            "DISAMBIG-ANALYTICS-OBS-1: OpenTelemetry tracing & pino logs stay on shadow-observe (never shadow-analytics)",
            "Set up OpenTelemetry distributed tracing, PromQL burn alerts, and structured pino logs for checkout service.",
            ["shadow-observe"],
            ["shadow-analytics", "shadow-perf"],
            "shadow-observe",
        ),
        (
            "SEO-MIGRATE-1: Crawl budget & redirect chain audit routes shadow-seo",
            "Audit crawl budget, faceted URL traps, and redirect chain loops before our domain migration SEO rollout.",
            ["shadow-seo"],
            ["shadow-perf"],
            "shadow-seo",
        ),
        (
            "EMAIL-RENDER-1: Outlook VML, Gmail 102KB clip & IP warm-up MTA-STS route shadow-email",
            "Fix Outlook VML button rendering, enforce Gmail 102KB clip limit, and plan IP warm-up with MTA-STS and TLS-RPT.",
            ["shadow-email"],
            ["shadow-perf"],
            "shadow-email",
        ),
        (
            "ANALYTICS-CUPED-1: CUPED variance reduction, power analysis & identity stitching route shadow-analytics",
            "Implement CUPED variance reduction, experiment power analysis, and cross-device identity stitching with logout reset.",
            ["shadow-analytics"],
            ["shadow-perf", "shadow-observe"],
            "shadow-analytics",
        ),
        (
            "SEO-CRUX-1: Search Console drop diagnosis, CrUX p75 & faceted navigation route shadow-seo",
            "Diagnose a Search Console traffic drop using CrUX p75 field data, faceted navigation rules, and keyword cannibalization checks.",
            ["shadow-seo"],
            ["shadow-perf"],
            "shadow-seo",
        ),
        (
            "EMAIL-INCIDENT-1: SMTP 250 missing in inbox, Postmaster Tools & header injection route shadow-email",
            "Investigate SMTP 250 OK missing in inbox via Postmaster Tools and block CRLF email header injection in Amazon SES outbox.",
            ["shadow-email"],
            ["shadow-perf"],
            "shadow-email",
        ),
        (
            "ANALYTICS-CAUSAL-1: Difference-in-Differences causal inference, mSPRT & delta method route shadow-analytics",
            "Design a Difference-in-Differences causal inference study alongside mSPRT sequential testing and delta method ratio metrics.",
            ["shadow-analytics"],
            ["shadow-perf", "shadow-observe"],
            "shadow-analytics",
        ),
    ]

    required_dr_keys = {
        "task_id",
        "intent",
        "primary_skill",
        "supporting_skills",
        "risk_review_skills",
        "activation_reason",
        "excluded_skills",
        "required_permissions",
        "prohibited_actions",
        "permission_policy",
        "user_input_policy",
        "subagent_policy",
    }

    for name, prompt, must_in, must_out, exp_primary in probes:
        routed = route_prompt(prompt)
        dr = routed.get("routing_decision", {})
        active = set(routed["companion_skills"]) | set(routed["always_on_ui_skills"])
        dr_active = ({dr.get("primary_skill")} if dr.get("primary_skill") != "shadow-monarch" else set()) | set(dr.get("supporting_skills", [])) | set(dr.get("risk_review_skills", []))
        combined_active = active | dr_active

        has_dr = required_dr_keys.issubset(dr.keys())
        only_valid = all(s in known_skills for s in combined_active if s)
        ok_in = all(s in combined_active for s in must_in)
        ok_out = all(s not in combined_active for s in must_out)
        ok_primary = True if exp_primary is None else (dr.get("primary_skill") == exp_primary)
        ok_trivial = True if (must_in or routed["always_on_ui_skills"]) else (len(routed["reference_modules"]) == 0)
        ok_neg5 = True
        if "NEG-5" in name:
            ok_neg5 = any("explicit_prod_read_approval_missing" in p for p in dr.get("required_permissions", []))
        ok_intent = True
        if "INTENT-1" in name:
            ok_intent = (
                dr.get("permission_policy", {}).get("intent_mode") == "code_review"
                and dr.get("permission_policy", {}).get("max_auto_level") == "L0_READ_ONLY"
                and "write_or_modify_source_files" in dr.get("prohibited_actions", [])
            )
        elif "INTENT-2" in name:
            ok_intent = dr.get("permission_policy", {}).get("intent_mode") == "unit_test" and dr.get("subagent_policy", {}).get("allow_level_upgrade") is False
        elif "INTENT-3" in name:
            ok_intent = dr.get("permission_policy", {}).get("intent_mode") == "debug" and dr.get("subagent_policy", {}).get("inherit_parent_scope") is True
        elif name.startswith("OFFICIAL-"):
            ok_intent = "OFFICIAL-FIRST-DEPENDENCY-POLICY.md" in routed["reference_modules"]
        elif name.startswith("SCOPE-2"):
            ok_intent = dr["permission_policy"]["max_auto_level"] == "L0_READ_ONLY" and "run_local_tests" not in dr["required_permissions"]

        input_policy = dr["user_input_policy"]
        load_list = set(routed["companion_skills"])
        recorded_skills = set(dr["supporting_skills"]) | set(dr["risk_review_skills"])
        if dr["primary_skill"] != "shadow-monarch":
            recorded_skills.add(dr["primary_skill"])
        ok_policy = input_policy["channel"] == "INTERACTIVE_IF_AVAILABLE" and input_policy["wait_before_dependent_work"] and not input_policy["repeat_resolved_questions"]
        ok_budget = load_list == recorded_skills and len(load_list) <= 4 and len(routed["reference_modules"]) <= 4

        results.append(
            {
                "probe": name,
                "passed": has_dr and only_valid and ok_in and ok_out and ok_primary and ok_trivial and ok_neg5 and ok_intent and ok_policy and ok_budget,
                "primary_skill": dr.get("primary_skill"),
                "supporting_skills": dr.get("supporting_skills"),
                "risk_review_skills": dr.get("risk_review_skills"),
                "routed_skills": sorted(combined_active),
                "routed_refs": routed["reference_modules"],
            }
        )

    passed = sum(1 for r in results if r["passed"])
    return {
        "tool": "skill_router.py",
        "total_probes": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "all_passed": passed == len(results),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Shadow Monarch Topic-Based Auto-Skill Router")
    parser.add_argument("--audit-descriptions", action="store_true")
    parser.add_argument("--route", default=None, help="Natural language prompt to route")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.audit_descriptions:
        res = audit_descriptions()
        print(json.dumps(res, indent=2))
        return 0 if res["all_passed"] else 1
    if args.route is not None:
        print(json.dumps(route_prompt(args.route), indent=2, ensure_ascii=False))
        return 0
    if args.self_test:
        res = run_self_test()
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0 if res["all_passed"] else 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
