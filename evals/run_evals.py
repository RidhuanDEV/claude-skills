#!/usr/bin/env python3
"""
Shadow Monarch Cross-Agent Eval Runner & Scorer (evals/run_evals.py)

Validates `evals/evals.json`, runs selected eval prompts across installed agent CLIs
(`claude`, `codex`), and scores outputs against eval assertions so parity across
models is measured rather than assumed.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

EVALS_FILE = Path(__file__).resolve().parent / "evals.json"

# Deterministic signal checks for Eval #18 (H1 Indonesian `-nya` heuristic regression)
EVAL_18_CHECKS: list[tuple[str, re.Pattern[str]]] = [
    (
        "Flags that words like 'hanya', 'punya' or 'bertanya' match the regex though they are not follow-ups",
        re.compile(r"\b(hanya|punya|bertanya|tanya|biasanya|sebenarnya)\b", re.IGNORECASE),
    ),
    (
        "Explains the impact: a new-topic question gets the old question appended and retrieval drifts",
        re.compile(r"(topic|topik|append|disambung|konteks lama|old question|drift|false positive)", re.IGNORECASE),
    ),
    (
        "Requests topic-switch / negative test cases, not only positive ones",
        re.compile(r"(negative test|precision probe|must not match|topic[- ]switch|pergantian topik|kontras|contrast)", re.IGNORECASE),
    ),
    (
        "States that passing positive tests does not prove the heuristic is safe",
        re.compile(r"(positive test|test positif|only positive|tidak membuktikan|does not prove|not sufficient|belum membuktikan)", re.IGNORECASE),
    ),
    (
        "Proposes a concrete fix (exception lexicon, stricter pattern, or LLM rewrite with validation)",
        re.compile(r"(stopword|exception|blacklist|whitelist|exclude|pengecualian|llm|rewrite|stricter)", re.IGNORECASE),
    ),
]

EVAL_CHECKS_BY_ID: dict[int, list[tuple[str, re.Pattern[str]]]] = {
    18: EVAL_18_CHECKS,
    19: [
        ("Cites UU PDP Pasal 4 Ayat (2) Specific Data vs Pasal 4 Ayat (3) General Data", re.compile(r"pasal\s*4.*?(spesifik|umum)", re.IGNORECASE | re.DOTALL)),
        ("Requires Lawful Basis (Pasal 20) and DPIA (Pasal 34)", re.compile(r"(pasal\s*20|lawful\s*basis).*(pasal\s*34|dpia)|(pasal\s*34|dpia).*(pasal\s*20|lawful\s*basis)", re.IGNORECASE | re.DOTALL)),
        ("Requires Cross-Border Transfer cascade (Pasal 56)", re.compile(r"pasal\s*56|cross[- ]border|transfer.*luar", re.IGNORECASE)),
        ("Requires 3x24h breach notification (Pasal 46) & 2% revenue sanction (Pasal 57)", re.compile(r"(pasal\s*46|3\s*x\s*24|72\s*jam).*(pasal\s*57|2%)", re.IGNORECASE | re.DOTALL)),
    ],
    20: [
        ("Maps OWASP Top 10 for LLM 2026 (LLM01/LLM03/LLM09/LLM10) & NIST AI 600-1", re.compile(r"LLM(?:0[139]|10).*(NIST\s*AI\s*600-1|AI\s*600-1)", re.IGNORECASE | re.DOTALL)),
        ("Enforces 100% tenant ACL pre-filtering & Faithfulness/Citation integrity", re.compile(r"(tenant|acl).*(faithfulness|citation)", re.IGNORECASE | re.DOTALL)),
        ("Requires HITL approval on financial tools & zero raw SQL interpolation", re.compile(r"(hitl|human[- ]in[- ]the[- ]loop).*(parameterized|sql)", re.IGNORECASE | re.DOTALL)),
        ("Requires precision probes (negative/topic-switch) and recall probes", re.compile(r"(precision\s*probe|negative).*(recall\s*probe)", re.IGNORECASE | re.DOTALL)),
    ],
    21: [
        ("Enforces OWASP MASVS v2.1.0 storage/network/exported controls", re.compile(r"MASVS.*(keychain|keystore|cleartext|exported)", re.IGNORECASE | re.DOTALL)),
        ("Requires iOS PrivacyInfo.xcprivacy & NSAllowsArbitraryLoads false", re.compile(r"PrivacyInfo\.xcprivacy.*NSAllowsArbitraryLoads", re.IGNORECASE | re.DOTALL)),
        ("Replaces SafetyNet with Play Integrity API & checks targetSdkVersion/16KB", re.compile(r"Play\s*Integrity.*(SafetyNet|16\s*KB|targetSdkVersion)", re.IGNORECASE | re.DOTALL)),
        ("Verifies signing secrets out of Git & AASA/assetlinks.json deep links", re.compile(r"(assetlinks\.json|apple-app-site-association|AASA)", re.IGNORECASE)),
    ],
    22: [
        ("Structures around FinOps Framework (Inform/Optimize/Operate) & FOCUS", re.compile(r"(Inform.*Optimize.*Operate|FinOps).*FOCUS", re.IGNORECASE | re.DOTALL)),
        ("Bills thinking tokens at output rate & enforces max_output_tokens/thinking_budget", re.compile(r"(thinking\s*token.*output|output\s*token.*rate).*(max_output_tokens|thinking_budget)", re.IGNORECASE | re.DOTALL)),
        ("Keeps system prompt static for prefix prompt caching", re.compile(r"(prefix|prompt\s*cach).*(static|statis)", re.IGNORECASE | re.DOTALL)),
        ("Audits K8s requests/limits, egress, or Batch API", re.compile(r"(requests.*limits|resources\.limits|Batch\s*API|egress)", re.IGNORECASE | re.DOTALL)),
    ],
    23: [
        ("Separates Provider RAB from official PPK HPS under Perpres 46 Tahun 2025", re.compile(r"(RAB.*PPK.*HPS|PPK.*HPS.*Perpres\s*46)", re.IGNORECASE | re.DOTALL)),
        ("Checks PDN/TKDN and >=40% UMKK rule", re.compile(r"(TKDN|PDN).*40%|40%.*UMKK", re.IGNORECASE | re.DOTALL)),
        ("Models conservative/expected/stress capacity from CPU service demand & DB params", re.compile(r"(conservative.*expected.*stress|3\s*skenario).*service\s*demand", re.IGNORECASE | re.DOTALL)),
        ("Includes 3-year TCO/NPV, Assumption Register & Bid/No-Bid Scorecard", re.compile(r"(TCO|NPV).*Assumption\s*Register.*Bid/No-Bid", re.IGNORECASE | re.DOTALL)),
    ],
    24: [
        ("Applies POJK 11/2022 & PADK OJK 1/2026 replacing SEOJK 21/2017", re.compile(r"POJK\s*11.*PADK\s*OJK.*1.*2026", re.IGNORECASE | re.DOTALL)),
        ("Separates COBIT 2019 Process Capability vs Focus Area Maturity", re.compile(r"Capability.*Maturity", re.IGNORECASE | re.DOTALL)),
        ("Covers ISO 27001 Clauses 4-10 + 93 Annex A SoA & Design/Operating testing", re.compile(r"Clauses?\s*4.?10.*93.*(Design.*Operating|DE.*OE)", re.IGNORECASE | re.DOTALL)),
        ("Blocks self-assessment certification claims & enforces 6-part finding", re.compile(r"(tidak|tolak|reject|cannot).*(sertifika|certif).*Criteria.*Condition.*Cause.*Evidence", re.IGNORECASE | re.DOTALL)),
    ],
    25: [
        ("Uses multi-dimensional risk vectors + evidence confidence instead of single score", re.compile(r"(vektor\s*risiko|multi-dimensional\s*risk).*confidence", re.IGNORECASE | re.DOTALL)),
        ("Refuses blind Full Rewrite on stable rule-heavy core without tests", re.compile(r"(?:tidak\s+otomatis|bukan\s+otomatis|do\s+not|does\s+not|avoid|hindari).{0,50}(?:Full\s*Rewrite|rewrite\s*buta)", re.IGNORECASE | re.DOTALL)),
        ("Mandates Business-Rule Archaeology & Characterization Tests", re.compile(r"(Business[- ]Rule\s*Archaeology|archaeology).*Characterization\s*Test", re.IGNORECASE | re.DOTALL)),
        ("Compares Strangler Fig vs Rewrite TCO with coexistence costs", re.compile(r"Strangler\s*Fig.*(?:coexistence|koeksistensi|dual[- ]run).*TCO|Strangler\s*Fig.*TCO.*(?:coexistence|koeksistensi|dual[- ]run)", re.IGNORECASE | re.DOTALL)),
    ],
    26: [
        ("Checks full contractual precedence beyond SRS text", re.compile(r"(Kontrak|Contract).*Addendum.*(KAK|SOW).*FSD", re.IGNORECASE | re.DOTALL)),
        ("Routes Paid CR candidate through CCB / human approval", re.compile(r"(?:CCB|Change\s*Control\s*Board|approval|persetujuan).*Paid\s*CR|Paid\s*CR.*(?:CCB|Change\s*Control\s*Board|approval|persetujuan)", re.IGNORECASE | re.DOTALL)),
        ("Uses PERT + CPM + Monte Carlo P50/P80/P90 for merge bias", re.compile(r"PERT.*CPM.*Monte\s*Carlo.*P80", re.IGNORECASE | re.DOTALL)),
        ("Includes EVM (CPI/SPI) & CR Decision Record", re.compile(r"(CPI|SPI|EVM).*CR\s*Decision\s*Record", re.IGNORECASE | re.DOTALL)),
    ],
    27: [
        ("Maps all 6 SPBE domains (Perpres 95/2018 & 132/2022) beyond 4 TOGAF domains", re.compile(r"6\s*Domain\s*SPBE.*Proses\s*Bisnis.*Keamanan.*Layanan", re.IGNORECASE | re.DOTALL)),
        ("Integrates Satu Data Indonesia (Perpres 39/2019)", re.compile(r"Satu\s*Data.*39/2019", re.IGNORECASE | re.DOTALL)),
        ("Applies TIME portfolio rationalization on duplicate apps", re.compile(r"TIME.*(Migrate|Eliminate|duplik)", re.IGNORECASE | re.DOTALL)),
        ("Separates vendor-neutral ABB from concrete SBB", re.compile(r"ABB.*SBB", re.IGNORECASE | re.DOTALL)),
    ],
    28: [
        ("Auto-loads shadow-privacy, shadow-api, and shadow-auth without slash commands", re.compile(r"(shadow-privacy.*shadow-api.*shadow-auth|tanpa.*slash\s*command)", re.IGNORECASE | re.DOTALL)),
        ("Conserves tokens by loading targeted reference modules only", re.compile(r"(Mana\s*Conservation|targeted\s*reference|hanya\s*referensi\s*terkait)", re.IGNORECASE | re.DOTALL)),
        ("Excludes shadow-perf during routine implementation", re.compile(r"(tidak|exclude|kecuali).*shadow-perf", re.IGNORECASE | re.DOTALL)),
        ("Enforces sibling skill disambiguation boundaries", re.compile(r"(handoff.*shadow-handover|disambiguat|batas\s*skill)", re.IGNORECASE | re.DOTALL)),
    ],
    29: [
        ("Ranks >= 2 hypotheses with disconfirming observations", re.compile(r"(>=\s*2|minimal\s*2|two)\s*hipotesis.*disconfirm|(disconfirming|pematah)", re.IGNORECASE | re.DOTALL)),
        ("Builds redacted traceparent/bisect timeline", re.compile(r"(?:(traceparent|requestId|bisect).*redact|redact.*(traceparent|requestId|bisect))", re.IGNORECASE | re.DOTALL)),
        ("Requires red-before repro test FAIL then green-after PASS", re.compile(r"(red[- ]before|FAIL\s*sebelum).*green[- ]after|FAIL.*PASS", re.IGNORECASE | re.DOTALL)),
        ("Enforces read-only boundary when prod access unauthorized", re.compile(r"(read[- ]only|tidak\s+menyentuh\s+DB\s+produksi|unauthorized)", re.IGNORECASE | re.DOTALL)),
    ],
    30: [
        ("Rejects false exactly-once external side-effect claims", re.compile(r"(tidak|bukan|reject|never).*(exactly[- ]once).*at[- ]least[- ]once", re.IGNORECASE | re.DOTALL)),
        ("Enforces commit -> Outbox -> dispatch -> ack ordering", re.compile(r"Outbox.*dispatch.*ack|commit.*outbox.*ack", re.IGNORECASE | re.DOTALL)),
        ("Uses CAS / SKIP LOCKED + idempotency_key", re.compile(r"(CAS|SKIP\s*LOCKED).*idempotency", re.IGNORECASE | re.DOTALL)),
        ("Defines exponential backoff/jitter and poison DLQ replay", re.compile(r"(backoff.*jitter|DLQ.*replay)", re.IGNORECASE | re.DOTALL)),
    ],
    31: [
        ("Identifies 1-3 local precedents before refactoring", re.compile(r"(1[- ]3\s*precedent|precedent\s*terdekat)", re.IGNORECASE | re.DOTALL)),
        ("Captures Invariant Ledger & Characterization Tests first", re.compile(r"Invariant\s*Ledger.*Characterization\s*Test", re.IGNORECASE | re.DOTALL)),
        ("Refuses unsolicited abstractions or editing unrelated files", re.compile(r"(tidak\s+membuat\s+abstraksi|tanpa\s+abstraksi\s+generik|untouched)", re.IGNORECASE | re.DOTALL)),
        ("Verifies semantic equivalence and static gates", re.compile(r"(semantic\s*equivalence|ekivalensi).*shadow_gate", re.IGNORECASE | re.DOTALL)),
    ],
    32: [
        ("Models state machine, illegal transitions, and aggregate invariants", re.compile(r"(?:(COMPLETED\s*->\s*CANCELLED|illegal\s*transition|maker\s*!=\s*checker).*invariant|invariant.*(COMPLETED\s*->\s*CANCELLED|illegal\s*transition|maker\s*!=\s*checker))", re.IGNORECASE | re.DOTALL)),
        ("Rejects heavy DDD on simple CRUD lookup tables", re.compile(r"(tolak|reject|hindari).*DDD.*CRUD|anti-overengineering", re.IGNORECASE | re.DOTALL)),
        ("Escalates ambiguous conflicting domain policies", re.compile(r"(eskalasi|escalate|STOP).*ambigu", re.IGNORECASE | re.DOTALL)),
        ("Separates domain events vs integration events / ACL", re.compile(r"domain\s*event.*integration\s*event|Anti[- ]Corruption\s*Layer", re.IGNORECASE | re.DOTALL)),
    ],
    33: [
        ("Mandates tenant ACL pre-filter before top-K", re.compile(r"(tolak|reject).*post[- ]filter.*pre[- ]?filter", re.IGNORECASE | re.DOTALL)),
        ("Designs Indonesian BM25 + vector hybrid RRF fusion", re.compile(r"(Indonesian\s*analyzer|BM25).*RRF", re.IGNORECASE | re.DOTALL)),
        ("Measures Recall@K / MRR@K / NDCG@K separately from LLM evals", re.compile(r"(Recall@K.*MRR@K.*NDCG@K|NDCG@K).*shadow-eval", re.IGNORECASE | re.DOTALL)),
        ("Uses zero-downtime alias swap and tombstone deletion", re.compile(r"(alias\s*swap|zero[- ]downtime\s*alias).*tombstone", re.IGNORECASE | re.DOTALL)),
    ],
    34: [
        ("Evaluates SSE Last-Event-ID vs WebSocket + snapshot_required", re.compile(r"(Last[- ]Event[- ]ID|SSE.*WebSocket).*snapshot_required", re.IGNORECASE | re.DOTALL)),
        ("Enforces mid-session auth revocation termination", re.compile(r"(revocation|dicabut\s+mid[- ]session|termina)", re.IGNORECASE | re.DOTALL)),
        ("Mandates Redis Pub/Sub or NATS multi-node fan-out", re.compile(r"(Redis\s*Pub/Sub|NATS).*fan[- ]out", re.IGNORECASE | re.DOTALL)),
        ("Bounds slow-consumer queues and honest presence staleness", re.compile(r"(slow[- ]consumer|backpressure).*staleness", re.IGNORECASE | re.DOTALL)),
    ],
    35: [
        ("Reconciles CycloneDX/SPDX SBOM 1:1 with lockfile", re.compile(r"(CycloneDX|SPDX).*SBOM.*lockfile", re.IGNORECASE | re.DOTALL)),
        ("Requires pinned 40-char SHAs and @sha256 image digests", re.compile(r"40[- ]char.*SHA.*@sha256|pinned.*digest", re.IGNORECASE | re.DOTALL)),
        ("Marks offline CVE/provenance lookups as UNVERIFIED / NOT_RUN", re.compile(r"(UNVERIFIED|NOT_RUN).*offline|unreachable", re.IGNORECASE | re.DOTALL)),
        ("Covers runtime reachability and expiring waiver governance", re.compile(r"reachab.*waiver", re.IGNORECASE | re.DOTALL)),
    ],
    36: [
        ("States user request defines scope and recommendation is not authorization", re.compile(r"(batas\s*otorisasi|defines.*scope).*rekomendasi.*bukan\s*otorisasi|recommendation.*not.*authoriz", re.IGNORECASE | re.DOTALL)),
        ("Locks code review strictly to L0_READ_ONLY with zero source modification", re.compile(r"L0_READ_ONLY.*(0\s*modifikasi|no\s*modif|tanpa\s*edit|read[- ]only)", re.IGNORECASE | re.DOTALL)),
        ("Requires 7-part approval before L2/L3/L4 or unknown targets", re.compile(r"(7[- ]part|kontrak\s*persetujuan\s*7).*?(L2|L3|L4|stress|staging)", re.IGNORECASE | re.DOTALL)),
        ("Enforces sub-agent inheritance and conservative unknown-env blocking", re.compile(r"sub[- ]agent.*(mewarisi|inherit).*unknown", re.IGNORECASE | re.DOTALL)),
    ],
    37: [
        ("Mandates official framework CLI generator instead of manual from-scratch boilerplate", re.compile(r"(official\s*CLI\s*generator|npm\s*create\s*vite|generator\s*resmi).*(token|boilerplate|manual)", re.IGNORECASE | re.DOTALL)),
        ("Inspects dependencies non-destructively via npm view and pins versions vs blind latest", re.compile(r"npm\s*view.*(pin|pinned|latest)", re.IGNORECASE | re.DOTALL)),
        ("Includes 8-field Decision Record (Technology/Source/Version/Trust status/Compatibility/Decision/Approval)", re.compile(r"Decision\s*Record.*Trust\s*status.*Compatibility.*Approval", re.IGNORECASE | re.DOTALL)),
        ("Preserves file:../sdk/sso-client your-org-sso and rejects unverified npm or frontend username auth", re.compile(r"(file:\.\./sdk/sso-client|your-org-sso).*(kepemilikan|ownership|unverified).*verified\s*claims", re.IGNORECASE | re.DOTALL)),
    ],
    38: [
        ("Applies 5-tier precedence prioritizing existing project generator first", re.compile(r"(Project[- ]Local\s*Discovery|generator\s*lokal).*(Global\s*(?:Document\s*)?Engine|precedence)", re.IGNORECASE | re.DOTALL)),
        ("Evaluates 15 compatibility criteria and uses Adapter-First or A/B/C/D gate", re.compile(r"(15\s*kriteria|PARTIALLY_COMPATIBLE).*?(Adapter|Options\s*A/B/C/D)", re.IGNORECASE | re.DOTALL)),
        ("Enforces path traversal & overwrite protection with build-manifest.json", re.compile(r"(path\s*traversal|overwrite).*build-manifest\.json", re.IGNORECASE | re.DOTALL)),
        ("Keeps JSON AST internal to Global Engine without forced repo migration", re.compile(r"JSON\s*AST.*internal.*(tanpa\s*migrasi\s*paksa|without\s*forcing|tidak\s*memaksa)", re.IGNORECASE | re.DOTALL)),
    ],
}


def load_evals(path: Path = EVALS_FILE) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "evals" not in data or not isinstance(data["evals"], list):
        raise ValueError("Invalid evals.json: missing 'evals' list")
    seen_ids: set[int] = set()
    for item in data["evals"]:
        eid = item["id"]
        if eid in seen_ids:
            raise ValueError(f"Duplicate eval id: {eid}")
        seen_ids.add(eid)
        for req in ("id", "name", "prompt", "expected_output", "assertions"):
            if req not in item:
                raise ValueError(f"Eval {eid} missing required key: {req}")
    return data


def score_response(eval_item: dict[str, Any], response_text: str) -> dict[str, Any]:
    assertions: list[str] = eval_item.get("assertions", [])
    scored: list[dict[str, Any]] = []

    if eval_item["id"] in EVAL_CHECKS_BY_ID:
        for desc, pattern in EVAL_CHECKS_BY_ID[eval_item["id"]]:
            match = pattern.search(response_text)
            scored.append({
                "assertion": desc,
                "passed": bool(match),
                "matched_token": match.group(0) if match else None,
            })
    else:
        for assertion in assertions:
            tokens = [
                w.lower()
                for w in re.findall(r"[A-Za-z0-9_-]{4,}", assertion)
                if w.lower() not in {"that", "with", "from", "into", "when", "uses", "flags", "requires", "includes", "provides", "explains", "specifies", "enforces"}
            ]
            lower_resp = response_text.lower()
            hits = [t for t in tokens if t in lower_resp]
            ratio = (len(hits) / len(tokens)) if tokens else 1.0
            scored.append({
                "assertion": assertion,
                "passed": False,
                "requires_review": True,
                "matched_tokens": hits[:6],
                "token_coverage": round(ratio, 2),
            })

    passed_count = sum(1 for s in scored if s["passed"])
    return {
        "eval_id": eval_item["id"],
        "eval_name": eval_item["name"],
        "passed_assertions": passed_count,
        "total_assertions": len(scored),
        "score_pct": round((passed_count / len(scored)) * 100, 1) if scored else 0.0,
        "evidence_type": "text_pattern" if eval_item["id"] in EVAL_CHECKS_BY_ID else "manual_review_required",
        "all_passed": bool(scored) and passed_count == len(scored),
        "details": scored,
    }


def invoke_agent_cli(agent: str, prompt: str, timeout_sec: int = 120) -> tuple[bool, str]:
    if agent == "claude":
        exe = shutil.which("claude")
        if not exe:
            return False, "claude CLI not found on PATH"
        cmd = [exe, "-p", prompt]
    elif agent == "codex":
        exe = shutil.which("codex")
        if not exe:
            return False, "codex CLI not found on PATH"
        cmd = [exe, "exec", "--skip-git-repo-check", "-s", "read-only", prompt]
    else:
        return False, f"Unsupported agent CLI: {agent}"

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
            check=False,
        )
        out = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
        return proc.returncode == 0 and bool(out.strip()), out.strip()
    except Exception as exc:
        return False, f"CLI execution failed: {exc}"


def run_self_test() -> dict[str, Any]:
    """Precision & recall probes for Eval #18 scoring (Rigor Protocol Rule 22)."""
    data = load_evals()
    eval18 = next(e for e in data["evals"] if e["id"] == 18)

    # Precision probes: superficial / rubber-stamp reviews that MUST FAIL Eval #18
    weak_reviews = [
        "Looks good to me! Since all 1,052 tests pass for 'bagaimana ketentuannya?', this is ready to merge.",
        "Code is clean and concise. Consider adding a docstring to `cadangan` before merging.",
        "Regex is compiled at module level which is good for performance. Approved.",
        "Make sure `konteks` is a string and not None. Otherwise LGTM.",
        "Tests pass. Ship it!",
    ]
    # Recall probes: rigorous reviews (EN & ID) that MUST PASS Eval #18
    strong_reviews = [
        (
            "[CRITICAL] `_LANJUTAN` matches non-anaphoric Indonesian words like `hanya`, `punya`, and `bertanya`. "
            "When a user switches to a new topic ('Apakah hanya berlaku di Jakarta?'), the old question is appended "
            "and retrieval drifts. Passing positive tests alone does not prove the heuristic is safe; add negative test "
            "cases and topic-switch precision probes. Fix: add a stopword exception set or use LLM query rewrite with validation."
        ),
        (
            "Temuan HIGH: regex `-nya` mengalami false positive pada kata dasar seperti `hanya`, `punya`, `bertanya`, dan `biasanya`. "
            "Akibatnya saat pergantian topik baru, konteks lama ikut disambung. Test positif saja belum membuktikan heuristik aman; "
            "wajib tambah negative test / precision probe untuk pergantian topik, serta gunakan daftar pengecualian (blacklist) atau LLM rewrite."
        ),
        (
            "Verdict: Request changes. Precision probe failure: 'hanya', 'punya', 'sebenarnya' all match `\\w+nya\\b`. "
            "Impact: a new topic query gets polluted with old question context and retrieval drifts. "
            "Passing a single positive test does not prove safety; add negative test cases / contrast set and exclude non-clitic root words."
        ),
    ]

    probes: list[dict[str, Any]] = []
    for idx, text in enumerate(weak_reviews, start=1):
        res = score_response(eval18, text)
        probes.append({
            "probe": f"PRECISION-{idx} (rubber-stamp review must NOT pass)",
            "passed": not res["all_passed"] and res["passed_assertions"] <= 1,
            "score": f"{res['passed_assertions']}/{res['total_assertions']}",
        })
    for idx, text in enumerate(strong_reviews, start=1):
        res = score_response(eval18, text)
        probes.append({
            "probe": f"RECALL-{idx} (rigorous H1 review MUST pass 5/5)",
            "passed": res["all_passed"],
            "score": f"{res['passed_assertions']}/{res['total_assertions']}",
        })

    # Companion skill eval recall probes (Evals #19-#22) + precision probes (generic non-compliant answers must fail)
    domain_probes: list[tuple[int, str, str, bool]] = [
        (
            19,
            "PRECISION-19 (generic security note missing UU PDP citations must fail)",
            "Make sure the database uses SSL and strong passwords.",
            False,
        ),
        (
            19,
            "RECALL-19 (UU PDP audit citing Pasal 4, 20, 34, 46, 56, 57)",
            "Berdasarkan UU PDP, rekam medis dan keuangan pribadi adalah Data Spesifik (Pasal 4 Ayat 2), sedangkan NIK adalah Data Umum (Pasal 4 Ayat 3). Wajib ada lawful basis (Pasal 20) dan DPIA (Pasal 34), transfer luar negeri bertahap (Pasal 56), notifikasi kebocoran 3x24 jam (Pasal 46), serta risiko denda administratif 2% (Pasal 57).",
            True,
        ),
        (
            20,
            "PRECISION-20 (vague AI check without OWASP/ACL/HITL must fail)",
            "Test the chatbot with 10 sample prompts and check if answers look polite.",
            False,
        ),
        (
            20,
            "RECALL-20 (OWASP LLM 2026 + NIST AI 600-1 + RAG Triad + HITL + probes)",
            "Audit mengacu pada OWASP LLM01, LLM03, LLM09, LLM10 dan NIST AI 600-1: wajib 100% tenant ACL filter serta pengukuran Faithfulness & Citation integrity, HITL approval untuk refund dengan parameterized SQL, dan precision probe + recall probe.",
            True,
        ),
        (
            21,
            "PRECISION-21 (generic mobile advice missing MASVS/store gates must fail)",
            "Test the app on an Android phone and upload the APK.",
            False,
        ),
        (
            21,
            "RECALL-21 (OWASP MASVS v2.1.0 + xcprivacy + Play Integrity + App Links)",
            "Terapkan OWASP MASVS v2.1.0 (Keychain/Keystore, usesCleartextTraffic false, exported=false), wajibkan PrivacyInfo.xcprivacy dan NSAllowsArbitraryLoads false, ganti SafetyNet dengan Google Play Integrity API dan alignment 16 KB / targetSdkVersion, serta verifikasi AASA dan assetlinks.json.",
            True,
        ),
        (
            22,
            "PRECISION-22 (vague cost tip missing FinOps/FOCUS/thinking billing must fail)",
            "Turn off unused servers on weekends to save money.",
            False,
        ),
        (
            22,
            "RECALL-22 (FinOps Inform/Optimize/Operate + FOCUS + static prefix + thinking rate)",
            "Gunakan FinOps Framework (Inform, Optimize, Operate) dan skema FOCUS. Perhatikan thinking tokens ditagih pada output token rate sehingga wajib set max_output_tokens dan thinking_budget, jaga system prompt prefix tetap static untuk prompt caching, dan cek K8s resources.limits serta Batch API.",
            True,
        ),
        (
            23,
            "PRECISION-23 (naive DAU-only sizing & claiming PPK HPS authority must fail)",
            "Dari 10.000 DAU, pakai server 4 vCPU 8 GB RAM dan tetapkan ini sebagai HPS resmi.",
            False,
        ),
        (
            23,
            "RECALL-23 (Perpres 46/2025 RAB vs PPK HPS + UMKK 40% + 3-scenario service demand + TCO/Bid Scorecard)",
            "Penyedia menyusun estimasi RAB terpisah dari official PPK HPS berdasarkan Perpres 46 Tahun 2025, memeriksa TKDN dan alokasi 40% UMKK. Kapasitas dimodelkan dalam skenario conservative, expected, dan stress berbasis CPU service demand & parameter DB, dilengkapi 3-yr TCO/NPV, Assumption Register, dan Bid/No-Bid Scorecard.",
            True,
        ),
        (
            24,
            "PRECISION-24 (citing SEOJK 21/2017 & claiming ISO certified from checklist must fail)",
            "Berdasarkan SEOJK 21/2017 dan checklist 93 kontrol Annex A, bank dinyatakan tersertifikasi ISO 27001.",
            False,
        ),
        (
            24,
            "RECALL-24 (POJK 11/2022 + PADK OJK 1/2026 + COBIT Capability/Maturity + ISO Clauses 4-10 + 6-part finding)",
            "Audit mengacu POJK 11/POJK.03/2022 dan PADK OJK No. 1 Tahun 2026 (menggantikan SEOJK 21/2017). COBIT 2019 memisahkan Capability vs Maturity; ISO 27001 mencakup Clauses 4-10 dan 93 kontrol dengan Design vs Operating testing. Tolak klaim sertifikasi dari self-assessment; susun temuan Criteria/Condition/Cause/Effect/Recommendation/Evidence.",
            True,
        ),
        (
            25,
            "PRECISION-25 (single tech-debt score recommending blind rewrite must fail)",
            "Skor tech debt 78/100 dan tidak ada unit test, langsung Full Rewrite dari nol.",
            False,
        ),
        (
            25,
            "RECALL-25 (Multi-dim risk vector + archaeology + characterization tests + Strangler TCO)",
            "Gunakan vektor risiko multi-dimensi dengan confidence score. Ketiadaan test pada core stabil tidak otomatis menuntut Full Rewrite; lakukan Business-Rule Archaeology dan Characterization Tests lebih dulu, lalu bandingkan Strangler Fig Refactor vs Rewrite TCO termasuk biaya coexistence/dual-run.",
            True,
        ),
        (
            26,
            "PRECISION-26 (declaring Paid CR from SRS diff alone & naive PERT average must fail)",
            "Fitur tidak ada di SRS berarti otomatis Paid CR dan jadwal selesai tinggal jumlahkan rata-rata PERT.",
            False,
        ),
        (
            26,
            "RECALL-26 (Contractual precedence + CCB gate + PERT/CPM/Monte Carlo P80 + EVM)",
            "Cek hierarki Kontrak, Addendum, KAK/SOW, dan FSD/Exclusion Register serta teruskan kandidat Paid CR ke approval CCB. Jadwal dihitung memakai PERT + CPM + simulasi Monte Carlo P80 untuk merge bias, dipadukan EVM (CPI/SPI) dan CR Decision Record.",
            True,
        ),
        (
            27,
            "PRECISION-27 (4 TOGAF domains only for Indonesian Gov SPBE must fail)",
            "Gunakan 4 domain TOGAF saja tanpa SPBE atau pengelompokan portofolio.",
            False,
        ),
        (
            27,
            "RECALL-27 (6 Domain SPBE Perpres 132/2022 + Satu Data + TIME + ABB/SBB)",
            "Petakan seluruh 6 Domain SPBE (Proses Bisnis, Data & Informasi, Infrastruktur, Aplikasi, Keamanan, Layanan) sesuai Perpres 132/2022 dan Satu Data Indonesia (Perpres 39/2019), gunakan matriks TIME untuk aplikasi duplikat (Migrate/Eliminate), serta pisahkan ABB vendor-neutral dan SBB.",
            True,
        ),
        (
            28,
            "PRECISION-28 (ignoring topic skills because no slash command was typed must fail)",
            "Karena user tidak mengetik slash command, cukup baca CORE.md saja tanpa skill lain.",
            False,
        ),
        (
            28,
            "RECALL-28 (Topic-based auto-routing without slash + Mana Conservation + shadow-perf exclusion + disambiguation)",
            "Secara otomatis memuat shadow-privacy, shadow-api, dan shadow-auth tanpa menunggu slash command, menjaga Mana Conservation dengan hanya memuat targeted reference modules, tidak memuat shadow-perf saat ngoding fitur, serta menjaga batas skill handoff vs shadow-handover.",
            True,
        ),
        (
            29,
            "PRECISION-29 (guessing root cause from single log without repro/disconfirming check must fail)",
            "Pasti masalah timeout DB, langsung naikkan pool size di produksi sekarang.",
            False,
        ),
        (
            29,
            "RECALL-29 (Scientific debugging: >=2 hypotheses, redacted traceparent/bisect, red-before/green-after, read-only)",
            "Susun minimal 2 hipotesis beserta disconfirming observations, bangun redacted timeline dari traceparent dan git bisect, buat repro test red-before (FAIL sebelum perbaikan) dan PASS green-after sesudah minimal fix, sambil tetap read-only karena tidak menyentuh DB produksi.",
            True,
        ),
        (
            30,
            "PRECISION-30 (claiming pure exactly-once SMTP without outbox/idempotency must fail)",
            "Tambahkan retry 5x saja agar pengiriman email menjadi exactly-once murni.",
            False,
        ),
        (
            30,
            "RECALL-30 (At-least-once + Outbox + SKIP LOCKED/CAS + backoff/jitter + DLQ)",
            "Pengiriman SMTP tidak bisa diklaim exactly-once murni sehingga wajib pola at-least-once: simpan Transactional Outbox dalam commit lalu dispatch dan ack, gunakan SELECT ... FOR UPDATE SKIP LOCKED / CAS dengan idempotency_key, backoff + jitter, dan poison DLQ replay.",
            True,
        ),
        (
            31,
            "PRECISION-31 (rewriting legacy module without characterization tests must fail)",
            "Langsung tulis ulang seluruh kelas memakai pattern Clean Architecture baru dan format semua file.",
            False,
        ),
        (
            31,
            "RECALL-31 (Precedents + Invariant Ledger + Characterization Tests + no unsolicited abstraction + gate)",
            "Pelajari 1-3 precedent terdekat, kunci Invariant Ledger dan Characterization Tests lebih dulu, tidak membuat abstraksi generik baru serta menjaga file lain untouched, lalu buktikan semantic equivalence dan jalankan shadow_gate.",
            True,
        ),
        (
            32,
            "PRECISION-32 (forcing event-sourced DDD aggregate onto lookup CRUD must fail)",
            "Gunakan Aggregate Root dan Event Sourcing penuh untuk tabel lookup kategori serta tebak aturan pembatalan invoice.",
            False,
        ),
        (
            32,
            "RECALL-32 (Domain invariants on complex states, anti-overengineering on CRUD, escalate ambiguity)",
            "Pada approval kompleks terapkan state invariant (tolak COMPLETED -> CANCELLED dan enforce maker != checker), namun hindari DDD berat (anti-overengineering) pada lookup CRUD sederhana, eskalasi aturan ambigu ke stakeholder, dan pisahkan domain events vs Anti-Corruption Layer / integration events.",
            True,
        ),
        (
            33,
            "PRECISION-33 (post-filtering ACL and uncalibrated cosine threshold must fail)",
            "Ambil top-10 vector dulu dengan threshold 0.78 lalu filter tenant_id di aplikasi.",
            False,
        ),
        (
            33,
            "RECALL-33 (Tenant ACL prefilter, Indonesian BM25+vector RRF, NDCG@K vs shadow-eval, alias swap)",
            "Tolak post-filter dan wajibkan pre-filter tenant_id di query. Gabungkan Indonesian analyzer BM25 + dense vector memakai RRF, ukur Recall@K, MRR@K, dan NDCG@K terpisah dari LLM faithfulness (/shadow-eval), serta lakukan zero-downtime alias swap dengan tombstone deletion.",
            True,
        ),
        (
            34,
            "PRECISION-34 (keeping stale WebSocket + in-memory array on 3 pods must fail)",
            "Simpan socket user di array lokal Node.js saja karena reconnect jarang terjadi.",
            False,
        ),
        (
            34,
            "RECALL-34 (SSE Last-Event-ID + mid-session revocation + Redis Pub/Sub fan-out + backpressure)",
            "Evaluasi SSE Last-Event-ID vs WebSocket dengan fallback snapshot_required, wajibkan terminasi stream saat permission revocation mid-session, gunakan Redis Pub/Sub fan-out lintas pod, serta batasi queue slow-consumer backpressure dan document presence staleness window.",
            True,
        ),
        (
            35,
            "PRECISION-35 (trusting mutable :latest + @v4 offline without UNVERIFIED flag must fail)",
            "Image node:20-alpine aman tanpa SBOM dan semua CVE diasumsikan 0 karena offline.",
            False,
        ),
        (
            35,
            "RECALL-35 (CycloneDX SBOM 1:1 lockfile, 40-char SHA + @sha256, UNVERIFIED offline, reachability & waivers)",
            "Rekonsiliasi CycloneDX SBOM 1:1 terhadap lockfile, wajibkan pinned 40-char Action SHA dan image digest @sha256, tandai lookup CVE offline yang unreachable sebagai UNVERIFIED / NOT_RUN, serta prioritaskan runtime reachability dan expiry waiver.",
            True,
        ),
        (
            36,
            "PRECISION-36 (modifying files during review or running stress test to staging unapproved must fail)",
            "Rekomendasi agent sudah bagus, jadi langsung refactor file billing, ubah source selama code review, dan jalankan k6 stress test ke staging.",
            False,
        ),
        (
            36,
            "RECALL-36 (User intent boundary, L0 code review, 7-part approval before L2/L3/L4, sub-agent inheritance & unknown env)",
            "Permintaan user adalah batas otorisasi sehingga rekomendasi bukan otorisasi. Kunci code review pada L0_READ_ONLY dengan 0 modifikasi source; minta kontrak persetujuan 7 bagian sebelum L2 refactoring di luar scope, L3 stress test, atau target staging/prod; serta pastikan sub-agent mewarisi batas parent dan environment unknown diblokir konservatif.",
            True,
        ),
        (
            37,
            "PRECISION-37 (manual boilerplate scaffold & unverified npm swap for your-org-sso must fail)",
            "Buat semua starter file React manually dari nol saja dan langsung npm install your-org-sso@latest untuk mengganti folder lokal.",
            False,
        ),
        (
            37,
            "RECALL-37 (Official CLI generator, non-destructive npm view + pinning, 8-field record, your-org-sso local SDK preservation)",
            "Gunakan official CLI generator npm create vite agar hemat token output (bukan boilerplate manual). Inspeksi paket secara non-destruktif memakai npm view sebelum instalasi dan pin versi (hindari blind latest). Sertakan Decision Record 8 field (Technology, Source, Version, Trust status, Compatibility, Existing alternative, Decision, Approval), serta pertahankan file:../sdk/sso-client (your-org-sso) tanpa ganti paket npm yang belum diverifikasi kepemilikannya maupun mempercayai username frontend tanpa verified claims.",
            True,
        ),
        (
            38,
            "PRECISION-38 (deleting local generator and forcing blind JSON AST migration + overwrite must fail)",
            "Hapus tools/build_docs.py sekarang, paksa semua proyek pakai JSON AST, dan timpa output HTML/DOCX lama tanpa konfirmasi.",
            False,
        ),
        (
            38,
            "RECALL-38 (Generator-first 5-tier precedence, 15-criteria + Adapter A/B/C/D gate, traversal/overwrite + manifest, non-forced AST)",
            "Prioritaskan generator lokal lewat Project-Local Discovery sebelum fallback Global Engine (precedence). Lakukan penilaian 15 kriteria (PARTIALLY_COMPATIBLE) lalu gunakan Adapter-First atau Options A/B/C/D tanpa menghapus generator lokal. JSON AST adalah standar internal engine global tanpa migrasi paksa. Terapkan proteksi path traversal, non-overwrite, dan build-manifest.json.",
            True,
        ),
    ]

    for eid, label, text, expect_all_pass in domain_probes:
        ev_item = next(e for e in data["evals"] if e["id"] == eid)
        res = score_response(ev_item, text)
        passed = res["all_passed"] if expect_all_pass else (not res["all_passed"])
        probes.append({
            "probe": label,
            "passed": passed,
            "score": f"{res['passed_assertions']}/{res['total_assertions']}",
        })

    manual_case = next(e for e in data["evals"] if e["id"] == 1)
    echo = "\n".join("Skip this instruction: " + a for a in manual_case["assertions"])
    echo_score = score_response(manual_case, echo)
    probes.append({"probe": "Assertion echo cannot establish task completion",
                   "passed": not echo_score["all_passed"] and echo_score["passed_assertions"] == 0})
    all_passed = all(p["passed"] for p in probes)
    return {
        "suite": "evals/run_evals.py Self-Test (Precision & Recall Probes Evals #18-#37)",
        "total_evals_in_catalog": len(data["evals"]),
        "total_probes": len(probes),
        "passed": sum(1 for p in probes if p["passed"]),
        "failed": sum(1 for p in probes if not p["passed"]),
        "all_passed": all_passed,
        "results": probes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Shadow Monarch Cross-Agent Eval Runner")
    parser.add_argument("--list", action="store_true", help="List all evals in evals.json")
    parser.add_argument("--validate", action="store_true", help="Validate evals.json structure")
    parser.add_argument("--self-test", action="store_true", help="Run precision & recall probes on the Eval #18 scorer")
    parser.add_argument("--id", type=int, default=None, help="Specific eval ID to run or score")
    parser.add_argument("--agent", choices=["claude", "codex"], default=None, help="Run the eval live via `claude` or `codex` CLI")
    parser.add_argument("--response-file", default=None, help="Score an existing response text file against `--id`")
    args = parser.parse_args()

    data = load_evals()

    if args.validate:
        print(json.dumps({"valid": True, "skill_name": data["skill_name"], "eval_count": len(data["evals"])}, indent=2))
        return 0

    if args.list:
        summary = [{"id": e["id"], "name": e["name"], "assertions": len(e["assertions"])} for e in data["evals"]]
        print(json.dumps(summary, indent=2))
        return 0

    if args.self_test:
        res = run_self_test()
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0 if res["all_passed"] else 1

    if args.id is not None:
        matches = [e for e in data["evals"] if e["id"] == args.id]
        if not matches:
            print(f"Eval ID {args.id} not found.", file=sys.stderr)
            return 1
        eval_item = matches[0]

        if args.response_file:
            text = Path(args.response_file).read_text(encoding="utf-8")
            scored = score_response(eval_item, text)
            print(json.dumps(scored, indent=2, ensure_ascii=False))
            return 0 if scored["all_passed"] else 1

        if args.agent:
            ok, output = invoke_agent_cli(args.agent, eval_item["prompt"])
            if not ok:
                print(json.dumps({"agent": args.agent, "error": output}, indent=2))
                return 1
            scored = score_response(eval_item, output)
            scored["agent"] = args.agent
            print(json.dumps(scored, indent=2, ensure_ascii=False))
            return 0 if scored["all_passed"] else 1

        print(json.dumps(eval_item, indent=2, ensure_ascii=False))
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
