from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "ops_hardening_verifier.py"


def _load_verifier() -> ModuleType:
    spec = importlib.util.spec_from_file_location("ops_hardening_verifier_profiles", SCRIPT)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ohv = _load_verifier()

HARDENED_TAIL = (
    "    mem_limit: 512m\n"
    "    healthcheck:\n"
    "      test: ['CMD', 'true']\n"
    "    logging:\n"
    "      options:\n"
    "        max-size: 10m\n"
    "        max-file: 3\n"
)
STATIC_SITE = "services:\n  web:\n    image: nginx:1.27.2-alpine\n    ports:\n      - '443:443'\n" + HARDENED_TAIL


def _stateful(ports_block: str) -> str:
    return (
        "services:\n  api:\n    image: ghcr.io/org/api:v1.2.0\n" + HARDENED_TAIL
        + "  db:\n    image: postgres:16.4-alpine\n    ports:\n" + ports_block
    )


def _compose_codes(text: str) -> set[str]:
    return {v["code"] for v in ohv.check_compose_text(text)}


class ComposeProfileTests(unittest.TestCase):
    def test_static_site_profile_without_db_passes(self) -> None:
        self.assertEqual(ohv.check_compose_text(STATIC_SITE), [])

    def test_stateful_profile_with_loopback_db_bind_passes(self) -> None:
        self.assertEqual(ohv.check_compose_text(_stateful("      - '127.0.0.1:5432:5432'\n")), [])

    def test_short_form_public_db_ports_are_blocked(self) -> None:
        for port_line in ("      - '5432:5432'\n", '      - "0.0.0.0:6379:6379"\n', "      - 27017\n", "      - '15432:3306/tcp'\n"):
            with self.subTest(port_line=port_line):
                self.assertIn("PUBLIC_INTERNAL_DB_PORT", _compose_codes(_stateful(port_line)))

    def test_long_form_loopback_or_unpublished_db_port_passes(self) -> None:
        for block in (
            "      - target: 5432\n        published: 5432\n        host_ip: 127.0.0.1\n",
            "      - target: 5432\n        protocol: tcp\n",
        ):
            with self.subTest(block=block):
                self.assertEqual(ohv.check_compose_text(_stateful(block)), [])

    def test_long_form_public_db_ports_are_blocked(self) -> None:
        for block in (
            "      - target: 5432\n        published: 5432\n        protocol: tcp\n",
            '      - target: "6379"\n        published: "16379"\n        host_ip: 0.0.0.0\n',
            "      - published: 3306\n        target: 3306\n",
            "    - target: 27017\n      published: 27017\n",
        ):
            with self.subTest(block=block):
                self.assertIn("PUBLIC_INTERNAL_DB_PORT", _compose_codes(_stateful(block)))

    def test_long_form_port_scope_ends_at_next_key(self) -> None:
        text = _stateful("      - target: 8080\n        published: 8080\n") + "    environment:\n      - target: 5432\n"
        self.assertNotIn("PUBLIC_INTERNAL_DB_PORT", _compose_codes(text))

    def test_privileged_latest_and_missing_controls_are_blocked(self) -> None:
        bad = "services:\n  api:\n    image: org/api:latest\n    privileged: true\n"
        self.assertEqual(
            _compose_codes(bad),
            {"FLOATING_LATEST_IMAGE", "PRIVILEGED_CONTAINER", "MISSING_MEMORY_LIMIT", "MISSING_LOG_ROTATION", "MISSING_HEALTHCHECK"},
        )
        self.assertEqual(_compose_codes(STATIC_SITE + "    privileged: false\n"), set())

    def test_empty_and_wrong_type_compose_are_rejected(self) -> None:
        for value in ("", "   \n", None, 42):
            with self.subTest(value=value):
                self.assertEqual(_compose_codes(value), {"EMPTY_COMPOSE"})


class DockerfileTests(unittest.TestCase):
    GOOD = "FROM node:22.11-alpine@sha256:abc\nUSER app\nCMD [\"node\"]\n"

    def test_hardened_dockerfile_passes(self) -> None:
        self.assertEqual(ohv.check_dockerfile_text(self.GOOD), [])

    def test_root_user_variants_are_blocked(self) -> None:
        for text in ("FROM node:22\nCMD x\n", "FROM node:22\nUSER app\nUSER 0\n", "FROM node:22\nUSER root\n"):
            with self.subTest(text=text):
                codes = {v["code"] for v in ohv.check_dockerfile_text(text)}
                self.assertIn("CONTAINER_RUNS_AS_ROOT", codes)

    def test_secret_env_and_curl_pipe_are_blocked_but_runtime_reference_passes(self) -> None:
        codes = {v["code"] for v in ohv.check_dockerfile_text(self.GOOD + "ENV API_TOKEN=abc123\nRUN wget -qO- https://x.sh | sh\n")}
        self.assertEqual(codes, {"HARDCODED_DOCKERFILE_SECRET", "UNVERIFIED_CURL_PIPE_SH"})
        self.assertEqual(ohv.check_dockerfile_text(self.GOOD + "ENV DB_PASSWORD=$DB_PASSWORD\n"), [])

    def test_empty_and_wrong_type_dockerfile_are_rejected(self) -> None:
        for value in ("", None, ["FROM node"]):
            with self.subTest(value=value):
                self.assertEqual({v["code"] for v in ohv.check_dockerfile_text(value)}, {"EMPTY_DOCKERFILE"})


class CliTests(unittest.TestCase):
    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, "-B", str(SCRIPT), *args], capture_output=True, text=True, timeout=60, check=False)

    def test_cli_pass_fail_and_usage_exit_codes(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            good = Path(folder) / "good.yml"
            good.write_text(STATIC_SITE, encoding="utf-8")
            bad = Path(folder) / "bad.yml"
            bad.write_text(_stateful("      - target: 5432\n        published: 5432\n"), encoding="utf-8")
            ok = self._run("--check-compose", str(good))
            self.assertEqual(ok.returncode, 0, ok.stdout)
            self.assertEqual(json.loads(ok.stdout)["status"], "PASS")
            fail = self._run("--check-compose", str(bad))
            self.assertEqual(fail.returncode, 1, fail.stdout)
            self.assertEqual(json.loads(fail.stdout)["status"], "FAIL")
        self.assertEqual(self._run().returncode, 2)


if __name__ == "__main__":
    unittest.main()
