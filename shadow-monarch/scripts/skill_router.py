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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shadow_input import run_checked_cli, strict_bool
from skill_retrieval import (
    Candidate, body_index, read_description, request_clauses, retrieve, retrieve_body, skill_index,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SKIP_ROOT_DIRS = {"evals", "mcp-servers", "reports", "docs", "scripts", "node_modules"}

DESCRIPTION_CHARACTER_LIMIT = 250
DESCRIPTION_CATALOG_LIMIT = 9000
USE_WHEN_RE = re.compile(r"\buse\s+(?:only\s+)?when\b", re.IGNORECASE)
CODE_REVIEW_RE = re.compile(
    r"\b(?:(?:only\s+review|hanya\s+(?:review|tinjau))\s+(?:(?:this|the)\s+)?(?:API|endpoint|webhook|handler|kode|code|diff|PR)\b|"
    r"code\s+review|PR\s+review|review\s+(?:(?:this|the)\s+)?(?:PR|code|diff|changes|kode|webhook(?:\s+handler)?|endpoint(?:\s+handler)?)|(?:audit|tinjau)\s+kode)\b",
    re.IGNORECASE,
)
READ_ONLY_SCOPE_RE = re.compile(
    r"(?:^\s*(?:read[- ]only\s+(?:inspection|review|audit)|inspeksi\s+baca\s+saja)\b|"
    r"\b(?:secara\s+read[- ]only|read[- ]only\s*\(\s*jangan\s+ubah\s+file|"
    r"from\s+(?:the\s+)?(?:existing\s+)?(?:source|config|configuration|logs)\s+only|"
    r"only\s+(?:inspect|review)\b[^\n]*\bread[- ]only)\b)",
    re.IGNORECASE,
)
SCOPE_DENIAL = r"\b(?:do\s+not|don't|never|without|jangan|tanpa|tidak\s+(?:menyetujui|boleh|perlu))\s+"
DENIAL_CLAUSE = r"(?:(?!\b(?:but|except|instead|tapi|kecuali|namun)\b)[^;\n.!?]){0,130}?"
LOAD_TEST_DENIAL_RE = re.compile(
    SCOPE_DENIAL + DENIAL_CLAUSE + r"\b(?:k6|(?:load|stress|spike|soak)\s+test(?:ing)?|load\s+(?:profile|scenario)|uji\s+beban|profil\s+beban|[/\$]?shadow-perf)\b",
    re.IGNORECASE,
)
BROWSER_DENIAL_RE = re.compile(
    SCOPE_DENIAL + DENIAL_CLAUSE + r"\b(?:launch|open|run|test|verify|use|enable|activate|aktifkan|jalankan|buka|gunakan|uji)\s+"
    r"(?:(?:a|the)\s+)?(?:browser|Playwright|Chrome|Chromium|Firefox|WebKit|peramban|(?:[/\$])?shadow-browser)\b",
    re.IGNORECASE,
)
OUTAGE_STATUS_RE = re.compile(
    r"^\s*(?:(?:urgent|help|darurat)\s*[:!,]?\s*|(?:our|the|layanan)\s+)?"
    r"(?:prod(?:uction)?|produksi)\s+(?:(?:is|sedang)\s+)?(?:down|outage|mati|lumpuh)\b"
    r"|\b(?:triage|investigate|mitigate|stabili[sz]e|respond\s+to|tangani|pulihkan)\s+(?:an?\s+|the\s+)?"
    r"(?:production\s+(?:(?:login|auth(?:entication)?|SSO)\s+)?(?:outage|incident)|"
    r"insiden\s+(?:(?:login|SSO|autentikasi)\s+)?produksi)\b",
    re.IGNORECASE,
)
PRODUCTION_CONTEXT_RE = re.compile(
    r"\b(?:prod(?:uction)?|produksi|live\s+(?:service|portal|site|users?|customers?)|"
    r"public\s+(?:portal|site)|portal\s+publik)\b", re.IGNORECASE,
)
INCIDENT_IMPACT_RE = re.compile(
    r"\b(?:outage|incident|unavailable|failing|fails?|failed|(?:cannot|can['’]t|unable\s+to)\s+(?:log\s+in|sign\s+in|access)|locked\s+out|blocked|stopped\s+working|"
    r"insiden|gagal|terhenti|terblokir|terkunci|tidak\s+bisa\s+(?:login|masuk|akses)|lumpuh|SEV[- ]?[1-4])\b", re.IGNORECASE,
)
INCIDENT_OPERATIONS_RE = re.compile(
    r"\b(?:incident\s+response|incident\s+command|on[- ]call\s+escalation|restore\s+(?:service|access)|"
    r"(?:lead|coordinate|run)\s+(?:an?\s+|the\s+)?(?:incident|triage|rollback|recovery)|"
    r"koordinasi\s+(?:insiden|pemulihan|rollback)|pulihkan\s+(?:layanan|akses)|eskalasi\s+on[- ]call|assess\s+(?:a\s+)?rollback|(?:prior|previous)\s+(?:stable\s+)?(?:build|artifact|release)|artefak\s+stabil\s+sebelumnya)\b",
    re.IGNORECASE,
)
OUTAGE_COPY_RE = re.compile(
    r"\b(?:copy|wording|headline|heading|microcopy|teks|judul)\b[^\n.]{0,55}"
    r"\b(?:outage|production\s+down|gangguan\s+produksi)\b"
    r"|\b(?:rewrite|edit|polish|perbaiki|ubah)\s+(?:that\s+|the\s+)?(?:wording|heading|headline|teks|judul)\b",
    re.IGNORECASE,
)
AUTH_CHANGE_REQUEST = re.compile(
    r"\b(?:design|implement|change|modify|rotate|rancang|ubah|tambah|rotasi)\b[^\n.!?]{0,45}"
    r"\b(?:JWT|JWKS|OAuth|OIDC|SSO|session|cookie|RBAC|login|auth(?:entication)?|autentikasi|sesi)\b",
    re.IGNORECASE,
)
NEGATED_OUTAGE_RE = re.compile(
    r"\b(?:no|without|tanpa|tidak\s+ada)\s+(?:an?\s+)?(?:production|prod|produksi)\s+(?:outage|incident|down|mati)\b",
    re.IGNORECASE,
)
QUOTED_LOG_RE = re.compile(
    r"```[\s\S]*?```|"
    r"(?:^|\n)[ \t]*~{3,}[^\n]*\n[\s\S]*?(?:\n[ \t]*~{3,}[ \t]*(?=\n|$)|\Z)|"
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
ARTIFACT_AUDIT_ACTION = r"(?:audit|verify|validate|scan|inspect|assess|check|review|cek|periksa|verifikasi|pindai|tinjau)"
ARTIFACT_INSTALL_ACTION = r"(?:install|register|activate|instal|pasang|aktifkan|(?:mcp|plugin)\s+add)"
ARTIFACT_AUDIT_ACTION_RE = re.compile(rf"\b{ARTIFACT_AUDIT_ACTION}\b", re.IGNORECASE)
ARTIFACT_INSTALL_ACTION_RE = re.compile(rf"\b{ARTIFACT_INSTALL_ACTION}\b", re.IGNORECASE)
NEGATED_ARTIFACT_ACTION_RE = re.compile(
    rf"\b(?:jangan|tidak\s+(?:perlu|usah)|stop\s+before|do\s+not|don't|no\s+need\s+to|skip|never)\s+"
    rf"(?:(?:lakukan|run|do)\s+)?(?:(?:a|an)\s+)?(?:{ARTIFACT_AUDIT_ACTION}|{ARTIFACT_INSTALL_ACTION})"
    rf"(?:\s+(?:or|and|atau|dan)\s+(?:{ARTIFACT_AUDIT_ACTION}|{ARTIFACT_INSTALL_ACTION}))*\b",
    re.IGNORECASE,
)
ARTIFACT_CLAUSE_SEPARATOR_RE = re.compile(r"\n+|[;.!?](?=\s|$)|\s+(?:but|tapi|tetapi)\s+", re.IGNORECASE)
NON_AUDIT_ARTIFACT_TASK_RE = re.compile(
    r"^\s*(?:(?:tolong|please|help\s+me|bantu(?:\s+saya)?)\s+)*(?:implement|build|create|write|update|enhance|fix|document|"
    r"buat(?:kan)?|tulis|perbaiki|tambah(?:kan)?|implementasi(?:kan)?|kembangkan|tingkatkan)\b",
    re.IGNORECASE,
)
EXTENSION_ARTIFACT_RE = re.compile(
    r"\b(?:skills?|plugins?|mcp(?:\s+servers?)?|agent\s+extensions?)\b",
    re.IGNORECASE,
)
EXTERNAL_ARTIFACT_RE = re.compile(
    r"\b(?:third[- ]party|pihak\s+ketiga|external|eksternal|download(?:s|ed)?|unduh(?:an)?|"
    r"(?:from|dari)\s+(?:GitHub|GitLab|Bitbucket|registry|marketplace|https?://))\b",
    re.IGNORECASE,
)
PRE_INSTALL_ARTIFACT_RE = re.compile(
    r"\b(?:(?:before|sebelum)\s+(?:install(?:ation|ing)?|instal(?:l|asi)?|diinstal|"
    r"dipasang|pasang|memasang|menginstal)|pre[- ]install(?:ation)?)\b",
    re.IGNORECASE,
)
DOCUMENT_DOWNLOAD_RE = re.compile(
    r"\b(?:download(?:s|ed)?|diunduh|unduh(?:an)?|di-download)\b",
    re.IGNORECASE,
)
DOCUMENT_SAFETY_TARGET_RE = re.compile(
    r"\b(?:pdf|markdown|html|referensi|(?:reference|research)\s+(?:file|document|paper))\b",
    re.IGNORECASE,
)
DOCUMENT_SAFETY_CONTEXT_RE = re.compile(
    r"\b(?:file|berkas|dokumen|document|keamanan|keaslian|malware|checksum|integrity|authenticity|signature|"
    r"security|safety|safe|aman|sebelum\s+dibuka|before\s+opening)\b",
    re.IGNORECASE,
)
ARTIFACT_AUDIT_HELPER_RE = re.compile(
    r"\b(?:with|using|use|pakai|gunakan)\s+[/\$]([a-z][a-z0-9-]+)(?![\w/-])",
    re.IGNORECASE,
)

DOCUMENT_AUDIT_PLAYBOOKS = ["shadow-doc/references/02-citations-reference-verifier-and-export-qa.md"]
EXTENSION_AUDIT_PLAYBOOK = "shadow-sec/references/09-third-party-download-and-install-audit.md"
EXTENSION_AUDIT_PLAYBOOKS = [
    EXTENSION_AUDIT_PLAYBOOK,
    "shadow-supplychain/references/04-slsa-v12-provenance-cosign-and-expiring-waivers.md",
]

# Ordered by domain specificity so primary ownership resolves cleanly before general helpers.
class _PostAwardSignal:
    """Detect requirement work after a tender or contract award, ignoring conditional future wins."""

    AWARD = re.compile(
        r"\b(?:(?:we\s+(?:just\s+|have\s+|recently\s+)?)?won\s+(?:[\w'.-]+\s+){0,4}?(?:tender|bid|contract|procurement)|"
        r"(?:menang(?:kan)?|memenangkan|dimenangkan)\s+(?:[\w'.-]+\s+){0,4}?tender|"
        r"tender\s+(?:[\w'.-]+\s+){0,3}?(?:sudah|telah)\s+(?:dimenangkan|menang|kami\s+menangkan)|"
        r"after\s+(?:the\s+)?(?:award|contract\s+signing)|pasca[- ]?(?:tender|kontrak|award)|"
        r"setelah\s+(?:menang|kontrak\s+(?:ditandatangani|diteken)|tender\s+dimenangkan)|"
        r"contract\s+(?:was|is|has\s+been)\s+signed|kontrak\s+(?:sudah|telah)\s+(?:ditandatangani|diteken))\b",
        re.IGNORECASE,
    )
    CONDITIONAL = re.compile(
        r"\b(?:kalau|jika|apabila|bila|seandainya|supaya|agar|biar|untuk|demi|if|whether|to)\s+(?:\w+\s+){0,2}?"
        r"(?:menang|memenangkan|win|won)\b",
        re.IGNORECASE,
    )

    def search(self, text: str) -> re.Match[str] | None:
        if self.CONDITIONAL.search(text):
            return None
        return self.AWARD.search(text)


POST_AWARD_RE = _PostAwardSignal()

ROUTING_RULES: list[dict[str, Any]] = [
    {
        "skill": "handoff",
        "layer": "task",
        "references": ["TOKEN-EFFICIENCY.md"],
        "include": re.compile(
            r"\b(?:lanjut\s+handoff|load\s+handoff|merge\s+handoff|save\s+handoff|session\s+handoff|simpan\s+handoff|"
            r"(?:tolong|minta|lakukan)\s+handoff|context\s+(?:udah|sudah|full|penuh|compaction)\s*(?:penuh)?|simpan\s+sesi)\b",
            re.IGNORECASE,
        ),
        "exclude": re.compile(
            r"\b(?:BAST|serah\s+terima\s+klien|admin\s+manual|operator\s+manual|training\s+of\s+trainers|client\s+handover)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-monarch",
        "layer": "task",
        "references": ["CROSS-SKILL-OWNERSHIP-MATRIX.md"],
        "include": re.compile(
            r"\b(?:bagi|petakan)\s+kepemilikan\b[^\n.!?]{0,30}\blintas\b|"
            r"\b(?:assign|coordinate)\s+(?:task\s+)?ownership\s+across\s+(?:specialists|domains|workstreams)\b",
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
            r"coexistence\s+cost|EOL\s+runtime|legacy\s+modernization|dual[- ]run\s+TCO|full\s+rewrite\s+vs|monolith\s+modernization|"
            r"\b(?:inherited|legacy)\b[^\n.!?]{0,45}\b(?:hidden|undocumented)\s+(?:business\s+)?rules?\b|(?:inventarisasi|petakan)\s+aturan\s+(?:tersembunyi|sistem\s+lama))\b",
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
            r"git\s+bisect|repro\s+bug|race\s+(?:condition|symptom)|production\s+bug|(?:temukan|selidiki|cari)\s+(?:mengapa|kenapa|penyebab)\b[^\n.!?]{0,70}\b(?:dua\s+kali|gagal|galat|error|bug)|"
            r"(?:ada|fix|perbaiki)\s+bug\b|sering\s+timeout|tidak\s+(?:mengirim|berfungsi|bekerja)\s+\w+|"
            r"\b(?:isolate|trace\s+(?:why|where)|telusuri)\b[^\n.!?]{0,42}\b(?:diverg\w*|root\s+cause|penyebab)\b)\b",
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
            r"branch[- ]by[- ]abstraction|semantic\s+equivalence|incremental\s+refactor|behavior[- ]preserving|extract\s+seam|safe\s+refactor|"
            r"\b(?:pecah|ekstrak)\b[^\n.!?]{0,68}\bfungsi\b[^\n.!?]{0,35}\btanpa\s+mengubah\b)\b",
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
            r"retrieval\s+ACL\s+prefilter|tenant\s+ACL\s+pre[- ]filter|searchDocumentsForTenant|Meilisearch|Typesense|OpenSearch|pgvector|Qdrant|HNSW|"
            r"typo[- ]tolerant\s+(?:search|candidate|ranking)|(?:typo|salah\s+eja)\b[^\n.!?]{0,35}\bperingkat\b)\b",
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
            r"collaborative\s+edit(?:ing|or)|"
            r"\b(?:revoke|cabut)\b[^\n.!?]{0,45}\b(?:channel|kanal)\s+(?:subscription|access|langganan|akses)\b|mid[- ]session\s+revocation)\b",
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
            r"\b(?:UU\s*PDP|UU\s*(?:No\.?\s*)?27\s*(?:Tahun\s*)?2022|GDPR|DPIA|ROPA|DSAR|penghapusan\s+(?:catatan|data)\s+pengguna|hak\s+(?:subjek|penghapusan)\s+data|data\s+(?:spesifik|pribadi)|cross[- ]border\s+transfer|PII\s+(?:redaction|masking)|NIK\s+log|kebocoran\s+data|erasure[-_]tombstones|legal[-_ ]?hold|3\s*x\s*24|"
            r"\b(?:obtain|access)\s+and\s+correct\s+(?:(?:their|personal)\s+)?records?\b|\b(?:subject|rights?)\s+request\b|hak\s+(?:akses|koreksi)\s+data\s+pribadi)\b",
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
            r"\b(?:OWASP\s*MASVS|PrivacyInfo\.xcprivacy|ITMS-91053|Play\s+Integrity|target\s*SDK(?:Version)?|AndroidManifest|App\s+Store\s+Connect|Play\s+Console|\.aab|Universal\s+Links|App\s+Links|assetlinks\.json|apple-app-site-association|Flutter\s+release|React\s+Native\s+signing)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-perf",
        "layer": "risk",
        "references": ["sub-OBSERVABILITY-PROFILING.md", "sub-QA-AUTOMATION.md"],
        "include": re.compile(
            r"\b(?:pre[- ]UAT\s+(?:perf|load)|uji\s+penerimaan\s+kinerja|(?:rancang|jalankan|siapkan)\b[^\n.!?]{0,24}\bskenario\s+beban|k6\s+load|load\s+test|stress\s+test|spike\s+test|EXPLAIN\s+ANALYZE|query\s+profiling|bottleneck\s+audit|"
            r"\b(?:staging\s+acceptance|pre[- ]UAT)\b[^\n.!?]{0,95}\b(?:arrival[- ]rate|virtual[- ]users?|load\s+(?:profile|scenario))\b)\b",
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
            r"(?:buat(?:kan)?|build|create)\s+(?:an?\s+)?endpoint|endpoint\s+CRUD|CRUD\s+(?:API|endpoint)|"
            r"endpoint\s+(?:Express|FastAPI|NestJS|Hono|Laravel|Go|REST)|\b(?:GET|POST|PUT|PATCH|DELETE)\s+/[a-z0-9_/:.-]+|"
            r"OpenAPI|openapi\.yaml|Swagger|Postman|Bruno|\.bru\b|Scalar|Redoc|Insomnia|TypeSpec|"
            r"HTTP\s+(?:route|controller)|GraphQL\s+(?:schema|contract)|AsyncAPI|gRPC\s+contract|RFC\s*9457|"
            r"tRPC|multipart\s+upload|presigned\s+URL|tus\s+resumable|S3\s+multipart|cursor\s+pagination|"
            r"gRPC\s+(?:interface|service|endpoint)|protobuf\s+(?:messages?|schemas?))\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-auth",
        "layer": "task",
        "references": ["SECURITY.md", "BACKEND.md"],
        "include": re.compile(
            r"\b(?:login|authentication|AuthN|AuthZ|RBAC|ABAC|ReBAC|OpenFGA|SpiceDB|Zanzibar|Passkeys?|WebAuthn|FIDO2|"
            r"MFA|TOTP|OAuth2?|OIDC|SSO|mTLS|DPoP|API\s+key\s+(?:lifecycle|rotation)|JWT\s+(?:refresh|signing\s+keys?)|rotat\w*\s+(?:JWT|JWKS)|session\s+rotation|"
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
            r"read[- ]only\s+query|MVCC\s+bloat|query\s+planner|slow\s+query|query\s+[^\n]{0,35}\b(?:lambat|slow|EXPLAIN)|N\+1|SELECT\s+\*\s+FROM|"
            r"Prisma\s+(?:query|N\+1|backend|schema)|ETL\s+dari\s+SQLite\s+ke\s+PostgreSQL|database\s+deadlock|"
            r"PgBouncer|transaction\s+pooling|SQLite\s+WAL|MongoDB|TimescaleDB|ClickHouse|connection\s+pool\s+sizing|"
            r"Row[- ]Level\s+Security|\bRLS\b\s+(?:policy|policies|index)|auth\.uid\(\)|SECURITY\s+DEFINER|Supabase\s+(?:Postgres|RLS|index)|"
            r"(?:partial|covering|composite)\s+index(?:es)?|indeks\s+(?:parsial|penutup|gabungan))\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-data",
        "layer": "task",
        "references": ["DATABASE.md", "sub-DATA-STORES.md"],
        "include": re.compile(
            r"\b(?:database\s+migration|migrasi\s+(?:database|skema|DB)|ETL\s+dari\s+SQLite\s+ke\s+PostgreSQL|Expand[- ]Contract|zero[- ]downtime\s+migration|(?:migrat\w*|migrasi)\s+column\s+[^\n.]{1,45}\bNOT\s+NULL|backfill|"
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
            r"\b(?:TanStack\s+Query|SWR|Redis\s+cach(?:e|es|ing)|cache\s+stampede|singleflight|request\s+coalescing|Bloom\s+filter|"
            r"negative\s+cach(?:e|ing)|CDN\s+cach(?:e|ing)|Surrogate-Key|ETag\s+cach|optimistic\s+UI|Idempotency[- ]Key|"
            r"stale[- ]while[- ]revalidate|cache\s+coherency|"
            r"\b(?:ETag|304)\b[^\n.!?]{0,55}\brevalidat\w*)\b",
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
            r"third[- ]party\s+API\s+(?:retry|timeout|integration)|WhatsApp\s+gateway|SMTP|emails?\s+duplicated|"
            r"(?:payment|refund)\s+providers?|penyedia\s+(?:pembayaran|refund)|vendor\s+refund\s+(?:status|identifiers?))\b",
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
            r"Outlook\s+VML|Gmail\s+102\s*KB|IP\s+warm[- ]?up|OTP\s+(?:mail|email)\b[^\n.]{0,30}\bspam|Mailpit|Resend|Postmark|Amazon\s+SES|SendGrid|"
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
            r"sequential\s+testing|assignment\s+vs\s+exposure|switchback\s+experiment|"
            r"minimum\s+detectable\s+effect|\bunit\s+(?:of\s+)?randomi[sz]ation\b|unit\s+randomisasi)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-sec",
        "layer": "risk",
        "references": ["SECURITY.md", "SECOPS-PENTEST.md"],
        "include": re.compile(
            r"\b(?:STRIDE|threat\s+model|model\s+ancaman|batas\s+kepercayaan|OWASP\s*ASVS|NIST\s*SSDF|VAPT|SAST|DAST|secret\s+scan|SQL\s+injection|SQLi|"
            r"IDOR|SSRF|XSS|CSRF|CSP|CSP\s+nonce|HSTS|CORS|security\s+headers|path\s+traversal|169\.254\.169\.254|"
            r"BOLA|broken\s+access|clickjacking|kerentanan|celah\s+keamanan|audit\s+keamanan|transitive\s+dependency|attack[- ]surface|"
            r"(?:review|audit)\s+defensif\b[^\n.!?]{0,35}\b(?:lampiran|berkas|unduhan)\b|directory\s+allowlist\b[^\n.!?]{0,30}\battachments?\b)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-browser",
        "layer": "risk",
        "references": ["FRONTEND.md", "sub-QA-AUTOMATION.md"],
        "include": re.compile(
            r"\b(?:Playwright|browser\s+E2E|(?:coba|uji|buka)\b[^\n.!?]{0,32}\b(?:di\s+peramban|browser\s+nyata)|375px|mobile\s+viewport\s+overflow|console\s+error\s+in\s+browser|UI\s+click[- ]through|"
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
            r"docs\s+GIF|LUFS\s+loudness|"
            r"\b(?:captioned|narrated)\b[^\n.!?]{0,30}\b(?:walkthrough|footage|screencast|demo)\b|sinkronkan\s+narasi\s+video)\b",
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
            r"procedural\s+(?:art|visual)|OG\s+card|Satori|spritesheet|sprite\s+sheets?|pixel[- ]art\s+(?:VFX|effects?|animations?)|"
            r"stack\s+diagram|diagram\s+(?:arsitektur\s+tech\s+stack|tech\s+stack)|favicon\s+(?:set|pack)|PWA\s+icons?|"
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
            r"content-visibility|fetchpriority|core\s+web\s+vitals|native\s+<dialog>|(?:fix|optimi[sz]e|improve)\s+(?:the\s+)?(?:LCP|INP|CLS)|"
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
            r"keyboard\s+navigation|tab\s+order|focus\s+order|accessible\s+names?|kontras\s+warna|color\s+contrast|aksesibilitas|lansia\s+contrast|"
            r"i18n|internationalization|RTL\s+layout|ICU\s+MessageFormat|pseudo[- ]localization)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-design",
        "layer": "task",
        "references": ["DESIGN.md", "UI_UX_Design_Knowledge_Base_v2_Art_Direction_Web_Mobile_ID.md"],
        "include": re.compile(
            r"\b(?:design\s+systems?|(?:design|rancang)\s+(?:a\s+|the\s+)?(?:pricing\s+page|hero\s+section)|wireframes?|UI/UX|user\s+flows?|thumb\s+zone|design\s+tokens?|9[- ]state\s+(?:component|machine)|"
            r"visual\s+(?:hierarchy|refinement)|hierarki\s+visual|competing\s+emphasis|anti[- ]slop\s+review|"
            r"Human[- ]AI\s+(?:UX|HITL)|komponen\s+UI|antarmuka|interview-script|task[- ]usability)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-test",
        "layer": "task",
        "references": ["TESTING.md", "sub-QA-AUTOMATION.md"],
        "include": re.compile(
            r"\b(?:unit\s+tests?|integration\s+tests?|contract\s+tests?|(?:tulis|tambahkan|buat)\s+(?:pengujian|tes\s+unit|uji\s+regresi)|(?:deterministic|flaky)\s+(?:test\s+)?(?:harness|assertion)|(?:fixed\s+pause|event\s+wait)\b[^\n.!?]{0,50}\btest\s+harness|(?:writes?|creates?|adds?|tulis|buat)\b[^\n.!?]{0,38}\bPlaywright\b[^\n.!?]{0,24}\btests?|Vitest|Jest|Pytest|Pest|PHPUnit|JUnit|xUnit|regression\s+test|property[- ]based\s+test|mutation\s+test|characterization\s+test)\b",
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
            r"pure\s+formatting\s+refactor|formatting[- ]only|"
            r"import\s+boundar(?:y|ies)|(?:larang|aturan|gagalkan)\b[^\n.!?]{0,60}\bimpor\b[^\n.!?]{0,75}\b(?:domain|infrastruktur|CI)\b)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-git",
        "layer": "task",
        "references": ["DEVOPS.md"],
        "include": re.compile(
            r"\b(?:git\s+merge-tree|merge\s+conflict|git\s+worktree|sync\s+branch|pull\s+branch|branching\s+strategy|(?:compare|bandingkan)\s+(?:(?:our|the|dua)\s+)?(?:release\s+branches|cabang)|common\s+base\s+.*\bconflict|"
            r"squash\b[^\n.!?]{0,40}\b(?:branch|cabang|commit)\b|(?:patch|commit)\b[^\n.!?]{0,33}\balready\s+(?:in|on)\s+upstream)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-doc",
        "layer": "task",
        "references": ["DOCS-PIPELINE.md", "sub-SPECS-DOCX-CODE.md"],
        "include": re.compile(
            r"\b(?:document\s+generator|document\s+engine|doc_orchestrator|build_doc\.py|(?:regenerasi|regenerate)\s+(?:output\s+)?(?:dokumen|document|SRS\s+docx|PRD\s+docx)|export\s+(?:to\s+)?(?:docx|pdf|html|xlsx)|render\s+(?:handover|grc|presales|pmo|architecture)\s+(?:report|document|proposal)|build-manifest|\.docx|\.xlsx|Canonical\s+AST|generate\s+document|SRS\s+doc|SDD\s+doc|reference_verifier)\b",
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
        "exclude": re.compile(
            r"\b(?:KAK|tender|RAB|HPS|paid\s+CR|decompose\s+(?:the\s+)?(?:approved\s+)?(?:PRD|SRS|BRD)\s+into|(?:pecah|turunkan)\s+kebutuhan\s+(?:ke|jadi|menjadi)\s+backlog)\b",
            re.IGNORECASE,
        ),
        # After an award, requirement work belongs to discovery even when the tender is mentioned.
        "exclude_unless": POST_AWARD_RE,
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
        "include": re.compile(
            r"\b(?:epics?|user\s+stor(?:y|ies)|sprint\s+tasks?|DoR|DoD|task\s+breakdown|vertical\s+slic(?:e|ing)|"
            r"sprint\s+planning|story\s+decomposition|(?:pecah|turunkan)\s+kebutuhan\s+(?:ke|jadi|menjadi)\s+backlog|dependency\s+graph|(?:susun|buat|urai)\s+(?:rencana\s+)?(?:backlog|sprint)|pecah\s+(?:kebutuhan|fitur)\b[^\n.!?]{0,35}\b(?:cerita|tugas)|bagi\s+(?:pekerjaan|fitur)\s+(?:menjadi|ke)\s+paket\s+(?:dua\s+mingguan|sprint))\b",
            re.IGNORECASE,
        ),
        "exclude": re.compile(r"\b(?:paid\s+CR|monte\s+carlo|EVM|CPI|SPI)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-bootstrap",
        "layer": "task",
        "references": ["OFFICIAL-FIRST-DEPENDENCY-POLICY.md", "CORE.md", "DEVOPS.md"],
        "include": re.compile(
            r"\b(?:scaffold\s+new\s+project|scaffold\s+(?:a\s+)?(?:new\s+|greenfield\s+)?(?:(?:HTTP|static|Node|Python|Go|Rust|CLI)\s+)?(?:service|CLI|site|library|worker|app)|"
            r"greenfield\s+(?:(?:HTTP|static|CLI|worker)\s+)?(?:project|service|site|app|CLI)|preview_scaffold|"
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
            r"tim\s+QA\s+melaporkan|Requirement\s+Traceability\s+Matrix|RTM|client\s+sign[- ]off|"
            r"\bperwakilan\b[^\n.!?]{0,27}\bpengguna\b[^\n.!?]{0,32}\bstaging\b)\b",
            re.IGNORECASE,
        ),
    },
    {
        "skill": "shadow-release",
        "layer": "risk",
        "references": ["DEVOPS.md", "CLOUD-SRE.md"],
        "include": re.compile(
            r"\b(?:production\s+(?:release|deploy)|SemVer|changelog|rollback\s+runbook|kriteria\s+rollback\s+aman|feature\s+flag\s+rollout|"
            r"kill[- ]switch\s+(?:flag|feature\s+flag)|canary\s+cohort|pre[- ]flight\s+release|release\s+checklist|runbook\s+rilis|(?:promosi|promosikan)\s+versi\b[^\n.!?]{0,35}\bproduksi|deployment\s+rollback|roll\s+forward\s+vs\s+rollback|"
            r"\b(?:promote|promotion)\b[^\n.!?]{0,55}\bartifact\b[^\n.!?]{0,45}\b(?:staging|production)\b|go\s*[/ -]\s*no[- ]go\s+release)\b",
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
            r"consumer[- ]driven\s+contract|tolerant\s+reader|API\s+versioning|"
            r"\b(?:breaks?|breaking|merusak)\b[^\n.!?]{0,30}\b(?:existing|older|lama)\b[^\n.!?]{0,36}\b(?:clients?|consumers?|klien)\b|change\s+compatibility\s+window)\b",
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
            r"resource_cleanup|bounded_exec|watchdog|anti[- ]stuck|(?:script|command|idle)\s+timeout|SSH\s+stuck|port\s+conflict|bersihkan\s+proses|"
            r"Terraform\s+state|state\s+Terraform|reverse[- ]proxy\s+(?:TLS|configuration)|configure\b[^\n.!?]{0,28}\breverse[- ]proxy\b|Helm\s+(?:deployment|manifest|chart))\b",
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
            r"graceful\s+degradation|feature\s+shedding|load\s+shedding|stale[- ]cache\s+fallback|business\s+continuity|fault\s+injection|"
            r"(?:rate[- ]limited|bounded)\s+(?:DLQ\s+)?replay|(?:latihan|simulasi)\s+staging\b[^\n.!?]{0,55}\b(?:laju|replay)\b)\b",
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
        "include": re.compile(r"\b(?:latest\s+(?:library|framework|SDK)\s+docs|Context7|breaking\s+API\s+in\s+v\d+|Prisma\s+v?\d+[^\n.]{1,40}(?:syntax|sintaks))\b", re.IGNORECASE),
    },
]

# Contextual co-activation bundles for §5.1 multi-skill ownership pairs without forcing false positives.
CO_ACTIVATION_MAP: dict[str, dict[str, list[str]]] = {
    "shadow-debug": {"supporting": ["shadow-test"], "risk": []},
    "shadow-refactor": {"supporting": ["shadow-test"], "risk": ["shadow-compat"]},
    "shadow-concurrency": {"supporting": ["shadow-test"], "risk": []},
    "shadow-domain": {"supporting": ["shadow-test"], "risk": []},
    "shadow-search": {"supporting": ["shadow-db"], "risk": []},
    "shadow-realtime": {"supporting": ["shadow-auth", "shadow-observe"], "risk": []},
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
UI_STRONG_SIGNAL_RE = re.compile(
    r"\b(?:UI|frontend|landing\s+page|CSS|Tailwind|React|Next\.js|Vue|Svelte|Angular|shadcn|"
    r"component|komponen|dropdown|dialog|drawer|tabs|sidebar|badge|toast|popover|tooltip|"
    r"accordion|theme|styling|modal|navbar|dashboard|tombol|button|layout|mobile\s+responsive|data\s+table)\b",
    re.IGNORECASE,
)
NON_UI_HOMOGRAPH_RE = re.compile(
    r"\b(?:"
    r"(?:HTTP|request|response|email|auth(?:orization)?|security|CORS|cache|deprecation|sunset|custom|MIME)\s+headers?|"
    r"headers?\s+(?:injection|Authorization|X-[A-Za-z0-9-]+|validation|Cache-Control|Surrogate-Key|ETag|"
    r"Content-[A-Za-z-]+|CORS|HTTP|HSTS|CSP|Set-Cookie|Vary|Location)|"
    r"(?:credit|debit|payment|gift|smart|id|sim|loyalty|business)\s+cards?|"
    r"(?:validasi|validate|validat\w*|sanitiz\w*|untrusted|client|user|API|DTO|Zod|schema|malformed|invalid|raw|prompt)\s+inputs?|"
    r"inputs?\s+(?:validation|Zod|schema|DTO|sanitiz\w*)|"
    r"multipart(?:\s*/\s*|\s+)form[- ]data|form[- ]urlencoded|"
    r"SELECT\s+(?:\*|[a-z0-9_.,\s]{1,40})\s+FROM\b|"
    r"(?:orders|users|products|invoices|payments|audit|logs|database|SQL|Postgres|PostgreSQL|MySQL|SQLite)\s+tables?|"
    r"tables?\s+(?:index|lock|migration|schema|bloat|partition|column)|"
    r"SEO\s+halaman|halaman\s+[^\n]{0,40}\b(?:SEO|JSON-LD|sitemap\.xml|robots\.txt|canonical|hreflang)|"
    r"(?:SEO|JSON-LD|sitemap(?:\.xml)?|robots\.txt|canonical|hreflang|Search\s+Console)\b[^\n]{0,80}\b(?:halaman|pages?)\b|"
    r"(?:halaman|pages?)\s+(?:[\w-]+\s+){0,3}?(?:tidak\s+|belum\s+|not\s+)?(?:terindeks|diindeks|indexed|crawled|dirayapi)|"
    r"(?:frontend|front-end|UI)\s+(?:package|repo(?:sitory)?|workspace|monorepo|build|bundle|pipeline|CI|"
    r"dependenc(?:y|ies)|deps|lockfile|container|image|Dockerfile|deploy(?:ment)?)"
    r")\b",
    re.IGNORECASE,
)
NON_UI_CONTEXT_RE = re.compile(
    r"\b(?:PostgreSQL|Postgres|MySQL|SQLite|SQL\s+query|CTE|EXPLAIN\s+ANALYZE|PgBouncer|"
    r"MVCC\s+bloat|database\s+schema|RLS\s+polic(?:y|ies)|Prisma\s+(?:query|N\+1|backend)|N\+1|"
    r"CLI|command[- ]line|terminal|stdin|stdout|stderr|compiler|"
    r"ESLint|tsc|typecheck|type[- ]check|lint(?:er|ing)?|Prettier|Ruff|mypy|CI\s+gate)\b",
    re.IGNORECASE,
)
COPYWRITING_RE = re.compile(
    r"\b(?:copywriting|microcopy|headline|CTA|call[- ]to[- ]action|pesan\s+error|UX\s+writing|product\s+prose)\b",
    re.IGNORECASE,
)
# Mail authentication and deliverability work is not UI copy, even when it mentions a newsletter headline.
EMAIL_DELIVERABILITY_RE = re.compile(
    r"\b(?:SPF|DKIM|DMARC|MTA-STS|BIMI|spam\s+folder|folder\s+spam|masuk\s+spam|deliverability|bounce[sd]?|"
    r"Postmaster|sender\s+reputation|reputasi\s+pengirim)\b",
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
TRIVIAL_FACT_RE = re.compile(
    r"^\s*(?:apa\s+itu|apa\s+bedanya|bedanya|what\s+is|difference\s+between|jelaskan\s+singkat|berapa|bagi\s+benchmark|knp|kenapa)\b",
    re.IGNORECASE,
)
# A question about a specific library version or code identifier needs version-accurate docs.
VERSIONED_API_RE = re.compile(
    r"\b[A-Za-z][\w.+-]*\s+v?\d+\.\d+(?:\.\d+)?\b|\bv\d+(?:\.\d+)*\b|`[^`\n]+`|@\d+\.\d+",
)
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
    """Check the local frontmatter budget. Hosts apply their own listing limits."""
    directories = sorted(
        path for path in repo_root.iterdir()
        if path.is_dir() and not path.name.startswith(".") and path.name not in SKIP_ROOT_DIRS
    )
    missing: list[str] = []
    missing_trigger: list[str] = []
    lengths: dict[str, int] = {}
    for directory in directories:
        metadata = directory / "SKILL.md"
        description = read_description(metadata) if metadata.is_file() else None
        if description is None:
            missing.append(directory.name)
            continue
        if not USE_WHEN_RE.search(description):
            missing_trigger.append(directory.name)
        lengths[directory.name] = len(description)

    total_chars = sum(lengths.values())
    oversized = [
        {"skill": skill, "length": size}
        for skill, size in lengths.items() if size > DESCRIPTION_CHARACTER_LIMIT
    ]
    return {
        "total_skills": len(directories),
        "missing_frontmatter": missing,
        "missing_use_when_trigger": missing_trigger,
        "oversized_descriptions_gt_500": [
            row for row in oversized if row["length"] > 500
        ],
        "oversized_descriptions": oversized,
        "description_character_limit": DESCRIPTION_CHARACTER_LIMIT,
        "catalog_character_limit": DESCRIPTION_CATALOG_LIMIT,
        "total_description_characters": total_chars,
        "longest_description_characters": max(lengths.values(), default=0),
        "all_passed": bool(directories) and not (missing or missing_trigger or oversized)
                      and total_chars <= DESCRIPTION_CATALOG_LIMIT,
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


def _artifact_audit_owners(prompt: str) -> tuple[str, ...]:
    if NON_AUDIT_ARTIFACT_TASK_RE.match(prompt):
        return ()
    has_document_audit = False
    for clause in ARTIFACT_CLAUSE_SEPARATOR_RE.split(prompt):
        active = NEGATED_ARTIFACT_ACTION_RE.sub(" ", clause)
        audit_requested = ARTIFACT_AUDIT_ACTION_RE.search(active)
        if (
            (audit_requested or ARTIFACT_INSTALL_ACTION_RE.search(active))
            and EXTENSION_ARTIFACT_RE.search(active)
            and (EXTERNAL_ARTIFACT_RE.search(active) or PRE_INSTALL_ARTIFACT_RE.search(active))
        ):
            return ("shadow-sec", "shadow-supplychain")
        if (
            audit_requested
            and DOCUMENT_DOWNLOAD_RE.search(active)
            and DOCUMENT_SAFETY_TARGET_RE.search(active)
            and DOCUMENT_SAFETY_CONTEXT_RE.search(active)
        ):
            has_document_audit = True
    if (
        EXTENSION_ARTIFACT_RE.search(prompt) and EXTERNAL_ARTIFACT_RE.search(prompt)
        and re.search(SCOPE_DENIAL + DENIAL_CLAUSE + r"\b(?:install|activate|pasang|aktifkan)\b", prompt, re.IGNORECASE)
        and re.search(r"\b(?:review|inspect|audit|tinjau|periksa)\b[^;\n.!?]{0,30}\bmanifest\b", prompt, re.IGNORECASE)
    ):
        return ("shadow-sec", "shadow-supplychain")
    return ("shadow-doc",) if has_document_audit else ()


PLAYBOOK_LINK_RE = re.compile(r"\[[^\]]+\]\((references/[^)#\s]+\.md)\)")
STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "when", "only", "use", "using",
    "yang", "dan", "untuk", "dengan", "dari", "pada", "atau", "tolong", "bantu", "buat", "buatkan",
    "kita", "kami", "agar", "supaya", "lebih", "tidak", "jangan", "bisa", "juga", "saja", "apa",
}


def _tokenize_keywords(text: str) -> set[str]:
    return {
        tok
        for tok in re.findall(r"[a-z0-9]{3,}", text.lower())
        if tok not in STOPWORDS
    }


def _recommend_skill_playbooks(
    prompt: str,
    companion_skills: list[str],
    primary_skill: str,
    repo_root: Path = REPO_ROOT,
    max_total: int = 4,
) -> list[str]:
    """2-Step Progressive Loading helper: select 1-2 matching references/*.md playbooks from loaded skills' Reference Guides."""
    if not companion_skills:
        return []
    prompt_tokens = _tokenize_keywords(prompt)
    selected: list[str] = []
    seen: set[str] = set()

    for skill in companion_skills:
        if len(selected) >= max_total:
            break
        skill_md = repo_root / skill / "SKILL.md"
        if not skill_md.is_file():
            continue
        text = skill_md.read_text(encoding="utf-8", errors="ignore")
        guide_idx = text.find("## Reference Guide")
        section = text[guide_idx:] if guide_idx != -1 else text

        candidates: list[tuple[int, int, str]] = []
        order = 0
        for line in section.splitlines():
            if "references/" not in line:
                continue
            for match in PLAYBOOK_LINK_RE.finditer(line):
                rel_ref = match.group(1)
                if not (repo_root / skill / rel_ref).is_file():
                    continue
                full_rel = f"{skill}/{rel_ref}"
                if full_rel == EXTENSION_AUDIT_PLAYBOOK or full_rel in seen:
                    continue
                row_tokens = _tokenize_keywords(f"{line} {Path(rel_ref).stem.replace('-', ' ')}")
                score = len(prompt_tokens & row_tokens)
                candidates.append((score, order, full_rel))
                order += 1

        if not candidates:
            continue
        preferred = None
        if skill == "shadow-integrate" and "webhook" in prompt_tokens and (
            {"signature", "hmac", "tanda", "replay"} & prompt_tokens
        ):
            preferred = "02-hmac-webhooks-replay-and-ordering.md"
        if skill == "shadow-db" and {"erd", "dbml"} & prompt_tokens:
            preferred = "01-relational-design-and-integrity-invariants.md"
        candidates.sort(key=lambda item: (
            Path(item[2]).name != preferred if preferred else False, -item[0], item[1]
        ))
        per_skill_limit = 2 if skill == primary_skill else 1
        picked = 0
        for score, _, full_rel in candidates:
            if picked >= per_skill_limit or len(selected) >= max_total:
                break
            if score > 0 or (skill == primary_skill and picked == 0):
                selected.append(full_rel)
                seen.add(full_rel)
                picked += 1

    return selected


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


EXECUTION_SENSITIVE = frozenset({"shadow-browser", "shadow-perf"})

REQUEST_PREFIX = r"^(?:(?:now|next|please|tolong|sekarang|lalu)\s+)*"
BROWSER_REQUEST = re.compile(
    REQUEST_PREFIX + r"(?:"
    r"(?:launch|open|navigate|run|buka|jalankan)\b[^\n.!?]{0,72}"
    r"\b(?:browser|Chrome|Chromium|Firefox|WebKit|peramban|Playwright)\b"
    r"(?!\s+(?:docs?|documentation|reference|support|dokumentasi)\b)|"
    r"(?:verify|uji|cek)\b[^\n.!?]{0,58}\b(?:in|di)\s+(?:(?:a|the|real|live)\s+)*"
    r"(?:browser|Chrome|Chromium|Firefox|WebKit|peramban)\b)",
    re.IGNORECASE,
)
PERFORMANCE_REQUEST = re.compile(
    REQUEST_PREFIX + r"(?:run|draft|plan|design|prepare|jalankan|siapkan|rancang|uji)\b[^\n.!?]{0,75}"
    r"\b(?:k6|load\s+(?:test|scenario|profile)|uji\s+beban|skenario\s+beban)\b",
    re.IGNORECASE,
)
PLAYWRIGHT_AUTHORING = re.compile(
    REQUEST_PREFIX + r"(?:write|create|add|draft|tulis|buat|tambahkan)\b[^\n.!?]{0,45}\bPlaywright\b"
    r"[^\n.!?]{0,25}\btests?\b",
    re.IGNORECASE,
)
PHYSICAL_QUERY_PLAN = re.compile(
    r"\b(?:partial|covering|composite)\s+index(?:es)?\b|\bindeks\s+(?:parsial|penutup|gabungan)\b",
    re.IGNORECASE,
)
REQUESTED_PROFILING = re.compile(
    r"\b(?:pre[- ]?UAT|k6|stress\s+test|load\s+test|uji\s+beban|query\s+profiling|"
    r"profil(?:e|ing)\s+(?:the\s+)?query|profil\s+kinerja)\b",
    re.IGNORECASE,
)


def _strong_candidate(ranked: list[Candidate]) -> Candidate | None:
    if not ranked:
        return None
    first = ranked[0]
    if not (first.phrases or (first.terms >= 2 and first.rare_terms >= 1)):
        return None
    if len(ranked) > 1:
        runner_up = ranked[1]
        if first.score < 1.23 * runner_up.score and first.phrases <= runner_up.phrases:
            return None
    return first


OWNER_WEIGHTS: dict[str, float] = {
    "lexical": 1.0,
    "phrase": 0.6,
    "requested_phrase": 0.6,
    "requested_terms": 0.15,
    "rare_terms": 0.1,
    "rank": 0.5,
    "rule": 1.0,
    "rule_first": 0.3,
    "requested_rule": 0.8,
    "risk_penalty": 0.6,
    "minimum": 1.0,
}


def _owner_score(
    skill: str,
    lexical: dict[str, tuple[int, Candidate]],
    top_score: float,
    rule_order: list[str],
    risk: list[str],
    requested: list[str],
    weights: dict[str, float],
) -> float:
    """Combine rule and lexical evidence for one candidate owner into a comparable score."""
    score = 0.0
    if skill in lexical:
        rank, candidate = lexical[skill]
        score += weights["lexical"] * (candidate.score / top_score if top_score > 0 else 0.0)
        score += weights["phrase"] * min(candidate.phrases, 2)
        score += weights["requested_phrase"] * min(candidate.requested_phrases, 2)
        score += weights["requested_terms"] * min(candidate.requested_terms, 4)
        score += weights["rare_terms"] * min(candidate.rare_terms, 4)
        score += weights["rank"] / (1 + rank)
    if skill in rule_order:
        score += weights["rule"]
        if rule_order[0] == skill:
            score += weights["rule_first"]
        if skill in risk:
            score -= weights["risk_penalty"]
    if skill in requested:
        score += weights["requested_rule"]
    return score


SHORTLIST_SIZE = 10
# Owners that never author product UI: they verify, record, draw, document, index, build, ship or
# version it. With one of them as owner, framework or page names in the request do not load the UI bundle.
NON_AUTHORING_VISUAL_OWNERS = frozenset({
    "shadow-browser", "shadow-doc", "shadow-git", "shadow-illustration", "shadow-ops", "shadow-release",
    "shadow-seo", "shadow-supplychain", "shadow-video",
})
UI_OWNERS = frozenset({
    "antislop", "antislop-ui", "antislop-layoutmobile", "antislop-human", "antislop-copywriting", "antislop-code",
    "modern-web-guidance", "shadow-design", "shadow-accessibility", "shadow-monarch",
})
ANTISLOP_FAMILY = frozenset({
    "antislop", "antislop-ui", "antislop-layoutmobile", "antislop-human", "antislop-copywriting", "antislop-code",
})
NO_OWNER = "none"
ORCHESTRATOR = "shadow-monarch"


def _owner_shortlist(
    signal_text: str,
    ranked: list[Candidate],
    rule_order: list[str],
    risk: list[str],
    requested: list[str],
    excluded: set[str],
    fixed: bool,
) -> list[str]:
    """Return the safe owner candidates a model may choose from, best deterministic guess first.

    Scope blocks, negative boundaries and explicit skill mentions are applied here, so a
    model selection can never activate a skill the deterministic layer has excluded.
    """
    if fixed:
        return [skill for skill in rule_order if skill not in excluded][:SHORTLIST_SIZE]
    known = tuple(sorted(get_known_skill_names()))
    translated = retrieve(signal_text, skill_index(REPO_ROOT, known, translate=True))
    allowed = [candidate for candidate in translated if candidate.skill not in excluded]
    lexical = {candidate.skill: (rank, candidate) for rank, candidate in enumerate(allowed)}
    top_score = allowed[0].score if allowed else 0.0
    pool = sorted((set(lexical) | set(rule_order)) - excluded)
    by_evidence = sorted(
        pool,
        key=lambda skill: (-_owner_score(skill, lexical, top_score, rule_order, risk, requested, OWNER_WEIGHTS), skill),
    )
    body = [
        skill for skill, _ in retrieve_body(signal_text, body_index(REPO_ROOT, known))
        if skill not in excluded
    ]
    fused: dict[str, float] = {}
    for order in (by_evidence, body):
        for position, skill in enumerate(order):
            fused[skill] = fused.get(skill, 0.0) + 1.0 / (60 + position)
    ordered = sorted(fused, key=lambda skill: (-fused[skill], skill))
    lead = [rule_order[0]] if rule_order and rule_order[0] not in excluded else []
    shortlist = list(dict.fromkeys(lead + ordered))[:SHORTLIST_SIZE]
    if ORCHESTRATOR not in shortlist and ORCHESTRATOR not in excluded:
        shortlist.append(ORCHESTRATOR)
    return shortlist


def route_prompt(
    prompt: str,
    max_companion_skills: int = 4,
    task_id: str = "TASK-AUTO",
    repo_context: dict[str, Any] | None = None,
    selected_owner: str | None = None,
) -> dict[str, Any]:
    """Route a natural-language task prompt to required skills, references & §2.2 Decision Record."""
    stripped = prompt.strip()
    signal_text = NEGATED_OUTAGE_RE.sub(" ", _strip_non_authoritative_signals(stripped))
    outage_copy = OUTAGE_COPY_RE.search(signal_text)
    active_outage = not outage_copy and bool(
        OUTAGE_STATUS_RE.search(signal_text) or (
            PRODUCTION_CONTEXT_RE.search(signal_text) and INCIDENT_IMPACT_RE.search(signal_text)
            and INCIDENT_OPERATIONS_RE.search(signal_text)
        )
    )
    known_skills = get_known_skill_names()

    mentions = re.findall(r"(?<![\w/.:])[/\$]([a-z][a-z0-9-]+)(?![\w/-])", signal_text.lower())
    explicit_skills = [skill for skill in mentions if skill in known_skills]
    unquoted = QUOTED_LOG_RE.sub(" ", stripped)
    is_code_review = bool(CODE_REVIEW_RE.search(signal_text) or READ_ONLY_SCOPE_RE.search(unquoted))
    is_load_test_denied = bool(LOAD_TEST_DENIAL_RE.search(unquoted))
    is_browser_denied = bool(BROWSER_DENIAL_RE.search(unquoted))
    directives = request_clauses(signal_text)
    auth_change_requested = any(AUTH_CHANGE_REQUEST.search(clause) for clause in directives)
    browser_requested = any(BROWSER_REQUEST.search(clause) for clause in directives)
    performance_requested = any(PERFORMANCE_REQUEST.search(clause) for clause in directives)
    test_context = bool(re.search(
        r"\b(?:unit\s+tests?|Vitest|Jest|Pytest|Pest|PHPUnit|JUnit|xUnit)\b", signal_text, re.IGNORECASE
    )) or any(PLAYWRIGHT_AUTHORING.search(clause) for clause in directives)
    is_unit_test_only = test_context and not (browser_requested or performance_requested)

    is_typo_only = bool(TYPO_ONLY_RE.search(signal_text)) and not explicit_skills
    is_definitional_query = bool(
        re.match(r"^\s*(?:apa\s+itu|apa\s+bedanya|bedanya|what\s+is|what\s+does|difference\s+between|jelaskan\s+singkat)\b", signal_text, re.IGNORECASE)
    )
    is_trivial_fact = (
        bool(TRIVIAL_FACT_RE.match(signal_text))
        and not explicit_skills
        and (is_definitional_query or not NON_TRIVIAL_INCIDENT_RE.search(signal_text))
        and not VERSIONED_API_RE.search(signal_text)
    )

    artifact_audit_owners = () if is_typo_only or is_definitional_query else _artifact_audit_owners(signal_text)
    is_code_review = is_code_review or bool(artifact_audit_owners)
    blocked_by_scope = set(EXECUTION_SENSITIVE) if is_code_review else set()
    if is_load_test_denied or (test_context and not performance_requested):
        blocked_by_scope.add("shadow-perf")
    if is_browser_denied or (test_context and not browser_requested):
        blocked_by_scope.add("shadow-browser")
    if PHYSICAL_QUERY_PLAN.search(signal_text) and not REQUESTED_PROFILING.search(signal_text):
        blocked_by_scope.add("shadow-perf")

    ranked = []
    if not (is_typo_only or is_trivial_fact or explicit_skills or artifact_audit_owners):
        index = skill_index(REPO_ROOT, tuple(sorted(known_skills)))
        ranked = retrieve(signal_text, index)

    matched_ordered: list[str] = []
    matched_task: list[str] = []
    matched_risk: list[str] = []
    matched_refs: list[str] = []
    excluded_records: list[dict[str, str]] = []

    matched_negative_rules: set[str] = set()
    requested_rule_owners: list[str] = []
    ranked_names = {candidate.skill for candidate in ranked}
    selected_skills = explicit_skills
    if artifact_audit_owners:
        requested_helpers = ARTIFACT_AUDIT_HELPER_RE.findall(signal_text.lower())
        selected_skills = [*artifact_audit_owners, *(skill for skill in requested_helpers if skill in known_skills)]
    for sl in selected_skills:
        if sl in blocked_by_scope:
            continue
        if sl not in matched_ordered:
            matched_ordered.append(sl)
        if sl not in matched_task:
            matched_task.append(sl)

    if not is_typo_only and not artifact_audit_owners:
        for rule in ROUTING_RULES:
            sname = rule["skill"]
            if sname not in known_skills or sname in blocked_by_scope:
                continue
            matches_rule = (
                rule["include"].search(signal_text)
                or (sname == "shadow-quality" and is_code_review)
                or (sname == "shadow-maintain" and active_outage)
                or (sname == "shadow-browser" and browser_requested)
                or (sname == "shadow-perf" and performance_requested)
            )
            excl = rule.get("exclude")
            unless = rule.get("exclude_unless")
            if (
                (excl and excl.search(signal_text) and not (unless and unless.search(signal_text)))
                or (sname == "shadow-maintain" and outage_copy)
                or (sname == "shadow-auth" and active_outage and not auth_change_requested)
            ):
                matched_negative_rules.add(sname)
                if matches_rule or sname in ranked_names:
                    excluded_records.append(
                        {"skill": sname, "reason": "Excluded by sibling disambiguation or negative trigger boundary."}
                    )
                continue
            if matches_rule:
                if (
                    any(rule["include"].search(clause) for clause in directives)
                    or (sname == "shadow-browser" and browser_requested)
                    or (sname == "shadow-perf" and performance_requested)
                ):
                    requested_rule_owners.append(sname)
                target_bucket = matched_risk if rule.get("layer") == "risk" else matched_task
                if sname not in matched_ordered:
                    matched_ordered.append(sname)
                if sname not in matched_task and sname not in matched_risk:
                    target_bucket.append(sname)

    always_on_ui: list[str] = []
    weak_ui_only = True
    if not is_typo_only and not artifact_audit_owners:
        ui_signal_text = NON_UI_HOMOGRAPH_RE.sub(" ", signal_text)
        is_non_ui_work = bool(NON_UI_CONTEXT_RE.search(signal_text)) and not bool(
            UI_STRONG_SIGNAL_RE.search(ui_signal_text)
        )
        weak_ui_only = not UI_STRONG_SIGNAL_RE.search(ui_signal_text)
        if UI_ANTISLOP_RE.search(ui_signal_text) and not is_non_ui_work:
            for ui_skill in ("antislop", "antislop-ui", "antislop-layoutmobile", "antislop-human", "modern-web-guidance"):
                if ui_skill in known_skills and ui_skill not in matched_ordered and ui_skill not in matched_negative_rules:
                    always_on_ui.append(ui_skill)
        if (
            COPYWRITING_RE.search(signal_text) and "antislop-copywriting" in known_skills
            and not EMAIL_DELIVERABILITY_RE.search(signal_text)
        ):
            if "antislop" not in always_on_ui and "antislop" in known_skills:
                always_on_ui.append("antislop")
            if "antislop-copywriting" not in always_on_ui:
                always_on_ui.append("antislop-copywriting")
        if CODE_COMMENT_RE.search(signal_text) and "antislop-code" in known_skills:
            if "antislop-code" not in always_on_ui:
                always_on_ui.append("antislop-code")

    eligible = [
        candidate for candidate in ranked
        if candidate.skill not in matched_negative_rules and candidate.skill not in blocked_by_scope
        and (candidate.skill not in EXECUTION_SENSITIVE or candidate.skill in matched_ordered)
    ]
    lexical_winner = _strong_candidate(eligible)
    used_retrieval = False
    directed_owner = (
        requested_rule_owners[0] if not selected_skills and not is_code_review
        and len(requested_rule_owners) == 1 else None
    )
    if directed_owner and directed_owner != matched_ordered[0]:
        matched_ordered.remove(directed_owner)
        matched_ordered.insert(0, directed_owner)
    mixed_copy_and_comments = bool(CODE_COMMENT_RE.search(signal_text) and COPYWRITING_RE.search(signal_text))
    if not (selected_skills or is_code_review or directed_owner or mixed_copy_and_comments) and lexical_winner:
        owner = lexical_winner.skill
        if not matched_ordered:
            matched_ordered.append(owner)
            matched_task.append(owner)
            used_retrieval = True
        elif owner != matched_ordered[0] and owner not in EXECUTION_SENSITIVE:
            current = next((candidate for candidate in eligible if candidate.skill == matched_ordered[0]), None)
            existing_rule_match = (
                owner in matched_ordered and lexical_winner.phrases
                and (current is None or (not current.phrases and lexical_winner.score >= 2 * current.score))
            )
            clear_request = (
                matched_ordered[0] not in EXECUTION_SENSITIVE
                and lexical_winner.requested_terms >= 2 and lexical_winner.requested_phrases
                and (current is None or (
                    not current.requested_phrases and current.requested_terms <= 1
                    and lexical_winner.score >= 1.75 * current.score
                ))
            )
            if existing_rule_match or clear_request:
                if owner in matched_ordered:
                    matched_ordered.remove(owner)
                else:
                    matched_task.append(owner)
                matched_ordered.insert(0, owner)
                used_retrieval = True

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

    owner_fixed = bool(selected_skills) or is_typo_only or is_trivial_fact
    rule_matches_before_selection = tuple(matched_ordered)
    owner_candidates = _owner_shortlist(
        signal_text, ranked, matched_ordered, matched_risk, requested_rule_owners,
        excluded=matched_negative_rules | blocked_by_scope, fixed=owner_fixed,
    )
    selection_status = "not_requested"
    if selected_owner is not None:
        if selected_owner == NO_OWNER and not selected_skills:
            matched_ordered.clear()
            matched_task.clear()
            matched_risk.clear()
            used_retrieval = False
            selection_status = "accepted_no_owner"
        elif selected_owner in owner_candidates or (
            not owner_fixed and selected_owner in known_skills
            and selected_owner not in matched_negative_rules and selected_owner not in blocked_by_scope
        ):
            # The model's choice replaces the deterministic guess. Keep only safety reviews;
            # topical rule matches were part of that guess.
            kept = [skill for skill in matched_ordered if skill != selected_owner and skill in matched_risk]
            matched_ordered[:] = [selected_owner, *kept]
            matched_task[:] = [selected_owner, *(skill for skill in kept if skill not in matched_risk)]
            if selected_owner in matched_risk:
                matched_risk.remove(selected_owner)
            used_retrieval = False
            selection_status = "accepted" if selected_owner in owner_candidates else "accepted_outside_shortlist"
        else:
            selection_status = (
                "rejected_unknown" if selected_owner not in known_skills
                else "rejected_fixed_owner" if owner_fixed else "rejected_excluded"
            )

    if not selected_skills and "shadow-maintain" in matched_ordered and active_outage:
        matched_ordered.remove("shadow-maintain")
        matched_ordered.insert(0, "shadow-maintain")
        used_retrieval = False

    primary_skill = matched_ordered[0] if matched_ordered else "shadow-monarch"
    if primary_skill in NON_AUTHORING_VISUAL_OWNERS:
        always_on_ui = [skill for skill in always_on_ui if skill in matched_ordered]
    model_selected = selection_status in {"accepted", "accepted_outside_shortlist"} and primary_skill == selected_owner
    # Skills the prompt itself supports: rule matches before selection, or strong lexical evidence.
    prompt_evidence = set(rule_matches_before_selection) | {
        candidate.skill for candidate in ranked if candidate.phrases or candidate.rare_terms >= 2
    }
    # Weak UI words (table, card, form, input, header) are ambiguous; with only those, the UI bundle
    # follows a selected owner that works on product UI.
    if model_selected and weak_ui_only and primary_skill not in UI_OWNERS:
        always_on_ui = [skill for skill in always_on_ui if skill in matched_ordered]
    if model_selected and primary_skill in ANTISLOP_FAMILY:
        always_on_ui = [skill for skill in always_on_ui if skill in {"antislop", primary_skill} or skill not in ANTISLOP_FAMILY]

    for skill in sorted(blocked_by_scope):
        excluded_records.append({"skill": skill, "reason": "Execution skill is outside the requested scope."})

    excluded_names = {entry["skill"] for entry in excluded_records}
    if primary_skill in CO_ACTIVATION_MAP and not is_trivial:
        bundle = CO_ACTIVATION_MAP[primary_skill]
        for sup in bundle["supporting"]:
            if model_selected and sup not in prompt_evidence:
                continue
            if sup in known_skills and sup != primary_skill and sup not in excluded_names and sup not in matched_ordered:
                matched_ordered.append(sup)
                matched_task.append(sup)
        for rsk in bundle["risk"]:
            if rsk in known_skills and rsk != primary_skill and rsk not in excluded_names and rsk not in matched_ordered:
                matched_ordered.append(rsk)
                matched_risk.append(rsk)

    if not is_trivial and not artifact_audit_owners and re.search(r"\b(?:your-org-sso|sso-client|SSO\s+SDK)\b", stripped, re.IGNORECASE):
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
            r"npm\s+install|add\s+package|tambah\s+library|dependency|your-org-sso|sso-client|file:\.\./sdk|SSO\s+SDK)\b",
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
    if artifact_audit_owners:
        prohibited_actions.extend(["execute_candidate_code", "install_candidate", "activate_candidate", "load_candidate_as_instructions"])
    if is_load_test_denied:
        prohibited_actions.append("run_explicitly_denied_load_test")
    if is_browser_denied:
        prohibited_actions.append("launch_explicitly_denied_browser")
    if intent_mode in {"debug", "unit_test", "ui_implementation"}:
        prohibited_actions.append("stress_or_load_test_without_l3_approval")

    if not (is_trivial or matched_ordered):
        routing_signal = "Layer 1 fallback without a confident specialist."
    elif used_retrieval:
        routing_signal = f"Primary owner `{primary_skill}` selected from lexical candidates"
    else:
        routing_signal = f"Primary owner `{primary_skill}` selected via topic/intent signal"
    activation_reason = (
        f"Layer 1 minimal edit only ({'typo-only' if is_typo_only else 'trivial query'})."
        if is_trivial
        else (
            routing_signal
            + (f"; paired with supporting {supporting_skills}" if supporting_skills else "")
            + (f"; risk gates {risk_review_skills}" if risk_review_skills else "")
            + "."
        )
    )

    ctx = repo_context or {}
    has_active_api_doc_gen = strict_bool(ctx.get("has_active_generator", False), "has_active_generator")
    readme_summary_only = strict_bool(ctx.get("readme_summary_only", False), "readme_summary_only")
    asks_generic_api_docs = bool(API_DOCS_GENERIC_RE.search(signal_text)) and not bool(
        API_DOCS_EXPLICIT_FORMAT_RE.search(signal_text)
    )
    requires_api_docs_decision = asks_generic_api_docs and readme_summary_only and not has_active_api_doc_gen

    final_refs = [] if is_trivial else matched_refs[:4]
    if artifact_audit_owners:
        audit_playbooks = DOCUMENT_AUDIT_PLAYBOOKS if primary_skill == "shadow-doc" else EXTENSION_AUDIT_PLAYBOOKS
        recommended_playbooks = [path for path in audit_playbooks if path.split("/", 1)[0] in companion_skills]
    else:
        recommended_playbooks = [] if is_trivial else _recommend_skill_playbooks(signal_text, companion_skills, primary_skill)
    disclosure_metrics = _compute_disclosure_metrics(companion_skills, always_on_ui, final_refs, is_trivial)

    denied_actions = ["load_test", "stress_test", "soak_test"] if is_code_review or is_load_test_denied else []
    if is_code_review:
        denied_actions.append("broad_e2e")
    if artifact_audit_owners:
        denied_actions.extend(["global_install", "execute_candidate_code", "install_candidate", "activate_candidate", "load_candidate_as_instructions"])

    primary_source = (
        "artifact_audit" if artifact_audit_owners else "explicit" if primary_skill in explicit_skills
        else "model_selected" if selection_status in {"accepted", "accepted_outside_shortlist"}
        and primary_skill == selected_owner
        else "retrieval" if used_retrieval else "rule" if matched_ordered else "fallback"
    )
    decision_record = {
        "primary_source": primary_source,
        "owner_candidates": owner_candidates,
        "owner_selection": {"requested": selected_owner, "status": selection_status},
        "task_id": task_id,
        "intent": stripped,
        "primary_skill": primary_skill,
        "supporting_skills": supporting_skills,
        "risk_review_skills": risk_review_skills,
        "recommended_playbooks": recommended_playbooks,
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
        "retrieval_candidates": [
            {"skill": candidate.skill, "score": round(candidate.score, 4)}
            for candidate in eligible[:5]
        ],
        "companion_skills": companion_skills,
        "always_on_ui_skills": always_on_ui,
        "reference_modules": final_refs,
        "recommended_playbooks": recommended_playbooks,
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
            "probe": "AUDIT-1: Skill descriptions use explicit triggers, <=250 chars each and <=9,000 in total",
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
            ["shadow-refactor", "shadow-compat"],
            ["shadow-bootstrap", "shadow-perf", "shadow-quality"],
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
            ["shadow-search", "shadow-db"],
            ["shadow-perf", "shadow-eval"],
            "shadow-search",
        ),
        (
            "S51-6: Realtime notifications disconnect -> shadow-realtime",
            "Realtime notifications disconnect on mobile clients; fix SSE Last-Event-ID resume and slow-consumer backpressure.",
            ["shadow-realtime", "shadow-auth", "shadow-observe"],
            ["shadow-perf", "shadow-concurrency"],
            "shadow-realtime",
        ),
        (
            "S51-7: Unsafe transitive dependency -> shadow-supplychain",
            "Audit unsafe transitive dependency, generate CycloneDX SBOM against lockfile, check typosquatting and SLSA provenance.",
            ["shadow-supplychain", "shadow-sec"],
            ["shadow-perf", "shadow-release"],
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
            "OFFICIAL-2: your-org-sso SDK integration loads shadow-auth + OFFICIAL-FIRST-DEPENDENCY-POLICY.md",
            "Integrate existing your-org-sso (file:../sdk/sso-client) SDK into our backend app.",
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
            ["shadow-supplychain"],
            ["shadow-perf", "shadow-sec", "shadow-release"],
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
            ["shadow-search", "shadow-db"],
            ["shadow-perf", "shadow-eval"],
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
        # W0 Blind-Spot Closure (closes all 7 zero-probe skills + shadow-doc primary -> 100% of non-always-on skills probed)
        (
            "W0-BLINDSPOT-CACHE: Redis cache stampede, singleflight & TanStack Query invalidation route shadow-cache",
            "Fix Redis cache stampede using singleflight request coalescing and configure TanStack Query invalidation.",
            ["shadow-cache"],
            ["shadow-perf", "shadow-db"],
            "shadow-cache",
        ),
        (
            "W0-BLINDSPOT-DESIGN: Design tokens, wireframes & UI/UX user flow route shadow-design",
            "Create a design system token hierarchy and checkout wireframe user flow for our web app.",
            ["shadow-design"],
            ["shadow-perf"],
            "shadow-design",
        ),
        (
            "W0-BLINDSPOT-DISCOVERY: PRD, stakeholder mapping & Given/When/Then NFRs route shadow-discovery",
            "Elicit requirements for a clinic portal: produce stakeholder mapping, PRD, measurable NFR table, and Given/When/Then acceptance criteria.",
            ["shadow-discovery"],
            ["shadow-presales", "shadow-pmo"],
            "shadow-discovery",
        ),
        (
            "W0-BLINDSPOT-GIT: git merge-tree dry-run conflict & parallel git worktree route shadow-git",
            "Run git merge-tree dry-run conflict checks and manage parallel git worktree branches safely.",
            ["shadow-git"],
            ["shadow-ops"],
            "shadow-git",
        ),
        (
            "W0-BLINDSPOT-PLAN: Epics, vertical slicing, sprint tasks & DoR/DoD route shadow-plan",
            "Decompose the approved feature spec into epics, vertical slicing user stories, sprint tasks, and DoR/DoD criteria.",
            ["shadow-plan"],
            ["shadow-pmo", "shadow-presales"],
            "shadow-plan",
        ),
        (
            "W0-BLINDSPOT-UAT: Staging UAT scenarios, RTM & client sign-off route shadow-uat",
            "Prepare Staging UAT scenarios, Requirement Traceability Matrix (RTM), UAT defect triage, and client sign-off exit gate.",
            ["shadow-uat"],
            ["shadow-handover", "shadow-perf"],
            "shadow-uat",
        ),
        (
            "W0-BLINDSPOT-CONTEXT7: Context7 official docs lookup for breaking API in v5 routes context7",
            "Use Context7 to look up latest framework docs for breaking API in v5 before coding.",
            ["context7"],
            ["shadow-perf"],
            "context7",
        ),
        (
            "W0-BLINDSPOT-DOC: Export Canonical AST to .docx and .xlsx via build_doc.py routes shadow-doc primary",
            "Generate document from Canonical AST and export to .docx and .xlsx using build_doc.py and reference_verifier.",
            ["shadow-doc"],
            ["shadow-perf"],
            "shadow-doc",
        ),
        # W0/W1 Cross-Skill Ownership & Anti-Overlap Contract Probes
        (
            "W1-OWNER-AUTH-SSO: Coexisting external SSO, cookie sessions & JWKS JWT owns shadow-auth (consults shadow-sec)",
            "Design external OIDC SSO coexisting with local cookie sessions and JWKS JWT rotation, auditing multi-tenant IDOR risks.",
            ["shadow-auth", "shadow-sec"],
            ["shadow-perf"],
            "shadow-auth",
        ),
        (
            "W1-OWNER-API-CONTRACT: Idempotent POST retry during v1 to v2 OpenAPI RFC 9457 migration owns shadow-api",
            "Handle client retry timeout on POST /orders with RFC 9457 errors, OpenAPI 3.1 contract, and RFC 9745 Deprecation header during v1 to v2 API versioning.",
            ["shadow-api", "shadow-compat"],
            ["shadow-perf"],
            "shadow-api",
        ),
        (
            "W1-OWNER-SEC-STRIDE: STRIDE threat model, SSRF 169.254.169.254 & OWASP ASVS audit owns shadow-sec",
            "Run a STRIDE threat model and OWASP ASVS audit for an SSRF vector targeting 169.254.169.254 and strict CSP nonce headers.",
            ["shadow-sec"],
            ["shadow-privacy", "shadow-perf"],
            "shadow-sec",
        ),
        (
            "W1-OWNER-PRIVACY-DSAR: UU PDP Pasal 4/46/56 multi-store DSAR erasure & 3x24h breach owns shadow-privacy",
            "Audit UU PDP Pasal 4 specific data, multi-store DSAR erasure receipts, cross-border transfer safeguards, and 3x24 hour breach runbook.",
            ["shadow-privacy"],
            ["shadow-sec", "shadow-perf"],
            "shadow-privacy",
        ),
        (
            "W0-OWNER-EVAL-RAG: RAG triad faithfulness, OWASP LLM red-team & held-out judge calibration owns shadow-eval",
            "Evaluate RAG faithfulness, citation grounding, precision probes, and OWASP LLM prompt injection red-team using a held-out golden dataset.",
            ["shadow-eval"],
            ["shadow-perf"],
            "shadow-eval",
        ),
        (
            "W2-OWNER-DB-VS-DATA: Live Postgres schema diff, PgBouncer & RLS owns shadow-db (not shadow-data backfill)",
            "Inspect live database schema, tune PgBouncer transaction pooling, and harden Postgres RLS using (SELECT auth.uid()).",
            ["shadow-db"],
            ["shadow-perf"],
            "shadow-db",
        ),
        (
            "W2-OWNER-DATA-BACKFILL: Zero-downtime Expand-Contract migration & keyset backfill owns shadow-data",
            "Design a zero-downtime Expand-Contract database migration with NOT VALID constraint, CONCURRENTLY index, and resumable backfill.",
            ["shadow-data"],
            ["shadow-perf"],
            "shadow-data",
        ),
        (
            "W3-OWNER-AI-ENG: MCP stdio server, structured outputs & HITL tool boundary owns shadow-ai-eng",
            "Build a stdio MCP server with Zod structured outputs, prefix prompt caching, and HITL tool confirmation boundary.",
            ["shadow-ai-eng"],
            ["shadow-perf"],
            "shadow-ai-eng",
        ),
        (
            "W3-OWNER-SEARCH-ACL: Indonesian BM25 analyzer, hybrid RRF & pre-top-K tenant ACL owns shadow-search",
            "Tune Indonesian BM25 morphology analyzer, hybrid RRF vector fusion, and pre-top-K tenant ACL filtering in OpenSearch.",
            ["shadow-search"],
            ["shadow-cache", "shadow-perf"],
            "shadow-search",
        ),
        (
            "W3-OWNER-OBS-NO-PERF: OTel tracing, burn-rate alerts & pino wide events owns shadow-observe (excludes shadow-perf)",
            "Implement OpenTelemetry tracing, multi-window SLO error-budget burn-rate alerts, and pino wide-event JSON redaction.",
            ["shadow-observe"],
            ["shadow-perf"],
            "shadow-observe",
        ),
        (
            "W3-OWNER-CACHE-STAMPEDE: Redis tenant cache, Singleflight stampede & TanStack Query rollback owns shadow-cache",
            "Design Redis tenant-partitioned caching with Singleflight stampede defense, negative caching, and TanStack Query optimistic rollback.",
            ["shadow-cache"],
            ["shadow-search", "shadow-perf"],
            "shadow-cache",
        ),
        (
            "W4-OWNER-TEST-PYRAMID: Polyglot pytest/Vitest integration, property invariants & ephemeral DB teardown owns shadow-test",
            "Write parameterized pytest and Vitest integration tests with fast-check property invariants and ephemeral Docker DB teardown.",
            ["shadow-test"],
            ["shadow-perf"],
            "shadow-test",
        ),
        (
            "W4-OWNER-DEBUG-FORENSICS: Intermittent 500 deadlock, memory leak, git bisect & competing hypotheses owns shadow-debug",
            "Diagnose an intermittent 500 deadlock and Node.js memory leak with git bisect, competing hypotheses, and a red-before regression test.",
            ["shadow-debug"],
            ["shadow-perf"],
            "shadow-debug",
        ),
        (
            "W4-OWNER-RESILIENCE-DRILL: Automated restore drill RPO/RTO, erasure tombstones & bulkhead degradation owns shadow-resilience",
            "Run an automated ephemeral backup restore drill to verify RPO/RTO, replay erasure tombstones, and add BulkheadSemaphore graceful degradation.",
            ["shadow-resilience"],
            ["shadow-perf"],
            "shadow-resilience",
        ),
        (
            "W4-OWNER-BROWSER-QA: Playwright 375px overflow, console errors & page.route fault injection owns shadow-browser",
            "Run Playwright browser verification checking 375px mobile viewport overflow, console errors, and page.route 500/401 fault injection.",
            ["shadow-browser"],
            ["shadow-mobile", "shadow-perf"],
            "shadow-browser",
        ),
        (
            "W4-OWNER-REALTIME-WS: WebSocket/SSE Last-Event-ID resumption, mid-connection revocation & backpressure owns shadow-realtime",
            "Design WebSocket and SSE streams with Last-Event-ID resumption cursors, mid-connection auth revocation, and slow-consumer backpressure.",
            ["shadow-realtime"],
            ["shadow-perf"],
            "shadow-realtime",
        ),
        (
            "W4-OWNER-A11Y-WCAG: WCAG 2.2 AA semantic landmarks, dialog focus traps, aria-live & RTL i18n owns shadow-accessibility",
            "Audit WCAG 2.2 AA semantic HTML landmarks, keyboard focus traps in dialogs, screen reader aria-live regions, and RTL i18n layouts.",
            ["shadow-accessibility"],
            ["shadow-perf"],
            "shadow-accessibility",
        ),
        (
            "W5-OWNER-RELEASE: SemVer changelog, 8-gate pre-flight, canary abort & rollback owns shadow-release",
            "Prepare a SemVer 2.0.0 changelog, 8-gate pre-flight release checklist, canary cohort abort thresholds, and rollback runbook.",
            ["shadow-release"],
            ["shadow-perf"],
            "shadow-release",
        ),
        (
            "W5-OWNER-OPS: Non-root Dockerfile, Compose 127.0.0.1 bind, Nginx TLS & systemd owns shadow-ops",
            "Harden production Dockerfile as non-root, bind docker-compose Postgres port to 127.0.0.1, and configure Nginx TLS reverse proxy with systemd.",
            ["shadow-ops"],
            ["shadow-perf"],
            "shadow-ops",
        ),
        (
            "W5-OWNER-ARCHITECT: Single-system Modular Monolith, C4 diagrams, ADR & module facades owns shadow-architect (not shadow-ea)",
            "Design a Modular Monolith application architecture with C4 Mermaid diagrams, ADR-001, and typed module public facades instead of microservices.",
            ["shadow-architect"],
            ["shadow-ea", "shadow-perf"],
            "shadow-architect",
        ),
        (
            "W5-OWNER-COMPAT: API backward compatibility, RFC 9745 Deprecation/Sunset & consumer replay owns shadow-compat",
            "Audit API backward compatibility, emit RFC 9745 Deprecation and RFC 8594 Sunset headers with 410 Gone, and run consumer payload replay.",
            ["shadow-compat"],
            ["shadow-perf"],
            "shadow-compat",
        ),
        (
            "W5-OWNER-BOOTSTRAP: Greenfield CLI/HTTP scaffolding via official CLI generator & preview owns shadow-bootstrap",
            "Scaffold a greenfield HTTP service in a new target directory using an official CLI generator and vertical-slice preview.",
            ["shadow-bootstrap"],
            ["shadow-perf"],
            "shadow-bootstrap",
        ),
        (
            "W5-OWNER-GIT: git merge-tree dry-run, parallel agent worktrees & safe sync owns shadow-git",
            "Run git merge-tree dry-run conflict checks, manage isolated parallel agent worktrees, and sync team feature branches safely.",
            ["shadow-git"],
            ["shadow-perf"],
            "shadow-git",
        ),
        (
            "W5-OWNER-SUPPLYCHAIN: CycloneDX SBOM, 40-char SHA CI pinning & SLSA provenance owns shadow-supplychain",
            "Generate a CycloneDX SBOM from frozen lockfile, pin GitHub Actions to 40-char commit SHA, and verify SLSA provenance attestation.",
            ["shadow-supplychain"],
            ["shadow-perf"],
            "shadow-supplychain",
        ),
        (
            "W5-OWNER-REFACTOR: Behavior-preserving characterization tests, seam extraction & branch-by-abstraction owns shadow-refactor",
            "Refactor a 400-line legacy billing module safely using characterization tests, seam extraction, and branch-by-abstraction within existing conventions.",
            ["shadow-refactor"],
            ["shadow-modernize", "shadow-perf"],
            "shadow-refactor",
        ),
        (
            "W5-OWNER-MODERN-WEB: Native dialog, Popover API, container queries & LCP fetchpriority activates modern-web-guidance",
            "Build a modal using native HTML dialog, Popover API, CSS container queries, :has(), and fetchpriority high for Core Web Vitals.",
            ["modern-web-guidance"],
            ["shadow-db", "shadow-perf"],
            None,
        ),
        (
            "W6A-OWNER-DESIGN: 9-state component contracts, semantic tokens, wireframes & Human-AI UX owns shadow-design",
            "Design a 9-state component contract, semantic design tokens, wireframes, and Human-AI HITL confirmation flow for our approval modal.",
            ["shadow-design"],
            ["shadow-perf"],
            "shadow-design",
        ),
        (
            "W6A-OWNER-DISCOVERY: PRD/SRS requirements elicitation, quantified NFRs & Gherkin acceptance owns shadow-discovery (not presales/pmo)",
            "Elicit software requirements, write a PRD and SRS with quantified NFRs, and define Given/When/Then acceptance criteria.",
            ["shadow-discovery"],
            ["shadow-presales", "shadow-pmo", "shadow-perf"],
            "shadow-discovery",
        ),
        (
            "W6A-OWNER-PLAN: Epics, vertical User Stories, Sprint Tasks, DAG & DoR/DoD owns shadow-plan (not shadow-pmo)",
            "Decompose the approved SRS into Epics, vertical User Stories, Sprint Tasks, an acyclic dependency graph, and DoR/DoD gates.",
            ["shadow-plan"],
            ["shadow-pmo", "shadow-perf"],
            "shadow-plan",
        ),
        (
            "W6A-OWNER-UAT: RTM, Staging UAT scenarios, defect triage & Berita Acara UAT owns shadow-uat",
            "Prepare a Requirement Traceability Matrix (RTM), Staging UAT business scenarios, defect triage log, and Berita Acara UAT sign-off.",
            ["shadow-uat"],
            ["shadow-perf"],
            "shadow-uat",
        ),
        (
            "W6A-OWNER-MAINTAIN: SEV1 production incident triage, blameless RCA, Harwat SLA & surgical hotfix owns shadow-maintain",
            "Triage a live SEV1 production incident, write a blameless 5-Why postmortem RCA, manage monthly Harwat SLA tickets, and ship a surgical hotfix with regression tests.",
            ["shadow-maintain"],
            ["shadow-perf"],
            "shadow-maintain",
        ),
        (
            "W6A-OWNER-MOBILE: OWASP MASVS v2.1.0, PrivacyInfo.xcprivacy, Play Integrity, 16 KB & App Links owns shadow-mobile (not shadow-browser)",
            "Audit OWASP MASVS v2.1.0, configure PrivacyInfo.xcprivacy, migrate to Google Play Integrity API, align 16 KB native libraries, and verify Android App Links.",
            ["shadow-mobile"],
            ["shadow-browser", "shadow-perf"],
            "shadow-mobile",
        ),
        (
            "W6A-OWNER-DOC: Canonical JSON AST v2.0 .docx/.pdf/.xlsx export & reference_verifier.py owns shadow-doc",
            "Generate formal .docx, .pdf, and .xlsx SDLC deliverables from Canonical JSON AST v2.0 and scan downloaded references with reference_verifier.py.",
            ["shadow-doc"],
            ["shadow-perf"],
            "shadow-doc",
        ),
        (
            "W6B-OWNER-HANDOVER: Client BAST, zero-plaintext vault cutover, Admin manuals & ToT owns shadow-handover (not /handoff)",
            "Prepare the client BAST Berita Acara Serah Terima package, zero-plaintext vault credential transfer manifest, Admin/Operator manuals, and Training of Trainers (ToT).",
            ["shadow-handover"],
            ["handoff", "shadow-perf"],
            "shadow-handover",
        ),
        (
            "W6B-OWNER-GRC: COBIT 2019 Capability vs Maturity, ISO 27001:2022 SoA & POJK 11/2022 + PADK OJK 1/2026 owns shadow-grc",
            "Audit COBIT 2019 Process Capability vs Maturity, ISO/IEC 27001:2022 93-control Annex A SoA, and POJK 11/2022 + PADK OJK 1/2026 banking IT governance.",
            ["shadow-grc"],
            ["shadow-perf"],
            "shadow-grc",
        ),
        (
            "W6B-OWNER-MODERNIZE: Legacy technical due diligence, business-rule archaeology & Strangler Fig vs Rewrite TCO owns shadow-modernize",
            "Conduct technical due diligence on an inherited legacy monolith, run business-rule archaeology, and compare Strangler Fig Refactor vs Full Rewrite coexistence TCO.",
            ["shadow-modernize"],
            ["shadow-refactor", "shadow-perf"],
            "shadow-modernize",
        ),
        (
            "W6B-OWNER-PMO: Contractual Precedence Defect vs Paid CR, PERT/CPM Monte Carlo P80 & EVM CPI/SPI owns shadow-pmo",
            "Triage a client request against Contractual Precedence as Defect vs Paid CR candidate, compute PERT + CPM + Monte Carlo P80 schedule, and evaluate EVM CPI/SPI.",
            ["shadow-pmo"],
            ["shadow-plan", "shadow-presales", "shadow-perf"],
            "shadow-pmo",
        ),
        (
            "W6B-OWNER-PRESALES: KAK tender Bid/No-Bid, 3-scenario workload sizing, 5-yr TCO/NPV & Perpres 46/2025 Provider RAB owns shadow-presales",
            "Analyze an Indonesian government KAK tender, score Bid/No-Bid, size 3-scenario workload capacity, model 5-year TCO/NPV, and build a Provider RAB/BoQ under Perpres 46/2025.",
            ["shadow-presales"],
            ["shadow-pmo", "shadow-perf"],
            "shadow-presales",
        ),
        (
            "W6B-OWNER-EA: TOGAF 10, Indonesia 6-Domain SPBE + Satu Data, TIME rationalization & ABB vs SBB owns shadow-ea (not shadow-architect)",
            "Design a multi-system TOGAF 10 and Indonesia 6-Domain SPBE (Perpres 95/2018 & 132/2022) + Satu Data blueprint with TIME application rationalization and ABB vs SBB separation.",
            ["shadow-ea"],
            ["shadow-architect", "shadow-perf"],
            "shadow-ea",
        ),
        (
            "W6B-OWNER-FINOPS: FinOps Framework, FOCUS EffectiveCost, prefix prompt caching & thinking token caps owns shadow-finops",
            "Audit Kubernetes and LLM token costs under FinOps Framework and FOCUS EffectiveCost, fix dynamic prefix prompt caching leaks, and cap thinking/output token budgets.",
            ["shadow-finops"],
            ["shadow-presales", "shadow-perf"],
            "shadow-finops",
        ),
        (
            "W7-OWNER-CONTEXT7: Version-accurate framework API docs via Context7 owns context7",
            "Check the latest breaking API in v15 docs via Context7 for Next.js App Router.",
            ["context7"],
            ["shadow-perf"],
            "context7",
        ),
        (
            "W7-OWNER-HANDOFF: AI coding session memory transfer via shadow_handoff MCP owns handoff (not shadow-handover)",
            "Save our session context with lanjut handoff via shadow_handoff MCP so the next agent continues cleanly.",
            ["handoff"],
            ["shadow-handover", "shadow-perf"],
            "handoff",
        ),
        (
            "W7-NOOP-ANTISLOP-BACKEND: Pure PostgreSQL DB task mentioning 'orders table' must NOT load any antislop UI skills",
            "Inspect the PostgreSQL database schema, MVCC bloat, and PgBouncer connection pool sizing on the orders table.",
            ["shadow-db"],
            ["antislop", "antislop-ui", "antislop-human", "antislop-copywriting", "antislop-layoutmobile", "antislop-code"],
            "shadow-db",
        ),
        (
            "W7-SCOPED-ANTISLOP-CODE: Code comment cleanup activates antislop-code without pulling backend/perf skills",
            "Clean up AI-slop code comments in orderService.ts while preserving non-obvious why-comments.",
            ["antislop-code"],
            ["shadow-db", "shadow-perf"],
            None,
        ),
        (
            "ADV-HOMOGRAPH-HTTP-HEADER: Express HTTP header validation must NOT load UI antislop skills",
            "Tambahkan validasi HTTP header Authorization dan X-Request-Id di REST API endpoint Express.",
            ["shadow-api"],
            ["antislop", "antislop-ui", "antislop-human", "antislop-layoutmobile", "modern-web-guidance"],
            "shadow-api",
        ),
        (
            "ADV-HOMOGRAPH-CREDIT-CARD: Midtrans credit card webhook must NOT load UI antislop skills",
            "Integrasikan pembayaran credit card dan QRIS lewat Midtrans webhook HMAC signature.",
            ["shadow-integrate"],
            ["antislop", "antislop-ui", "antislop-human", "antislop-layoutmobile", "modern-web-guidance"],
            "shadow-integrate",
        ),
        (
            "ADV-HOMOGRAPH-ZOD-INPUT: Backend Zod input validation must NOT load UI antislop skills",
            "Perbaiki validasi input Zod untuk POST /api/v1/orders supaya menolak amount negatif.",
            ["shadow-api"],
            ["antislop", "antislop-ui", "antislop-human", "antislop-layoutmobile", "modern-web-guidance"],
            "shadow-api",
        ),
        (
            "ADV-HOMOGRAPH-MULTIPART-FORM: S3 multipart form-data upload must NOT load UI antislop skills",
            "Implementasikan multipart form-data upload file PDF ke S3 dengan presigned URL.",
            ["shadow-api"],
            ["antislop", "antislop-ui", "antislop-human", "antislop-layoutmobile", "modern-web-guidance"],
            "shadow-api",
        ),
        (
            "ADV-HOMOGRAPH-SQL-SELECT-N1: Prisma N+1 SELECT * FROM users table owns shadow-db with zero UI skills",
            "Perbaiki query SELECT * FROM users table yang lambat karena N+1 di Prisma backend.",
            ["shadow-db"],
            ["antislop", "antislop-ui", "antislop-human", "antislop-layoutmobile", "modern-web-guidance"],
            "shadow-db",
        ),
        (
            "ADV-HOMOGRAPH-EMAIL-HEADER: Email header injection SPF/DKIM/DMARC must NOT load UI antislop skills",
            "Audit email header injection dan SPF DKIM DMARC alignment untuk transactional email.",
            ["shadow-email"],
            ["antislop", "antislop-ui", "antislop-human", "antislop-layoutmobile", "modern-web-guidance"],
            "shadow-email",
        ),
        (
            "ADV-HOMOGRAPH-SEO-HALAMAN: Pure JSON-LD & sitemap.xml SEO on halaman produk must NOT load UI styling skills",
            "Perbaiki SEO halaman produk kami, tambahkan JSON-LD schema dan sitemap.xml.",
            ["shadow-seo"],
            ["antislop", "antislop-ui", "antislop-human", "antislop-layoutmobile", "modern-web-guidance"],
            "shadow-seo",
        ),
        (
            "ADV-ID-CRUD-MIGRASI: Indonesian endpoint CRUD + migrasi database routes to shadow-api and shadow-data",
            "Tolong buatkan endpoint CRUD master produk beserta migrasi database dan testnya.",
            ["shadow-api", "shadow-data"],
            ["antislop", "shadow-perf"],
            "shadow-api",
        ),
        (
            "ADV-ID-HANDOFF-NATURAL: Indonesian casual context full + tolong handoff routes to handoff",
            "Context udah penuh nih, tolong handoff dulu ya.",
            ["handoff"],
            ["shadow-handover", "antislop"],
            "handoff",
        ),
        (
            "ADV-ID-TRIVIAL-BEDANYA: Indonesian definitional question hits L0 trivial fast path with 0 skills/refs",
            "Bedanya HTTP 401 dan 403 apa sih?",
            [],
            ["shadow-auth", "shadow-api", "antislop"],
            "shadow-monarch",
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
    parser.add_argument(
        "--select-owner", default=None,
        help="Stage two: the owner chosen from owner_candidates (or 'none'); the router validates it.",
    )
    args = parser.parse_args()

    if args.audit_descriptions:
        res = audit_descriptions()
        print(json.dumps(res, indent=2))
        return 0 if res["all_passed"] else 1
    if args.route is not None:
        print(json.dumps(route_prompt(args.route, selected_owner=args.select_owner), indent=2, ensure_ascii=False))
        return 0
    if args.self_test:
        res = run_self_test()
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0 if res["all_passed"] else 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(run_checked_cli(main))
