import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import shadow_gate


class DockerOwnershipTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.repo = Path(folder.name)
        self.run_id = "job-a"
        self.ledger = self.repo / "ledger.json"
        self.owned = "a" * 64
        self.foreign = "b" * 64
        self.neighbor = "c" * 64
        self.rows = {
            self.owned: self.row(self.owned, self.repo, self.run_id),
            self.foreign: self.row(self.foreign, self.repo, "job-b"),
            self.neighbor: self.row(self.neighbor, self.repo / "another", self.run_id),
        }
        self.write_ledger([self.owned])
        self.calls = []
        self.inspect_count = {}
        self.restart_on_recheck = False
        self.fail_after_remove = False
        self.docker = patch.object(subprocess, "run", side_effect=self.fake_docker).start()
        self.addCleanup(patch.stopall)

    def row(self, cid, repo, run):
        return dict(id=cid, name="/app-test-db", image="postgres", status="exited",
                    repo=repo.resolve().as_posix(), run=run, ephemeral="true")

    def write_ledger(self, ids, **changes):
        payload = dict(version=1, repo=self.repo.resolve().as_posix(),
                       run_id=self.run_id, container_ids=ids)
        payload.update(changes)
        self.ledger.write_text(json.dumps(payload), encoding="utf-8")

    def fake_docker(self, cmd, **kwargs):
        self.calls.append(cmd)
        if cmd[:2] == ["docker", "ps"]:
            filters = [arg for arg in cmd if arg.startswith("label=")]
            self.assertIn("label=shadow.repo=" + self.repo.resolve().as_posix(), filters)
            self.assertIn("label=shadow.run=" + self.run_id, filters)
            self.assertIn("--no-trunc", cmd)
            ids = [cid for cid, row in self.rows.items()
                   if row["repo"] == self.repo.resolve().as_posix() and row["run"] == self.run_id]
            return subprocess.CompletedProcess(cmd, 0, "\n".join(ids), "")
        cid = cmd[-1]
        if cmd[:3] == ["docker", "container", "inspect"]:
            if cid not in self.rows:
                return subprocess.CompletedProcess(cmd, 1, "", "No such container: " + cid)
            self.inspect_count[cid] = self.inspect_count.get(cid, 0) + 1
            if self.restart_on_recheck and self.inspect_count[cid] == 2:
                self.rows[cid]["status"] = "running"
            return subprocess.CompletedProcess(cmd, 0, json.dumps(self.rows[cid]), "")
        self.assertEqual(cmd, ["docker", "rm", self.owned])
        self.assertEqual(self.rows[cid]["status"], "exited")
        del self.rows[cid]
        if self.fail_after_remove:
            raise subprocess.TimeoutExpired(cmd, 8)
        return subprocess.CompletedProcess(cmd, 0, cid, "")

    def gate(self, cleanup=False):
        return shadow_gate.inspect_or_cleanup_docker_leaks(
            cleanup=cleanup, repo_root=self.repo, run_id=self.run_id, ledger_path=self.ledger)

    def test_unscoped_cleanup_refuses_before_docker_and_check_is_unmeasured(self):
        self.assertEqual(shadow_gate.inspect_or_cleanup_docker_leaks(cleanup=True)["status"], "BLOCKED")
        self.assertEqual(shadow_gate.inspect_or_cleanup_docker_leaks()["status"], "NOT_RUN")
        self.assertFalse(self.calls)

    def test_scoped_preview_and_cleanup_do_not_target_other_job_or_repo(self):
        preview = self.gate()
        self.assertEqual([c["id"] for c in preview["leaked_containers"]], [self.owned])
        self.assertEqual(preview["status"], "FAIL")
        self.assertFalse(any(c[1] == "rm" for c in self.calls))
        result = self.gate(cleanup=True)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["cleaned_count"], 1)
        self.assertEqual(set(self.rows), {self.foreign, self.neighbor})
        self.assertEqual(self.gate(cleanup=True)["cleaned_count"], 0)

    def test_wrong_repo_job_or_short_id_in_ledger_blocks_before_listing(self):
        for override in [dict(repo="."), dict(run_id="job-b"),
                         dict(container_ids=[self.owned[:12]]), dict(version=True)]:
            with self.subTest(override=override):
                self.write_ledger([self.owned], **override)
                self.assertEqual(self.gate(cleanup=True)["status"], "BLOCKED")
                self.assertFalse(self.calls)

    def test_recorded_id_with_wrong_owner_and_unrecorded_candidate_are_not_removed(self):
        self.write_ledger([self.foreign, self.neighbor])
        result = self.gate(cleanup=True)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(set(self.rows), {self.owned, self.foreign, self.neighbor})
        self.assertFalse(any(c[1] == "rm" for c in self.calls))

    def test_tampered_or_wrong_scope_id_never_grants_ownership(self):
        for cid in [self.foreign, self.neighbor]:
            with self.subTest(cid=cid):
                self.write_ledger([self.owned, cid])
                self.assertEqual(self.gate(cleanup=True)["status"], "BLOCKED")
        self.rows[self.owned]["id"] = self.neighbor
        self.write_ledger([self.owned])
        self.assertEqual(self.gate(cleanup=True)["status"], "BLOCKED")
        self.assertFalse(any(c[1] == "rm" for c in self.calls))

    def test_unscoped_cli_check_preserves_code_result_and_marks_docker_unmeasured(self):
        output = io.StringIO()
        argv = ["shadow_gate.py", "--repo", str(self.repo), "--files", "--check-docker-leaks"]
        with patch.object(sys, "argv", argv), redirect_stdout(output):
            self.assertEqual(shadow_gate.main(), 0)
        result = json.loads(output.getvalue())
        self.assertTrue(result["passed"])
        self.assertEqual(result["docker_leaks"]["status"], "NOT_RUN")
        self.assertEqual(result["recommended_max_readiness"], "IMPLEMENTED")
        self.assertFalse(self.calls)

    def test_legacy_label_and_running_or_created_container_are_never_removed(self):
        for field, value in [("ephemeral", ""), ("ephemeral", "false"), ("status", "running"),
                             ("status", "created"), ("status", "paused")]:
            with self.subTest(field=field, value=value):
                self.rows[self.owned] = self.row(self.owned, self.repo, self.run_id)
                self.rows[self.owned][field] = value
                self.assertIn(self.gate(cleanup=True)["status"], ["FAIL", "BLOCKED"])
                self.assertFalse(any(c[1] == "rm" for c in self.calls))

    def test_container_restarted_after_preview_is_preserved(self):
        self.restart_on_recheck = True
        self.assertIn(self.gate(cleanup=True)["status"], ["FAIL", "BLOCKED"])
        self.assertIn(self.owned, self.rows)
        self.assertFalse(any(c[1] == "rm" for c in self.calls))

    def test_retry_after_daemon_applies_removal_then_client_times_out(self):
        self.fail_after_remove = True
        self.assertEqual(self.gate(cleanup=True)["status"], "BLOCKED")
        self.assertEqual(self.gate(cleanup=True)["status"], "PASS")
        self.assertEqual(sum(c[1] == "rm" for c in self.calls), 1)

    def test_docker_unavailable_cli_returns_structured_failure(self):
        self.docker.side_effect = FileNotFoundError("docker unavailable")
        argv = ["shadow_gate.py", "--repo", str(self.repo), "--files", "--check-docker-leaks",
                "--docker-run-id", self.run_id, "--docker-ledger", str(self.ledger)]
        output = io.StringIO()
        with patch.object(sys, "argv", argv), redirect_stdout(output):
            code = shadow_gate.main()
        result = json.loads(output.getvalue())
        self.assertEqual(code, 1)
        self.assertEqual(result["docker_leaks"]["status"], "BLOCKED")
        self.assertFalse(result["passed"])
