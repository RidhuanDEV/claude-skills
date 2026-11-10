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
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from v2_core import compute_file_sha256, scan_and_redact_secrets

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
            cols = [str(c) for c in td.get("columns", td.get("headers", []))]
            if cols:
                if td.get("caption"):
                    lines.append(f"**{td['caption']}**")
                    lines.append("")
                lines.append("| " + " | ".join(cols) + " |")
                lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
                for r in td.get("rows", []):
                    padded = [str(c) for c in r] + [""] * max(0, len(cols) - len(r))
                    lines.append("| " + " | ".join(padded[: len(cols)]) + " |")
                lines.append("")
        elif kind == "list":
            items = b.get("list_items") or str(b.get("body", "")).splitlines()
            for it in items:
                lines.append(f"- {it}")
            lines.append("")
        elif kind == "figure":
            fd = b.get("figure_data") or {}
            lines.append(f"**{fd.get('caption') or b.get('title') or bid}**")
            lines.append("```mermaid")
            lines.append(str(fd.get("mermaid") or b.get("body") or ""))
            lines.append("```")
            lines.append("")
        elif kind == "code":
            lang = b.get("code_language", "text")
            lines.append(f"```{lang}")
            lines.append(str(b.get("body", "")))
            lines.append("```")
            lines.append("")
        elif kind == "opaque":
            lines.append(f"<!-- OPAQUE BLOCK {bid} -->")
            lines.append(str(b.get("body", "")))
            lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


import re


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
            for it in items:
                wdoc.add_paragraph(str(it), style="List Bullet")
        elif kind in ("code", "figure", "opaque"):
            p = wdoc.add_paragraph()
            r = p.add_run(str(b.get("body", "")))
            r.font.name = "Consolas"
            r.font.size = Pt(9.5)

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


def render_v2_to_pdf(doc: Dict[str, Any], out_path: Path) -> Path:
    from fpdf import FPDF

    d = prepare_redacted_doc(doc)
    L = get_labels(d)
    is_landscape = str(d.get("document_type", "")).upper() == "RTM"
    orientation = "L" if is_landscape else "P"

    class ShadowPDF(FPDF):
        def header(self) -> None:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(100, 116, 139)
            hdr = _ascii_clean(
                f"{d.get('project_id')} | {d.get('classification', 'INTERNAL')} | {d.get('document_id')}"
            )
            self.cell(0, 6, hdr, align="R", new_x="LMARGIN", new_y="NEXT")
            self.ln(2)

        def footer(self) -> None:
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(100, 116, 139)
            ftr = _ascii_clean(
                f"Rev {d.get('revision')} ({d.get('status')}) | {L['page']} {self.page_no()}/{{nb}}"
            )
            self.cell(0, 10, ftr, align="R")

    pdf = ShadowPDF(orientation=orientation, unit="mm", format="A4")
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.alias_nb_pages()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(15, 23, 42)
    pdf.multi_cell(0, 8, _ascii_clean(d.get("title", "Document")))
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, _ascii_clean(L["doc_info"]), new_x="LMARGIN", new_y="NEXT")
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
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.cell(48, 5.5, _ascii_clean(k) + ":", border=1)
        pdf.set_font("Helvetica", "", 8.5)
        pdf.cell(0, 5.5, _ascii_clean(v), border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    for b in d.get("blocks", []):
        kind = b.get("kind", "paragraph")
        bid = str(b.get("id", ""))
        pdf.set_x(pdf.l_margin)
        if kind == "heading":
            t_str = _ascii_clean(b.get("title", bid))
            lvl = max(0, min(int(b.get("level", 2)) - 2, 2))
            try:
                pdf.start_section(t_str, level=lvl)
            except Exception:
                pass
            pdf.set_font("Helvetica", "B", max(12 - lvl, 10))
            pdf.set_text_color(30, 41, 59)
            pdf.multi_cell(0, 6.5, t_str, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
        elif kind == "paragraph":
            pdf.set_font("Helvetica", "", 9.5)
            pdf.set_text_color(15, 23, 42)
            prefix = f"[{bid}] " if re.match(r"^(?:FR|NFR|TC|UAT|BUG|INC|CR|ADR|SDD|RISK)-\d+", bid) else ""
            pdf.multi_cell(0, 5, _ascii_clean(f"{prefix}{b.get('body', '')}"), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1.5)
        elif kind == "table" and isinstance(b.get("table_data"), dict):
            td = b["table_data"]
            cols = [_ascii_clean(c) for c in td.get("columns", td.get("headers", []))]
            if cols:
                pdf.set_font("Helvetica", "B", 8)
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(0, 5, " | ".join(cols), border=1, new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", "", 8)
                for r in td.get("rows", []):
                    pdf.set_x(pdf.l_margin)
                    pdf.multi_cell(0, 4.8, " | ".join(_ascii_clean(c) for c in r), border=1, new_x="LMARGIN", new_y="NEXT")
                pdf.ln(2)
        elif kind == "list":
            pdf.set_font("Helvetica", "", 9.5)
            items = b.get("list_items") or str(b.get("body", "")).splitlines()
            for it in items:
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(0, 5, f"  * {_ascii_clean(it)}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
        else:
            pdf.set_font("Courier", "", 8)
            for ln in str(b.get("body", "")).splitlines() or [""]:
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(0, 4.5, _ascii_clean(ln), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1.5)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(out_path))
    return out_path


# ============================================================================
# 5. CROSS-FORMAT QA VERIFIER (AT-08)
# ============================================================================
def verify_rendered_outputs_qa(
    doc: Dict[str, Any], rendered_paths: Dict[str, Path]
) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    expected_doc_id = str(doc.get("document_id", ""))
    expected_rev = str(doc.get("revision", ""))

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
        md_ok = (expected_doc_id in md_txt) and (expected_rev in md_txt)

    docx_ok = True
    if "docx" in rendered_paths and rendered_paths["docx"].exists():
        import docx as _docx

        d = _docx.Document(str(rendered_paths["docx"]))
        all_txt = "\n".join(p.text for p in d.paragraphs) + "\n" + "\n".join(
            c.text for t in d.tables for r in t.rows for c in r.cells
        )
        docx_ok = (expected_doc_id in all_txt) and (expected_rev in all_txt)

    xlsx_ok = True
    if "xlsx" in rendered_paths and rendered_paths["xlsx"].exists():
        import openpyxl as _oxl

        wb = _oxl.load_workbook(str(rendered_paths["xlsx"]), read_only=True)
        xlsx_ok = "README_Metadata" in wb.sheetnames and "Register_Data" in wb.sheetnames
        wb.close()

    passed = all(c["exists_and_non_empty"] for c in checks) and md_ok and docx_ok and xlsx_ok
    return {
        "passed": passed,
        "document_id": expected_doc_id,
        "revision": expected_rev,
        "md_parity": md_ok,
        "docx_parity": docx_ok,
        "xlsx_parity": xlsx_ok,
        "artifacts": checks,
    }


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
