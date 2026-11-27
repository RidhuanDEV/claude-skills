from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "rollback_decision.py"
_spec = importlib.util.spec_from_file_location("rollback_decision", SCRIPT)
assert _spec is not None and _spec.loader is not None
rollback_decision = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rollback_decision)


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(SCRIPT), *args], capture_output=True, text=True, timeout=60, check=False,
    )

BASE = {
    "current_version": "2.4.0", "target_version": "2.3.0", "feature_flag_available": True,
    "migration_is_expand_only": True, "incident_commander_approved": True,
}


class IncidentRollbackGateTests(unittest.TestCase):
    def test_t07_t17_flag_off_and_expand_rollback_vs_destructive_schema(self) -> None:
        safe = rollback_decision.decide(BASE)
        self.assertEqual((safe["rollback_allowed"], safe["mode"]), (True, "FLAG_OFF_AND_BINARY_ROLLBACK"))
        expand = rollback_decision.decide({**BASE, "feature_flag_available": False})
        self.assertEqual((expand["rollback_allowed"], expand["mode"]), (True, "EXPAND_COMPATIBLE_ROLLBACK"))
        blocked = rollback_decision.decide({**BASE, "migration_is_expand_only": False})
        self.assertEqual((blocked["rollback_allowed"], blocked["mode"]), (False, "BLOCKED_INCOMPATIBLE_SCHEMA"))

    def test_compatible_rollback_still_needs_incident_commander_approval(self) -> None:
        pending = rollback_decision.decide({**BASE, "incident_commander_approved": False})
        self.assertEqual((pending["rollback_allowed"], pending["mode"]), (False, "AWAITING_APPROVAL"))

    def test_malformed_input_never_allows_rollback(self) -> None:
        for record in (
            {**BASE, "migration_is_expand_only": "true"},
            {**BASE, "incident_commander_approved": "false"},
            {key: value for key, value in BASE.items() if key != "feature_flag_available"},
            {**BASE, "target_version": "2.4.0"},
            {**BASE, "current_version": ""},
            [],
        ):
            with self.subTest(record=record):
                result = rollback_decision.decide(record)
                self.assertEqual((result["rollback_allowed"], result["mode"]), (False, "INVALID_INPUT"))

    def test_cli_self_test_and_exit_codes(self) -> None:
        self.assertEqual(run_cli("--self-test").returncode, 0)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rollback.json"
            path.write_text(json.dumps({**BASE, "migration_is_expand_only": False}), encoding="utf-8")
            self.assertEqual(run_cli("--assess", str(path)).returncode, 1)
            path.write_text(json.dumps(BASE), encoding="utf-8")
            self.assertEqual(run_cli("--assess", str(path)).returncode, 0)


if __name__ == "__main__":
    unittest.main()
