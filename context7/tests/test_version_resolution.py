from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "resolve_installed_version.py"
_spec = importlib.util.spec_from_file_location("resolve_installed_version", SCRIPT)
assert _spec is not None and _spec.loader is not None
resolve_installed_version = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(resolve_installed_version)


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(SCRIPT), *args], capture_output=True, text=True, timeout=60, check=False,
    )

def workspace(root: Path, name: str, declared: str, locked: str | None = None, installed: str | None = None) -> Path:
    path = root / name
    path.mkdir()
    (path / "package.json").write_text(json.dumps({"dependencies": {"next": declared}}), encoding="utf-8")
    if locked:
        lock = {"packages": {"node_modules/next": {"version": locked}}}
        (path / "package-lock.json").write_text(json.dumps(lock), encoding="utf-8")
    if installed:
        (path / "node_modules" / "next").mkdir(parents=True)
        (path / "node_modules" / "next" / "package.json").write_text(json.dumps({"version": installed}), encoding="utf-8")
    return path


class Context7VersionResolutionTests(unittest.TestCase):
    def test_c02_multi_major_workspaces_resolve_from_lockfiles_without_mixing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            r14 = resolve_installed_version.resolve(workspace(root, "legacy-web", "^14.2.15", locked="14.2.18"), "next")
            r15 = resolve_installed_version.resolve(workspace(root, "modern-web", "^15.1.0", locked="15.1.3"), "next")
            self.assertEqual((r14["status"], r14["major"], r14["version"]), ("RESOLVED", 14, "14.2.18"))
            self.assertEqual((r15["status"], r15["major"], r15["version"]), ("RESOLVED", 15, "15.1.3"))

    def test_manifest_range_alone_is_not_a_resolved_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = resolve_installed_version.resolve(workspace(Path(tmp), "app", "^14.2.15"), "next")
            self.assertEqual(result["status"], "RANGE_ONLY")
            self.assertNotIn("version", result)

    def test_installed_package_wins_over_lockfile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = workspace(Path(tmp), "app", "^14", locked="14.0.0", installed="14.2.20")
            result = resolve_installed_version.resolve(app, "next")
            self.assertEqual((result["version"], result["source"]), ("14.2.20", "node_modules"))

    def test_malformed_or_missing_metadata_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(resolve_installed_version.resolve(root, "next")["status"], "UNRESOLVED")
            app = workspace(root, "app", "^14.2.15")
            bad_lock = {"packages": {"node_modules/next": {"version": "^14"}}}
            (app / "package-lock.json").write_text(json.dumps(bad_lock), encoding="utf-8")
            self.assertEqual(resolve_installed_version.resolve(app, "next")["status"], "RANGE_ONLY")
            self.assertEqual(resolve_installed_version.resolve(app, "react")["status"], "NOT_DECLARED")

    def test_cli_self_test(self) -> None:
        self.assertEqual(run_cli("--self-test").returncode, 0)


if __name__ == "__main__":
    unittest.main()
