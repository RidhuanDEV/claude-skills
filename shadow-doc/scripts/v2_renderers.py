#!/usr/bin/env python3
"""
Shadow-Doc v2.0 — Multi-Format Renderers & Handover Packager
Renders Canonical AST v2.0 (`blocks[]`, `history[]`, `signoff_record[]`) into:
- Markdown (.md)
- Word (.docx) with corporate/institutional profiles, running headers/footers, TOC field, repeating table headers
- PDF (.pdf) with page numbers, outlines/bookmarks, metadata & content tables
- Excel (.xlsx) & CSV (.csv) with README_Metadata, Register_Data, Traceability_Links, Data_Dictionary
- Stage Handover Package (.zip + manifest.json with SHA-256)
"""

import copy
import csv
import html as html_lib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Tuple

from doc_orchestrator import atomic_write_text
from v2_core import compute_file_sha256, scan_and_redact_secrets

RENDERER_ENGINE_VERSION = "2.1.0"

RENDERER_CONTRACTS: Dict[str, Dict[str, Any]] = {
    "md": {
        "schema_versions": ["2.0", "2.1"],
        "node_types": ["heading", "paragraph", "table", "figure", "list", "code", "opaque", "finding", "decision-matrix", "appendix"],
        "output_formats": ["md"],
        "dependencies": ["stdlib"],
        "asset_support": ["mermaid-fenced", "dbml-fenced", "image-link"],
        "limitations": [],
        "validation": "verify_rendered_outputs_qa(md_parity)",
    },
    "html": {
        "schema_versions": ["2.0", "2.1"],
        "node_types": ["heading", "paragraph", "table", "figure", "list", "code", "opaque", "finding", "decision-matrix", "appendix"],
        "output_formats": ["html"],
        "dependencies": ["stdlib"],
        "asset_support": ["mermaid-pre", "dbml-pre", "svg-embed-when-cli-available"],
        "limitations": ["Interactive Mermaid/DBML rendering in browser requires external JS or pre-rendered SVG via mmdc"],
        "validation": "verify_rendered_outputs_qa(html_parity)",
    },
    "docx": {
        "schema_versions": ["2.0", "2.1"],
        "node_types": ["heading", "paragraph", "table", "figure", "list", "code", "opaque", "finding", "decision-matrix", "appendix"],
        "output_formats": ["docx"],
        "dependencies": ["python-docx"],
        "asset_support": ["mermaid-source", "dbml-source", "png-embed-when-present"],
        "limitations": ["Word TOC page numbers populate upon pressing Ctrl+A -> F9 in Microsoft Word"],
        "validation": "verify_rendered_outputs_qa(docx_parity)",
    },
    "pdf": {
        "schema_versions": ["2.0", "2.1"],
        "node_types": ["heading", "paragraph", "table", "figure", "list", "code", "opaque", "finding", "decision-matrix", "appendix"],
        "output_formats": ["pdf"],
        "dependencies": ["fpdf2"],
        "asset_support": ["mermaid-source", "dbml-source"],
        "limitations": ["fpdf2 built-in Helvetica normalizes non-ASCII characters via _ascii_clean"],
        "validation": "verify_rendered_outputs_qa(exists_and_non_empty)",
    },
    "xlsx": {
        "schema_versions": ["2.0", "2.1"],
        "node_types": ["table", "heading", "paragraph", "finding", "decision-matrix"],
        "output_formats": ["xlsx"],
        "dependencies": ["openpyxl"],
        "asset_support": ["structured-sheets"],
        "limitations": ["Primarily exports tabular registers and traceability matrices"],
        "validation": "verify_rendered_outputs_qa(xlsx_parity)",
    },
    "csv": {
        "schema_versions": ["2.0", "2.1"],
        "node_types": ["table"],
        "output_formats": ["csv"],
        "dependencies": ["stdlib"],
        "asset_support": ["flat-table"],
        "limitations": ["Exports primary tabular block only"],
        "validation": "verify_rendered_outputs_qa(exists_and_non_empty)",
    },
}


def render_diagram_asset(
    diagram_type: str,
    source_text: str,
    *,
    render_to_asset: bool = False,
    output_dir: Path | None = None,
    asset_stem: str = "diagram",
    output_format: str = "svg",
    timeout_sec: int = 10,
    cli_override: str | None = None,
) -> Dict[str, Any]:
    """
    Attempt bounded diagram CLI rendering safely without shell interpolation or AST corruption (`R07`).
    Explicitly distinguishes: CLI_MISSING | RENDER_UNSUPPORTED_FOR_TOOL | RENDERED | RENDER_FAILED |
    RENDER_TIMEOUT | FALLBACK_SOURCE_PRESERVED. Never treats dbml2sql as a diagram-to-image renderer.
    """
    d_type = (diagram_type or "mermaid").lower()
    if d_type == "dbml":
        # dbml2sql transpiles DBML -> SQL DDL, NOT SVG/PNG diagram images!
        dbml_img_cli = cli_override if cli_override is not None else None
        if not dbml_img_cli:
            return {
                "diagram_type": "dbml",
                "cli_tool": None,
                "cli_available": False,
                "render_attempted": False,
                "render_status": "FALLBACK_SOURCE_PRESERVED",
                "reason": "No DBML diagram-image CLI configured (dbml2sql only outputs SQL, not image assets); source preserved verbatim.",
                "source_length": len(source_text or ""),
            }
        cli_path = shutil.which(dbml_img_cli) if not Path(dbml_img_cli).exists() else dbml_img_cli
        cli_name = str(dbml_img_cli)
    else:
        cli_name = cli_override or "mmdc"
        cli_path = cli_override if (cli_override and Path(cli_override).exists()) else shutil.which(cli_name)

    if not cli_path:
        return {
            "diagram_type": d_type,
            "cli_tool": cli_name,
            "cli_available": False,
            "render_attempted": False,
            "render_status": "FALLBACK_SOURCE_PRESERVED" if not render_to_asset else "CLI_MISSING",
            "fallback_used": True,
            "source_length": len(source_text or ""),
        }

    if not render_to_asset or output_dir is None:
        return {
            "diagram_type": d_type,
            "cli_tool": cli_name,
            "cli_available": True,
            "render_attempted": False,
            "render_status": "CLI_DETECTED_NOT_ATTEMPTED",
            "fallback_used": True,
            "source_length": len(source_text or ""),
        }

    ext = "png" if output_format.lower() == "png" else "svg"
    output_dir.mkdir(parents=True, exist_ok=True)
    target_asset = (output_dir / f"{asset_stem}.{ext}").resolve()
    try:
        target_asset.relative_to(output_dir.resolve())
    except ValueError:
        return {
            "diagram_type": d_type,
            "cli_tool": cli_name,
            "cli_available": True,
            "render_attempted": False,
            "render_status": "RENDER_FAILED",
            "reason": "Invalid diagram asset stem path traversal rejected.",
            "fallback_used": True,
            "source_length": len(source_text or ""),
        }

    with tempfile.TemporaryDirectory() as tmpd:
        in_file = Path(tmpd) / f"in.{d_type}"
        tmp_out = Path(tmpd) / f"out.{ext}"
        in_file.write_text(source_text or "", encoding="utf-8")

        # Argument-array execution ONLY (shell=False, bounded timeout)
        if Path(cli_path).suffix.lower() == ".py":
            cmd = [sys.executable, str(cli_path), "-i", str(in_file), "-o", str(tmp_out)]
        else:
            cmd = [str(cli_path), "-i", str(in_file), "-o", str(tmp_out)]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                shell=False,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {
                "diagram_type": d_type,
                "cli_tool": cli_name,
                "cli_available": True,
                "render_attempted": True,
                "render_status": "RENDER_TIMEOUT",
                "fallback_used": True,
                "reason": f"Diagram renderer exceeded {timeout_sec}s timeout.",
                "source_length": len(source_text or ""),
            }
        except OSError as exc:
            return {
                "diagram_type": d_type,
                "cli_tool": cli_name,
                "cli_available": True,
                "render_attempted": True,
                "render_status": "RENDER_FAILED",
                "fallback_used": True,
                "reason": f"OS error invoking diagram CLI: {exc}",
                "source_length": len(source_text or ""),
            }

        if proc.returncode != 0 or not tmp_out.is_file() or tmp_out.stat().st_size == 0:
            return {
                "diagram_type": d_type,
                "cli_tool": cli_name,
                "cli_available": True,
                "render_attempted": True,
                "render_status": "RENDER_FAILED",
                "fallback_used": True,
                "exit_code": proc.returncode,
                "reason": (proc.stderr or proc.stdout or "Renderer failed to emit non-empty asset.")[:300],
                "source_length": len(source_text or ""),
            }

        raw_bytes = tmp_out.read_bytes()
        valid_asset = (raw_bytes.startswith(b"\x89PNG\r\n\x1a\n") if ext == "png" else (b"<svg" in raw_bytes[:2048].lower()))
        if not valid_asset:
            return {
                "diagram_type": d_type,
                "cli_tool": cli_name,
                "cli_available": True,
                "render_attempted": True,
                "render_status": "RENDER_FAILED",
                "fallback_used": True,
                "reason": f"Rendered output failed .{ext} format signature validation.",
                "source_length": len(source_text or ""),
            }

        shutil.copyfile(tmp_out, target_asset)
        return {
            "diagram_type": d_type,
            "cli_tool": cli_name,
            "cli_available": True,
            "render_attempted": True,
            "render_status": "RENDERED",
            "fallback_used": False,
            "asset_path": str(target_asset),
            "size_bytes": len(raw_bytes),
            "source_length": len(source_text or ""),
        }

I18N_LABELS: Dict[str, Dict[str, str]] = {
    "id-ID": {
        "doc_info": "Informasi Dokumen",
        "project_id": "ID Proyek",
        "doc_id": "ID Dokumen",
        "doc_type": "Jenis Dokumen",
        "classification": "Klasifikasi",
        "status": "Status",
        "revision": "Revisi",
        "owner": "Pemilik Dokumen",
        "updated_at": "Terakhir Diperbarui",
        "toc": "Daftar Isi",
        "rev_history": "Riwayat Revisi",
        "approvals": "Daftar Distribusi dan Persetujuan",
        "version": "Revisi",
        "date": "Tanggal",
        "author": "Diubah Oleh",
        "summary": "Alasan Perubahan",
        "role": "Peran",
        "name": "Identitas",
        "decision": "Keputusan",
        "signed_at": "Waktu & Bukti",
        "page": "Halaman",
        "of": "dari",
    },
    "en-US": {
        "doc_info": "Document Information",
        "project_id": "Project ID",
        "doc_id": "Document ID",
        "doc_type": "Document Type",
        "classification": "Classification",
        "status": "Status",
        "revision": "Revision",
        "owner": "Document Owner",
        "updated_at": "Last Updated",
        "toc": "Table of Contents",
        "rev_history": "Revision History",
        "approvals": "Distribution & Approval Record",
        "version": "Revision",
        "date": "Date",
        "author": "Changed By",
        "summary": "Change Reason",
        "role": "Role",
        "name": "Identity",
        "decision": "Decision",
        "signed_at": "Timestamp & Evidence",
        "page": "Page",
        "of": "of",
    },
}


def get_labels(doc: Dict[str, Any]) -> Dict[str, str]:
    lang = str(doc.get("language", "id-ID"))
    return I18N_LABELS.get(lang, I18N_LABELS["id-ID"])


def prepare_redacted_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    cloned = copy.deepcopy(doc)
    scan_and_redact_secrets(cloned, redact_in_place=True)
    return cloned


def extract_tables(doc: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
    """Return list of (block_id, table_data) from doc['blocks']."""
    tables: List[Tuple[str, Dict[str, Any]]] = []
    for b in doc.get("blocks", []):
        if b.get("kind") == "table" and isinstance(b.get("table_data"), dict):
            tables.append((str(b.get("id", "TBL")), b["table_data"]))
    return tables


# ============================================================================
# 1. MARKDOWN RENDERER (.md)
# ============================================================================
def render_v2_to_markdown(doc: Dict[str, Any], out_path: Path) -> Path:
    d = prepare_redacted_doc(doc)
    L = get_labels(d)
    lines: List[str] = []

    lines.append(f"# {d.get('title', 'Document')}")
    lines.append("")
    lines.append(f"## {L['doc_info']}")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("| --- | --- |")
    lines.append(f"| **{L['project_id']}** | `{d.get('project_id')}` |")
    lines.append(f"| **{L['doc_id']}** | `{d.get('document_id')}` |")
    lines.append(f"| **{L['doc_type']}** | `{d.get('document_type')}` |")
    lines.append(f"| **{L['classification']}** | `{d.get('classification', 'INTERNAL')}` |")
    lines.append(f"| **{L['status']}** | `{d.get('status')}` |")
    lines.append(f"| **{L['revision']}** | `{d.get('revision')}` |")
    lines.append(f"| **{L['owner']}** | `{d.get('owner') or '[ISI DARI SUMBER PROYEK]'}` |")
    lines.append(f"| **{L['updated_at']}** | `{d.get('updated_at')}` |")
    if d.get("supersedes"):
        lines.append(f"| **Supersedes** | `{d.get('supersedes')}` |")
    lines.append("")

    # Table of Contents from heading blocks
    headings = [b for b in d.get("blocks", []) if b.get("kind") == "heading"]
    if headings:
        lines.append(f"## {L['toc']}")
        lines.append("")
        for idx, h in enumerate(headings, start=1):
            indent = "  " * max(0, int(h.get("level", 2)) - 2)
            lines.append(f"{indent}- **{h.get('title')}** (`{h.get('id')}`)")
        lines.append("")

    # Revision History
    lines.append(f"## {L['rev_history']}")
    lines.append("")
    lines.append(f"| {L['version']} | {L['date']} | {L['author']} | {L['summary']} |")
    lines.append("| --- | --- | --- | --- |")
    for h in d.get("history", []):
        lines.append(
            f"| {h.get('revision')} | {h.get('changed_at')} | "
            f"{h.get('changed_by') or '-'} | {h.get('reason')} |"
        )
    lines.append("")

    # Approvals / Sign-Off Record
    if d.get("signoff_record"):
        lines.append(f"## {L['approvals']}")
        lines.append("")
        lines.append(f"| {L['role']} | {L['name']} | {L['decision']} | {L['signed_at']} |")
        lines.append("| --- | --- | --- | --- |")
        for s in d.get("signoff_record", []):
            ev = f"{s.get('timestamp') or '-'} ({s.get('evidence_ref') or '-'})"
            lines.append(
                f"| {s.get('role')} | {s.get('identity') or '[MENUNGGU PERSETUJUAN]'} | "
                f"{s.get('decision')} | {ev} |"
            )
        lines.append("")

    # Content Blocks
    for b in d.get("blocks", []):
        kind = b.get("kind", "paragraph")
        bid = b.get("id", "")
        if kind == "heading":
            lvl = max(2, min(int(b.get("level", 2)), 6))
            lines.append(f"{'#' * lvl} {b.get('title', bid)}")
            lines.append("")
        elif kind == "paragraph":
            prefix = f"**[{bid}]** " if re.match(r"^(?:FR|NFR|TC|UAT|BUG|INC|CR|ADR|SDD|RISK)-\d+", str(bid)) else ""
            lines.append(f"{prefix}{b.get('body', '')}")
            lines.append("")
        elif kind == "table" and isinstance(b.get("table_data"), dict):
            td = b["table_data"]
            cols = [str(c).replace("|", "\\|") for c in td.get("columns", td.get("headers", []))]
            if cols:
                if td.get("caption"):
                    lines.append(f"**{td['caption']}**")
                    lines.append("")
                lines.append("| " + " | ".join(cols) + " |")
                lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
                for r in td.get("rows", []):
                    padded = [str(c).replace("|", "\\|") for c in r] + [""] * max(0, len(cols) - len(r))
                    lines.append("| " + " | ".join(padded[: len(cols)]) + " |")
                lines.append("")
        elif kind == "list":
            items = b.get("list_items") or str(b.get("body", "")).splitlines()
            ordered = bool(b.get("ordered", False))
            for idx_item, it in enumerate(items, start=1):
                lines.append(f"{idx_item}. {it}" if ordered else f"- {it}")
            lines.append("")
        elif kind == "figure":
            fd = b.get("figure_data") or {}
            d_type = (fd.get("diagram_type") or ("dbml" if fd.get("dbml") else "mermaid")).lower()
            raw_src = str(fd.get("dbml") or fd.get("mermaid") or b.get("body") or "")
            lines.append(f"**{fd.get('caption') or b.get('title') or bid}**")
            if fd.get("path"):
                lines.append(f"![{fd.get('alt_text') or b.get('title') or bid}]({fd['path']})")
            if raw_src.strip():
                fence = "dbml" if d_type == "dbml" else "mermaid"
                lines.append(f"```{fence}")
                lines.append(raw_src)
                lines.append("```")
            lines.append("")
        elif kind == "finding":
            fnd = b.get("finding_data") or {}
            lines.append(f"### Finding [{bid}] ({fnd.get('severity', b.get('status') or 'INFO')}) — {b.get('title') or bid}")
            lines.append("")
            for lbl, key in (
                ("Criteria", "criteria"),
                ("Condition", "condition"),
                ("Cause", "cause"),
                ("Effect", "effect"),
                ("Recommendation", "recommendation"),
                ("Evidence Ref", "evidence_ref"),
            ):
                if fnd.get(key):
                    lines.append(f"- **{lbl}**: {fnd[key]}")
            lines.append("")
        elif kind == "decision-matrix":
            dd = b.get("decision_data") or {}
            lines.append(f"### Decision Matrix [{bid}] — {b.get('title') or bid}")
            lines.append("")
            opts = dd.get("options", [])
            if opts:
                lines.append("| Option | Title | Status |")
                lines.append("| --- | --- | --- |")
                for o in opts:
                    lines.append(f"| {o.get('id', '-')} | {o.get('title', '-')} | {o.get('status', '-')} |")
                lines.append("")
            lines.append(f"- **Selected Option**: `{dd.get('selectedOption')}` | **Approved By**: `{dd.get('approvedBy')}` | **Approved At**: `{dd.get('approvedAt')}`")
            lines.append("")
        elif kind == "appendix":
            lines.append(f"## Appendix [{bid}]: {b.get('title') or bid}")
            lines.append("")
            if b.get("body"):
                lines.append(str(b.get("body")))
                lines.append("")
        elif kind == "code":
            lang = b.get("code_language", "text")
            code_body = str(b.get("body", ""))
            runs = re.findall(r"`+", code_body)
            fence = "`" * max(3, max((len(r) for r in runs), default=0) + 1)
            lines.append(f"{fence}{lang}")
            lines.append(code_body)
            lines.append(fence)
            lines.append("")
        elif kind == "opaque":
            lines.append(f"<!-- OPAQUE BLOCK {bid} -->")
            lines.append(str(b.get("body", "")))
            lines.append("")

    # Source & Evidence Traceability Appendix (Section 6.1)
    if d.get("sources") or d.get("code_refs") or d.get("git_commits"):
        lines.append("## Sources & Traceability")
        lines.append("")
        for s in d.get("sources", []):
            lines.append(f"- `{s.get('source_id')}`: {s.get('reference')}")
        if d.get("code_refs"):
            lines.append(f"- **Code Refs**: {', '.join(d['code_refs'])}")
        if d.get("git_commits"):
            lines.append(f"- **Git Commits**: {', '.join(d['git_commits'])}")
        lines.append("")

    atomic_write_text(out_path, "\n".join(lines), encoding="utf-8")
    return out_path


# ============================================================================
# 2. WORD DOCX RENDERER (.docx)
# ============================================================================
def render_v2_to_docx(doc: Dict[str, Any], out_path: Path) -> Path:
    import docx
    from docx.enum.section import WD_ORIENT
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Mm, Pt, RGBColor

    d = prepare_redacted_doc(doc)
    L = get_labels(d)
    profile = str(d.get("style_profile", "corporate"))
    font_name = "Times New Roman" if profile == "institutional" else "Calibri"
    base_pt = 12 if profile == "institutional" else 11

    wdoc = docx.Document()
    section = wdoc.sections[0]
    is_landscape = str(d.get("document_type", "")).upper() == "RTM"
    if is_landscape:
        section.orientation = WD_ORIENT.LANDSCAPE
        section.page_width = Mm(297)
        section.page_height = Mm(210)
    else:
        section.orientation = WD_ORIENT.PORTRAIT
        section.page_width = Mm(210)
        section.page_height = Mm(297)

    section.top_margin = Mm(25)
    section.bottom_margin = Mm(25)
    section.left_margin = Mm(25)
    section.right_margin = Mm(22)

    normal_style = wdoc.styles["Normal"]
    normal_style.font.name = font_name
    normal_style.font.size = Pt(base_pt)

    def _set_cell_bg(cell: Any, hex_color: str) -> None:
        tcPr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), hex_color)
        tcPr.append(shd)

    def _set_repeat_header_and_cant_split(row: Any, is_header: bool = False) -> None:
        trPr = row._tr.get_or_add_trPr()
        if is_header:
            trPr.append(OxmlElement("w:tblHeader"))
        trPr.append(OxmlElement("w:cantSplit"))

    def _add_field(p: Any, field_text: str) -> None:
        run = p.add_run()
        fldChar1 = OxmlElement("w:fldChar")
        fldChar1.set(qn("w:fldCharType"), "begin")
        instrText = OxmlElement("w:instrText")
        instrText.set(qn("xml:space"), "preserve")
        instrText.text = field_text
        fldChar2 = OxmlElement("w:fldChar")
        fldChar2.set(qn("w:fldCharType"), "separate")
        fldChar3 = OxmlElement("w:fldChar")
        fldChar3.set(qn("w:fldCharType"), "end")
        r = run._r
        r.append(fldChar1)
        r.append(instrText)
        r.append(fldChar2)
        r.append(fldChar3)

    # Header & Footer
    hdr_p = section.header.paragraphs[0]
    hdr_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    hdr_run = hdr_p.add_run(
        f"{d.get('project_id')} | {d.get('classification', 'INTERNAL')} | {d.get('document_id')}"
    )
    hdr_run.font.name = font_name
    hdr_run.font.size = Pt(9)
    hdr_run.font.color.rgb = RGBColor(100, 116, 139)

    ftr_p = section.footer.paragraphs[0]
    ftr_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r1 = ftr_p.add_run(f"Rev {d.get('revision')} ({d.get('status')})  |  {L['page']} ")
    r1.font.name = font_name
    r1.font.size = Pt(9)
    _add_field(ftr_p, "PAGE")
    r2 = ftr_p.add_run(f" {L['of']} ")
    r2.font.name = font_name
    r2.font.size = Pt(9)
    _add_field(ftr_p, "NUMPAGES")

    # Title
    t_p = wdoc.add_heading(str(d.get("title", "Document")), level=0)
    for r in t_p.runs:
        r.font.name = font_name
        r.font.color.rgb = RGBColor(15, 23, 42)

    def _add_table(headers: List[str], rows: List[List[str]]) -> None:
        if not headers:
            return
        tbl = wdoc.add_table(rows=1, cols=len(headers))
        tbl.style = "Table Grid"
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        hdr_row = tbl.rows[0]
        _set_repeat_header_and_cant_split(hdr_row, is_header=True)
        for idx, h_txt in enumerate(headers):
            c = hdr_row.cells[idx]
            c.text = str(h_txt)
            _set_cell_bg(c, "1E293B")
            for p in c.paragraphs:
                for r in p.runs:
                    r.font.bold = True
                    r.font.name = font_name
                    r.font.size = Pt(base_pt - 1)
                    r.font.color.rgb = RGBColor(255, 255, 255)
        for r_idx, r_vals in enumerate(rows):
            row_obj = tbl.add_row()
            _set_repeat_header_and_cant_split(row_obj, is_header=False)
            bg = "F8FAFC" if r_idx % 2 == 1 else "FFFFFF"
            for c_idx in range(len(headers)):
                val = r_vals[c_idx] if c_idx < len(r_vals) else ""
                c = row_obj.cells[c_idx]
                c.text = str(val)
                if bg != "FFFFFF":
                    _set_cell_bg(c, bg)
                for p in c.paragraphs:
                    for r in p.runs:
                        r.font.name = font_name
                        r.font.size = Pt(base_pt - 1)
        wdoc.add_paragraph("")

    # Document Control Metadata
    h_info = wdoc.add_heading(L["doc_info"], level=1)
    h_info.paragraph_format.keep_with_next = True
    _add_table(
        ["Property", "Value"],
        [
            [L["project_id"], str(d.get("project_id", ""))],
            [L["doc_id"], str(d.get("document_id", ""))],
            [L["doc_type"], str(d.get("document_type", ""))],
            [L["classification"], str(d.get("classification", "INTERNAL"))],
            [L["status"], str(d.get("status", ""))],
            [L["revision"], str(d.get("revision", ""))],
            [L["owner"], str(d.get("owner") or "[ISI DARI SUMBER PROYEK]")],
            [L["updated_at"], str(d.get("updated_at", ""))],
        ],
    )

    # Revision History
    h_rev = wdoc.add_heading(L["rev_history"], level=1)
    h_rev.paragraph_format.keep_with_next = True
    _add_table(
        [L["version"], L["date"], L["author"], L["summary"]],
        [
            [
                str(h.get("revision", "")),
                str(h.get("changed_at", "")),
                str(h.get("changed_by") or "-"),
                str(h.get("reason", "")),
            ]
            for h in d.get("history", [])
        ],
    )

    # Approvals
    if d.get("signoff_record"):
        h_app = wdoc.add_heading(L["approvals"], level=1)
        h_app.paragraph_format.keep_with_next = True
        _add_table(
            [L["role"], L["name"], L["decision"], L["signed_at"]],
            [
                [
                    str(s.get("role", "")),
                    str(s.get("identity") or "[MENUNGGU PERSETUJUAN]"),
                    str(s.get("decision", "")),
                    f"{s.get('timestamp') or '-'} ({s.get('evidence_ref') or '-'})",
                ]
                for s in d.get("signoff_record", [])
            ],
        )

    # Word TOC Field
    h_toc = wdoc.add_heading(L["toc"], level=1)
    h_toc.paragraph_format.keep_with_next = True
    p_toc = wdoc.add_paragraph()
    _add_field(p_toc, 'TOC \\o "1-3" \\h \\z \\u')
    wdoc.add_page_break()

    # Blocks
    for b in d.get("blocks", []):
        kind = b.get("kind", "paragraph")
        bid = str(b.get("id", ""))
        if kind == "heading":
            lvl = max(1, min(int(b.get("level", 2)) - 1, 4))
            h = wdoc.add_heading(str(b.get("title", bid)), level=lvl)
            h.paragraph_format.keep_with_next = True
            for r in h.runs:
                r.font.name = font_name
        elif kind == "paragraph":
            prefix = f"[{bid}] " if re.match(r"^(?:FR|NFR|TC|UAT|BUG|INC|CR|ADR|SDD|RISK)-\d+", bid) else ""
            p = wdoc.add_paragraph(f"{prefix}{b.get('body', '')}")
            p.paragraph_format.space_after = Pt(6)
        elif kind == "table" and isinstance(b.get("table_data"), dict):
            td = b["table_data"]
            cols = [str(c) for c in td.get("columns", td.get("headers", []))]
            rows = [[str(c) for c in r] for r in td.get("rows", [])]
            if td.get("caption"):
                cp = wdoc.add_paragraph(str(td["caption"]))
                cp.paragraph_format.keep_with_next = True
                for r in cp.runs:
                    r.font.bold = True
            _add_table(cols, rows)
        elif kind == "list":
            items = b.get("list_items") or str(b.get("body", "")).splitlines()
            style_nm = "List Number" if b.get("ordered") else "List Bullet"
            for it in items:
                wdoc.add_paragraph(str(it), style=style_nm)
        elif kind == "finding":
            fnd = b.get("finding_data") or {}
            hf = wdoc.add_heading(f"[{bid}] {b.get('title') or bid} ({fnd.get('severity', 'INFO')})", level=2)
            hf.paragraph_format.keep_with_next = True
            _add_table(
                ["Field", "Detail"],
                [[lbl, str(fnd.get(k, "-"))] for lbl, k in (
                    ("Criteria", "criteria"), ("Condition", "condition"), ("Cause", "cause"),
                    ("Effect", "effect"), ("Recommendation", "recommendation"), ("Evidence Ref", "evidence_ref"),
                ) if fnd.get(k)],
            )
        elif kind == "decision-matrix":
            dd = b.get("decision_data") or {}
            hd = wdoc.add_heading(f"[{bid}] {b.get('title') or bid}", level=2)
            hd.paragraph_format.keep_with_next = True
            opts = dd.get("options", [])
            if opts:
                _add_table(
                    ["Option", "Title", "Status"],
                    [[str(o.get("id", "")), str(o.get("title", "")), str(o.get("status", ""))] for o in opts],
                )
            wdoc.add_paragraph(f"Selected: {dd.get('selectedOption')} | ApprovedBy: {dd.get('approvedBy')} | ApprovedAt: {dd.get('approvedAt')}")
        elif kind == "appendix":
            ha = wdoc.add_heading(f"Appendix [{bid}]: {b.get('title') or bid}", level=1)
            ha.paragraph_format.keep_with_next = True
            if b.get("body"):
                wdoc.add_paragraph(str(b.get("body")))
        elif kind == "figure":
            fd = b.get("figure_data") or {}
            cap = fd.get("caption") or b.get("title") or bid
            cp = wdoc.add_paragraph(str(cap))
            cp.paragraph_format.keep_with_next = True
            for r in cp.runs:
                r.font.bold = True
            raw_src = str(fd.get("dbml") or fd.get("mermaid") or b.get("body") or "")
            if raw_src:
                p = wdoc.add_paragraph()
                r = p.add_run(raw_src)
                r.font.name = "Consolas"
                r.font.size = Pt(9.5)
        elif kind in ("code", "opaque"):
            p = wdoc.add_paragraph()
            r = p.add_run(str(b.get("body", "")))
            r.font.name = "Consolas"
            r.font.size = Pt(9.5)

    wdoc.core_properties.title = str(d.get("title", "Document"))
    wdoc.core_properties.author = str(d.get("owner") or "Shadow Army")
    wdoc.core_properties.subject = f"{d.get('project_id')} | {d.get('document_id')} | {d.get('revision')}"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wdoc.save(str(out_path))
    return out_path


# ============================================================================
# 3. EXCEL XLSX & CSV RENDERERS (.xlsx / .csv)
# ============================================================================
def render_v2_to_xlsx(doc: Dict[str, Any], out_path: Path) -> Path:
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation

    d = prepare_redacted_doc(doc)
    wb = openpyxl.Workbook()
    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    body_font = Font(name="Calibri", size=10)

    # Sheet 1: README_Metadata
    ws_meta = wb.active
    ws_meta.title = "README_Metadata"
    ws_meta.append(["Attribute", "Value"])
    for cell in ws_meta[1]:
        cell.fill = header_fill
        cell.font = header_font
    for k, v in [
        ("Schema Version", d.get("schema_version")),
        ("Project ID", d.get("project_id")),
        ("Document ID", d.get("document_id")),
        ("Document Type", d.get("document_type")),
        ("Title", d.get("title")),
        ("Classification", d.get("classification")),
        ("Status", d.get("status")),
        ("Revision", d.get("revision")),
        ("Owner", d.get("owner") or "[ISI DARI SUMBER PROYEK]"),
        ("Updated At", d.get("updated_at")),
        ("Semantic Hash", d.get("semantic_hash")),
    ]:
        ws_meta.append([str(k), str(v)])
    ws_meta.column_dimensions["A"].width = 24
    ws_meta.column_dimensions["B"].width = 65

    # Sheet 2: Register_Data
    ws_reg = wb.create_sheet(title="Register_Data")
    tables = extract_tables(d)
    if tables:
        _, first_td = tables[0]
        cols = ["Block_ID"] + [str(c) for c in first_td.get("columns", first_td.get("headers", []))]
        ws_reg.append(cols)
        for bid, td in tables:
            for r in td.get("rows", []):
                ws_reg.append([bid] + [str(c) for c in r])
    else:
        ws_reg.append(["Block_ID", "Kind", "Title", "Status", "Body", "Trace_IDs"])
        for b in d.get("blocks", []):
            ws_reg.append([
                str(b.get("id", "")),
                str(b.get("kind", "")),
                str(b.get("title") or ""),
                str(b.get("status") or ""),
                str(b.get("body") or ""),
                ", ".join(b.get("trace_ids", [])),
            ])

    ws_reg.freeze_panes = "A2"
    ws_reg.auto_filter.ref = ws_reg.dimensions
    for cell in ws_reg[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for r_i in range(2, ws_reg.max_row + 1):
        for c_i in range(1, ws_reg.max_column + 1):
            c = ws_reg.cell(row=r_i, column=c_i)
            c.font = body_font
            c.alignment = Alignment(vertical="top", wrap_text=True)
            if r_i % 2 == 1:
                c.fill = zebra_fill

    for c_i in range(1, ws_reg.max_column + 1):
        ws_reg.column_dimensions[get_column_letter(c_i)].width = 24

    dv = DataValidation(
        type="list",
        formula1='"PASS,FAIL,OPEN,CLOSED,PENDING,APPROVED,DRAFT,IN_REVIEW,BLOCKED"',
        allow_blank=True,
    )
    ws_reg.add_data_validation(dv)
    dv.add("A2:Z500")

    # Sheet 3: Traceability_Links
    ws_tr = wb.create_sheet(title="Traceability_Links")
    ws_tr.append(["Block_ID", "Kind", "Linked_Trace_ID", "Source_Refs"])
    ws_tr.freeze_panes = "A2"
    for cell in ws_tr[1]:
        cell.fill = header_fill
        cell.font = header_font
    for b in d.get("blocks", []):
        for tid in b.get("trace_ids", []):
            ws_tr.append([
                str(b.get("id")),
                str(b.get("kind")),
                str(tid),
                ", ".join(b.get("source_refs", [])),
            ])
    for c_i in range(1, 5):
        ws_tr.column_dimensions[get_column_letter(c_i)].width = 26

    # Sheet 4: Data_Dictionary
    ws_dd = wb.create_sheet(title="Data_Dictionary")
    ws_dd.append(["Column_Name", "Type", "Required", "Description"])
    ws_dd.freeze_panes = "A2"
    for cell in ws_dd[1]:
        cell.fill = header_fill
        cell.font = header_font
    for row in [
        ("Block_ID", "string", "Yes", "Unique block or requirement/test/defect identifier"),
        ("Trace_IDs", "array<string>", "No", "Bidirectional links across FR/NFR/SDD/TC/UAT/BUG/CR"),
        ("Source_Refs", "array<string>", "Yes", "Verified project evidence sources backing the block"),
        ("Status", "enum", "No", "Execution or verification status (PASS, FAIL, OPEN, CLOSED, etc.)"),
    ]:
        ws_dd.append(list(row))
    for c_i in range(1, 5):
        ws_dd.column_dimensions[get_column_letter(c_i)].width = 28

    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(out_path))
    return out_path


def render_v2_to_csv(doc: Dict[str, Any], out_path: Path) -> Path:
    d = prepare_redacted_doc(doc)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tables = extract_tables(d)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if tables:
            _, first_td = tables[0]
            cols = ["Block_ID"] + [str(c) for c in first_td.get("columns", first_td.get("headers", []))]
            writer.writerow(cols)
            for bid, td in tables:
                for r in td.get("rows", []):
                    writer.writerow([bid] + [str(c) for c in r])
        else:
            writer.writerow(["Block_ID", "Kind", "Title", "Status", "Body", "Trace_IDs"])
            for b in d.get("blocks", []):
                writer.writerow([
                    str(b.get("id", "")),
                    str(b.get("kind", "")),
                    str(b.get("title") or ""),
                    str(b.get("status") or ""),
                    str(b.get("body") or ""),
                    ", ".join(b.get("trace_ids", [])),
                ])
    return out_path


# ============================================================================
# 4. PDF RENDERER (.pdf)
# ============================================================================
def _ascii_clean(text: Any) -> str:
    s = str(text if text is not None else "")
    for k, v in {
        "\u2014": "--",
        "\u2013": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "*",
        "\u2026": "...",
        "\u2192": "->",
        "\u2194": "<->",
    }.items():
        s = s.replace(k, v)
    return s.encode("latin-1", "replace").decode("latin-1")


def _discover_unicode_pdf_fonts() -> Dict[str, Any]:
    """Discover licensed OS system Unicode TTF fonts cleanly without bundling proprietary binaries (H01)."""
    sans_sets = [
        (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\ariali.ttf"),
        (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\segoeuii.ttf"),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"),
        ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf"),
        ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/Supplemental/Arial Italic.ttf"),
    ]
    mono_cands = [
        r"C:\Windows\Fonts\consola.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "/System/Library/Fonts/Supplemental/Courier New.ttf",
    ]
    sans_reg = sans_bold = sans_ital = mono_reg = None
    for reg, bld, itl in sans_sets:
        if Path(reg).is_file():
            sans_reg = reg
            sans_bold = bld if Path(bld).is_file() else reg
            sans_ital = itl if Path(itl).is_file() else reg
            break
    for m in mono_cands:
        if Path(m).is_file():
            mono_reg = m
            break
    return {
        "unicode_enabled": sans_reg is not None,
        "sans": (sans_reg, sans_bold, sans_ital),
        "mono": mono_reg,
    }


def _safe_pdf_text(text: Any, unicode_enabled: bool) -> str:
    if unicode_enabled:
        return str(text if text is not None else "")
    return _ascii_clean(text)


def render_v2_to_pdf(doc: Dict[str, Any], out_path: Path) -> Path:
    from fpdf import FPDF

    d = prepare_redacted_doc(doc)
    L = get_labels(d)
    is_landscape = str(d.get("document_type", "")).upper() == "RTM"
    orientation = "L" if is_landscape else "P"
    font_info = _discover_unicode_pdf_fonts()
    u_on = bool(font_info["unicode_enabled"])
    body_family = "ShadowSans" if u_on else "Helvetica"
    mono_family = "ShadowMono" if (u_on and font_info["mono"]) else ("ShadowSans" if u_on else "Courier")

    class ShadowPDF(FPDF):
        def header(self) -> None:
            self.set_font(body_family, "I", 8)
            self.set_text_color(100, 116, 139)
            hdr = _safe_pdf_text(
                f"{d.get('project_id')} | {d.get('classification', 'INTERNAL')} | {d.get('document_id')}",
                u_on,
            )
            self.cell(0, 6, hdr, align="R", new_x="LMARGIN", new_y="NEXT")
            self.ln(2)

        def footer(self) -> None:
            self.set_y(-15)
            self.set_font(body_family, "I", 8)
            self.set_text_color(100, 116, 139)
            ftr = _safe_pdf_text(
                f"Rev {d.get('revision')} ({d.get('status')}) | {L['page']} {self.page_no()}/{{nb}}",
                u_on,
            )
            self.cell(0, 10, ftr, align="R")

    pdf = ShadowPDF(orientation=orientation, unit="mm", format="A4")
    if u_on:
        s_reg, s_bld, s_itl = font_info["sans"]
        pdf.add_font("ShadowSans", "", s_reg)
        pdf.add_font("ShadowSans", "B", s_bld)
        pdf.add_font("ShadowSans", "I", s_itl)
        if font_info["mono"]:
            pdf.add_font("ShadowMono", "", font_info["mono"])

    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.alias_nb_pages()
    pdf.add_page()

    pdf.set_font(body_family, "B", 15)
    pdf.set_text_color(15, 23, 42)
    pdf.multi_cell(0, 8, _safe_pdf_text(d.get("title", "Document"), u_on), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font(body_family, "B", 11)
    pdf.cell(0, 7, _safe_pdf_text(L["doc_info"], u_on), new_x="LMARGIN", new_y="NEXT")
    for k, v in [
        (L["project_id"], d.get("project_id")),
        (L["doc_id"], d.get("document_id")),
        (L["doc_type"], d.get("document_type")),
        (L["classification"], d.get("classification", "INTERNAL")),
        (L["status"], d.get("status")),
        (L["revision"], d.get("revision")),
        (L["owner"], d.get("owner") or "[ISI DARI SUMBER PROYEK]"),
        (L["updated_at"], d.get("updated_at")),
    ]:
        pdf.set_font(body_family, "B", 8.5)
        pdf.cell(48, 5.5, _safe_pdf_text(k, u_on) + ":", border=1)
        pdf.set_font(body_family, "", 8.5)
        pdf.cell(0, 5.5, _safe_pdf_text(v, u_on), border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    for b in d.get("blocks", []):
        kind = b.get("kind", "paragraph")
        bid = str(b.get("id", ""))
        pdf.set_x(pdf.l_margin)
        if kind == "heading":
            t_str = _safe_pdf_text(b.get("title", bid), u_on)
            lvl = max(0, min(int(b.get("level", 2)) - 2, 2))
            try:
                pdf.start_section(t_str, level=lvl)
            except Exception:
                pass
            pdf.set_font(body_family, "B", max(12 - lvl, 10))
            pdf.set_text_color(30, 41, 59)
            pdf.multi_cell(0, 6.5, t_str, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
        elif kind == "paragraph":
            pdf.set_font(body_family, "", 9.5)
            pdf.set_text_color(15, 23, 42)
            prefix = f"[{bid}] " if re.match(r"^(?:FR|NFR|TC|UAT|BUG|INC|CR|ADR|SDD|RISK)-\d+", bid) else ""
            pdf.multi_cell(0, 5, _safe_pdf_text(f"{prefix}{b.get('body', '')}", u_on), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1.5)
        elif kind == "table" and isinstance(b.get("table_data"), dict):
            td = b["table_data"]
            cols = [_safe_pdf_text(c, u_on) for c in td.get("columns", td.get("headers", []))]
            if cols:
                pdf.set_font(body_family, "B", 8)
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(0, 5, " | ".join(cols), border=1, new_x="LMARGIN", new_y="NEXT")
                pdf.set_font(body_family, "", 8)
                for r in td.get("rows", []):
                    pdf.set_x(pdf.l_margin)
                    pdf.multi_cell(0, 4.8, " | ".join(_safe_pdf_text(c, u_on) for c in r), border=1, new_x="LMARGIN", new_y="NEXT")
                pdf.ln(2)
        elif kind == "list":
            pdf.set_font(body_family, "", 9.5)
            items = b.get("list_items") or str(b.get("body", "")).splitlines()
            ordered = bool(b.get("ordered", False))
            for idx_it, it in enumerate(items, start=1):
                pdf.set_x(pdf.l_margin)
                prefix_li = f"{idx_it}." if ordered else "*"
                pdf.multi_cell(0, 5, f"  {prefix_li} {_safe_pdf_text(it, u_on)}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
        elif kind == "finding":
            fnd = b.get("finding_data") or {}
            pdf.set_font(body_family, "B", 9.5)
            pdf.multi_cell(0, 5.5, _safe_pdf_text(f"[{bid}] {b.get('title') or bid} ({fnd.get('severity', 'INFO')})", u_on), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font(body_family, "", 8.5)
            for lbl, k in (("Criteria", "criteria"), ("Condition", "condition"), ("Cause", "cause"), ("Effect", "effect"), ("Recommendation", "recommendation"), ("Evidence Ref", "evidence_ref")):
                if fnd.get(k):
                    pdf.set_x(pdf.l_margin)
                    pdf.multi_cell(0, 4.8, _safe_pdf_text(f"  - {lbl}: {fnd[k]}", u_on), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1.5)
        elif kind == "decision-matrix":
            dd = b.get("decision_data") or {}
            pdf.set_font(body_family, "B", 9.5)
            pdf.multi_cell(0, 5.5, _safe_pdf_text(f"[{bid}] {b.get('title') or bid}", u_on), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font(body_family, "", 8.5)
            for o in dd.get("options", []):
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(0, 4.8, _safe_pdf_text(f"  [{o.get('id')}] {o.get('title')} ({o.get('status')})", u_on), new_x="LMARGIN", new_y="NEXT")
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(0, 4.8, _safe_pdf_text(f"  Decision: selected={dd.get('selectedOption')}, approvedBy={dd.get('approvedBy')}", u_on), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1.5)
        elif kind == "figure":
            fd = b.get("figure_data") or {}
            cap = fd.get("caption") or b.get("title") or bid
            pdf.set_font(body_family, "B", 9)
            pdf.multi_cell(0, 5, _safe_pdf_text(cap, u_on), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font(mono_family, "", 8)
            raw_src = str(fd.get("dbml") or fd.get("mermaid") or b.get("body") or "")
            for ln in raw_src.splitlines() or [""]:
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(0, 4.5, _safe_pdf_text(ln, u_on), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1.5)
        else:
            pdf.set_font(mono_family, "", 8)
            for ln in str(b.get("body", "")).splitlines() or [""]:
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(0, 4.5, _safe_pdf_text(ln, u_on), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1.5)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(out_path))
    return out_path


# ============================================================================
# 4B. SEMANTIC HTML RENDERER (.html) (SA-DOC-ENGINE-001 G3)
# ============================================================================
def render_v2_to_html(doc: Dict[str, Any], out_path: Path) -> Path:
    d = prepare_redacted_doc(doc)
    L = get_labels(d)
    esc = html_lib.escape
    profile = str(d.get("style_profile", "corporate"))
    font_css = '"Times New Roman", Georgia, serif' if profile == "institutional" else '"Segoe UI", Calibri, system-ui, sans-serif'

    parts: List[str] = [
        "<!DOCTYPE html>",
        f'<html lang="{esc(str(d.get("language", "id-ID")))}">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{esc(str(d.get('title', 'Document')))}</title>",
        "<style>",
        f"body{{font-family:{font_css};line-height:1.6;max-width:960px;margin:2rem auto;padding:0 1.25rem;color:#0f172a;background:#fff}}",
        "table{border-collapse:collapse;width:100%;margin:1rem 0}th,td{border:1px solid #cbd5e1;padding:.5rem .65rem;text-align:left;vertical-align:top}",
        "th{background:#1e3a8a;color:#fff}pre{background:#f8fafc;border:1px solid #cbd5e1;padding:.75rem;overflow-x:auto;border-radius:4px}",
        ".meta-card,.finding-card,.decision-card{border:1px solid #cbd5e1;border-radius:6px;padding:1rem;margin:1rem 0;background:#f8fafc}",
        ".badge{display:inline-block;padding:.15rem .45rem;border-radius:4px;background:#e2e8f0;font-size:.85rem;font-weight:600}",
        "</style>",
        "</head>",
        "<body>",
        f"<h1>{esc(str(d.get('title', 'Document')))}</h1>",
        f'<section class="meta-card"><h2>{esc(L["doc_info"])}</h2><table><tbody>',
    ]
    for lbl, val in [
        (L["project_id"], d.get("project_id")),
        (L["doc_id"], d.get("document_id")),
        (L["doc_type"], d.get("document_type")),
        (L["classification"], d.get("classification", "INTERNAL")),
        (L["status"], d.get("status")),
        (L["revision"], d.get("revision")),
        (L["owner"], d.get("owner") or "[ISI DARI SUMBER PROYEK]"),
        (L["updated_at"], d.get("updated_at")),
    ]:
        parts.append(f"<tr><th>{esc(str(lbl))}</th><td>{esc(str(val))}</td></tr>")
    parts.append("</tbody></table></section>")

    for b in d.get("blocks", []):
        kind = b.get("kind", "paragraph")
        bid = str(b.get("id", ""))
        if kind == "heading":
            lvl = max(2, min(int(b.get("level", 2)), 6))
            parts.append(f'<h{lvl} id="{esc(bid)}">{esc(str(b.get("title", bid)))}</h{lvl}>')
        elif kind == "paragraph":
            parts.append(f'<p id="{esc(bid)}">{esc(str(b.get("body", "")))}</p>')
        elif kind == "table" and isinstance(b.get("table_data"), dict):
            td = b["table_data"]
            cols = [str(c) for c in td.get("columns", td.get("headers", []))]
            if cols:
                parts.append(f'<table id="{esc(bid)}">')
                if td.get("caption"):
                    parts.append(f"<caption>{esc(str(td['caption']))}</caption>")
                parts.append("<thead><tr>" + "".join(f"<th>{esc(c)}</th>" for c in cols) + "</tr></thead><tbody>")
                for row in td.get("rows", []):
                    padded = [str(c) for c in row] + [""] * max(0, len(cols) - len(row))
                    parts.append("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in padded[: len(cols)]) + "</tr>")
                parts.append("</tbody></table>")
        elif kind == "list":
            items = b.get("list_items") or str(b.get("body", "")).splitlines()
            tag = "ol" if b.get("ordered") else "ul"
            parts.append(f"<{tag}>" + "".join(f"<li>{esc(str(it))}</li>" for it in items) + f"</{tag}>")
        elif kind == "figure":
            fd = b.get("figure_data") or {}
            d_type = (fd.get("diagram_type") or ("dbml" if fd.get("dbml") else "mermaid")).lower()
            raw_src = str(fd.get("dbml") or fd.get("mermaid") or b.get("body") or "")
            cap = str(fd.get("caption") or b.get("title") or bid)
            parts.append(f'<figure id="{esc(bid)}">')
            if fd.get("path"):
                parts.append(f'<img src="{esc(str(fd["path"]))}" alt="{esc(str(fd.get("alt_text") or cap))}" />')
            if raw_src:
                parts.append(f'<pre class="{esc(d_type)}"><code>{esc(raw_src)}</code></pre>')
            parts.append(f"<figcaption>{esc(cap)}</figcaption></figure>")
        elif kind == "finding":
            fnd = b.get("finding_data") or {}
            parts.append(f'<section class="finding-card" id="{esc(bid)}"><h3>[{esc(bid)}] {esc(str(b.get("title") or bid))} <span class="badge">{esc(str(fnd.get("severity", "INFO")))}</span></h3><ul>')
            for lbl, k in (("Criteria", "criteria"), ("Condition", "condition"), ("Cause", "cause"), ("Effect", "effect"), ("Recommendation", "recommendation"), ("Evidence Ref", "evidence_ref")):
                if fnd.get(k):
                    parts.append(f"<li><strong>{esc(lbl)}:</strong> {esc(str(fnd[k]))}</li>")
            parts.append("</ul></section>")
        elif kind == "decision-matrix":
            dd = b.get("decision_data") or {}
            parts.append(f'<section class="decision-card" id="{esc(bid)}"><h3>[{esc(bid)}] {esc(str(b.get("title") or bid))}</h3>')
            opts = dd.get("options", [])
            if opts:
                parts.append("<table><thead><tr><th>Option</th><th>Title</th><th>Status</th></tr></thead><tbody>")
                for o in opts:
                    parts.append(f"<tr><td>{esc(str(o.get('id', '')))}</td><td>{esc(str(o.get('title', '')))}</td><td>{esc(str(o.get('status', '')))}</td></tr>")
                parts.append("</tbody></table>")
            parts.append(f"<p><strong>Selected:</strong> {esc(str(dd.get('selectedOption')))} | <strong>Approved By:</strong> {esc(str(dd.get('approvedBy')))} | <strong>Approved At:</strong> {esc(str(dd.get('approvedAt')))}</p></section>")
        elif kind == "appendix":
            parts.append(f'<section id="{esc(bid)}"><h2>Appendix [{esc(bid)}]: {esc(str(b.get("title") or bid))}</h2><p>{esc(str(b.get("body") or ""))}</p></section>')
        elif kind in ("code", "opaque"):
            lang = str(b.get("code_language") or "text")
            parts.append(f'<pre id="{esc(bid)}"><code class="language-{esc(lang)}">{esc(str(b.get("body", "")))}</code></pre>')

    parts.extend(["</body>", "</html>"])
    atomic_write_text(out_path, "\n".join(parts), encoding="utf-8")
    return out_path


# ============================================================================
# 5. CROSS-FORMAT QA VERIFIER (AT-08 & R06 Real Content Validation)
# ============================================================================
class _HtmlStructureChecker(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: List[str] = []
        self.external_urls: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, str | None]]) -> None:
        self.tags.append(tag.lower())
        for k, v in attrs:
            if k in ("src", "href") and v and re.match(r"^https?://", v, re.IGNORECASE):
                self.external_urls.append(v)


def verify_rendered_outputs_qa(
    doc: Dict[str, Any], rendered_paths: Dict[str, Path]
) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    parity_failures: List[str] = []
    expected_doc_id = str(doc.get("document_id", ""))
    expected_rev = str(doc.get("revision", ""))
    expected_title = str(doc.get("title", ""))
    expected_headings = [str(b.get("title", "")) for b in doc.get("blocks", []) if b.get("kind") == "heading" and b.get("title")]

    for fmt, p in rendered_paths.items():
        exists = p.exists() and p.stat().st_size > 0
        checks.append({
            "format": fmt,
            "path": str(p),
            "exists_and_non_empty": exists,
            "size_bytes": p.stat().st_size if exists else 0,
            "sha256": compute_file_sha256(p) if exists else None,
        })

    md_ok = True
    if "md" in rendered_paths and rendered_paths["md"].exists():
        md_txt = rendered_paths["md"].read_text(encoding="utf-8")
        md_ok = (expected_doc_id in md_txt) and (expected_rev in md_txt) and (not expected_title or expected_title in md_txt)
        if not md_ok:
            parity_failures.append("md: missing doc_id, revision, or title")

    html_ok = True
    if "html" in rendered_paths and rendered_paths["html"].exists():
        html_txt = rendered_paths["html"].read_text(encoding="utf-8")
        hc = _HtmlStructureChecker()
        hc.feed(html_txt)
        has_core = all(t in hc.tags for t in ("html", "head", "body", "h1", "table"))
        no_raw_script = "<script" not in html_txt.lower()
        no_ext_deps = len(hc.external_urls) == 0
        has_headings = all(html_lib.escape(h) in html_txt or h in html_txt for h in expected_headings[:3])
        html_ok = (expected_doc_id in html_txt) and (expected_rev in html_txt) and ("<!DOCTYPE html>" in html_txt) and has_core and no_raw_script and no_ext_deps and has_headings
        if not html_ok:
            parity_failures.append(f"html: core={has_core}, no_raw_script={no_raw_script}, no_ext_deps={no_ext_deps}, has_headings={has_headings}")

    docx_ok = True
    if "docx" in rendered_paths and rendered_paths["docx"].exists():
        import docx as _docx

        pkg_ok = False
        with zipfile.ZipFile(str(rendered_paths["docx"]), "r") as zf:
            names = set(zf.namelist())
            pkg_ok = "[Content_Types].xml" in names and "word/document.xml" in names
        d = _docx.Document(str(rendered_paths["docx"]))
        all_txt = "\n".join(p.text for p in d.paragraphs) + "\n" + "\n".join(
            c.text for t in d.tables for r in t.rows for c in r.cells
        )
        heading_paras = [p.text for p in d.paragraphs if p.style and "heading" in p.style.name.lower()]
        meta_ok = bool(d.core_properties.title) or (expected_title in all_txt)
        headings_ok = all(h in all_txt for h in expected_headings[:3]) and len(heading_paras) >= 1
        docx_ok = pkg_ok and (expected_doc_id in all_txt) and (expected_rev in all_txt) and meta_ok and headings_ok and len(d.tables) >= 2
        if not docx_ok:
            parity_failures.append(f"docx: pkg_ok={pkg_ok}, meta_ok={meta_ok}, headings_ok={headings_ok}, tables={len(d.tables)}")

    pdf_ok = True
    pdf_pages = 0
    if "pdf" in rendered_paths and rendered_paths["pdf"].exists():
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(rendered_paths["pdf"]))
            pdf_pages = len(reader.pages)
            pdf_txt = "\n".join((pg.extract_text() or "") for pg in reader.pages)
            # Note: header/footer carries doc_id and rev; verify body title + headings extracted cleanly
            pdf_ok = pdf_pages >= 1 and (expected_doc_id in pdf_txt) and (expected_rev in pdf_txt) and (not expected_headings or any(h[:12] in pdf_txt for h in expected_headings))
            if not pdf_ok:
                parity_failures.append(f"pdf: pages={pdf_pages}, doc_id_present={expected_doc_id in pdf_txt}, rev_present={expected_rev in pdf_txt}")
        except Exception as exc:
            pdf_ok = False
            parity_failures.append(f"pdf: parse_error={exc}")

    xlsx_ok = True
    if "xlsx" in rendered_paths and rendered_paths["xlsx"].exists():
        import openpyxl as _oxl

        wb = _oxl.load_workbook(str(rendered_paths["xlsx"]), read_only=True)
        xlsx_ok = "README_Metadata" in wb.sheetnames and "Register_Data" in wb.sheetnames
        wb.close()
        if not xlsx_ok:
            parity_failures.append("xlsx: missing required sheets")

    passed = all(c["exists_and_non_empty"] for c in checks) and md_ok and html_ok and docx_ok and pdf_ok and xlsx_ok
    return {
        "passed": passed,
        "document_id": expected_doc_id,
        "revision": expected_rev,
        "md_parity": md_ok,
        "html_parity": html_ok,
        "docx_parity": docx_ok,
        "pdf_parity": pdf_ok,
        "pdf_pages": pdf_pages,
        "xlsx_parity": xlsx_ok,
        "parity_failures": parity_failures,
        "artifacts": checks,
    }


def write_build_manifest(
    doc: Dict[str, Any],
    rendered_paths: Dict[str, Path],
    qa_result: Dict[str, Any],
    out_manifest_path: Path,
    *,
    generator_id: str = "shadow-doc-global",
    generator_version: str = RENDERER_ENGINE_VERSION,
    warnings: List[str] | None = None,
) -> Path:
    """Emit reproducible build-manifest.json recording versions, refs, output SHA-256 hashes, and limitations."""
    diag_checks = []
    for b in doc.get("blocks", []):
        if b.get("kind") == "figure" and isinstance(b.get("figure_data"), dict):
            fd = b["figure_data"]
            d_type = str(fd.get("diagram_type") or ("dbml" if fd.get("dbml") else "mermaid"))
            src_txt = str(fd.get("dbml") or fd.get("mermaid") or b.get("body") or "")
            if src_txt:
                diag_checks.append(render_diagram_asset(d_type, src_txt))

    payload = {
        "manifest_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "document_schema_version": str(doc.get("schema_version", "2.0")),
        "document_id": doc.get("document_id"),
        "document_type": doc.get("document_type"),
        "revision": doc.get("revision"),
        "generator": {"id": generator_id, "version": generator_version},
        "template": {"id": doc.get("template_id") or doc.get("document_type"), "version": doc.get("template_version") or "2.1.0"},
        "renderer_version": RENDERER_ENGINE_VERSION,
        "renderer_contracts_used": {fmt: RENDERER_CONTRACTS.get(fmt, {}) for fmt in rendered_paths},
        "input_source_refs": [s.get("source_id") for s in doc.get("sources", []) if isinstance(s, dict)],
        "diagram_status": diag_checks,
        "output_artifacts": qa_result.get("artifacts", []),
        "generation_status": "PASS" if qa_result.get("passed") else "FAIL",
        "warnings_and_limitations": warnings or [],
    }
    atomic_write_text(out_manifest_path, json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_manifest_path


# ============================================================================
# 6. HANDOVER STAGE PACKAGER (.zip + manifest.json with SHA-256) (AT-13)
# ============================================================================
def build_stage_package(
    source_dir: Path,
    project_id: str,
    stage: str,
    out_zip_path: Path,
) -> Dict[str, Any]:
    out_zip_path.parent.mkdir(parents=True, exist_ok=True)
    artifacts_manifest: List[Dict[str, Any]] = []
    unresolved_issues: List[str] = []

    candidates = sorted(
        [
            p
            for p in source_dir.rglob("*")
            if p.is_file()
            and p.resolve() != out_zip_path.resolve()
            and p.name != "manifest.json"
            and not p.name.endswith(".tmp")
            and not p.name.endswith(".bak")
        ]
    )

    for p in candidates:
        rel = p.relative_to(source_dir).as_posix()
        sha = compute_file_sha256(p)
        doc_id = None
        rev = None
        status = None
        if p.suffix.lower() == ".json":
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "document_id" in data:
                    if str(data.get("project_id", project_id)).upper() != project_id.upper():
                        continue
                    doc_id = data.get("document_id")
                    rev = data.get("revision")
                    status = data.get("status")
                    raw_dump = json.dumps(data.get("blocks", []), ensure_ascii=False)
                    if "[ISI DARI SUMBER PROYEK]" in raw_dump or "TBD" in raw_dump:
                        unresolved_issues.append(f"{doc_id}: Contains unresolved [ISI DARI SUMBER PROYEK] / TBD placeholders")
            except Exception:
                pass
        artifacts_manifest.append({
            "relative_path": rel,
            "size_bytes": p.stat().st_size,
            "sha256": sha,
            "document_id": doc_id,
            "revision": rev,
            "status": status,
        })

    manifest_data = {
        "package_version": "2.0.0",
        "project_id": project_id,
        "stage": stage,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "artifact_count": len(artifacts_manifest),
        "unresolved_issues": unresolved_issues,
        "artifacts": artifacts_manifest,
    }

    manifest_path = out_zip_path.parent / "manifest.json"
    manifest_path.write_text(json.dumps(manifest_data, indent=2, ensure_ascii=False), encoding="utf-8")

    with zipfile.ZipFile(str(out_zip_path), "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(str(manifest_path), arcname="manifest.json")
        for item in artifacts_manifest:
            full_p = source_dir / item["relative_path"]
            zf.write(str(full_p), arcname=item["relative_path"])

    return {
        "zip_path": str(out_zip_path),
        "zip_sha256": compute_file_sha256(out_zip_path),
        "manifest": manifest_data,
    }
