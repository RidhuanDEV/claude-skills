import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import api_contract_verifier as verifier  # noqa: E402


class ApiContractVerifierTests(unittest.TestCase):
    def test_self_test_probes(self) -> None:
        res = verifier.run_self_test()
        self.assertTrue(res["all_passed"], f"Self-test failures: {res}")
        self.assertEqual(res["total_probes"], 7)

    def test_duplicate_operation_id_rejected(self) -> None:
        res = verifier.check_openapi_contract(
            {
                "openapi": "3.1.0",
                "paths": {
                    "/a": {"get": {"operationId": "dupOp"}},
                    "/b": {"get": {"operationId": "dupOp"}},
                },
            }
        )
        self.assertFalse(res["passed"])
        self.assertTrue(any("duplicate operationId" in e for e in res["errors"]))

    def test_python_traceback_in_error_detail_rejected(self) -> None:
        res = verifier.check_problem_json(
            {
                "content_type": "application/problem+json",
                "body": {
                    "type": "about:blank",
                    "title": "Internal Server Error",
                    "status": 500,
                    "detail": "Traceback (most recent call last): File app.py line 10",
                },
            }
        )
        self.assertFalse(res["passed"])


if __name__ == "__main__":
    unittest.main()
