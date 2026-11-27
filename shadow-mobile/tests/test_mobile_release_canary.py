from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "mobile_release_gate.py"


def _load_gate() -> ModuleType:
    spec = importlib.util.spec_from_file_location("mobile_release_gate", SCRIPT)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = _load_gate()

MAIN_MANIFEST = "android/app/src/main/AndroidManifest.xml"
DEBUG_MANIFEST = "android/app/src/debug/AndroidManifest.xml"
HARDENED_MANIFEST = '<application android:debuggable="false" android:usesCleartextTraffic="false" />'
INSECURE_MANIFEST = '<application android:debuggable="true" android:usesCleartextTraffic="true" />'


def _rules(content: str, file_name: str) -> set[str]:
    return {str(f["rule_id"]) for f in gate.audit_mobile_text(content, file_name)}


def _write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class AuditMobileTextTests(unittest.TestCase):
    def test_hardened_release_manifest_passes(self) -> None:
        self.assertEqual(gate.audit_mobile_text(HARDENED_MANIFEST, MAIN_MANIFEST), [])

    def test_release_manifest_with_debug_flags_is_blocked(self) -> None:
        self.assertEqual(
            _rules(INSECURE_MANIFEST, MAIN_MANIFEST),
            {"MASVS_CODE_DEBUGGABLE_ENABLED", "MASVS_NETWORK_CLEARTEXT_ENABLED"},
        )

    def test_string_flag_casing_and_quote_style_still_blocked(self) -> None:
        for content in (
            "<application android:debuggable='TRUE' />",
            '<application android:debuggable = "True" />',
        ):
            with self.subTest(content=content):
                self.assertIn("MASVS_CODE_DEBUGGABLE_ENABLED", _rules(content, MAIN_MANIFEST))

    def test_debug_variant_manifest_may_keep_debug_flags(self) -> None:
        self.assertEqual(gate.audit_mobile_text(INSECURE_MANIFEST, DEBUG_MANIFEST), [])

    def test_lookalike_debug_paths_stay_in_release_scope(self) -> None:
        for file_name in (
            "android/app/src/release/AndroidManifest.xml",
            "debug/AndroidManifest.xml",
            "android/app/src/debug/other/AndroidManifest.xml",
        ):
            with self.subTest(file_name=file_name):
                self.assertIn("MASVS_CODE_DEBUGGABLE_ENABLED", _rules(INSECURE_MANIFEST, file_name))

    def test_exported_component_requires_permission(self) -> None:
        guarded = '<service android:name=".S" android:exported="true" android:permission="com.x.SIGNED" />'
        self.assertEqual(gate.audit_mobile_text(guarded, MAIN_MANIFEST), [])
        unguarded = '<receiver android:name=".R" android:exported="true" />'
        self.assertIn("MASVS_PLATFORM_EXPORTED_WITHOUT_PERMISSION", _rules(unguarded, MAIN_MANIFEST))

    def test_signing_secret_from_env_passes_and_literal_is_blocked(self) -> None:
        self.assertEqual(
            gate.audit_mobile_text('storePassword System.getenv("STORE_PASS")', "android/app/build.gradle"), []
        )
        self.assertIn(
            "MASVS_CRYPTO_HARDCODED_SIGNING_SECRET",
            _rules('keyPassword = "hunter2hunter2"', "android/app/build.gradle"),
        )

    def test_ats_bypass_and_safetynet_are_blocked(self) -> None:
        self.assertIn(
            "MASVS_NETWORK_IOS_ATS_BYPASS",
            _rules("<key>NSAllowsArbitraryLoads</key>\n<true/>", "ios/Runner/Info.plist"),
        )
        self.assertEqual(
            gate.audit_mobile_text("<key>NSAllowsArbitraryLoads</key><false/>", "ios/Runner/Info.plist"), []
        )
        self.assertIn("MASVS_RESILIENCE_DEPRECATED_SAFETYNET", _rules("SafetyNet.getClient(ctx)", "App.kt"))

    def test_empty_snippet_has_no_findings_and_wrong_type_raises(self) -> None:
        self.assertEqual(gate.audit_mobile_text("", MAIN_MANIFEST), [])
        with self.assertRaises(TypeError):
            gate.audit_mobile_text(None, MAIN_MANIFEST)

    def test_self_test_probes_all_pass(self) -> None:
        report = gate.run_self_test()
        self.assertTrue(report["all_passed"], report)
        self.assertGreaterEqual(report["total_probes"], 10)


class ScanMobileRepoTests(unittest.TestCase):
    def setUp(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)

    def test_hardened_repo_with_privacy_manifest_passes(self) -> None:
        _write(self.root, "android/app/src/main/AndroidManifest.xml", HARDENED_MANIFEST)
        _write(self.root, "ios/Runner/Info.plist", "<key>NSAllowsArbitraryLoads</key><false/>")
        _write(self.root, "ios/Runner/PrivacyInfo.xcprivacy", "<plist></plist>")
        result = gate.scan_mobile_repo(self.root)
        self.assertEqual(result["status"], "PASS", result)
        self.assertEqual(result["scanned_files"], 3)

    def test_ios_without_privacy_manifest_is_blocked(self) -> None:
        _write(self.root, "ios/Runner/Info.plist", "<key>NSAllowsArbitraryLoads</key><false/>")
        result = gate.scan_mobile_repo(self.root)
        self.assertEqual(result["status"], "FINDINGS_DETECTED")
        self.assertIn("MASVS_PRIVACY_MISSING_XCPRIVACY", {f["rule_id"] for f in result["findings"]})

    def test_release_manifest_in_repo_is_blocked_but_debug_variant_is_not(self) -> None:
        _write(self.root, "android/app/src/main/AndroidManifest.xml", INSECURE_MANIFEST)
        _write(self.root, "android/app/src/debug/AndroidManifest.xml", INSECURE_MANIFEST)
        result = gate.scan_mobile_repo(self.root)
        self.assertEqual(result["status"], "FINDINGS_DETECTED")
        flagged_files = {Path(str(f["file"])).parent.name for f in result["findings"]}
        self.assertEqual(flagged_files, {"main"})

    def test_empty_or_missing_target_is_not_a_pass(self) -> None:
        for target in (self.root, self.root / "does-not-exist"):
            with self.subTest(target=str(target)):
                result = gate.scan_mobile_repo(target)
                self.assertEqual(result["scanned_files"], 0)
                self.assertNotEqual(result["status"], "PASS")

    def test_skip_dirs_are_not_scanned(self) -> None:
        _write(self.root, "node_modules/pkg/android/AndroidManifest.xml", INSECURE_MANIFEST)
        _write(self.root, "android/app/src/main/AndroidManifest.xml", HARDENED_MANIFEST)
        result = gate.scan_mobile_repo(self.root)
        self.assertEqual(result["status"], "PASS", result)
        self.assertEqual(result["scanned_files"], 1)


class MobileReleaseGateCliTests(unittest.TestCase):
    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT), *args], capture_output=True, text=True, timeout=60, check=False
        )

    def test_cli_exit_codes_follow_status(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            empty = self._run("--scan", str(root))
            self.assertEqual(empty.returncode, 1, empty.stdout)
            _write(root, "android/app/src/main/AndroidManifest.xml", HARDENED_MANIFEST)
            clean = self._run("--scan", str(root))
            self.assertEqual(clean.returncode, 0, clean.stdout)
            self.assertEqual(json.loads(clean.stdout)["status"], "PASS")
            _write(root, "android/app/src/main/AndroidManifest.xml", INSECURE_MANIFEST)
            dirty = self._run("--scan", str(root))
            self.assertEqual(dirty.returncode, 1, dirty.stdout)

    def test_cli_self_test_passes(self) -> None:
        proc = self._run("--self-test")
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertTrue(json.loads(proc.stdout)["all_passed"])


if __name__ == "__main__":
    unittest.main()
