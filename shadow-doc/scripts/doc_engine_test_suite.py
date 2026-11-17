#!/usr/bin/env python3
"""
SA-DOC-ENGINE-001 Mandatory 44-Test Verification Suite (`G5`)
==============================================================
Tests all 44 scenarios from Section 11 across 6 domains:
  1-9:   Generator Discovery
  10-16: Compatibility & Reuse / Adapter-First
  17-22: Structured Documents (Canonical AST v2.0 & v2.1)
  23-31: Multi-Format Rendering (MD, PDF, DOCX, HTML, XLSX, Mermaid, DBML)
  32-38: Security & Governance (Traversal, Overwrite, Auth, Cross-Project, Cleanup)
  39-44: End-to-End Cross-Skill Workflows & Controlled Reproducibility

Distinguishes PASS, FAIL, BLOCKED, and NOT_RUN explicitly without fabricating passes.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from doc_orchestrator import (
    MarkdownCompatibilityAdapter,
    assess_generator_compatibility,
    check_output_overwrite_safety,
    classify_document_action,
    discover_project_generators,
    resolve_document_generator,
    validate_safe_path,
)
from domain_adapters import (
    adapt_grc_payload,
    adapt_handover_payload,
    adapt_pmo_or_ea_payload,
    adapt_presales_payload,
)
from v2_core import (
    create_document_from_template,
    migrate_schema_version,
    normalize_document_v2,
    parse_markdown_into_blocks,
    validate_document_v2,
    validate_schema_v2,
)
from v2_renderers import (
    render_diagram_asset,
    render_v2_to_docx,
    render_v2_to_html,
    render_v2_to_markdown,
    render_v2_to_pdf,
    render_v2_to_xlsx,
    verify_rendered_outputs_qa,
    write_build_manifest,
)


def _sample_v21_doc(doc_id: str = "DOC-TEST-001", project_id: str = "PRJ-SA") -> dict[str, Any]:
    return {
        "schema_version": "2.1",
        "document_id": doc_id,
        "project_id": project_id,
        "document_type": "TECH_AUDIT",
        "template_id": "TECH_AUDIT",
        "template_version": "2.1.0",
        "title": "Architecture & Audit Report",
        "revision": "1.0-DRAFT",
        "status": "DRAFT",
        "language": "en-US",
        "classification": "INTERNAL",
        "style_profile": "corporate",
        "owner": "Shadow Architect",
        "code_refs": ["shadow-doc/scripts/doc_orchestrator.py#L1"],
        "git_commits": ["ad007dd"],
        "rendering_hints": {"toc": True},
        "extensions": {"x-shadow:suite": "SA-DOC-ENGINE-001"},
        "sources": [
            {"source_id": "STD-ISO-29148", "reference": "ISO/IEC/IEEE 29148:2018", "source_type": "STANDARD", "peer_reviewed": True},
            {"source_id": "EVID-01", "reference": "logs/audit_evidence.json", "source_type": "PROJECT_ARTIFACT"},
        ],
        "blocks": [
            {"id": "SEC-1", "kind": "heading", "level": 2, "title": "1. Overview", "body": None, "source_refs": ["EVID-01"], "trace_ids": []},
            {"id": "FR-001", "kind": "paragraph", "title": "Summary", "body": "System overview with verified trace.", "source_refs": ["STD-ISO-29148"], "evidence_refs": ["EVID-01"], "trace_ids": []},
            {"id": "LST-01", "kind": "list", "ordered": True, "list_items": ["Step 1: Discover", "Step 2: Resolve"], "source_refs": [], "trace_ids": []},
            {
                "id": "TBL-01",
                "kind": "table",
                "table_data": {"caption": "Metrics", "columns": ["Metric", "Value"], "rows": [["Coverage", "100%"]]},
                "source_refs": ["EVID-01"],
                "trace_ids": [],
            },
            {"id": "COD-01", "kind": "code", "code_language": "python", "body": "def ok() -> bool:\n    return True", "source_refs": [], "trace_ids": []},
            {
                "id": "FIG-MMD",
                "kind": "figure",
                "title": "Flowchart",
                "figure_data": {"diagram_type": "mermaid", "caption": "Flow", "mermaid": "flowchart TD\n  A[\"Start\"] --> B[\"End\"]"},
                "source_refs": [],
                "trace_ids": [],
            },
            {
                "id": "FIG-DBML",
                "kind": "figure",
                "title": "DB Schema",
                "figure_data": {"diagram_type": "dbml", "caption": "Core Tables", "dbml": "Table docs {\n  id uuid [pk]\n}"},
                "source_refs": [],
                "trace_ids": [],
            },
            {
                "id": "FND-01",
                "kind": "finding",
                "title": "Sample Control Finding",
                "finding_data": {
                    "severity": "MEDIUM",
                    "criteria": "ISO 27001 A.8.24",
                    "condition": "TLS check passed",
                    "cause": "Enforced policy",
                    "effect": "Low risk",
                    "recommendation": "Maintain quarterly rotation",
                    "evidence_ref": "EVID-01",
                },
                "source_refs": ["EVID-01"],
                "evidence_refs": ["EVID-01"],
                "trace_ids": [],
            },
            {
                "id": "DEC-01",
                "kind": "decision-matrix",
                "title": "Generator Choice",
                "decision_data": {
                    "options": [{"id": "A", "title": "Project Local", "status": "current"}, {"id": "B", "title": "Global Fallback", "status": "proposed"}],
                    "selectedOption": "A",
                    "approvedBy": "Monarch",
                    "approvedAt": "2026-11-17T12:00:00Z",
                },
                "source_refs": ["EVID-01"],
                "trace_ids": [],
            },
            {"id": "APP-01", "kind": "appendix", "title": "Appendix A", "body": "Supplementary metadata.", "source_refs": [], "trace_ids": []},
        ],
        "history": [{"revision": "1.0-DRAFT", "reason": "Initial", "changed_by": "Shadow Army"}],
        "signoff_record": [{"role": "Approver", "identity": None, "decision": "PENDING", "timestamp": None, "evidence_ref": None}],
    }


def run_44_tests() -> dict[str, Any]:
    results: list[dict[str, Any]] = []

    def run_case(num: int, category: str, name: str, fn: Callable[[Path], tuple[str, str]]) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            try:
                status, detail = fn(Path(tmp))
            except Exception as exc:
                status, detail = "FAIL", f"{type(exc).__name__}: {exc}"
        results.append({"test_no": num, "category": category, "name": name, "status": status, "detail": detail})

    # --- 1..9: Generator Discovery ---
    def t01(r: Path):
        (r / "custom").mkdir()
        p = r / "custom" / "emit.py"
        p.write_text("import docx\n", encoding="utf-8")
        res = resolve_document_generator(r, {"required_outputs": ["docx"]}, explicit_generator=str(p))
        return ("PASS" if res["resolution_tier"] == "1_EXPLICIT_USER_SELECTION" and res["status"] == "RESOLVED" else "FAIL", res["status"])

    def t02(r: Path):
        (r / "docs_tools" / "nested").mkdir(parents=True)
        (r / "docs_tools" / "nested" / "build_docx.py").write_text("import docx\n", encoding="utf-8")
        d = discover_project_generators(r, include_system_clis=False)
        ok = any("docs_tools/nested/build_docx.py" in c.get("source", "") for c in d["projectCandidates"])
        return ("PASS" if ok else "FAIL", f"found={len(d['projectCandidates'])}")

    def t03(r: Path):
        (r / "package.json").write_text(json.dumps({"scripts": {"docs:build": "node render.mjs"}, "devDependencies": {"md-to-pdf": "^5.0.0"}}), encoding="utf-8")
        d = discover_project_generators(r, include_system_clis=False)
        ok = any(c["id"] == "npm-script:docs:build" for c in d["projectCandidates"])
        return ("PASS" if ok else "FAIL", str([c["id"] for c in d["projectCandidates"]]))

    def t04(r: Path):
        (r / ".shadow").mkdir()
        (r / "bin").mkdir()
        (r / "bin" / "custom_gen.py").write_text("print('ok')\n", encoding="utf-8")
        cfg = {"schemaVersion": "1.0.0", "documentGeneration": {"projectGenerator": {"id": "cfg-gen", "entry": "./bin/custom_gen.py", "supportedInputs": ["markdown"], "supportedOutputs": ["html"]}}}
        (r / ".shadow" / "document-engine.json").write_text(json.dumps(cfg), encoding="utf-8")
        res = resolve_document_generator(r, {"required_outputs": ["html"]})
        return ("PASS" if res["resolution_tier"] == "3_PROJECT_CONFIGURATION" and res["selected"]["id"] == "cfg-gen" else "FAIL", res.get("resolution_tier", ""))

    def t05(r: Path):
        res = resolve_document_generator(r, {"required_outputs": ["md", "html"]})
        return ("PASS" if res["resolution_tier"] == "4_GLOBAL_ENGINE_FALLBACK" and res["selected"]["id"] == "shadow-doc-global" else "FAIL", res["resolution_tier"])

    def t06(r: Path):
        (r / "a").mkdir()
        (r / "b").mkdir()
        (r / "a" / "gen1.py").write_text("import docx\n", encoding="utf-8")
        (r / "b" / "gen2.py").write_text("import docx\n", encoding="utf-8")
        res = resolve_document_generator(r, {"required_outputs": ["docx"]})
        return ("PASS" if res["status"] == "CONFLICT_USER_DECISION_REQUIRED" and len(res["competing_candidates"]) == 2 else "FAIL", res["status"])

    def t07(r: Path):
        res = resolve_document_generator(r, {"required_outputs": ["md"]}, explicit_generator="missing/tool.py")
        return ("PASS" if res["status"] == "INVALID_EXPLICIT_GENERATOR" else "FAIL", res["status"])

    def t08(r: Path):
        d = discover_project_generators(r, include_system_clis=False)
        return ("PASS" if d["projectConfigFound"] is False and d["globalEngine"]["exists"] is True else "FAIL", str(d["projectConfigFound"]))

    def t09(r: Path):
        unknown_cand = {"id": "opaque-bin", "exists": True, "supported_inputs": [], "supported_outputs": [], "paths": {}}
        a = assess_generator_compatibility(unknown_cand, {"required_outputs": ["pdf"]})
        return ("PASS" if a["status"] == "UNKNOWN" else "FAIL", a["status"])

    # --- 10..16: Compatibility ---
    def t10(r: Path):
        (r / "build_docs.py").write_text("import docx\n", encoding="utf-8")
        res = resolve_document_generator(r, {"required_outputs": ["docx"]})
        return ("PASS" if res["status"] == "RESOLVED" and res["selected"]["kind"] == "project-local" else "FAIL", res["status"])

    def t11(r: Path):
        (r / "docgen.mjs").write_text("import { Document } from 'docx';\n", encoding="utf-8")
        res = resolve_document_generator(r, {"required_outputs": ["docx"], "preferred_input": "json-ast-v2.1"})
        return ("PASS" if res["status"] == "RESOLVED_WITH_ADAPTER" and res["assessment"]["status"] == "PARTIALLY_COMPATIBLE" else "FAIL", res["status"])

    def t12(r: Path):
        (r / "only_pdf.py").write_text("import reportlab\n", encoding="utf-8")
        res = resolve_document_generator(r, {"required_outputs": ["pdf", "xlsx"], "requires_code_blocks": True}, allow_global_fallback=False)
        return ("PASS" if res["status"] == "USER_DECISION_REQUIRED" and set(res["decision_gate"]["options"].keys()) == {"A", "B", "C", "D"} else "FAIL", res["status"])

    def t13(r: Path):
        adapted = MarkdownCompatibilityAdapter().adapt(_sample_v21_doc())
        ok = adapted["target_format"] == "markdown" and adapted["source_refs_preserved"] == 2 and "DOC-TEST-001" in adapted["content"]
        return ("PASS" if ok else "FAIL", f"len={len(adapted['content'])}")

    def t14(r: Path):
        tpl = r / "templates" / "custom.md"
        tpl.parent.mkdir()
        tpl.write_text("# Custom Template\nKEEP_EXACT", encoding="utf-8")
        (r / "make_doc.py").write_text("import docx\n", encoding="utf-8")
        resolve_document_generator(r, {"required_outputs": ["docx"]})
        return ("PASS" if tpl.read_text(encoding="utf-8") == "# Custom Template\nKEEP_EXACT" else "FAIL", "template untouched")

    def t15(r: Path):
        gen = r / "gen.py"
        gen.write_text("# ORIGINAL_LOCAL\nimport docx\n", encoding="utf-8")
        resolve_document_generator(r, {"required_outputs": ["docx"]})
        return ("PASS" if "# ORIGINAL_LOCAL" in gen.read_text(encoding="utf-8") else "FAIL", "no replacement")

    def t16(r: Path):
        (r / "gen.py").write_text("import docx\n", encoding="utf-8")
        resolve_document_generator(r, {"required_outputs": ["docx"]})
        ok = not (r / "shadow-document-engine").exists() and not (r / ".shadow").exists()
        return ("PASS" if ok else "FAIL", "no duplicate global scaffold")

    # --- 17..22: Structured Documents ---
    def t17(r: Path):
        v = validate_document_v2(_sample_v21_doc(), strict=False)
        return ("PASS" if v["valid"] and v["critical_count"] == 0 else "FAIL", str(v["issues"]))

    def t18(r: Path):
        bad = {"schema_version": "9.9", "document_id": "", "blocks": "bad"}
        issues = validate_schema_v2(bad)
        return ("PASS" if len(issues) >= 2 else "FAIL", f"issues={len(issues)}")

    def t19(r: Path):
        v20 = create_document_from_template("SRS", "PRJ-1", "DOC-1", "Sample SRS", "Owner", "id-ID", "corporate")
        migrated = migrate_schema_version(v20, target_version="2.1")
        ok = migrated["schema_version"] == "2.1" and migrated["schema_migration"]["from_version"] == "2.0" and validate_schema_v2(migrated) == []
        return ("PASS" if ok else "FAIL", str(migrated.get("schema_migration")))

    def t20(r: Path):
        doc = _sample_v21_doc()
        doc["blocks"].append({"id": "UNK-1", "kind": "quantum-widget"})
        issues = validate_schema_v2(doc)
        ok = any(i["code"] == "SCHEMA_UNSUPPORTED_NODE" for i in issues)
        return ("PASS" if ok else "FAIL", str([i["code"] for i in issues]))

    def t21(r: Path):
        doc = _sample_v21_doc()
        norm = normalize_document_v2(doc)
        ok = norm["blocks"][1]["evidence_refs"] == ["EVID-01"] and norm["blocks"][7]["finding_data"]["evidence_ref"] == "EVID-01"
        return ("PASS" if ok else "FAIL", "evidence_refs checked")

    def t22(r: Path):
        doc = normalize_document_v2(_sample_v21_doc())
        ok = doc["code_refs"] == ["shadow-doc/scripts/doc_orchestrator.py#L1"] and doc["git_commits"] == ["ad007dd"]
        return ("PASS" if ok else "FAIL", "metadata preserved")

    # --- 23..31: Rendering ---
    def _doc_and_dir(r: Path) -> tuple[dict[str, Any], Path]:
        return _sample_v21_doc(), r / "out"

    def t23(r: Path):
        doc, out = _doc_and_dir(r)
        p = render_v2_to_markdown(doc, out / "d.md")
        return ("PASS" if "DOC-TEST-001" in p.read_text(encoding="utf-8") else "FAIL", str(p.stat().st_size))

    def t24(r: Path):
        doc, out = _doc_and_dir(r)
        p = render_v2_to_pdf(doc, out / "d.pdf")
        return ("PASS" if p.exists() and p.read_bytes().startswith(b"%PDF-") else "FAIL", str(p.stat().st_size))

    def t25(r: Path):
        doc, out = _doc_and_dir(r)
        p = render_v2_to_docx(doc, out / "d.docx")
        qa = verify_rendered_outputs_qa(doc, {"docx": p})
        return ("PASS" if qa["docx_parity"] else "FAIL", str(p.stat().st_size))

    def t26(r: Path):
        doc, out = _doc_and_dir(r)
        p = render_v2_to_html(doc, out / "d.html")
        qa = verify_rendered_outputs_qa(doc, {"html": p})
        return ("PASS" if qa["html_parity"] else "FAIL", str(p.stat().st_size))

    def t27(r: Path):
        doc, out = _doc_and_dir(r)
        p = render_v2_to_xlsx(doc, out / "d.xlsx")
        qa = verify_rendered_outputs_qa(doc, {"xlsx": p})
        return ("PASS" if qa["xlsx_parity"] else "FAIL", str(p.stat().st_size))

    def t28(r: Path):
        doc, out = _doc_and_dir(r)
        md_p = render_v2_to_markdown(doc, out / "d.md")
        html_p = render_v2_to_html(doc, out / "d.html")
        ok = "```mermaid" in md_p.read_text(encoding="utf-8") and 'class="mermaid"' in html_p.read_text(encoding="utf-8")
        return ("PASS" if ok else "FAIL", render_diagram_asset("mermaid", "flowchart TD")["render_status"])

    def t29(r: Path):
        doc, out = _doc_and_dir(r)
        md_p = render_v2_to_markdown(doc, out / "d.md")
        html_p = render_v2_to_html(doc, out / "d.html")
        ok = "```dbml" in md_p.read_text(encoding="utf-8") and 'class="dbml"' in html_p.read_text(encoding="utf-8")
        return ("PASS" if ok else "FAIL", render_diagram_asset("dbml", "Table docs {}")["render_status"])

    def t30(r: Path):
        doc, out = _doc_and_dir(r)
        html_txt = render_v2_to_html(doc, out / "d.html").read_text(encoding="utf-8")
        ok = "<table>" in html_txt and "def ok()" in html_txt
        return ("PASS" if ok else "FAIL", "html table + code verified")

    def t31(r: Path):
        diag_res = render_diagram_asset("mermaid", "flowchart TD\n  A-->B")
        doc = _sample_v21_doc()
        # Even if external CLI is unavailable, canonical doc stays uncorrupted & fallback succeeds
        ok = diag_res["render_status"] in ("CLI_AVAILABLE", "FALLBACK_SOURCE_PRESERVED") and validate_schema_v2(doc) == []
        return ("PASS" if ok else "FAIL", diag_res["render_status"])

    # --- 32..38: Security & Governance ---
    def t32(r: Path):
        blocked = False
        try:
            validate_safe_path(r / "sub" / ".." / ".." / "outside.docx", allowed_root=r)
        except ValueError:
            blocked = True
        return ("PASS" if blocked else "FAIL", f"traversal_blocked={blocked}")

    def t33(r: Path):
        f = r / "keep.docx"
        f.write_text("existing", encoding="utf-8")
        blocked = False
        try:
            check_output_overwrite_safety(f, overwrite=False)
        except FileExistsError:
            blocked = True
        return ("PASS" if blocked else "FAIL", f"overwrite_blocked={blocked}")

    def t34(r: Path):
        c1 = classify_document_action("change_global_config")
        c2 = classify_document_action("discover")
        return ("PASS" if c1["requires_approval"] and c1["permission_level"] == "L4" and not c2["requires_approval"] else "FAIL", c1["permission_level"])

    def t35(r: Path):
        c = classify_document_action("install_global_dependency")
        return ("PASS" if c["requires_approval"] and c["permission_level"] == "L3" else "FAIL", c["permission_level"])

    def t36(r: Path):
        c1 = classify_document_action("export_unrequested_format")
        c2 = classify_document_action("publish_external", external_publish=True)
        return ("PASS" if c1["requires_approval"] and c2["requires_approval"] else "FAIL", f"{c1['permission_level']},{c2['permission_level']}")

    def t37(r: Path):
        doc_a = _sample_v21_doc("DOC-A", "PRJ-ALPHA")
        doc_b = _sample_v21_doc("DOC-B", "PRJ-BETA")
        doc_a["blocks"][1]["body"] = "Refers to project:prj-beta secret leak"
        res = validate_document_v2(doc_a, workspace_docs=[doc_a, doc_b], strict=False)
        ok = any(i["code"] == "CROSS_PROJECT_OR_FORBIDDEN_TERM_BLEED" for i in res["issues"])
        return ("PASS" if ok else "FAIL", str([i["code"] for i in res["issues"]]))

    def t38(r: Path):
        out_p = r / "clean_out" / "d.html"
        render_v2_to_html(_sample_v21_doc(), out_p)
        leftover_tmps = list(r.rglob("*.tmp"))
        return ("PASS" if out_p.exists() and not leftover_tmps else "FAIL", f"tmp_count={len(leftover_tmps)}")

    # --- 39..44: End-to-End Workflows ---
    def t39(r: Path):
        gen = r / "emit_md.py"
        gen.write_text(
            "import sys, pathlib\n"
            "import docx\n"
            "src = pathlib.Path(sys.argv[1]).read_text(encoding='utf-8')\n"
            "pathlib.Path(sys.argv[2]).write_text('LOCAL_GEN_OK\\n' + src, encoding='utf-8')\n",
            encoding="utf-8",
        )
        res = resolve_document_generator(r, {"required_outputs": ["docx"]})
        hand_doc = adapt_handover_payload({"title": "Handover Alpha", "summary": "Delivered cleanly", "dbml": "Table users { id uuid [pk] }"})
        adapted = MarkdownCompatibilityAdapter().adapt(hand_doc)
        in_md = r / "handover_in.md"
        out_md = r / "handover_local.out"
        in_md.write_text(adapted["content"], encoding="utf-8")
        subprocess.run([sys.executable, str(gen), str(in_md), str(out_md)], check=True, timeout=15)
        ok = res["selected"]["source"] == "emit_md.py" and "LOCAL_GEN_OK" in out_md.read_text(encoding="utf-8") and "```dbml" in out_md.read_text(encoding="utf-8")
        return ("PASS" if ok else "FAIL", res["resolution_tier"])

    def t40(r: Path):
        hand_doc = adapt_handover_payload({"title": "Handover Global", "summary": "Global engine test", "mermaid": "flowchart LR\n  A-->B"})
        out_dir = r / "handover_global"
        p_docx = render_v2_to_docx(hand_doc, out_dir / "DOC-HANDOVER-001.docx")
        p_html = render_v2_to_html(hand_doc, out_dir / "DOC-HANDOVER-001.html")
        qa = verify_rendered_outputs_qa(hand_doc, {"docx": p_docx, "html": p_html})
        m_p = write_build_manifest(hand_doc, {"docx": p_docx, "html": p_html}, qa, out_dir / "build-manifest.json")
        return ("PASS" if qa["passed"] and m_p.exists() else "FAIL", str(qa["passed"]))

    def t41(r: Path):
        grc_doc = adapt_grc_payload({
            "sector": "BANKING",
            "findings": [{"id": "FND-01", "severity": "HIGH", "criteria": "POJK 11/2022", "condition": "DR drill overdue", "cause": "Manual runbook", "effect": "RTO risk", "recommendation": "Automate drill", "evidence_ref": "GRC-EVIDENCE"}],
        })
        p_html = render_v2_to_html(grc_doc, r / "grc.html")
        val = validate_document_v2(grc_doc)
        return ("PASS" if val["valid"] and "POJK 11/2022" in p_html.read_text(encoding="utf-8") else "FAIL", str(val["valid"]))

    def t42(r: Path):
        pre_doc = adapt_presales_payload({
            "scenarios": [{"name": "conservative", "rps": 20, "vcpu": 2, "ram_gb": 8, "notes": "Min"}, {"name": "expected", "rps": 100, "vcpu": 8, "ram_gb": 32, "notes": "Target"}, {"name": "stress", "rps": 300, "vcpu": 16, "ram_gb": 64, "notes": "Peak"}],
            "selected_option": "B",
        })
        p_xlsx = render_v2_to_xlsx(pre_doc, r / "presales.xlsx")
        p_md = render_v2_to_markdown(pre_doc, r / "presales.md")
        qa = verify_rendered_outputs_qa(pre_doc, {"xlsx": p_xlsx, "md": p_md})
        return ("PASS" if qa["passed"] and "conservative" in p_md.read_text(encoding="utf-8") else "FAIL", str(qa["passed"]))

    def t43(r: Path):
        pmo_doc = adapt_pmo_or_ea_payload({"metrics": {"CPI": "1.04", "SPI": "0.98", "P80_Date": "2026-12-15"}}, skill_name="shadow-pmo")
        blocks_ok = any(s.get("source_id") == "ENGINE-OUTPUT" for s in pmo_doc["sources"]) and any(b.get("source_refs") for b in pmo_doc["blocks"] if b["kind"] == "table")
        return ("PASS" if blocks_ok else "FAIL", "cross-skill source traceability")

    def t44(r: Path):
        doc = _sample_v21_doc()
        p1 = render_v2_to_markdown(doc, r / "run1" / "out.md").read_text(encoding="utf-8")
        p2 = render_v2_to_markdown(doc, r / "run2" / "out.md").read_text(encoding="utf-8")
        h1 = render_v2_to_html(doc, r / "run1" / "out.html").read_text(encoding="utf-8")
        h2 = render_v2_to_html(doc, r / "run2" / "out.html").read_text(encoding="utf-8")
        return ("PASS" if p1 == p2 and h1 == h2 else "FAIL", "deterministic md & html byte equality verified")

    cases: list[tuple[int, str, str, Callable[[Path], tuple[str, str]]]] = [
        (1, "Discovery", "Explicit user-selected generator", t01),
        (2, "Discovery", "Existing generator in custom directory", t02),
        (3, "Discovery", "Generator discovered via package scripts", t03),
        (4, "Discovery", "Project configuration resolution (.shadow)", t04),
        (5, "Discovery", "Global configuration fallback", t05),
        (6, "Discovery", "Multiple competing generators conflict", t06),
        (7, "Discovery", "Invalid explicit generator path refused", t07),
        (8, "Discovery", "Missing configuration handled cleanly", t08),
        (9, "Discovery", "Unknown generator implementation classified UNKNOWN", t09),
        (10, "Compatibility", "Compatible existing generator reused", t10),
        (11, "Compatibility", "Partially compatible generator bridged", t11),
        (12, "Compatibility", "Incompatible generator triggers A/B/C/D gate", t12),
        (13, "Compatibility", "Adapter-based integration preserves semantics", t13),
        (14, "Compatibility", "Preservation of existing templates", t14),
        (15, "Compatibility", "No unnecessary generator replacement", t15),
        (16, "Compatibility", "No duplicate generator initialization", t16),
        (17, "Structured AST", "Valid JSON AST v2.1 passes", t17),
        (18, "Structured AST", "Invalid schema rejected", t18),
        (19, "Structured AST", "Schema v2.0->v2.1 migration preserves lineage", t19),
        (20, "Structured AST", "Unknown node fails explicitly (not dropped)", t20),
        (21, "Structured AST", "Evidence reference preservation", t21),
        (22, "Structured AST", "Source code & git metadata preservation", t22),
        (23, "Rendering", "Markdown output", t23),
        (24, "Rendering", "PDF output", t24),
        (25, "Rendering", "DOCX output", t25),
        (26, "Rendering", "HTML output", t26),
        (27, "Rendering", "XLSX output", t27),
        (28, "Rendering", "Mermaid source preservation & render hook", t28),
        (29, "Rendering", "DBML source preservation & render hook", t29),
        (30, "Rendering", "HTML table and code block rendering", t30),
        (31, "Rendering", "Graceful recovery when diagram CLI absent", t31),
        (32, "Security & Auth", "Path traversal prevention", t32),
        (33, "Security & Auth", "Output overwrite protection", t33),
        (34, "Security & Auth", "Global config mutation requires approval", t34),
        (35, "Security & Auth", "Unauthorized dependency install blocked", t35),
        (36, "Security & Auth", "Scope expansion / external publish gated", t36),
        (37, "Security & Auth", "Cross-project isolation bleed rejected", t37),
        (38, "Security & Auth", "Temporary-file cleanup (.tmp zero)", t38),
        (39, "E2E Workflows", "Handover via existing project-local generator", t39),
        (40, "E2E Workflows", "Handover via Global Document Engine", t40),
        (41, "E2E Workflows", "GRC report via shared orchestration & adapter", t41),
        (42, "E2E Workflows", "Presales proposal with structured tables", t42),
        (43, "E2E Workflows", "Cross-skill source & evidence traceability", t43),
        (44, "E2E Workflows", "Controlled reproducibility (MD & HTML identical)", t44),
    ]

    for num, cat, nm, fn in cases:
        run_case(num, cat, nm, fn)

    counts = {
        "PASS": sum(1 for r in results if r["status"] == "PASS"),
        "FAIL": sum(1 for r in results if r["status"] == "FAIL"),
        "BLOCKED": sum(1 for r in results if r["status"] == "BLOCKED"),
        "NOT_RUN": sum(1 for r in results if r["status"] == "NOT_RUN"),
    }
    return {
        "suite": "SA-DOC-ENGINE-001 Mandatory 44-Test Verification Suite",
        "total": len(results),
        "counts": counts,
        "all_passed": counts["FAIL"] == 0 and counts["BLOCKED"] == 0 and counts["NOT_RUN"] == 0,
        "results": results,
    }


def main() -> int:
    summary = run_44_tests()
    print(json.dumps(summary, indent=2))
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
