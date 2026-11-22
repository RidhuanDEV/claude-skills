from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import resource_cleanup as rc


class ResourceCleanupTests(unittest.TestCase):
    def test_self_test_precision_and_recall_probes(self) -> None:
        res = rc.run_self_test()
        self.assertTrue(res["all_passed"], json.dumps(res, indent=2))
        self.assertEqual(res["failed"], 0)

    def test_cleanup_owned_kills_only_verified_task_pids_and_preserves_foreign(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger_path = Path(tmp) / "task-resources.json"
            procs = [
                {
                    "pid": 1001,
                    "ppid": 100,
                    "name": "claude.exe",
                    "command": "claude.exe",
                    "created_at": "2026-11-22T13:48:00Z",
                    "rss_mb": 110.0,
                },
                {
                    "pid": 2001,
                    "ppid": 1001,
                    "name": "node.exe",
                    "command": "node shadow-api-mcp/index.mjs",
                    "created_at": "2026-11-22T13:48:02Z",
                    "rss_mb": 68.0,
                },
                {
                    "pid": 5174,
                    "ppid": 400,
                    "name": "node.exe",
                    "command": "node D:/Work/PRPM/node_modules/vite/bin/vite.js --port 5174",
                    "created_at": "2026-11-22T14:00:00Z",
                    "rss_mb": 150.0,
                },
                {
                    "pid": 7001,
                    "ppid": 400,
                    "name": "node.exe",
                    "command": "node D:/Work/Notulen/tools/video-env.cjs",
                    "created_at": "2026-11-22T18:00:00Z",
                    "rss_mb": 90.0,
                },
                {
                    "pid": 7002,
                    "ppid": 400,
                    "name": "postgres.exe",
                    "command": "postgres.exe -D C:/pgdata",
                    "created_at": "2026-11-22T19:00:00Z",
                    "rss_mb": 300.0,
                },
            ]

            rc.register_resource(
                ledger_path,
                pid=7001,
                kind="video_env",
                workspace="D:/Work/Notulen",
                label="video-recording-env",
                processes=procs,
            )
            # Inject a stale ledger record whose PID was reused by postgres.exe
            ledger = rc.load_ledger(ledger_path)
            ledger["entries"].append(
                {
                    "pid": 7002,
                    "kind": "dev_server",
                    "label": "stale-vite",
                    "port": 5173,
                    "workspace": "d:/work/notulen",
                    "created_at": "2026-11-22T12:00:00Z",
                    "command_hint": "vite",
                }
            )
            rc.save_ledger(ledger_path, ledger)

            killed: list[int] = []

            def fake_kill(pid: int) -> tuple[bool, str]:
                killed.append(pid)
                return True, f"mock stopped {pid}"

            result = rc.cleanup_owned_resources(ledger_path, dry_run=False, processes=procs, terminator=fake_kill)
            self.assertEqual(killed, [7001])
            self.assertEqual(result["protected_foreign_count"], 1)
            self.assertEqual(result["protected_active_host_sessions"], 1)
            self.assertEqual(len(result["refused_pid_reused"]), 1)
            self.assertFalse(result["passed"])  # Refusal surfaced explicitly so operator sees PID-reuse warning

            # Confirm ledger cleaned up PID 7001 and dropped stale reused entry
            after = rc.load_ledger(ledger_path)
            self.assertEqual(after["entries"], [])

    def test_port_to_pid_mapping_and_if_ledger_exists_hook_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing_ledger = Path(tmp) / "does-not-exist.json"
            hook_res = rc.cleanup_owned_resources(missing_ledger, if_ledger_exists=True)
            self.assertTrue(hook_res["passed"])
            self.assertEqual(hook_res["status"], "NO_LEDGER_NOTHING_TO_CLEAN")

            # Bare node server without --port in CLI args is still detected & protected via OS TCP port map
            procs = [
                {
                    "pid": 9100,
                    "ppid": 500,
                    "name": "node.exe",
                    "command": "node D:/OtherProject/dist/index.js",
                    "created_at": "2026-11-22T15:00:00Z",
                    "rss_mb": 64.0,
                }
            ]
            audit = rc.classify_process_snapshot(
                procs,
                ledger=None,
                current_workspace="D:/CurrentProject",
                listening_ports={9100: [5174]},
            )
            self.assertEqual(audit["summary"]["foreign_project_resources_protected"], 1)
            self.assertEqual(audit["foreign_project_resources_protected"][0]["ports"], [5174])
            self.assertFalse(audit["foreign_project_resources_protected"][0]["auto_cleanup_allowed"])


if __name__ == "__main__":
    unittest.main()
