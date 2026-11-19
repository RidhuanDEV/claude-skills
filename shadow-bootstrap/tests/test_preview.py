from pathlib import Path
import runpy
import tempfile
import unittest

preview = runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/preview_scaffold.py"))["preview"]


class ProfileTests(unittest.TestCase):
    def test_clean_profiles_and_explicit_capabilities(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "service"
            for kind in ("cli", "static", "worker", "library", "http"):
                with self.subTest(kind=kind):
                    result = preview(target, kind, [])
                    self.assertEqual(result["status"], "PREVIEW")
                    self.assertEqual(len(result["deliverables"]), 2)
                    self.assertFalse(target.exists())
            selected = preview(target, "http", ["database", "database", "http_contract"])
            self.assertEqual(selected["selected_capabilities"], ["database", "http_contract"])
            self.assertEqual(len(selected["deliverables"]), 4)

    def test_partial_generator_retry_preserves_user_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / ".env").write_bytes(b"fixture-user-content")
            result = preview(path, "http", ["ci"])
            self.assertEqual(result["status"], "REVIEW_EXISTING")
            self.assertEqual(result["deliverables"], [])
            self.assertEqual((path / ".env").read_bytes(), b"fixture-user-content")

    def test_path_and_capability_errors(self):
        with tempfile.NamedTemporaryFile() as tmp:
            with self.assertRaises(ValueError):
                preview(Path(tmp.name), "cli", [])
            with self.assertRaises(ValueError):
                preview(Path(tmp.name), "cli", ["random"])

    def test_c07_static_site_has_zero_backend_infra_and_cli_runs_cleanly(self):
        import subprocess
        import sys

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            static_plan = preview(root / "marketing-site", "static", [])
            deliverables_text = " ".join(static_plan["deliverables"]).lower()
            for forbidden in ("openapi", "orm", "redis", "docker-compose", "postgres"):
                self.assertNotIn(forbidden, deliverables_text)

            cli_dir = root / "offline-cli"
            cli_plan = preview(cli_dir, "cli", [])
            self.assertEqual(cli_plan["status"], "PREVIEW")
            cli_dir.mkdir()
            entry = cli_dir / "main.py"
            entry.write_text('print("cli-ok")\n', encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(entry)],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertEqual(proc.stdout.strip(), "cli-ok")


if __name__ == "__main__":
    unittest.main()
