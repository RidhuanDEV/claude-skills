from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "shadow-monarch" / "scripts" / "bounded_exec.py"
sys.path.insert(0, str(SCRIPT.parent))

from bounded_exec import inject_ssh_safe_flags, run_bounded


class BoundedExecWatchdogTests(unittest.TestCase):
    def test_self_test_cli_passes(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--self-test"],
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["status"], "PASS")
        self.assertGreaterEqual(payload["probes"], 5)

    def test_fast_command_passes_and_failing_exit_code_is_preserved(self) -> None:
        ok = run_bounded(
            [sys.executable, "-c", "print('ok-line')"],
            timeout=10,
            idle_timeout=5,
            heartbeat=0,
            stream_output=False,
        )
        self.assertEqual(ok["status"], "PASS")
        self.assertEqual(ok["exit_code"], 0)
        self.assertTrue(any("ok-line" in line for line in ok["tail"]))

        fail = run_bounded(
            [sys.executable, "-c", "import sys; sys.stderr.write('boom\\n'); sys.exit(42)"],
            timeout=10,
            idle_timeout=5,
            heartbeat=0,
            stream_output=False,
        )
        self.assertEqual(fail["status"], "FAIL")
        self.assertEqual(fail["exit_code"], 42)
        self.assertGreater(fail["stderr_bytes"], 0)

    def test_idle_watchdog_kills_silent_hung_script_before_wall_timeout(self) -> None:
        res = run_bounded(
            [sys.executable, "-c", "import time; time.sleep(20)"],
            timeout=15,
            idle_timeout=0.7,
            heartbeat=0,
            kill_grace=0.3,
            stream_output=False,
        )
        self.assertEqual(res["status"], "IDLE_TIMEOUT")
        self.assertEqual(res["exit_code"], 125)
        self.assertLess(res["elapsed_sec"], 5.0)

    def test_wall_timeout_kills_chatty_infinite_loop(self) -> None:
        res = run_bounded(
            [sys.executable, "-c", "import time\nwhile True:\n print('alive', flush=True)\n time.sleep(0.1)"],
            timeout=1.0,
            idle_timeout=5.0,
            heartbeat=0,
            kill_grace=0.3,
            stream_output=False,
        )
        self.assertEqual(res["status"], "WALL_TIMEOUT")
        self.assertEqual(res["exit_code"], 124)
        self.assertGreater(res["stdout_bytes"], 0)

    def test_ssh_safe_flag_injection_precision_and_idempotency(self) -> None:
        injected = inject_ssh_safe_flags(["ssh", "vps-lab", "hostname"])
        joined = " ".join(injected)
        self.assertIn("BatchMode=yes", joined)
        self.assertIn("ConnectTimeout=10", joined)
        self.assertIn("ServerAliveInterval=15", joined)
        self.assertIn("ServerAliveCountMax=2", joined)

        # Does not duplicate already-specified options
        custom = inject_ssh_safe_flags(["ssh", "-o", "ConnectTimeout=5", "vps-lab", "hostname"])
        self.assertEqual(" ".join(custom).lower().count("connecttimeout="), 1)

        # Does not touch non-ssh commands
        self.assertEqual(inject_ssh_safe_flags(["python", "script.py"]), ["python", "script.py"])

    def test_cli_quiet_json_summary_emits_structured_report(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--timeout",
                "10",
                "--idle-timeout",
                "0.6",
                "--heartbeat",
                "0",
                "--kill-grace",
                "0.2",
                "--quiet",
                "--",
                sys.executable,
                "-c",
                "import time; time.sleep(10)",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 125)
        summary = json.loads(proc.stderr)
        self.assertEqual(summary["status"], "IDLE_TIMEOUT")
        self.assertEqual(summary["exit_code"], 125)


if __name__ == "__main__":
    unittest.main()
