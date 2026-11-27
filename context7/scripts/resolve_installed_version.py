"""Resolve the installed version of an npm package in one workspace before looking up its docs.

Usage:
    python resolve_installed_version.py --workspace path/to/app --package next
    python resolve_installed_version.py --self-test

Resolution order: node_modules/<package>/package.json, then package-lock.json (v2/v3 "packages"
or v1 "dependencies"). A version range in package.json alone is reported as RANGE_ONLY, never
as a resolved version, because the range does not say which release is installed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import tempfile

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _exact(value: object) -> str | None:
    return value if isinstance(value, str) and VERSION_RE.match(value) else None


def resolve(workspace: Path, package: str) -> dict[str, object]:
    """Return RESOLVED with an exact version, RANGE_ONLY, NOT_DECLARED, or UNRESOLVED."""
    result: dict[str, object] = {"package": package, "workspace": str(workspace)}
    installed = _read_json(workspace / "node_modules" / package / "package.json")
    if isinstance(installed, dict) and (version := _exact(installed.get("version"))):
        return {**result, "status": "RESOLVED", "version": version, "major": int(version.split(".")[0]), "source": "node_modules"}
    lock = _read_json(workspace / "package-lock.json")
    if isinstance(lock, dict):
        packages = lock.get("packages")
        entry = packages.get(f"node_modules/{package}") if isinstance(packages, dict) else None
        if not isinstance(entry, dict):
            dependencies = lock.get("dependencies")
            entry = dependencies.get(package) if isinstance(dependencies, dict) else None
        if isinstance(entry, dict) and (version := _exact(entry.get("version"))):
            return {**result, "status": "RESOLVED", "version": version, "major": int(version.split(".")[0]), "source": "package-lock.json"}
    manifest = _read_json(workspace / "package.json")
    if not isinstance(manifest, dict):
        return {**result, "status": "UNRESOLVED", "reason": "No readable package.json, lockfile or installed package."}
    declared: object = None
    for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        block = manifest.get(section)
        if isinstance(block, dict) and package in block:
            declared = block[package]
            break
    if declared is None:
        return {**result, "status": "NOT_DECLARED"}
    return {
        **result, "status": "RANGE_ONLY", "declared_range": declared,
        "reason": "Only a manifest range is available; install or lock dependencies before claiming a version.",
    }


def self_test() -> list[str]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "package.json").write_text(json.dumps({"dependencies": {"next": "^14.2.15"}}), encoding="utf-8")
        if resolve(root, "next")["status"] != "RANGE_ONLY":
            failures.append("range-only manifest must not resolve")
        (root / "package-lock.json").write_text(json.dumps({"packages": {"node_modules/next": {"version": "14.2.18"}}}), encoding="utf-8")
        got = resolve(root, "next")
        if got.get("version") != "14.2.18":
            failures.append(f"lockfile resolution failed: {got}")
        if resolve(root, "react")["status"] != "NOT_DECLARED":
            failures.append("undeclared package must be NOT_DECLARED")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--package")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        failures = self_test()
        print(json.dumps({"self_test": "FAIL" if failures else "PASS", "failures": failures}, indent=2))
        return 1 if failures else 0
    if not args.workspace or not args.package:
        parser.error("--workspace and --package are required.")
    result = resolve(args.workspace, args.package)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "RESOLVED" else 1


if __name__ == "__main__":
    sys.exit(main())
