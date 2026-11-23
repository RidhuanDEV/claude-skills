import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import ops_hardening_verifier as ohv


class OpsHardeningVerifierTests(unittest.TestCase):
    def test_self_test_probes(self) -> None:
        report = ohv.run_self_test()
        self.assertTrue(report["all_passed"], report)
        self.assertEqual(report["total_probes"], 7)

    def test_mysql_public_port_rejected(self) -> None:
        compose = (
            "services:\n  mysql:\n    image: mysql:8.4\n    mem_limit: 1g\n"
            "    ports:\n      - '3306:3306'\n    healthcheck:\n      test: ['CMD', 'true']\n"
            "    logging:\n      options:\n        max-size: 10m\n        max-file: 3\n"
        )
        codes = {v["code"] for v in ohv.check_compose_text(compose)}
        self.assertIn("PUBLIC_INTERNAL_DB_PORT", codes)


if __name__ == "__main__":
    unittest.main()
