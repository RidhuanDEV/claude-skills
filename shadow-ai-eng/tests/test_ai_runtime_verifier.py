import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import ai_runtime_verifier as verifier  # noqa: E402


class AiRuntimeVerifierTests(unittest.TestCase):
    def test_self_test_probes(self) -> None:
        res = verifier.run_self_test()
        self.assertTrue(res["all_passed"], f"Self-test failures: {res}")
        self.assertEqual(res["total_probes"], 7)

    def test_shell_command_tool_arg_rejected(self) -> None:
        res = verifier.check_tool_spec(
            {
                "max_steps": 4,
                "server_injected_tenant_context": True,
                "tools": [
                    {
                        "name": "run_helper",
                        "llm_supplied_args": ["shell_command"],
                        "runtime_schema_validated": True,
                        "timeout_ms": 5000,
                    }
                ],
            }
        )
        self.assertFalse(res["passed"])


if __name__ == "__main__":
    unittest.main()
