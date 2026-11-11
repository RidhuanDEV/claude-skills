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

    if eval_item["id"] == 18:
        for desc, pattern in EVAL_18_CHECKS:
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
                "passed": ratio >= 0.4,
                "matched_tokens": hits[:6],
                "token_coverage": round(ratio, 2),
            })

    passed_count = sum(1 for s in scored if s["passed"])
    return {
        "eval_id": eval_item["id"],
        "eval_name": eval_item["name"],
        "passed_assertions": passed_count,
        "total_assertions": len(scored),
        "score_pct": round((passed_count / len(scored)) * 100, 1) if scored else 100.0,
        "all_passed": passed_count == len(scored),
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

    all_passed = all(p["passed"] for p in probes)
    return {
        "suite": "evals/run_evals.py Self-Test (Eval #18 Precision & Recall Probes)",
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
