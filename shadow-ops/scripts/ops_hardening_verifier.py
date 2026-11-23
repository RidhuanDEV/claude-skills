#!/usr/bin/env python3
"""Deterministic DevOps & container hardening verifier for shadow-ops.

Audits Dockerfiles and docker-compose production manifests for the 7 Non-Negotiable Hardening Rules:
  - Compose: forbids 0.0.0.0/unqualified DB/Redis ports (5432/3306/6379/27017 bypassing ufw),
    forbids :latest tags, privileged:true, requires memory limits, log rotation (max-size/max-file),
    and healthcheck.
  - Dockerfile: forbids :latest base image, missing non-root USER (or final USER root/0),
    unverified curl|sh piping, and hardcoded ENV secrets/passwords.
Zero external dependencies (Python stdlib only).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

INTERNAL_DATA_PORTS = ("5432", "3306", "6379", "27017")
PUBLIC_DB_PORT_RE = re.compile(
    r"""^\s*-\s*["']?(?:0\.0\.0\.0:)?(?:\d+:)?(?:5432|3306|6379|27017)(?:/(?:tcp|udp))?["']?\s*$""",
    re.MULTILINE,
)
LOCALHOST_DB_PORT_RE = re.compile(r"127\.0\.0\.1:")
LATEST_IMAGE_RE = re.compile(r"^\s*(?:image:|FROM)\s+\S+:latest(?:\s|$)", re.IGNORECASE | re.MULTILINE)
PRIVILEGED_RE = re.compile(r"^\s*privileged\s*:\s*true\b", re.IGNORECASE | re.MULTILINE)
DOCKERFILE_USER_RE = re.compile(r"^\s*USER\s+(\S+)", re.IGNORECASE | re.MULTILINE)
CURL_PIPE_SH_RE = re.compile(r"\b(?:curl|wget)\b[^\n|]*\|\s*(?:ba)?sh\b", re.IGNORECASE)
HARDCODED_ENV_SECRET_RE = re.compile(
    r"^\s*ENV\s+[A-Z0-9_]*(?:PASSWORD|SECRET|API_KEY|PRIVATE_KEY|TOKEN)[A-Z0-9_]*\s*=\s*['\"]?[^\s$'\"][^\n]*$",
    re.IGNORECASE | re.MULTILINE,
)


def check_compose_text(yaml_text: str) -> list[dict[str, str]]:
    """Audit a docker-compose production YAML manifest for core hardening controls."""
    violations: list[dict[str, str]] = []
    if not isinstance(yaml_text, str) or not yaml_text.strip():
        return [{"code": "EMPTY_COMPOSE", "detail": "Compose content must be non-empty."}]

    for line in yaml_text.splitlines():
        if PUBLIC_DB_PORT_RE.match(line) and not LOCALHOST_DB_PORT_RE.search(line):
            violations.append({
                "code": "PUBLIC_INTERNAL_DB_PORT",
                "detail": f"Internal DB/cache port bound publicly (`{line.strip()}`); Docker bypasses ufw — bind to `127.0.0.1:<port>:<port>` or keep on an `internal: true` network.",
            })

    if LATEST_IMAGE_RE.search(yaml_text):
        violations.append({
            "code": "FLOATING_LATEST_IMAGE",
            "detail": "Production compose references mutable `:latest` image tag; pin SemVer+SHA or `@sha256:` digest.",
        })

    if PRIVILEGED_RE.search(yaml_text):
        violations.append({
            "code": "PRIVILEGED_CONTAINER",
            "detail": "`privileged: true` grants full host root capabilities; remove and drop unused Linux capabilities.",
        })

    has_mem_limit = bool(re.search(r"\b(?:mem_limit|memory)\s*:", yaml_text))
    if not has_mem_limit:
        violations.append({
            "code": "MISSING_MEMORY_LIMIT",
            "detail": "Compose manifest lacks container memory limits (`mem_limit` or `deploy.resources.limits.memory`).",
        })

    has_log_rotation = "max-size" in yaml_text and "max-file" in yaml_text
    if not has_log_rotation:
        violations.append({
            "code": "MISSING_LOG_ROTATION",
            "detail": "Compose manifest lacks Docker log rotation (`max-size` and `max-file`) risking host disk exhaustion.",
        })

    if "healthcheck:" not in yaml_text:
        violations.append({
            "code": "MISSING_HEALTHCHECK",
            "detail": "Compose manifest lacks `healthcheck:` definition for zero-downtime readiness verification.",
        })

    return violations


def check_dockerfile_text(dockerfile_text: str) -> list[dict[str, str]]:
    """Audit a Dockerfile for non-root USER, pinned base image, safe install, and zero hardcoded secrets."""
    violations: list[dict[str, str]] = []
    if not isinstance(dockerfile_text, str) or not dockerfile_text.strip():
        return [{"code": "EMPTY_DOCKERFILE", "detail": "Dockerfile content must be non-empty."}]

    if LATEST_IMAGE_RE.search(dockerfile_text):
        violations.append({
            "code": "FLOATING_LATEST_BASE_IMAGE",
            "detail": "Dockerfile uses floating `:latest` base image; pin explicit version + `@sha256:` digest.",
        })

    users = DOCKERFILE_USER_RE.findall(dockerfile_text)
    if not users or users[-1].strip().lower() in {"root", "0", "0:0"}:
        violations.append({
            "code": "CONTAINER_RUNS_AS_ROOT",
            "detail": "Dockerfile final stage lacks a non-root `USER` instruction (OWASP Docker Cheat Sheet).",
        })

    if CURL_PIPE_SH_RE.search(dockerfile_text):
        violations.append({
            "code": "UNVERIFIED_CURL_PIPE_SH",
            "detail": "Unverified `curl|sh` pipe inside Dockerfile bypasses checksum/signature verification.",
        })

    if HARDCODED_ENV_SECRET_RE.search(dockerfile_text):
        violations.append({
            "code": "HARDCODED_DOCKERFILE_SECRET",
            "detail": "Hardcoded secret/password detected in Dockerfile `ENV` instruction; inject secrets at runtime only.",
        })

    return violations


def run_self_test() -> dict[str, Any]:
    probes: list[tuple[str, bool]] = []

    good_compose = """
services:
  api:
    image: ghcr.io/org/api@sha256:abc123def456
    init: true
    mem_limit: 512m
    healthcheck:
      test: ["CMD", "curl", "-f", "http://127.0.0.1:3000/healthz"]
    logging:
      driver: json-file
      options:
        max-size: "20m"
        max-file: "5"
  db:
    image: postgres:16.4-alpine@sha256:999888777
    ports:
      - "127.0.0.1:5432:5432"
"""
    probes.append(("PRECISION-1: Hardened Compose with 127.0.0.1 DB bind, mem_limit, log rotation & healthcheck passes", len(check_compose_text(good_compose)) == 0))

    bad_compose = """
services:
  api:
    image: ghcr.io/org/api:latest
    privileged: true
  db:
    image: postgres:16
    ports:
      - "5432:5432"
      - "0.0.0.0:6379:6379"
"""
    codes = {v["code"] for v in check_compose_text(bad_compose)}
    probes.append((
        "RECALL-1: Flags public 5432/6379 binds, :latest, privileged, missing mem/logs/healthcheck",
        {
            "PUBLIC_INTERNAL_DB_PORT",
            "FLOATING_LATEST_IMAGE",
            "PRIVILEGED_CONTAINER",
            "MISSING_MEMORY_LIMIT",
            "MISSING_LOG_ROTATION",
            "MISSING_HEALTHCHECK",
        }.issubset(codes),
    ))

    good_dockerfile = """
FROM node:22.11-alpine@sha256:1234567890abcdef AS runner
WORKDIR /app
RUN addgroup -S app && adduser -S app -G app
COPY --chown=app:app dist ./dist
USER app
CMD ["node", "dist/server.js"]
"""
    probes.append(("PRECISION-2: Hardened non-root pinned Dockerfile passes", len(check_dockerfile_text(good_dockerfile)) == 0))

    bad_dockerfile = """
FROM node:latest
ENV DB_PASSWORD=supersecret_prod_pass
RUN curl -fsSL https://example.com/install.sh | bash
CMD ["node", "server.js"]
"""
    d_codes = {v["code"] for v in check_dockerfile_text(bad_dockerfile)}
    probes.append((
        "RECALL-2: Flags :latest base, root USER, curl|bash, and hardcoded ENV password",
        {
            "FLOATING_LATEST_BASE_IMAGE",
            "CONTAINER_RUNS_AS_ROOT",
            "UNVERIFIED_CURL_PIPE_SH",
            "HARDCODED_DOCKERFILE_SECRET",
        }.issubset(d_codes),
    ))

    # RECALL-3: Multi-stage Dockerfile ending back in USER root caught
    root_revert = "FROM node:22-alpine\nUSER app\nUSER root\nCMD ['node']"
    probes.append(("RECALL-3: Flags Dockerfile reverting final stage back to USER root", any(v["code"] == "CONTAINER_RUNS_AS_ROOT" for v in check_dockerfile_text(root_revert))))

    # PRECISION-3: Compose keeping DB strictly internal without any published host ports passes
    internal_compose = """
services:
  api:
    image: ghcr.io/org/api:v1.2.0
    deploy:
      resources:
        limits:
          memory: 512M
    healthcheck:
      test: ["CMD-SHELL", "exit 0"]
    logging:
      options:
        max-size: "10m"
        max-file: "3"
"""
    probes.append(("PRECISION-3: Internal-network Compose with deploy.resources.limits.memory passes", len(check_compose_text(internal_compose)) == 0))

    # BOUNDARY-1: Empty inputs rejected cleanly
    probes.append(("BOUNDARY-1: Rejects empty compose & Dockerfile inputs gracefully", len(check_compose_text("")) == 1 and len(check_dockerfile_text(" ")) == 1))

    passed = sum(1 for _, ok in probes if ok)
    return {
        "tool": "ops_hardening_verifier.py",
        "total_probes": len(probes),
        "passed": passed,
        "failed": len(probes) - passed,
        "all_passed": passed == len(probes),
        "results": [{"probe": name, "passed": ok} for name, ok in probes],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Dockerfiles and docker-compose manifests against production ops hardening rules.")
    parser.add_argument("--self-test", action="store_true", help="Run built-in precision/recall falsification probes.")
    parser.add_argument("--check-compose", type=Path, help="Path to docker-compose.yml file.")
    parser.add_argument("--check-dockerfile", type=Path, help="Path to Dockerfile.")
    args = parser.parse_args(argv)

    if args.self_test:
        report = run_self_test()
        print(json.dumps(report, indent=2))
        return 0 if report["all_passed"] else 1

    violations: list[dict[str, str]] = []
    checked = False
    if args.check_compose:
        checked = True
        violations.extend(check_compose_text(args.check_compose.read_text(encoding="utf-8")))
    if args.check_dockerfile:
        checked = True
        violations.extend(check_dockerfile_text(args.check_dockerfile.read_text(encoding="utf-8")))

    if not checked:
        parser.print_help()
        return 2

    output = {"status": "PASS" if not violations else "FAIL", "violation_count": len(violations), "violations": violations}
    print(json.dumps(output, indent=2))
    return 0 if not violations else 1


if __name__ == "__main__":
    sys.exit(main())
