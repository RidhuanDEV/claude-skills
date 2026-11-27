"""Semantic conservation tests against the shipped R03 Markdown adapter, diff, hash and quality gate."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from typing import Any, Callable
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import doc_orchestrator  # noqa: E402
import v2_core  # noqa: E402
import v2_renderers  # noqa: E402

REAL_RENDER = v2_renderers.render_v2_to_markdown
COLUMNS = ["req_id", "test_case", "status", "exception_notes"]


def uat_doc(**overrides: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "schema_version": "2.1",
        "document_id": "DOC-UAT-1",
        "project_id": "PRJ-UAT",
        "document_type": "UAT",
        "title": "UAT Sign-Off Matrix",
        "revision": "1.0",
        "status": "DRAFT",
        "language": "en-US",
        "sources": [{"source_id": "SRC-1", "reference": "docs/uat.md"}],
        "blocks": [
            {"id": "SEC-1", "kind": "heading", "level": 2, "title": "1. Sign-Off", "source_refs": [], "trace_ids": []},
            {
                "id": "TBL-1",
                "kind": "table",
                "table_data": {
                    "columns": list(COLUMNS),
                    "rows": [["FR-01", "TC-01", "PASS", ""], ["FR-02", "TC-02", "PASS", "waived by PO"]],
                },
                "source_refs": ["SRC-1"],
                "trace_ids": [],
            },
        ],
        "history": [{"revision": "1.0", "reason": "Init"}],
    }
    doc.update(overrides)
    return doc


def table(doc: dict[str, Any]) -> dict[str, Any]:
    return next(b for b in doc["blocks"] if b["kind"] == "table")["table_data"]


def lossy_renderer(mutate: Callable[[dict[str, Any]], None]) -> Callable[[dict[str, Any], Path], Path]:
    def render(doc: dict[str, Any], out_path: Path) -> Path:
        working = copy.deepcopy(doc)
        mutate(working)
        return REAL_RENDER(working, out_path)

    return render


def drop_column(name: str, blank_only: bool) -> Callable[[dict[str, Any]], None]:
    def mutate(doc: dict[str, Any]) -> None:
        td = table(doc)
        idx = td["columns"].index(name)
        td["columns"].pop(idx)
        if blank_only:
            td["rows"] = [row for row in td["rows"] if not row[idx]]
        for row in td["rows"]:
            row.pop(idx)

    return mutate


def adapt_with(doc: dict[str, Any], mutate: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    adapter = doc_orchestrator.MarkdownCompatibilityAdapter()
    if mutate is None:
        return adapter.adapt(doc)
    with mock.patch.object(v2_renderers, "render_v2_to_markdown", lossy_renderer(mutate)):
        return adapter.adapt(doc)


class SemanticConservationTests(unittest.TestCase):
    def test_e14_catches_removed_exception_column_while_allowing_title_wording_change(self) -> None:
        baseline = uat_doc()
        title_only = uat_doc(title="Staging UAT Sign-Off Matrix (Rev 2)", revision="1.1")
        dropped = uat_doc(revision="1.1")
        drop_column("exception_notes", blank_only=False)(dropped)

        res_title = v2_core.diff_documents_v2(baseline, title_only)
        self.assertEqual((res_title["removed_blocks"], res_title["modified_blocks"]), ([], []))
        self.assertEqual(adapt_with(title_only)["fidelity_status"], "LOSSLESS_VERIFIED")

        res_drop = v2_core.diff_documents_v2(baseline, dropped)
        self.assertEqual([m["id"] for m in res_drop["modified_blocks"]], ["TBL-1"])
        before_cols = res_drop["modified_blocks"][0]["before"]["table_data"]["columns"]
        after_cols = res_drop["modified_blocks"][0]["after"]["table_data"]["columns"]
        self.assertEqual(sorted(set(before_cols) - set(after_cols)), ["exception_notes"])


class MarkdownFidelityGate(unittest.TestCase):
    def test_clean_roundtrip_is_lossless(self) -> None:
        res = adapt_with(uat_doc())
        self.assertEqual(res["fidelity_status"], "LOSSLESS_VERIFIED", res["fidelity_failures"])
        self.assertIs(res["lossless_verified"], True)

    def test_renderer_dropping_blank_column_fails(self) -> None:
        res = adapt_with(uat_doc(), drop_column("exception_notes", blank_only=True))
        self.assertEqual(res["fidelity_status"], "FAILED")
        self.assertIs(res["lossless_verified"], False)
        self.assertTrue(any("header" in f for f in res["fidelity_failures"]))

    def test_renderer_dropping_populated_column_fails(self) -> None:
        res = adapt_with(uat_doc(), drop_column("exception_notes", blank_only=False))
        self.assertEqual(res["fidelity_status"], "FAILED")
        self.assertTrue(any("waived by PO" in f for f in res["fidelity_failures"]))

    def test_renderer_reordering_columns_fails(self) -> None:
        def reorder(doc: dict[str, Any]) -> None:
            td = table(doc)
            td["columns"] = list(reversed(td["columns"]))
            td["rows"] = [list(reversed(r)) for r in td["rows"]]

        self.assertEqual(adapt_with(uat_doc(), reorder)["fidelity_status"], "FAILED")

    def test_renderer_losing_heading_title_or_source_fails(self) -> None:
        def rename_heading(doc: dict[str, Any]) -> None:
            doc["blocks"][0]["title"] = "1. Sign Off"

        def rename_title(doc: dict[str, Any]) -> None:
            doc["title"] = "UAT Matrix"

        def drop_source(doc: dict[str, Any]) -> None:
            doc["sources"] = []

        for mutate in (rename_heading, rename_title, drop_source):
            with self.subTest(mutate=mutate.__name__):
                res = adapt_with(uat_doc(), mutate)
                self.assertEqual(res["fidelity_status"], "FAILED")
                self.assertIs(res["lossless_verified"], False)

    def test_structured_extensions_are_lossy_not_lossless(self) -> None:
        res = adapt_with(uat_doc(extensions={"x-uat:sla": "P1"}))
        self.assertEqual(res["fidelity_status"], "LOSSY_WITH_WARNINGS")
        self.assertIs(res["lossless_verified"], False)


class SemanticHash(unittest.TestCase):
    def test_volatile_fields_ignored_and_semantic_change_detected(self) -> None:
        base = v2_core.compute_semantic_hash(uat_doc())
        self.assertEqual(base, v2_core.compute_semantic_hash(uat_doc(updated_at="2026-11-27T00:00:00Z", hash="x")))
        dropped = uat_doc()
        drop_column("exception_notes", blank_only=False)(dropped)
        self.assertNotEqual(base, v2_core.compute_semantic_hash(dropped))
        self.assertNotEqual(base, v2_core.compute_semantic_hash(uat_doc(title="Other")))


class DocumentQualityGate(unittest.TestCase):
    def test_valid_draft_passes(self) -> None:
        res = v2_core.validate_document_v2(uat_doc())
        self.assertTrue(res["valid"], res["issues"])

    def test_invalid_documents_fail(self) -> None:
        missing_title = uat_doc()
        del missing_title["title"]
        cases: dict[str, dict[str, Any]] = {
            "empty": {},
            "missing_title": missing_title,
            "lowercase_status": uat_doc(status="approved"),
            "string_schema_version": uat_doc(schema_version=2.1),
            "approved_without_signoff": uat_doc(status="APPROVED"),
            "duplicate_ids": uat_doc(blocks=[{"id": "A", "kind": "heading", "title": "x"}] * 2),
            "pass_claim_without_evidence": uat_doc(blocks=[{"id": "TC-1", "kind": "paragraph", "body": "ok", "status": "PASS", "source_refs": []}]),
        }
        for label, doc in cases.items():
            with self.subTest(case=label):
                res = v2_core.validate_document_v2(doc)
                self.assertFalse(res["valid"])
                self.assertGreater(res["critical_count"], 0)


if __name__ == "__main__":
    unittest.main()
