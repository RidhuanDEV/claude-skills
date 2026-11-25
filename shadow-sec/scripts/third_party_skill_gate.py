#!/usr/bin/env python3
"""Inspect and install a reviewed, documentation-only Agent Skill ZIP on Windows/Codex."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import stat
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit


POLICY = "shadow-sec/third-party-skill-v1"
MAX_SNAPSHOT_BYTES = 8 * 1024 * 1024
MAX_UNPACKED_BYTES = 8 * 1024 * 1024
MAX_ENTRIES = 256
SHA256 = re.compile(r"[0-9a-f]{64}")
COMMIT = re.compile(r"[0-9a-f]{40}")
SKILL_NAME = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*")
PATH_COMPONENT = re.compile(r"[A-Za-z0-9_][A-Za-z0-9._-]{0,119}")
RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL"} | {f"{prefix}{number}" for prefix in ("COM", "LPT") for number in range(1, 10)}
HOST_INSTRUCTIONS = {"agents.md", "claude.md", "gemini.md", "global.md", "skill.md"}
DESCRIPTION = re.compile(r"[A-Za-z][A-Za-z0-9 ,./()!?_-]{0,1023}")
YAML_LITERAL = {"true", "false", "yes", "no", "on", "off", "null", "y", "n"}


def is_link(info: os.stat_result) -> bool:
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def plain_directory(path: Path) -> Path:
    absolute = Path(os.path.abspath(path))
    if absolute.drive.startswith("\\\\"):
        raise ValueError("Use a local directory, with no network share.")
    for directory in (*reversed(absolute.parents), absolute):
        info = directory.lstat()
        if not stat.S_ISDIR(info.st_mode) or is_link(info):
            raise ValueError("Directory must have no symbolic links or reparse points.")
    return absolute


def read_bounded(path: Path, limit: int) -> bytes:
    path = plain_directory(path.parent) / path.name
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or is_link(before) or before.st_nlink != 1 or before.st_size > limit:
        raise ValueError("Expected a bounded, regular file with one link.")
    with path.open("rb") as stream:
        after = os.fstat(stream.fileno())
        if not os.path.samestat(before, after) or after.st_nlink != 1:
            raise ValueError("Input changed while opening.")
        data = stream.read(limit + 1)
    if not data or len(data) > limit:
        raise ValueError("Input is empty or exceeds its size limit.")
    return data


def unpack_snapshot(raw: bytes) -> tuple[str, dict[str, bytes]]:
    files: dict[str, bytes] = {}
    seen: dict[str, str] = {}
    explicit_paths: set[str] = set()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries = archive.infolist()
        if len(entries) > MAX_ENTRIES or sum(entry.file_size for entry in entries) > MAX_UNPACKED_BYTES:
            raise ValueError("Snapshot exceeds its entry or unpacked size limit.")
        for entry in entries:
            if entry.orig_filename != entry.filename:
                raise ValueError("Snapshot contains an invalid filename.")
            path = entry.filename.removesuffix("/")
            parts = path.split("/")
            if len(parts) > 8 or any(
                not PATH_COMPONENT.fullmatch(part) or part.endswith(".") or part.split(".")[0].upper() in RESERVED_NAMES
                for part in parts
            ):
                raise ValueError("Snapshot contains an unsafe or unsupported path.")
            for depth in range(1, len(parts) + 1):
                name = "/".join(parts[:depth])
                key = name.casefold()
                if seen.setdefault(key, name) != name:
                    raise ValueError("Snapshot contains paths that collide on Windows.")
            if path in explicit_paths:
                raise ValueError("Snapshot contains a duplicate path.")
            explicit_paths.add(path)
            kind = stat.S_IFMT(entry.external_attr >> 16)
            if entry.is_dir():
                if kind not in (0, stat.S_IFDIR) or entry.file_size:
                    raise ValueError("Snapshot contains an unsupported directory entry.")
                continue
            if (
                kind not in (0, stat.S_IFREG)
                or entry.flag_bits & 1
                or entry.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                or PurePosixPath(entry.filename).suffix.lower() not in {".md", ".txt"}
                or (parts[-1].casefold() in HOST_INSTRUCTIONS and entry.filename != "SKILL.md")
            ):
                raise ValueError("Snapshot must contain only unique Markdown and text files.")
            with archive.open(entry) as stream:
                data = stream.read(entry.file_size + 1)
            if len(data) != entry.file_size:
                raise ValueError("Snapshot entry size differs from its inventory.")
            if "\x00" in data.decode("utf-8"):
                raise ValueError("Snapshot text contains a null character.")
            files[entry.filename] = data

    paths = {PurePosixPath(name) for name in files}
    if any(parent in paths for path in paths for parent in path.parents):
        raise ValueError("Snapshot contains a path used as both a file and a directory.")
    if "SKILL.md" not in files:
        raise ValueError("Snapshot must contain a root SKILL.md.")
    lines = files["SKILL.md"].decode("utf-8").replace("\r\n", "\n").split("\n")
    if len(lines) < 4 or lines[0] != "---" or lines[3] != "---":
        raise ValueError("SKILL.md requires a two-field frontmatter header.")
    fields = dict(line.split(": ", 1) for line in lines[1:3])
    name = fields.get("name", "")
    description = fields.get("description", "")
    if (
        len(name) > 64 or not SKILL_NAME.fullmatch(name) or name.upper() in RESERVED_NAMES
        or not DESCRIPTION.fullmatch(description) or {name.lower(), description.strip().lower()} & YAML_LITERAL
    ):
        raise ValueError("SKILL.md requires a plain skill name and a single-line plain description.")
    return name, files


def unique_keys(items: list[tuple[str, object]]) -> dict:
    result = dict(items)
    if len(result) != len(items):
        raise ValueError("Receipt contains duplicate keys.")
    return result


def valid_source_url(value: object) -> bool:
    if not isinstance(value, str) or not value or any(character.isspace() or ord(character) < 32 for character in value):
        return False
    parts = urlsplit(value)
    return bool(parts.scheme == "https" and parts.hostname and parts.path.strip("/") and not any(
        (parts.username, parts.password, parts.query, parts.fragment, "\\" in value, "@" in parts.netloc)
    ))


def checked_receipt(raw: bytes, expected: str, snapshot_sha256: str, name: str, root: Path) -> dict:
    if not SHA256.fullmatch(expected) or hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("Receipt does not match the operator-provided SHA-256.")
    receipt = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique_keys)
    if type(receipt.get("schema_version")) is not int or receipt["schema_version"] != 1 or receipt.get("policy") != POLICY:
        raise ValueError("Unsupported receipt schema or policy.")
    source_commit = receipt.get("source_commit")
    if not valid_source_url(receipt.get("source_url")) or not isinstance(source_commit, str) or not COMMIT.fullmatch(source_commit):
        raise ValueError("Receipt must identify the HTTPS source and full Git commit SHA.")
    if receipt.get("snapshot_sha256") != snapshot_sha256 or receipt.get("verdict") != "APPROVED":
        raise ValueError("Receipt does not approve these exact snapshot bytes.")
    gates = receipt["gates"]
    if set(gates) != {f"G{index}" for index in range(7)}:
        raise ValueError("Receipt must account for every audit gate G0–G6.")
    for gate_id, gate in gates.items():
        allowed = {"PASS", "NOT_APPLICABLE"} if gate_id in {"G2", "G6"} else {"PASS"}
        if gate.get("status") not in allowed or not isinstance(gate.get("evidence"), str) or not gate["evidence"].strip():
            raise ValueError(f"{gate_id} lacks an acceptable status or evidence.")

    target = receipt["target"]
    if target != {"host": "codex", "skills_root": str(root), "skill_name": name, "action": "install-new"}:
        raise ValueError("Approval does not match the exact host, profile, skill, and action.")
    approval = receipt["approval"]
    if not isinstance(approval.get("approved_by"), str) or not approval["approved_by"].strip():
        raise ValueError("Receipt needs an explicit approver.")
    approved = datetime.fromisoformat(approval["approved_at"].replace("Z", "+00:00"))
    expires = datetime.fromisoformat(approval["expires_at"].replace("Z", "+00:00"))
    if approved.utcoffset() is None or expires.utcoffset() is None or not approved <= datetime.now(timezone.utc) < expires:
        raise ValueError("Approval must be timezone-aware and currently valid.")
    return receipt


def check_target_available(target: Path) -> None:
    if os.path.lexists(target):
        raise ValueError("Target already exists. Existing skills are preserved.")


def install_snapshot(root: Path, name: str, files: dict[str, bytes]) -> None:
    if os.name != "nt":
        raise ValueError("Managed activation currently supports Windows/Codex only.")
    with tempfile.TemporaryDirectory(prefix=".shadow-skill-", dir=root.parent) as folder:
        staged = Path(folder) / name
        staged.mkdir()
        for relative, data in files.items():
            path = staged / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(data)
        if any((staged / relative).read_bytes() != data for relative, data in files.items()):
            raise ValueError("Staged files do not match the reviewed snapshot.")
        target = plain_directory(root) / name
        check_target_available(target)
        staged.rename(target)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["inspect", "preflight", "install"])
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--receipt-sha256")
    parser.add_argument("--skills-root", type=Path)
    parser.add_argument("--approve", action="store_true", help="Confirm the exact activation described in the pinned receipt")
    args = parser.parse_args()

    try:
        raw = read_bounded(args.snapshot, MAX_SNAPSHOT_BYTES)
        name, files = unpack_snapshot(raw)
        sha256 = hashlib.sha256(raw).hexdigest()
        if args.action == "inspect":
            result = {
                "status": "INVENTORIED",
                "policy": POLICY,
                "snapshot_sha256": sha256,
                "skill_name": name,
                "files": [{"path": path, "sha256": hashlib.sha256(data).hexdigest()} for path, data in sorted(files.items())],
            }
        else:
            if not all((args.receipt, args.receipt_sha256, args.skills_root)):
                raise ValueError("Provide a trusted receipt, its independently obtained SHA-256, and the exact skills root.")
            root = plain_directory(args.skills_root)
            inputs = (Path(os.path.abspath(path)) for path in (args.snapshot, args.receipt))
            if any(root in (path, *path.parents) for path in inputs):
                raise ValueError("Snapshot and receipt must stay outside the skill discovery directory.")
            target = root / name
            check_target_available(target)
            receipt = checked_receipt(read_bounded(args.receipt, 128 * 1024), args.receipt_sha256, sha256, name, root)
            if args.action == "install":
                if not args.approve:
                    raise ValueError("Activation requires explicit --approve after reviewing the pinned receipt.")
                install_snapshot(root, name, files)
            result = {
                "status": "INSTALLED" if args.action == "install" else "ELIGIBLE",
                "source_commit": receipt["source_commit"],
                "snapshot_sha256": sha256,
                "target": str(target),
            }
    except (OSError, ValueError, TypeError, AttributeError, KeyError, RuntimeError, zipfile.BadZipFile, NotImplementedError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
