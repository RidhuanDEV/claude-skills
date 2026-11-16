#!/usr/bin/env python3
"""
Shadow FinOps Cost Auditor & LLM Token Economics Estimator (finops_cost_auditor.py)

Deterministic static auditor grounded in the FinOps Foundation Framework,
FOCUS specification principles, Kubernetes resource governance, and LLM Token FinOps.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SKIP_DIRS = {".git", "node_modules", ".next", "dist", "build", "__pycache__", ".venv", "venv"}

K8S_WORKLOAD_KIND = re.compile(r"^\s*kind:\s*(?:Deployment|StatefulSet|DaemonSet)\b", re.MULTILINE)
K8S_RESOURCES_BLOCK = re.compile(r"\bresources:\s*[\s\S]{0,400}?\blimits:\s*", re.MULTILINE)

LLM_CALL_START = re.compile(
    r"(?:messages\.create|chat\.completions\.create|generate_content|generateContent)\s*\(",
)
OUTPUT_CAP_PARAM = re.compile(r"\b(?:max_tokens|max_output_tokens|max_completion_tokens|maxOutputTokens)\b")

SYSTEM_PROMPT_ASSIGN = re.compile(
    r"""\b(?:system_instruction|systemInstruction|system_prompt|systemPrompt|system)\s*[:=]\s*[^\n;]{0,300}""",
    re.IGNORECASE,
)
SIBLING_PARAM_BOUNDARY = re.compile(
    r",\s*(?:messages|contents|model|tools|max_tokens|max_output_tokens|max_completion_tokens|generationConfig)\s*[:=]",
    re.IGNORECASE,
)
DYNAMIC_CACHE_BUSTER = re.compile(
    r"\b(?:datetime\.(?:now|utcnow)|time\.time|Date\.now|new\s+Date|uuid\.uuid4|crypto\.randomUUID)\s*\(",
)


def _extract_paren_block(text: str, start_idx: int) -> str:
    depth = 0
    for pos in range(start_idx, min(len(text), start_idx + 2000)):
        ch = text[pos]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[start_idx : pos + 1]
    return text[start_idx : min(len(text), start_idx + 500)]


def audit_finops_text(content: str, file_name: str = "<snippet>") -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    lower_name = file_name.lower()

    # 1. Kubernetes workload YAML missing resources.limits
    if lower_name.endswith((".yaml", ".yml")) and K8S_WORKLOAD_KIND.search(content):
        if not K8S_RESOURCES_BLOCK.search(content):
            findings.append({
                "rule_id": "FINOPS_K8S_MISSING_RESOURCE_LIMITS",
                "severity": "HIGH",
                "file": file_name,
                "message": "Kubernetes workload manifest lacks resources.limits (risk of noisy-neighbor OOM and uncontrolled autoscaling spend).",
                "remediation": "Define explicit resources.requests and resources.limits for CPU and memory.",
            })

    # 2. LLM API call missing explicit max output token cap (OWASP LLM10 / FinOps)
    if lower_name.endswith((".py", ".ts", ".tsx", ".js", ".jsx", "<snippet>")) or "." not in lower_name:
        for match in LLM_CALL_START.finditer(content):
            paren_pos = match.end() - 1
            call_block = _extract_paren_block(content, paren_pos)
            if not OUTPUT_CAP_PARAM.search(call_block):
                line_num = content[: match.start()].count("\n") + 1
                findings.append({
                    "rule_id": "FINOPS_LLM_UNBOUNDED_OUTPUT",
                    "severity": "HIGH",
                    "file": file_name,
                    "line": line_num,
                    "message": "LLM API call lacks max_tokens / max_output_tokens / max_completion_tokens cap.",
                    "remediation": "Set bounded max_output_tokens and thinking_budget to prevent runaway output/reasoning billing.",
                })

        # 3. Dynamic timestamp or UUID injected directly into system prompt prefix (busts prompt cache)
        for idx, line in enumerate(content.splitlines(), start=1):
            sys_match = SYSTEM_PROMPT_ASSIGN.search(line)
            if sys_match:
                sys_expr = SIBLING_PARAM_BOUNDARY.split(sys_match.group(0), maxsplit=1)[0]
                if DYNAMIC_CACHE_BUSTER.search(sys_expr):
                    findings.append({
                        "rule_id": "FINOPS_LLM_SYSTEM_PREFIX_CACHE_BUST",
                        "severity": "MEDIUM",
                        "file": file_name,
                        "line": idx,
                        "message": "Dynamic timestamp/UUID injected inside system prompt breaks prefix prompt caching.",
                        "remediation": "Keep system prompt prefix strictly static and pass timestamps/request IDs in the trailing user message.",
                    })

    return findings


def estimate_llm_monthly_cost(
    calls_per_day: int,
    input_tokens: int,
    output_tokens: int,
    thinking_tokens: int,
    cache_hit_rate: float,
    input_rate_per_1m: float,
    output_rate_per_1m: float,
    cached_discount: float,
) -> dict[str, Any]:
    monthly_calls = 30 * calls_per_day
    uncached_in_cost = (monthly_calls * input_tokens * (1.0 - cache_hit_rate) / 1_000_000) * input_rate_per_1m
    cached_in_cost = (monthly_calls * input_tokens * cache_hit_rate / 1_000_000) * (input_rate_per_1m * (1.0 - cached_discount))
    no_cache_in_cost = (monthly_calls * input_tokens / 1_000_000) * input_rate_per_1m

    # Thinking tokens are billed at the output token rate
    billed_output_tokens = output_tokens + thinking_tokens
    total_out_cost = (monthly_calls * billed_output_tokens / 1_000_000) * output_rate_per_1m

    total_with_cache = round(uncached_in_cost + cached_in_cost + total_out_cost, 2)
    total_without_cache = round(no_cache_in_cost + total_out_cost, 2)
    cache_savings = round(total_without_cache - total_with_cache, 2)

    return {
        "monthly_calls": monthly_calls,
        "monthly_cost_usd_with_cache": total_with_cache,
        "monthly_cost_usd_without_cache": total_without_cache,
        "monthly_cache_savings_usd": cache_savings,
        "output_and_thinking_cost_usd": round(total_out_cost, 2),
        "thinking_share_of_output_pct": round((thinking_tokens / max(1, billed_output_tokens)) * 100, 1),
    }


def audit_directory(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    scanned = 0
    exts = {".yaml", ".yml", ".py", ".ts", ".tsx", ".js", ".jsx"}
    files = [
        p for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in exts and not any(part in SKIP_DIRS for part in p.parts)
    ]
    for fpath in files:
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        scanned += 1
        findings.extend(audit_finops_text(text, str(fpath)))

    return {
        "target": str(root),
        "scanned_files": scanned,
        "finding_count": len(findings),
        "status": "PASS" if not findings else "FINDINGS_DETECTED",
        "findings": findings,
    }


def run_self_test() -> dict[str, Any]:
    """Execute >=5 precision probes and >=3 recall probes (Rule 22)."""
    precision_cases = [
        (
            "PRECISION-1: K8s Deployment with explicit requests and limits",
            "apiVersion: apps/v1\nkind: Deployment\nspec:\n  template:\n    spec:\n      containers:\n      - name: api\n        resources:\n          requests:\n            cpu: 250m\n            memory: 256Mi\n          limits:\n            cpu: 1000m\n            memory: 512Mi\n",
            "k8s/deployment.yaml",
        ),
        (
            "PRECISION-2: Non-workload K8s Service YAML",
            "apiVersion: v1\nkind: Service\nmetadata:\n  name: api-svc\n",
            "k8s/service.yaml",
        ),
        (
            "PRECISION-3: Bounded LLM call with max_tokens and static system prompt",
            'SYSTEM_PROMPT = "You are a concise SQL assistant."\nres = client.messages.create(model="claude-sonnet", max_tokens=1024, system=SYSTEM_PROMPT, messages=[{"role": "user", "content": f"Time: {datetime.now()} Query: {q}"}])',
            "src/llm_client.py",
        ),
        (
            "PRECISION-4: Gemini generateContent with maxOutputTokens",
            "const resp = await model.generateContent({ contents, generationConfig: { maxOutputTokens: 2048 } });",
            "src/gemini.ts",
        ),
        (
            "PRECISION-5: Log line calling Date.now() outside system prompt",
            'console.info("Request started", { requestId: crypto.randomUUID(), ts: Date.now() });',
            "src/logger.ts",
        ),
    ]
    recall_cases = [
        (
            "RECALL-1: K8s Deployment missing resources.limits",
            "apiVersion: apps/v1\nkind: Deployment\nspec:\n  template:\n    spec:\n      containers:\n      - name: worker\n        image: app:1.0\n",
            "k8s/worker.yaml",
            "FINOPS_K8S_MISSING_RESOURCE_LIMITS",
        ),
        (
            "RECALL-2: Unbounded OpenAI/Anthropic call lacking max_tokens",
            'res = client.chat.completions.create(model="gpt-5", messages=msgs)',
            "src/chat.py",
            "FINOPS_LLM_UNBOUNDED_OUTPUT",
        ),
        (
            "RECALL-3: Dynamic datetime.now() inside system_instruction breaking prefix cache",
            'system_instruction = f"Current time is {datetime.now().isoformat()}. Follow policy."\nresp = client.generate_content(contents, max_output_tokens=512)',
            "src/agent.py",
            "FINOPS_LLM_SYSTEM_PREFIX_CACHE_BUST",
        ),
    ]

    results: list[dict[str, Any]] = []
    for name, snippet, fname in precision_cases:
        hits = audit_finops_text(snippet, fname)
        results.append({"probe": name, "passed": len(hits) == 0, "finding_count": len(hits)})

    for name, snippet, fname, expected in recall_cases:
        hits = audit_finops_text(snippet, fname)
        rules = {h["rule_id"] for h in hits}
        results.append({"probe": name, "passed": expected in rules, "matched_rules": sorted(rules)})

    # Also verify math of estimator (thinking tokens billed as output)
    est = estimate_llm_monthly_cost(1000, 10000, 500, 1500, 0.8, 1.50, 7.50, 0.90)
    math_ok = est["thinking_share_of_output_pct"] == 75.0 and est["monthly_cache_savings_usd"] > 0
    results.append({"probe": "RECALL-4: Estimator bills thinking tokens at output rate & computes cache savings", "passed": math_ok, "details": est})

    passed = sum(1 for r in results if r["passed"])
    return {
        "tool": "finops_cost_auditor.py",
        "total_probes": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "all_passed": passed == len(results),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Shadow FinOps — Cloud & LLM Cost Auditor")
    parser.add_argument("--audit", default=None, help="Directory to scan for K8s & LLM FinOps anti-patterns")
    parser.add_argument("--estimate-llm", action="store_true", help="Estimate monthly LLM spend with caching & thinking tokens")
    parser.add_argument("--calls-per-day", type=int, default=10000)
    parser.add_argument("--input-tokens", type=int, default=4000)
    parser.add_argument("--output-tokens", type=int, default=500)
    parser.add_argument("--thinking-tokens", type=int, default=1000)
    parser.add_argument("--cache-hit-rate", type=float, default=0.80)
    parser.add_argument("--input-rate", type=float, default=1.50)
    parser.add_argument("--output-rate", type=float, default=7.50)
    parser.add_argument("--cached-discount", type=float, default=0.90)
    parser.add_argument("--self-test", action="store_true", help="Run precision & recall probes")
    args = parser.parse_args()

    if args.self_test:
        res = run_self_test()
        print(json.dumps(res, indent=2))
        return 0 if res["all_passed"] else 1

    if args.estimate_llm:
        res = estimate_llm_monthly_cost(
            args.calls_per_day,
            args.input_tokens,
            args.output_tokens,
            args.thinking_tokens,
            args.cache_hit_rate,
            args.input_rate,
            args.output_rate,
            args.cached_discount,
        )
        print(json.dumps(res, indent=2))
        return 0

    if args.audit:
        res = audit_directory(Path(args.audit))
        print(json.dumps(res, indent=2))
        return 0 if res["finding_count"] == 0 else 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
