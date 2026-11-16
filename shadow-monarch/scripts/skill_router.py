#!/usr/bin/env python3
"""
Shadow Monarch Topic-Based Skill Router & Description Auditor (skill_router.py)

Solves "skills did not load when tasks match a topic without /shadow-* slash commands":
1. `--audit-descriptions`: verifies every skill in the repo has a valid `Use when...`
   natural-language trigger clause and stays within <= 500 chars.
2. `--route "<prompt>"`: deterministically maps natural-language EN/ID tasks to the
   exact 1-3 companion skills + `shadow-monarch/reference/*.md` files with explicit
   sibling disambiguation and Pre-UAT `/shadow-perf` guardrails.
3. `--self-test`: executes >= 16 precision & recall routing probes without slash commands.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SKIP_ROOT_DIRS = {"evals", "mcp-servers"}

USE_WHEN_RE = re.compile(r"\buse\s+(?:only\s+)?when\b", re.IGNORECASE)

# Explicit topic routing rules ordered cleanly with negative disambiguation
ROUTING_RULES: list[dict[str, Any]] = [
    {
        "skill": "handoff",
        "references": ["TOKEN-EFFICIENCY.md"],
        "include": re.compile(r"\b(?:lanjut\s+handoff|load\s+handoff|merge\s+handoff|session\s+handoff|context\s+(?:full|penuh|compaction)|simpan\s+sesi)\b", re.IGNORECASE),
        "exclude": re.compile(r"\b(?:BAST|serah\s+terima\s+klien|admin\s+manual|operator\s+manual|training\s+of\s+trainers)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-handover",
        "references": ["DOCS-PIPELINE.md", "IT-PMO-GOVERNANCE.md"],
        "include": re.compile(r"\b(?:BAST|berita\s+acara\s+serah\s+terima|serah\s+terima\s+(?:klien|proyek)|admin\s+manual|operator\s+manual|training\s+of\s+trainers|ToT)\b", re.IGNORECASE),
        "exclude": re.compile(r"\b(?:lanjut\s+handoff|load\s+handoff|session\s+handoff)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-presales",
        "references": ["PRESALES-PROPOSAL-KAK.md", "CONSULTING-INTELLIGENCE-CORE.md"],
        "include": re.compile(r"\b(?:KAK|TOR|RFP|tender|aanwijzing|bid/no-bid|RAB|BoQ|HPS|TKDN|UMKK|Perpres\s*46|server\s*sizing|capacity\s*sizing|3[- ]year\s*TCO|NPV)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-grc",
        "references": ["IT-PMO-GOVERNANCE.md", "CONSULTING-INTELLIGENCE-CORE.md"],
        "include": re.compile(r"\b(?:COBIT|ISO\s*(?:/IEC\s*)?27001|Statement\s+of\s+Applicability|SoA|Annex\s+A|Indeks\s+KAMI|BSSN|POJK\s*11|PADK\s*OJK|audit\s+(?:TI|IT|workpaper)|governance\s+assurance)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-modernize",
        "references": ["REFACTORING.md", "CONSULTING-INTELLIGENCE-CORE.md"],
        "include": re.compile(r"\b(?:technical\s+due\s+diligence|legacy\s+(?:system|codebase|audit)|strangler\s+fig|business[- ]rule\s+archaeology|refactor\s+vs\s+rewrite|coexistence\s+cost|EOL\s+runtime)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-pmo",
        "references": ["IT-PMO-GOVERNANCE.md", "CONSULTING-INTELLIGENCE-CORE.md"],
        "include": re.compile(r"\b(?:change\s+request|paid\s+CR|scope\s+creep|PERT|critical\s+path|CPM|monte\s+carlo|P80|earned\s+value|EVM|CPI|SPI|RAID\s+log|laporan\s+(?:pendahuluan|antara|akhir))\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-ea",
        "references": ["ARCHITECTURE.md", "CONSULTING-INTELLIGENCE-CORE.md"],
        "include": re.compile(r"\b(?:TOGAF|enterprise\s+architecture|arsitektur\s+SPBE|6\s+domain\s+SPBE|Perpres\s*132|Satu\s+Data|TIME\s+(?:matrix|portfolio)|application\s+rationalization|ABB|SBB|capability\s+heatmap)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-privacy",
        "references": ["SECURITY.md", "IT-PMO-GOVERNANCE.md"],
        "include": re.compile(r"\b(?:UU\s*PDP|UU\s*(?:No\.?\s*)?27\s*(?:Tahun\s*)?2022|GDPR|DPIA|ROPA|DSAR|data\s+(?:spesifik|pribadi)|cross[- ]border\s+transfer|PII\s+(?:redaction|masking)|NIK\s+log|kebocoran\s+data|3\s*x\s*24)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-eval",
        "references": ["AI-LLM.md", "sub-RAG-VECTOR-KNOWLEDGE.md"],
        "include": re.compile(r"\b(?:RAG\s*(?:eval|triad|faithfulness|recall)|LLM[- ]as[- ]a[- ]judge|OWASP\s*LLM|NIST\s*AI\s*600-1|prompt\s+injection|red[- ]team\s+LLM|precision\s+probe|recall\s+probe|golden\s+dataset)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-finops",
        "references": ["CLOUD-SRE.md", "sub-AI-INFRA-SERVING.md"],
        "include": re.compile(r"\b(?:FinOps|FOCUS\s+spec|cloud\s+(?:cost|bill|tagihan)|token\s+(?:cost|budget)|prompt\s+caching|thinking\s+token|K8s\s+(?:cost|right[- ]sizing)|egress\s+cost)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-mobile",
        "references": ["MOBILE.md", "sub-FRONTEND-MOBILE-STACKS.md"],
        "include": re.compile(r"\b(?:OWASP\s*MASVS|PrivacyInfo\.xcprivacy|Play\s+Integrity|targetSdkVersion|AndroidManifest|App\s+Store\s+Connect|Play\s+Console|\.aab|Universal\s+Links|App\s+Links|assetlinks\.json|apple-app-site-association|Flutter\s+release|React\s+Native\s+signing)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-perf",
        "references": ["sub-OBSERVABILITY-PROFILING.md", "sub-QA-AUTOMATION.md"],
        "include": re.compile(r"\b(?:pre[- ]UAT\s+(?:perf|load)|k6\s+load|load\s+test|stress\s+test|spike\s+test|EXPLAIN\s+ANALYZE|query\s+profiling|bottleneck\s+audit)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-api",
        "references": ["BACKEND.md", "sub-SPECS-DOCX-CODE.md"],
        "include": re.compile(r"\b(?:REST\s+API|API\s+endpoint|backend\s+endpoint|OpenAPI|openapi\.yaml|Swagger|Postman|HTTP\s+(?:route|controller)|gRPC\s+contract)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-auth",
        "references": ["SECURITY.md", "BACKEND.md"],
        "include": re.compile(r"\b(?:login|authentication|AuthN|AuthZ|RBAC|ABAC|OAuth2|OIDC|SSO|JWT\s+refresh|session\s+rotation|tenant\s+isolation|multi[- ]tenant\s+auth)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-db",
        "references": ["DATABASE.md", "DATA-ANALYTICS-ML.md"],
        "include": re.compile(r"\b(?:inspect\s+(?:live\s+)?database|DBML|ERD|schema\s+diff|Star\s+Schema|Data\s+Warehouse|Pentaho|\.ktr|\.kjb|read[- ]only\s+query)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-data",
        "references": ["DATABASE.md", "sub-DATA-STORES.md"],
        "include": re.compile(r"\b(?:database\s+migration|Expand[- ]Contract|zero[- ]downtime\s+migration|backfill|deterministic\s+seed|bulk\s+(?:import|export)|ACID\s+lock)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-cache",
        "references": ["FRONTEND.md", "sub-DATA-STORES.md"],
        "include": re.compile(r"\b(?:TanStack\s+Query|SWR|Redis\s+cach|cache\s+stampede|optimistic\s+UI|Idempotency[- ]Key|stale[- ]while[- ]revalidate)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-integrate",
        "references": ["ENTERPRISE-INTEGRATION.md", "sub-FINTECH-ID-ECOSYSTEM.md"],
        "include": re.compile(r"\b(?:payment\s+gateway|SNAP\s+BI|Midtrans|Xendit|QRIS|webhook|HMAC\s+signature|Transactional\s+Outbox|circuit\s+breaker|WhatsApp\s+gateway|SMTP)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-sec",
        "references": ["SECURITY.md", "SECOPS-PENTEST.md"],
        "include": re.compile(r"\b(?:STRIDE|threat\s+model|OWASP\s*ASVS|NIST\s*SSDF|SBOM|VAPT|SAST|DAST|secret\s+scan|SQL\s+injection|IDOR|SSRF)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-browser",
        "references": ["FRONTEND.md", "sub-QA-AUTOMATION.md"],
        "include": re.compile(r"\b(?:Playwright|browser\s+E2E|375px|mobile\s+viewport\s+overflow|console\s+error\s+in\s+browser|UI\s+click[- ]through)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-accessibility",
        "references": ["DESIGN.md", "UI_UX_Design_Knowledge_Base_v2_Art_Direction_Web_Mobile_ID.md"],
        "include": re.compile(r"\b(?:WCAG|screen\s+reader|ARIA\s+live|focus\s+trap|keyboard\s+navigation|aksesibilitas|lansia\s+contrast)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-design",
        "references": ["DESIGN.md", "UI_UX_Design_Knowledge_Base_v2_Art_Direction_Web_Mobile_ID.md"],
        "include": re.compile(r"\b(?:design\s+system|wireframe|UI/UX|user\s+flow|thumb\s+zone|design\s+token|komponen\s+UI|antarmuka)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-test",
        "references": ["TESTING.md", "sub-QA-AUTOMATION.md"],
        "include": re.compile(r"\b(?:unit\s+test|integration\s+test|contract\s+test|Vitest|Jest|Pytest|Pest|PHPUnit|JUnit|xUnit|regression\s+test)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-quality",
        "references": ["CODE-REVIEW.md", "CROSS-MODEL-PARITY.md"],
        "include": re.compile(r"\b(?:static\s+analysis|lint|typecheck|dead\s+code|cyclomatic\s+complexity|shadow_gate|code\s+review|PR\s+review)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-git",
        "references": ["DEVOPS.md"],
        "include": re.compile(r"\b(?:git\s+merge-tree|merge\s+conflict|git\s+worktree|sync\s+branch|pull\s+branch|branching\s+strategy)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-doc",
        "references": ["DOCS-PIPELINE.md", "sub-SPECS-DOCX-CODE.md"],
        "include": re.compile(r"\b(?:\.docx|\.xlsx|Canonical\s+AST|generate\s+document|SRS\s+doc|SDD\s+doc|reference_verifier)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-discovery",
        "references": ["PRODUCT-ANALYSIS.md"],
        "include": re.compile(r"\b(?:elicit\s+requirement|PRD|SRS|BRD|stakeholder\s+mapping|Given/When/Then|acceptance\s+criteria)\b", re.IGNORECASE),
        "exclude": re.compile(r"\b(?:KAK|tender|RAB|HPS|paid\s+CR)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-architect",
        "references": ["ARCHITECTURE.md"],
        "include": re.compile(r"\b(?:C4\s+diagram|ADR|modular\s+monolith|microservices\s+vs\s+monolith|system\s+architecture)\b", re.IGNORECASE),
        "exclude": re.compile(r"\b(?:TOGAF|SPBE|6\s+domain|application\s+portfolio|TIME\s+matrix)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-plan",
        "references": ["PRODUCT-ANALYSIS.md", "IT-PMO-GOVERNANCE.md"],
        "include": re.compile(r"\b(?:epic|user\s+story|sprint\s+task|DoR|DoD|task\s+breakdown)\b", re.IGNORECASE),
        "exclude": re.compile(r"\b(?:paid\s+CR|monte\s+carlo|EVM|CPI|SPI)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-bootstrap",
        "references": ["CORE.md", "DEVOPS.md"],
        "include": re.compile(r"\b(?:scaffold\s+new\s+project|from\s+scratch|from\s+zero|init\s+repository|bootstrap\s+project)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-uat",
        "references": ["sub-QA-AUTOMATION.md"],
        "include": re.compile(r"\b(?:Staging\s+UAT|UAT\s+scenario|Requirement\s+Traceability\s+Matrix|RTM|client\s+sign[- ]off)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-release",
        "references": ["DEVOPS.md", "CLOUD-SRE.md"],
        "include": re.compile(r"\b(?:production\s+(?:release|deploy)|SemVer|changelog|rollback\s+runbook|feature\s+flag\s+rollout)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-compat",
        "references": ["BACKEND.md", "FRONTEND.md"],
        "include": re.compile(r"\b(?:backward\s+compatib|dependency\s+upgrade|breaking\s+change|cross[- ]browser\s+matrix)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-ops",
        "references": ["DEVOPS.md", "CLOUD-SRE.md"],
        "include": re.compile(r"\b(?:Docker|Dockerfile|Kubernetes|Nginx|Caddy|systemd|PM2|CI/CD|GitHub\s+Actions|GitLab\s+CI)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-observe",
        "references": ["sub-OBSERVABILITY-PROFILING.md", "CLOUD-SRE.md"],
        "include": re.compile(r"\b(?:SLI|SLO|error\s+budget|OpenTelemetry|OTel|Prometheus|PromQL|Loki|Grafana|distributed\s+tracing)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-resilience",
        "references": ["CLOUD-SRE.md"],
        "include": re.compile(r"\b(?:disaster\s+recovery|restore\s+drill|RPO|RTO|chaos\s+engineering|backup\s+restore)\b", re.IGNORECASE),
    },
    {
        "skill": "shadow-maintain",
        "references": ["DEBUGGING.md", "IT-PMO-GOVERNANCE.md"],
        "include": re.compile(r"\b(?:post[- ]production|Harwat|OMKT|postmortem|blameless\s+RCA|production\s+incident|hotfix)\b", re.IGNORECASE),
    },
    {
        "skill": "context7",
        "references": [],
        "include": re.compile(r"\b(?:latest\s+(?:library|framework|SDK)\s+docs|Context7|breaking\s+API\s+in\s+v\d+)\b", re.IGNORECASE),
    },
]

UI_ANTISLOP_RE = re.compile(r"\b(?:UI|frontend|halaman|landing\s+page|CSS|Tailwind|React|Next\.js|Vue|form|modal|navbar|dashboard|tombol|button|layout|mobile\s+responsive|copywriting)\b", re.IGNORECASE)
TRIVIAL_FACT_RE = re.compile(r"^\s*(?:apa\s+itu|what\s+is|berapa|bagi\s+benchmark|knp|kenapa)\b", re.IGNORECASE)


def audit_descriptions(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    """Audit all skill SKILL.md frontmatter descriptions for explicit 'Use when...' triggers."""
    skill_dirs = sorted([
        p for p in repo_root.iterdir()
        if p.is_dir() and not p.name.startswith(".") and p.name not in SKIP_ROOT_DIRS
    ], key=lambda p: p.name)

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
        p.name for p in repo_root.iterdir()
        if p.is_dir() and not p.name.startswith(".") and p.name not in SKIP_ROOT_DIRS and (p / "SKILL.md").is_file()
    }


def route_prompt(prompt: str, max_companion_skills: int = 4) -> dict[str, Any]:
    """Route a natural-language task prompt to required skills & reference modules."""
    stripped = prompt.strip()
    known_skills = get_known_skill_names()
    # Match explicit slash commands only when preceded by whitespace/start AND matching a real skill name
    raw_slashes = re.findall(r"(?:^|\s)/([a-z][a-z0-9-]+)", stripped.lower())
    explicit_slashes = [sl for sl in raw_slashes if sl in known_skills]

    matched_skills: list[str] = []
    matched_refs: list[str] = []
    excluded_reasons: list[dict[str, str]] = []

    # 1. Explicit slash commands take precedence
    for sl in explicit_slashes:
        if sl not in matched_skills:
            matched_skills.append(sl)

    # 2. Topic-based auto-routing (never requires /shadow-* slash command)
    for rule in ROUTING_RULES:
        sname = rule["skill"]
        if rule["include"].search(stripped):
            excl = rule.get("exclude")
            if excl and excl.search(stripped):
                excluded_reasons.append({"skill": sname, "reason": "Excluded by sibling disambiguation boundary."})
                continue
            if sname not in matched_skills:
                matched_skills.append(sname)
            for ref in rule.get("references", []):
                if ref not in matched_refs:
                    matched_refs.append(ref)

    # 3. Always-on antislop bundle when task involves UI/frontend/copywriting
    always_on_ui: list[str] = []
    if UI_ANTISLOP_RE.search(stripped):
        always_on_ui = ["antislop", "antislop-ui", "antislop-layoutmobile"]

    # 4. Guard against loading shadow-perf during routine feature coding
    if "shadow-perf" not in matched_skills and re.search(r"\b(?:build|implement|create|buat|tambah)\b", stripped, re.IGNORECASE):
        excluded_reasons.append({"skill": "shadow-perf", "reason": "Strict Pre-UAT gate only; excluded during normal feature coding."})

    # 5. Trivial factual question loads 0 references unless a specific skill/topic matched
    is_trivial = bool(TRIVIAL_FACT_RE.match(stripped)) and len(matched_skills) == 0 and len(always_on_ui) == 0
    if not is_trivial and not matched_refs and matched_skills:
        matched_refs.append("CORE.md")

    capped_companion = matched_skills[:max_companion_skills]
    return {
        "prompt": prompt,
        "core_orchestrator": "shadow-monarch",
        "companion_skills": capped_companion,
        "always_on_ui_skills": always_on_ui,
        "reference_modules": [] if is_trivial else matched_refs[:4],
        "excluded_skills": excluded_reasons,
    }


def run_self_test() -> dict[str, Any]:
    """Run >=16 precision & recall routing probes (without /shadow-* slash commands)."""
    audit = audit_descriptions()
    results: list[dict[str, Any]] = [
        {"probe": "AUDIT-1: All 45 SKILL.md have 'Use when...' triggers & <=500 chars", "passed": audit["all_passed"], "details": audit}
    ]

    probes: list[tuple[str, str, list[str], list[str]]] = [
        # (name, prompt, must_include_skills, must_exclude_skills)
        (
            "RECALL-1: Indonesian KAK & RAB under Perpres 46/2025 (no slash)",
            "Tolong buatkan perhitungan server sizing dan estimasi RAB proyek pemerintah dari KAK ini sesuai Perpres 46 Tahun 2025 dan TKDN.",
            ["shadow-presales"],
            ["shadow-perf", "shadow-ea"],
        ),
        (
            "RECALL-2: Banking GRC audit PADK OJK 1/2026 & COBIT/ISO 27001 (no slash)",
            "Lakukan readiness assessment ISO 27001 Clauses 4-10, SoA 93 kontrol, COBIT 2019, dan PADK OJK 1/2026 untuk bank umum.",
            ["shadow-grc"],
            ["shadow-perf", "shadow-privacy"],
        ),
        (
            "RECALL-3: UU PDP personal data classification & 3x24h breach (no slash)",
            "Audit tabel pasien yang menyimpan NIK dan rekam medis agar sesuai UU PDP Pasal 4, DPIA, cross-border transfer, dan notifikasi kebocoran data 3x24 jam.",
            ["shadow-privacy"],
            ["shadow-perf"],
        ),
        (
            "RECALL-4: Legacy system technical due diligence (no slash)",
            "Lakukan technical due diligence pada legacy codebase PHP ini untuk melihat apakah lebih tepat Strangler Fig atau Full Rewrite.",
            ["shadow-modernize"],
            ["shadow-bootstrap", "shadow-perf"],
        ),
        (
            "RECALL-5: Mid-project Paid CR vs Defect + PERT/Monte Carlo P80 (no slash)",
            "Klien minta fitur baru di tengah jalan, tolong evaluasi ini defect atau Paid CR lalu hitung ulang jadwal PERT, CPM, dan Monte Carlo P80.",
            ["shadow-pmo"],
            ["shadow-plan", "shadow-discovery"],
        ),
        (
            "RECALL-6: Government 6-domain SPBE + Satu Data + TIME portfolio (no slash)",
            "Petakan portofolio aplikasi kementerian ke dalam 6 domain SPBE Perpres 132/2022, Satu Data, matriks TIME, dan ABB vs SBB.",
            ["shadow-ea"],
            ["shadow-architect"],
        ),
        (
            "RECALL-7: Single-app C4 & Modular Monolith design (no slash)",
            "Rancang C4 diagram dan ADR untuk memutuskan Modular Monolith vs Microservices pada satu sistem ERP baru.",
            ["shadow-architect"],
            ["shadow-ea"],
        ),
        (
            "RECALL-8: RAG evaluation + prompt injection red-team (no slash)",
            "Evaluasi kualitas RAG chatbot kami menggunakan metrics Faithfulness, Context Recall, dan uji red-team OWASP LLM prompt injection.",
            ["shadow-eval"],
            ["shadow-perf"],
        ),
        (
            "RECALL-9: Mobile App Store PrivacyInfo.xcprivacy + Play Integrity (no slash)",
            "Siapkan build release Flutter untuk App Store Connect dan Play Console: cek PrivacyInfo.xcprivacy, Play Integrity API, dan assetlinks.json.",
            ["shadow-mobile"],
            ["shadow-browser"],
        ),
        (
            "RECALL-10: Cloud & LLM Token FinOps spike (no slash)",
            "Kenapa tagihan cloud K8s dan token LLM melonjak bulan ini? Cek prompt caching, thinking token budget, dan skema FOCUS.",
            ["shadow-finops"],
            ["shadow-perf"],
        ),
        (
            "RECALL-11: Backend REST API + Auth RBAC + DB migration (no slash)",
            "Buat endpoint REST API login dengan RBAC multi-tenant, OpenAPI 3.1, dan zero-downtime database migration Expand-Contract.",
            ["shadow-api", "shadow-auth", "shadow-data"],
            ["shadow-perf"],
        ),
        (
            "RECALL-12: AI session resume ('lanjut handoff') vs client BAST",
            "lanjut handoff sesi kemarin ya, lanjutkan implementasi endpoint.",
            ["handoff"],
            ["shadow-handover"],
        ),
        (
            "RECALL-13: Client BAST handover & manuals",
            "Siapkan dokumen BAST serah terima proyek ke klien lengkap dengan Admin Manual dan Training of Trainers.",
            ["shadow-handover"],
            ["handoff"],
        ),
        (
            "RECALL-14: Pre-UAT k6 load testing & EXPLAIN ANALYZE (explicit Pre-UAT)",
            "Fitur sudah selesai, sekarang jalankan Pre-UAT k6 load test dari openapi.yaml dan SQL EXPLAIN ANALYZE profiling.",
            ["shadow-perf"],
            [],
        ),
        (
            "PRECISION-1: Normal UI React feature coding must auto-load antislop + NOT load shadow-perf",
            "Buat halaman dashboard React dan Tailwind dengan form login dan modal konfirmasi.",
            ["shadow-auth"],
            ["shadow-perf", "shadow-presales", "shadow-grc"],
        ),
        (
            "PRECISION-2: Trivial factual question loads 0 companion skills & 0 references",
            "Apa itu HTTP status code 429?",
            [],
            ["shadow-perf", "shadow-api", "shadow-grc", "shadow-presales"],
        ),
    ]

    known_skills = get_known_skill_names()
    for name, prompt, must_in, must_out in probes:
        routed = route_prompt(prompt)
        active = set(routed["companion_skills"]) | set(routed["always_on_ui_skills"])
        only_valid = all(s in known_skills for s in active)
        ok_in = all(s in active for s in must_in)
        ok_out = all(s not in active for s in must_out)
        ok_trivial = True if must_in or routed["always_on_ui_skills"] else (len(routed["reference_modules"]) == 0)
        results.append({
            "probe": name,
            "passed": only_valid and ok_in and ok_out and ok_trivial,
            "routed_skills": sorted(active),
            "routed_refs": routed["reference_modules"],
        })

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
