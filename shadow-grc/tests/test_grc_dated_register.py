"""Dated control register and gate tests against the shipped grc_assurance_engine.py."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from typing import Any

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "grc_assurance_engine.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("grc_assurance_engine_under_test", SCRIPT)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


engine = _load()
ALL_CLAUSES = ["4", "5", "6", "7", "8", "9", "10"]


def control(**overrides: Any) -> dict[str, Any]:
    ctrl: dict[str, Any] = {
        "control_id": "A.8.24",
        "theme": "TECHNOLOGICAL",
        "applicable": True,
        "status": "IMPLEMENTED",
        "justification": "Cryptography required for cardholder data",
        "design_evidence_ref": "EVD-D-Q3",
        "operating_evidence_ref": "EVD-O-Q3",
    }
    ctrl.update(overrides)
    return ctrl


def soa(*controls: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {"management_clauses_covered": list(ALL_CLAUSES), "annex_a_controls": list(controls)}
    doc.update(overrides)
    return doc


def finding(**overrides: Any) -> dict[str, Any]:
    item: dict[str, Any] = {
        "finding_id": "GRC-BNK-01",
        "criteria": "POJK 11/POJK.03/2022",
        "condition": "2 of 5 critical vendors lack reassessment",
        "cause": "Vendor workflow omits risk trigger",
        "effect": "Operational resilience exposure",
        "recommendation": "Institute annual materiality review",
        "evidence_ref": "EVD-VEND-01",
        "regulation_ids": ["POJK-11-2022"],
    }
    item.update(overrides)
    return item


class GrcDatedRegisterTests(unittest.TestCase):
    def test_missing_operating_sample_is_design_only_and_blocks_soa(self) -> None:
        q3 = engine.validate_iso27001_soa(soa(control(operating_evidence_ref=None)))
        self.assertFalse(q3["valid"])
        self.assertTrue(any("operating_evidence_ref" in e for e in q3["errors"]))
        q4 = engine.validate_iso27001_soa(soa(control(operating_evidence_ref="EVD-O-Q4")))
        self.assertTrue(q4["valid"], q4)

    def test_dated_snapshot_changes_verdict_for_superseded_regulation(self) -> None:
        old = [finding(criteria="SEOJK 21/SEOJK.03/2017", regulation_ids=["SEOJK-21-2017"])]
        before = engine.validate_audit_findings(old, sector="BANKING", as_of_date="2026-02-28")
        on_cutover = engine.validate_audit_findings(old, sector="BANKING", as_of_date="2026-03-01")
        self.assertTrue(before["valid"], before)
        self.assertFalse(on_cutover["valid"])
        self.assertEqual((before["as_of_date"], on_cutover["as_of_date"]), ("2026-02-28", "2026-03-01"))


class SoaGate(unittest.TestCase):
    def test_not_applicable_control_with_justification_passes(self) -> None:
        res = engine.validate_iso27001_soa(
            soa(control(), control(control_id="A.7.1", theme="PHYSICAL", applicable=False, status="NOT_APPLICABLE",
                                   design_evidence_ref=None, operating_evidence_ref=None))
        )
        self.assertTrue(res["valid"], res)
        self.assertEqual(res["theme_counts"]["PHYSICAL"], 1)

    def test_wrong_type_or_blank_evidence_refs_fail(self) -> None:
        for field in ("design_evidence_ref", "operating_evidence_ref"):
            for value in (True, "   ", "", 1, None):
                with self.subTest(field=field, value=value):
                    self.assertFalse(engine.validate_iso27001_soa(soa(control(**{field: value})))["valid"])

    def test_string_booleans_rejected(self) -> None:
        with self.assertRaises(engine.InvalidInput):
            engine.validate_iso27001_soa(soa(control(applicable="false")))
        with self.assertRaises(engine.InvalidInput):
            engine.validate_iso27001_soa(soa(control(), require_full_93_controls="true"))

    def test_missing_clauses_empty_controls_and_overclaim_fail(self) -> None:
        self.assertFalse(engine.validate_iso27001_soa(soa(control(), management_clauses_covered=["4"]))["valid"])
        self.assertFalse(engine.validate_iso27001_soa(soa())["valid"])
        self.assertFalse(engine.validate_iso27001_soa({})["valid"])
        overclaim = soa(control(), summary="We are officially certified ISO 27001.")
        self.assertFalse(engine.validate_iso27001_soa(overclaim)["valid"])

    def test_full_93_distribution_enforced(self) -> None:
        self.assertFalse(engine.validate_iso27001_soa(soa(control(), require_full_93_controls=True))["valid"])

    def test_malformed_controls_rejected(self) -> None:
        for bad in ({"annex_a_controls": "A.8.24"}, soa("A.8.24"), soa(control(theme="NONE")), soa(control(control_id=""))):
            with self.subTest(bad=bad):
                with self.assertRaises(engine.InvalidInput):
                    engine.validate_iso27001_soa(bad)


class FindingsGate(unittest.TestCase):
    def test_complete_finding_passes(self) -> None:
        self.assertTrue(engine.validate_audit_findings([finding()], sector="BANKING", as_of_date="2026-11-16")["valid"])

    def test_empty_findings_rejected(self) -> None:
        res = engine.validate_audit_findings([], as_of_date="2026-11-16")
        self.assertFalse(res["valid"])
        self.assertEqual(res["errors"][0]["finding_id"], "FINDINGS_GATE")

    def test_missing_or_wrong_type_parts_fail(self) -> None:
        for part in ("criteria", "condition", "cause", "effect", "recommendation", "evidence_ref"):
            for value in (None, "  ", True):
                with self.subTest(part=part, value=value):
                    res = engine.validate_audit_findings([finding(**{part: value})], as_of_date="2026-11-16")
                    self.assertFalse(res["valid"])

    def test_bad_dates_fail(self) -> None:
        for as_of in (None, "", "2026-02-30", "16/11/2026", "2026-11-16T00:00"):
            with self.subTest(as_of=as_of):
                self.assertFalse(engine.validate_audit_findings([finding()], as_of_date=as_of)["valid"])

    def test_fabricated_regulation_fails(self) -> None:
        res = engine.validate_audit_findings([finding(regulation_ids=["POJK-99-2099"])], as_of_date="2026-11-16")
        self.assertFalse(res["valid"])

    def test_non_list_input_rejected(self) -> None:
        for bad in ({"findings": []}, "finding", [["not", "object"]]):
            with self.subTest(bad=bad):
                with self.assertRaises(engine.InvalidInput):
                    engine.validate_audit_findings(bad, as_of_date="2026-11-16")


class CobitGate(unittest.TestCase):
    def test_focus_maturity_is_weakest_capability(self) -> None:
        res = engine.assess_cobit_2019({
            "objectives": [
                {"objective_id": "APO12", "capability_level": 4, "evidence_refs": ["E1", "E2"]},
                {"objective_id": "DSS05", "capability_level": 2, "evidence_refs": ["E3", "E4"]},
            ],
            "focus_areas": [{"name": "Cyber", "objective_ids": ["APO12", "DSS05"]}],
        })
        self.assertTrue(res["assurance_ready"])
        self.assertEqual(res["focus_area_maturity"][0]["focus_area_maturity_level"], 2)

    def test_missing_evidence_not_assurance_ready(self) -> None:
        res = engine.assess_cobit_2019({"objectives": [{"objective_id": "APO13", "capability_level": 5, "evidence_refs": []}]})
        self.assertFalse(res["assurance_ready"])

    def test_bad_inputs_rejected(self) -> None:
        cases: list[dict[str, Any]] = [
            {},
            {"objectives": []},
            {"objectives": [{"objective_id": "APO12", "capability_level": 6, "evidence_refs": ["E"]}]},
            {"objectives": [{"objective_id": "APO12", "capability_level": True, "evidence_refs": ["E"]}]},
            {"objectives": [{"objective_id": "APO12", "capability_level": "3", "evidence_refs": ["E"]}]},
            {"objectives": [{"objective_id": "APO12", "capability_level": 3, "evidence_refs": "E1"}]},
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    engine.assess_cobit_2019(payload)


class EngineCli(unittest.TestCase):
    def run_cli(self, payload: object, *extra: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "findings.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return subprocess.run([sys.executable, "-B", str(SCRIPT), "--validate-findings", str(path), *extra],
                                  capture_output=True, text=True, timeout=60)

    def test_cli_exit_codes(self) -> None:
        self.assertEqual(self.run_cli([finding()], "--as-of-date", "2026-11-16").returncode, 0)
        self.assertEqual(self.run_cli([], "--as-of-date", "2026-11-16").returncode, 1)
        self.assertEqual(self.run_cli({"as_of_date": "2026-11-16"}).returncode, 1)
        self.assertEqual(self.run_cli([finding()]).returncode, 1)
        bad = self.run_cli(["nope"], "--as-of-date", "2026-11-16")
        self.assertEqual(bad.returncode, 2)
        self.assertEqual(json.loads(bad.stdout)["status"], "INVALID_INPUT")

    def test_self_test(self) -> None:
        self.assertTrue(engine.run_self_test()["all_passed"])


if __name__ == "__main__":
    unittest.main()
