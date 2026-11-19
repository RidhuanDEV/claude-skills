import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GATE = Path(__file__).resolve().parents[1] / "scripts/supplychain_sbom_gate.py"


class SupplychainCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.artifact = self.root / "build"
        self.artifact.write_bytes(b"fixture")
        pkg = {"ecosystem": "npm", "name": "my-facade", "version": "2", "scope": "runtime"}
        self.manifest = {"lockfile_synced": True, "lockfile_packages": [pkg.copy()], "sbom_components": [pkg.copy()]}
        policy = {"issuer": "ci-issuer", "builder_id": "org/build", "build_type": "release", "verifier": "ci-wrapper"}
        self.policy = {"platform": "linux", "trusted_builds": [policy]}
        self.receipt = {**policy, "status": "VERIFIED", "subject_sha256": hashlib.sha256(b"fixture").hexdigest()}

    def check(self, expected, *, receipt=True, as_of="2026-11-19"):
        for name, data in (("manifest", self.manifest), ("policy", self.policy), ("receipt", self.receipt)):
            (self.root / name).write_text(json.dumps(data), encoding="utf8")
        args = ["--verify", str(self.root/"manifest"), "--artifact", str(self.artifact), "--policy", str(self.root/"policy")]
        if as_of:
            args += ["--as-of-date", as_of]
        if receipt:
            args += ["--receipt", str(self.root/"receipt")]
        proc = subprocess.run([sys.executable, str(GATE), *args], capture_output=True, text=True, check=False)
        output = json.loads(proc.stdout)
        self.assertEqual(output["status"], expected, output)
        self.assertEqual(proc.returncode, 0 if expected == "PASS" else 1)
        return output

    def test_exact_artifact_and_trusted_build(self):
        self.assertEqual(self.check("PASS")["provenance_status"], "VERIFIED_RECEIPT")
        self.artifact.write_bytes(b"same filename, different artifact")
        self.check("FAIL")

    def test_wrong_issuer_builder_combination(self):
        self.policy["trusted_builds"].append(dict(self.policy["trusted_builds"][0], issuer="other", builder_id="other"))
        self.receipt["issuer"] = "other"
        self.check("FAIL")

    def test_offline_and_untrusted_declarations(self):
        self.manifest["provenance"] = {"signer_verified": True}
        self.check("INCOMPLETE", receipt=False)
        self.receipt["status"] = "OFFLINE"
        self.check("INCOMPLETE")
        self.manifest["provenance"]["signer_verified"] = "false"
        self.check("FAIL")

    def test_platform_exclusion_and_ecosystem_identity(self):
        pkg = {"ecosystem": "npm", "name": "native", "version": "1", "scope": "optional", "platforms": ["darwin"]}
        self.manifest["lockfile_packages"].append(pkg)
        self.assertEqual(len(self.check("PASS")["platform_exclusions"]), 1)
        self.manifest["sbom_components"][0]["ecosystem"] = "pypi"
        self.check("FAIL")

    def test_waiver_assessment_is_independent_of_manifest(self):
        self.manifest["waivers"] = [{"cve_id": "TEST-1", "expires_at": "2026-11-19"}]
        self.manifest["as_of_date"] = "2000-01-01"
        self.check("PASS")
        self.check("INCOMPLETE", as_of=None)
        self.check("FAIL", as_of="2026-11-20")
        self.manifest["waivers"][0]["expires_at"] = "2026-02-30"
        self.check("FAIL")

    def test_malformed_rows_and_typed_flag(self):
        self.manifest["lockfile_packages"].append(None)
        self.check("FAIL")
        self.manifest["lockfile_packages"].pop()
        self.manifest["lockfile_synced"] = "true"
        self.check("FAIL")


if __name__ == "__main__":
    unittest.main()
