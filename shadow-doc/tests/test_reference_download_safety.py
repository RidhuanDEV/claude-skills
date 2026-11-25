from __future__ import annotations

import contextlib
import hashlib
import io
import json
import socket
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import reference_verifier as verifier


class ReferenceDownloadSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()

    def scan_cli(self, path: Path, *flags: str) -> tuple[int, dict, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch.object(sys, "argv", ["reference_verifier.py", "scan", str(path), *flags]):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                status = verifier.main()
        return status, json.loads(stdout.getvalue()), stderr.getvalue()

    def test_empty_missing_and_valid_scans(self) -> None:
        for path in (self.root, self.root / "missing"):
            with self.subTest(path=path):
                code, report, _ = self.scan_cli(path)
                self.assertEqual(code, 1)
                self.assertFalse(report["all_safe"])
        (self.root / "plain.txt").write_text("Ordinary reference", encoding="utf-8")
        code, report, _ = self.scan_cli(self.root)
        self.assertEqual(code, 0)
        self.assertEqual(report["checked_count"], 1)

    def test_legacy_delete_flag_is_read_only(self) -> None:
        sample = self.root / "unsupported.extension"
        sample.write_bytes(b"Plain fixture with unsupported filename")
        code, report, warning = self.scan_cli(sample, "--quarantine-delete")
        self.assertEqual(code, 1)
        self.assertEqual(report["results"][0]["quarantine_action"], "NONE")
        self.assertIn("deprecated", warning)
        self.assertTrue(sample.is_file())

    def test_scan_skips_link_contents_and_reports_reparse_points(self) -> None:
        outside = self.root / "outside.txt"
        outside.write_text("Outside sample", encoding="utf-8")
        archive = self.root / "archive"
        archive.mkdir()
        suspect = archive / "entry.txt"
        suspect.write_text("Synthetic reparse marker", encoding="utf-8")
        original_lstat = Path.lstat

        def lstat(path: Path):
            if path == suspect:
                return SimpleNamespace(st_mode=stat.S_IFREG, st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT)
            return original_lstat(path)

        with patch.object(Path, "lstat", lstat), patch.object(verifier, "_read_reference") as read:
            code, report, _ = self.scan_cli(archive, "--quarantine-delete")
        self.assertEqual(code, 1)
        self.assertIn("reparse points", report["results"][0]["reasons"][0])
        read.assert_not_called()
        self.assertEqual(outside.read_text(encoding="utf-8"), "Outside sample")

    def test_symlink_root_is_blocked(self) -> None:
        outside = self.root / "documents"
        outside.mkdir()
        (outside / "ok.txt").write_text("External fixture", encoding="utf-8")
        link = self.root / "alias"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"Creating a directory symlink is unavailable in this profile: {exc}")
        for path in (link, link / "ok.txt"):
            with self.subTest(path=path):
                code, report, _ = self.scan_cli(path)
                self.assertEqual(code, 1)
                self.assertIn("reparse points", report["results"][0]["reasons"][0])

    def test_https_redirect_rejects_downgrade_and_credentials(self) -> None:
        expected = "https://publisher.example/paper.txt"
        for destination in ("http://cdn.example/paper.txt", "https://name@cdn.example/paper.txt"):
            with self.subTest(destination=destination):
                response = Mock(status=302, getheader=Mock(return_value=destination))
                with patch.object(verifier, "_PublicHTTPSConnection", side_effect=[self.connection(response)]) as connect:
                    with self.assertRaises(ValueError):
                        verifier._download_to_stage(expected, self.root / "paper.txt")
                connect.assert_called_once()
                response.read1.assert_not_called()

    def test_socket_policy_rejects_nonpublic_dns_and_pins_public_address(self) -> None:
        context = Mock()
        connection = verifier._PublicHTTPSConnection("publisher.example", timeout=30, context=context)
        record = (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("8.8.8.8", 443))
        with patch.object(socket, "getaddrinfo", return_value=[record]), patch.object(socket, "socket") as create:
            connection.connect()
        create.return_value.connect.assert_called_once_with(("8.8.8.8", 443))
        context.wrap_socket.assert_called_once_with(create.return_value, server_hostname="publisher.example")

        for address in ("127.0.0.1", "10.0.0.10", "169.254.0.10", "224.0.0.1", "::1", "::ffff:127.0.0.1"):
            blocked = (*record[:-1], (address, 443))
            with self.subTest(address=address):
                with patch.object(socket, "getaddrinfo", return_value=[record, blocked]), patch.object(socket, "socket") as connect:
                    with self.assertRaisesRegex(ValueError, "public addresses"):
                        connection.connect()
                    connect.assert_not_called()
        self.assertTrue(verifier._is_public_address("2606:4700:4700::1111"))

    def connection(self, response: Mock) -> Mock:
        connection = Mock()
        connection.getresponse.return_value = contextlib.nullcontext(response)
        return connection

    def download(self, content: bytes, expected: str, *, content_length: str | None = None) -> dict:
        redirect = Mock(status=302, getheader=Mock(return_value="https://cdn.example/paper.txt?secret=omitted#anchor"))
        headers = {"Content-Length": content_length}
        response = Mock(status=200, getheader=Mock(side_effect=headers.get), read1=io.BytesIO(content).read1)
        with patch.object(verifier, "_PublicHTTPSConnection", side_effect=[self.connection(redirect), self.connection(response)]):
            return verifier.download_and_verify_reference(
                "https://publisher.example/paper.txt?secret=omitted", self.root,
                "Reference", "Publisher", "2026", expected_sha256=expected,
            )

    def test_verified_download_and_digest_failure_preserve_prior_archive(self) -> None:
        content = b"Trusted reference bytes\n"
        digest = hashlib.sha256(content).hexdigest()
        published = self.download(content, digest.upper())
        self.assertTrue(published["safety"]["safe"])
        self.assertEqual(published["download_url"], "https://publisher.example/paper.txt")
        self.assertEqual(published["final_url"], "https://cdn.example/paper.txt")
        manifest = self.root / verifier.MANIFEST_NAME
        initial_manifest = manifest.read_bytes()
        self.assertEqual(verifier.assess_reference(manifest, "paper.txt", "2026")["status"], "PIN_MATCH")

        result = self.download(b"Changed download", digest)
        self.assertEqual(result["safety"]["status"], "INTEGRITY_MISMATCH")
        self.assertEqual(result["safety"]["quarantine_action"], "DISCARDED_STAGING_FILE")
        self.assertEqual((self.root / "paper.txt").read_bytes(), content)
        self.assertEqual(manifest.read_bytes(), initial_manifest)
        self.assertEqual(sorted(path.name for path in self.root.iterdir()), ["paper.txt", verifier.MANIFEST_NAME])

    def test_reserved_filename_and_invalid_expected_digest_fail_before_download(self) -> None:
        with patch.object(verifier, "_download_to_stage") as fetch:
            for inputs in ({"filename": "CON.txt"}, {"filename": "references_manifest.json"}, {"expected_sha256": "wrong"}):
                with self.subTest(inputs=inputs), self.assertRaises(ValueError):
                    verifier.download_and_verify_reference(
                        "https://publisher.example/paper.txt", self.root, "Reference", "Publisher", "2026", **inputs,
                    )
        fetch.assert_not_called()

    def test_redirect_responses_are_closed_and_payload_is_streamed(self) -> None:
        first = Mock(status=307, getheader=Mock(return_value="/final.txt"))
        final = Mock(status=200, getheader=Mock(return_value=None), read1=io.BytesIO(b"reference").read1)
        first_request, final_request = self.connection(first), self.connection(final)
        target = self.root / "paper.txt"
        with patch.object(verifier, "_PublicHTTPSConnection", side_effect=[first_request, final_request]):
            origin = verifier._download_to_stage("https://publisher.example/paper.txt", target)
        self.assertEqual(origin, "https://publisher.example/final.txt")
        self.assertEqual(final_request.request.call_args.args[:2], ("GET", "/final.txt"))
        self.assertEqual(target.read_bytes(), b"reference")
        first.read1.assert_not_called()
        first_request.close.assert_called_once()

    def test_download_cap_and_incomplete_content(self) -> None:
        with patch.object(verifier, "MAX_FILE_BYTES", 8):
            with self.assertRaisesRegex(ValueError, "size limit"):
                self.download(b"x" * 9, "a" * 64)
            with self.assertRaisesRegex(ValueError, "Incomplete"):
                self.download(b"short", "a" * 64, content_length="8")
        self.assertEqual(list(self.root.iterdir()), [])

    def test_publish_failure_rolls_back_preexisting_file(self) -> None:
        content = b"Previous verified document"
        self.download(content, hashlib.sha256(content).hexdigest())
        target = self.root / "paper.txt"
        manifest = self.root / verifier.MANIFEST_NAME
        recorded_manifest = manifest.read_bytes()
        replacement = b"New verified document"
        original_replace = Path.replace

        def replace(path: Path, destination: Path):
            if destination == manifest:
                raise OSError("Simulated manifest publish failure")
            return original_replace(path, destination)

        with patch.object(Path, "replace", replace), self.assertRaisesRegex(OSError, "Simulated"):
            self.download(replacement, hashlib.sha256(replacement).hexdigest())
        self.assertEqual(target.read_bytes(), content)
        self.assertEqual(manifest.read_bytes(), recorded_manifest)
        self.assertEqual(sorted(path.name for path in self.root.iterdir()), [target.name, manifest.name])


if __name__ == "__main__":
    unittest.main()
