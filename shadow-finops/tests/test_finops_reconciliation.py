"""Reconciliation and gate tests against the shipped finops_cost_auditor.py."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from typing import Any

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "finops_cost_auditor.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("finops_cost_auditor_under_test", SCRIPT)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


auditor = _load()

BASE_ARGS: dict[str, Any] = {
    "calls_per_day": 1000,
    "input_tokens": 10000,
    "output_tokens": 500,
    "thinking_tokens": 1500,
    "cache_hit_rate": 0.8,
    "input_rate_per_1m": 1.50,
    "output_rate_per_1m": 7.50,
    "cached_discount": 0.90,
}


def estimate(**overrides: Any) -> dict[str, Any]:
    kwargs = dict(BASE_ARGS)
    kwargs.update(overrides)
    return auditor.estimate_llm_monthly_cost(**kwargs)


class EstimatorReconciliation(unittest.TestCase):
    def test_components_reconcile_to_hand_computed_invoice(self) -> None:
        # 30k calls * 10k input = 300M tokens -> 450.00 uncached; 20% full price (90.00) + 80% at 10% (36.00);
        # (500 + 1500) * 30k = 60M output tokens * 7.50 = 450.00.
        res = estimate()
        self.assertEqual(res["monthly_calls"], 30000)
        self.assertEqual(res["monthly_cost_usd_with_cache"], 576.00)
        self.assertEqual(res["monthly_cost_usd_without_cache"], 900.00)
        self.assertEqual(res["monthly_cache_savings_usd"], 324.00)
        self.assertEqual(res["output_and_thinking_cost_usd"], 450.00)
        self.assertEqual(res["thinking_share_of_output_pct"], 75.0)
        self.assertAlmostEqual(
            res["monthly_cost_usd_with_cache"] + res["monthly_cache_savings_usd"],
            res["monthly_cost_usd_without_cache"],
            places=2,
        )

    def test_dated_tariff_snapshots_reproduce_historical_bills(self) -> None:
        tariffs = {"2026-Q3": 0.50, "2026-Q4": 0.60}
        bills = {
            quarter: estimate(output_tokens=0, thinking_tokens=0, cache_hit_rate=0.0, input_rate_per_1m=rate)[
                "monthly_cost_usd_with_cache"
            ]
            for quarter, rate in tariffs.items()
        }
        self.assertEqual(bills, {"2026-Q3": 150.00, "2026-Q4": 180.00})

    def test_rate_boundaries_accepted(self) -> None:
        self.assertEqual(estimate(cache_hit_rate=0.0)["monthly_cache_savings_usd"], 0.0)
        self.assertEqual(estimate(cache_hit_rate=1.0, cached_discount=1.0)["monthly_cost_usd_with_cache"], 450.00)

    def test_out_of_range_or_wrong_type_rates_rejected(self) -> None:
        for name in ("cache_hit_rate", "cached_discount"):
            for value in (1.5, -0.1, float("nan"), True, "0.8", None):
                with self.subTest(rate=name, value=value):
                    with self.assertRaises(ValueError):
                        estimate(**{name: value})


class AuditTextGate(unittest.TestCase):
    def rules(self, content: str, name: str) -> set[str]:
        return {f["rule_id"] for f in auditor.audit_finops_text(content, name)}

    def test_clean_inputs_have_no_findings(self) -> None:
        self.assertEqual(self.rules('client.messages.create(model="m", max_tokens=256, messages=m)', "a.py"), set())
        limited = "kind: Deployment\nspec:\n  containers:\n  - resources:\n      limits:\n        cpu: 1\n"
        self.assertEqual(self.rules(limited, "d.yaml"), set())
        self.assertEqual(self.rules("", "a.py"), set())

    def test_unbounded_llm_call_flagged(self) -> None:
        self.assertIn("FINOPS_LLM_UNBOUNDED_OUTPUT", self.rules("client.chat.completions.create(model=m, messages=x)", "c.ts"))

    def test_k8s_workload_without_limits_flagged(self) -> None:
        self.assertIn("FINOPS_K8S_MISSING_RESOURCE_LIMITS", self.rules("kind: StatefulSet\nspec: {}\n", "s.yml"))

    def test_dynamic_system_prefix_flagged(self) -> None:
        src = 'system_prompt = f"now={datetime.now()}"\nclient.generate_content(c, max_output_tokens=9)'
        self.assertIn("FINOPS_LLM_SYSTEM_PREFIX_CACHE_BUST", self.rules(src, "agent.py"))

    def test_self_test_probes_pass(self) -> None:
        res = auditor.run_self_test()
        self.assertTrue(res["all_passed"], res)


class AuditDirectoryGate(unittest.TestCase):
    def audit(self, files: dict[str, str]) -> dict[str, Any]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel, text in files.items():
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
            return auditor.audit_directory(root)

    def test_clean_tree_passes(self) -> None:
        res = self.audit({"src/a.py": 'client.messages.create(max_tokens=10, messages=m)'})
        self.assertEqual((res["status"], res["scanned_files"]), ("PASS", 1))

    def test_findings_block(self) -> None:
        cases = {
            "llm": {"src/a.py": "client.messages.create(messages=m)"},
            "k8s": {"k8s/w.yaml": "kind: DaemonSet\n"},
            "cache": {"src/b.py": 'system = f"{uuid.uuid4()}"'},
        }
        for label, files in cases.items():
            with self.subTest(case=label):
                res = self.audit(files)
                self.assertEqual(res["status"], "FINDINGS_DETECTED")
                self.assertGreaterEqual(res["finding_count"], 1)

    def test_cli_blocks_on_missing_directory(self) -> None:
        import subprocess
        script = Path(__file__).resolve().parents[1] / "scripts" / "finops_cost_auditor.py"
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, "-B", str(script), "--audit", str(Path(tmp) / "missing")],
                                    capture_output=True, text=True, timeout=60, check=False)
        self.assertEqual(result.returncode, 1)
        self.assertIn("BLOCKED_NO_FILES_SCANNED", result.stdout)

    def test_skip_dirs_not_scanned(self) -> None:
        res = self.audit({"node_modules/x/a.js": "client.messages.create(messages=m)"})
        # Only skipped folders exist, so nothing is scanned and the gate must not report PASS.
        self.assertEqual((res["status"], res["scanned_files"]), ("BLOCKED_NO_FILES_SCANNED", 0))


class AuditorCli(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, "-B", str(SCRIPT), *args], capture_output=True, text=True, timeout=60)

    def test_estimate_cli_rejects_cache_hit_rate_above_one(self) -> None:
        bad = self.run_cli("--estimate-llm", "--cache-hit-rate", "1.5")
        self.assertEqual(bad.returncode, 2)
        self.assertIn("cache_hit_rate", bad.stderr)
        good = self.run_cli("--estimate-llm", "--cache-hit-rate", "0.5")
        self.assertEqual(good.returncode, 0)
        self.assertIn("monthly_cost_usd_with_cache", json.loads(good.stdout))

    def test_audit_cli_exit_codes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "a.py").write_text("client.messages.create(messages=m)", encoding="utf-8")
            self.assertEqual(self.run_cli("--audit", tmp).returncode, 1)
            Path(tmp, "a.py").write_text("print('ok')", encoding="utf-8")
            self.assertEqual(self.run_cli("--audit", tmp).returncode, 0)


if __name__ == "__main__":
    unittest.main()
