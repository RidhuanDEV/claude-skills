"""Regression probes for false-success decisions in shipped offline verifiers."""

from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shadow-monarch" / "scripts"))
from shadow_input import InvalidInput

MALFORMED_FLAGS = ("false", "true", 0, 1, None)
EXPERIMENT = {
    "variants": [
        {"name": "control", "expected_ratio": 0.5, "assigned_count": 10000, "conversions": 1000},
        {"name": "treatment", "expected_ratio": 0.5, "assigned_count": 10000, "conversions": 1300},
    ],
    "guardrails": [{"name": "checkout latency", "regressed": False}],
}
RECEIPT = {
    "operation_id": "order-1", "state": "CONFIRMED", "verified": True, "account": "merchant-1",
    "currency": "IDR", "provider_tx_id": "provider-1", "amount_minor": 50000,
}
DNS_AUTH = {
    "spf_record": "v=spf1 -all", "dmarc_record": "v=DMARC1; p=reject; adkim=s; aspf=s",
    "from_domain": "example.test", "dkim_domain": "example.test", "dkim_key_bits": 2048,
}


@lru_cache(maxsize=None)
def verifier(skill: str, script: str, function: str):
    return runpy.run_path(str(ROOT / skill / "scripts" / f"{script}.py"))[function]


class Wave1EvidenceTests(unittest.TestCase):
    def test_real_verifiers_reject_non_boolean_evidence(self):
        cases = (
            ("shadow-analytics", "analytics_experiment_verifier", "check_event", ({},), (0, "consent_analytics")),
            ("shadow-analytics", "analytics_experiment_verifier", "check_dsar_plan", ({},), (0, "warehouse_tables_covered")),
            ("shadow-analytics", "analytics_experiment_verifier", "check_experiment", (EXPERIMENT,), (0, "guardrails", 0, "regressed")),
            ("shadow-auth", "auth_policy_verifier", "check_policy_matrix", ({"deny_by_default": True, "routes": [{"path": "/admin/users"}]},), (0, "routes", 0, "public")),
            ("shadow-auth", "auth_policy_verifier", "check_sso_coexistence", ({},), (0, "tenant_bound_from_email_domain_only")),
            ("shadow-cache", "cache_policy_verifier", "check_cache_config", ({"redis_keys": [{"pattern": "tenant:{tenant_id}:v1:report"}]},), (0, "redis_keys", 0, "persistent_structure")),
            ("shadow-compat", "compat_deprecation_verifier", "check_compat_spec", ({"contract_diff": {"new_request_fields": {"name": {}}}},), (0, "contract_diff", "new_request_fields", "name", "required")),
            ("shadow-concurrency", "concurrency_invariant_checker", "simulate_at_least_once_replay", ({},), (0, "uses_durable_idempotency_store")),
            ("shadow-doc", "doc_orchestrator", "assess_generator_compatibility", ({}, {}), (1, "requires_tables")),
            ("shadow-domain", "domain_invariant_verifier", "verify_domain_model", ({"simulated_commands": [{}]},), (0, "simulated_commands", 0, "expected_allowed")),
            ("shadow-email", "email_deliverability_verifier", "validate_rfc8058_policy", ({"category": "MARKETING_BULK"},), (0, "unsubscribe_requires_login")),
            ("shadow-grc", "grc_assurance_engine", "validate_iso27001_soa", ({"annex_a_controls": [{"control_id": "A.5.15", "theme": "ORGANIZATIONAL"}]},), (0, "annex_a_controls", 0, "applicable")),
            ("shadow-modernize", "modernize_forensics_engine", "evaluate_modernization_options", ({"risk_dimensions": {"operations_slo": {"score": 2, "evidence_refs": ["E1"]}}},), (0, "has_automated_tests")),
            ("shadow-monarch", "execution_approval_gate", "evaluate_execution_request", ({"environment": "local"},), (0, "is_mutation")),
            ("shadow-monarch", "official_first_verifier", "verify_auth_sdk_policy", ({"existing_sdk_source": "file:../sdk/sso-client", "proposed_source": "lookalike", "verified_authenticated_claims": True},), (0, "publisher_ownership_verified")),
            ("shadow-monarch", "official_first_verifier", "verify_decision_record", ({"replaces_auth_or_sso_sdk": True},), (0, "introduces_new_framework")),
            ("shadow-monarch", "skill_router", "route_prompt", ("document the API", 4, "wave1", {}), (3, "has_active_generator")),
            ("shadow-observe", "telemetry_hygiene_verifier", "check_metrics_config", ({"alerts": [{}]},), (0, "alerts", 0, "paging")),
            ("shadow-plan", "sprint_dag_verifier", "audit_sprint_plan", ({"tasks": [{"task_id": "T1"}]},), (0, "tasks", 0, "approval_required")),
            ("shadow-pmo", "pmo_governance_engine", "evaluate_change_request", ({},), (0, "introduces_net_new_workflow_or_integration")),
            ("shadow-presales", "presales_commercial_engine", "compute_tco_and_commercial", ({"infra_capex_items": [{"qty": 1, "unit_price": 100}]},), (0, "infra_capex_items", 0, "is_umkk_pdn")),
            ("shadow-refactor", "refactor_characterization_gate", "verify_refactor_plan", ({"precedents_inspected": ["src/order.py"], "invariants_locked": ["Keep response schema"]},), (0, "adr_approved_for_new_pattern")),
            ("shadow-release", "release_readiness_verifier", "check_release_manifest", ({},), (0, "has_breaking_changes")),
            ("shadow-seo", "seo_audit_verifier", "validate_ssr_seo_page", ({},), (0, "has_noindex")),
            ("shadow-test", "suite_hygiene_verifier", "check_test_hygiene", ({"test_snippets": [{"code": "time.sleep(3)"}]},), (0, "test_snippets", 0, "uses_fake_timers")),
        )

        for skill, script, function, values, path in cases:
            check = verifier(skill, script, function)
            for flag in (*MALFORMED_FLAGS, False, True):
                with self.subTest(check=f"{skill}/{function}", field=path[-1], flag=repr(flag)):
                    args = deepcopy(values)
                    target = args
                    for key in path[:-1]:
                        target = target[key]
                    target[path[-1]] = flag
                    if isinstance(flag, bool):
                        check(*args)
                    else:
                        with self.assertRaisesRegex(InvalidInput, "JSON boolean"):
                            check(*args)

    def test_required_evidence_missing(self):
        concurrency = verifier("shadow-concurrency", "concurrency_invariant_checker", "simulate_at_least_once_replay")
        spec = {"uses_durable_idempotency_store": True, "uses_atomic_claim_or_lock": True, "has_dlq": True, "max_attempts": 3}
        self.assertTrue(concurrency(dict(spec, ack_before_durable_commit=False))["valid"])
        self.assertFalse(concurrency(spec)["valid"])
        self.assertFalse(concurrency(dict(spec, ack_before_durable_commit=True))["valid"])

        sso = verifier("shadow-monarch", "official_first_verifier", "verify_auth_sdk_policy")
        spec = {"verified_authenticated_claims": True, "existing_sdk_source": "file:../sdk/sso-client",
                "proposed_source": "new-sdk", "user_approval_granted": True, "publisher_ownership_verified": True}
        self.assertEqual(sso(spec)["status"], "PASS")
        for field in ("verified_authenticated_claims", "user_approval_granted", "publisher_ownership_verified"):
            with self.subTest(field=field):
                self.assertEqual(sso({key: value for key, value in spec.items() if key != field})["status"], "BLOCKED")

        refactor = verifier("shadow-refactor", "refactor_characterization_gate", "verify_refactor_plan")
        for field in ("precedents_inspected", "invariants_locked"):
            for value in (*MALFORMED_FLAGS, [], [" "]):
                spec = {"precedents_inspected": ["src/order.py"], "invariants_locked": ["API response"]}
                spec[field] = value
                with self.subTest(field=field, value=value), self.assertRaisesRegex(InvalidInput, field):
                    refactor(spec)

    def test_invalid_cli_exit_and_optional_default(self):
        script = ROOT / "shadow-auth/scripts/auth_policy_verifier.py"
        data = {"deny_by_default": True, "routes": [{
            "path": "/admin/users", "server_auth_enforced": True, "tenant_scoped_in_query": True,
            "privileged": True, "negative_tests": {"unauth_401": True, "cross_tenant_denied": True, "role_denied_403": True},
        }]}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "policy.json"
            for flag, expected in ((False, 0), (True, 1), ("false", 2), ("true", 2), (0, 2), (1, 2), (None, 2)):
                with self.subTest(flag=repr(flag)):
                    payload = deepcopy(data)
                    payload["routes"][0]["public"] = flag
                    path.write_text(json.dumps(payload), encoding="utf-8")
                    result = subprocess.run(
                        [sys.executable, "-B", str(script), "--check-policy-matrix", str(path)],
                        capture_output=True, text=True, timeout=10,
                    )
                    self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
                    decoded = json.loads(result.stdout)
                    if expected == 2:
                        self.assertEqual((decoded["status"], decoded["passed"]), ("INVALID_INPUT", False))
            path.write_text(json.dumps(data), encoding="utf-8")
            result = subprocess.run([sys.executable, "-B", str(script), "--check-policy-matrix", str(path)],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_srm_threshold_and_guardrails(self):
        check = verifier("shadow-analytics", "analytics_experiment_verifier", "check_experiment")
        self.assertEqual(check(EXPERIMENT)["verdict"], "SHIP_CANDIDATE")
        self.assertNotEqual(check(dict(EXPERIMENT, guardrails=[{"regressed": True}]))["verdict"], "SHIP_CANDIDATE")
        for bad_guardrail in ({}, None, {"regressed": True, "severity": "blockng"}):
            with self.subTest(guardrail=bad_guardrail), self.assertRaises(InvalidInput):
                check(dict(EXPERIMENT, guardrails=[bad_guardrail]))

        mismatched = deepcopy(EXPERIMENT)
        mismatched["variants"][1]["assigned_count"] = 10600
        self.assertEqual(check(mismatched)["verdict"], "BLOCKED_SRM")
        for alpha in (0, -1, 1e-7, 0.1, "0.001", True, None, float("nan"), float("inf"), 0.01):
            with self.subTest(alpha=alpha), self.assertRaises(InvalidInput):
                check(dict(mismatched, srm_alpha=alpha))
        with self.assertRaisesRegex(InvalidInput, "finite JSON number"):
            check(dict(mismatched, srm_alpha=0, srm_alpha_justification="Attempted override."))
        justified = dict(mismatched, srm_alpha=0.01, srm_alpha_justification="Pre-registered screening threshold.")
        self.assertEqual(check(justified)["verdict"], "BLOCKED_SRM")
        mismatched["variants"][0]["expected_ratio"] = float("nan")
        with self.assertRaisesRegex(InvalidInput, "expected_ratio"):
            check(mismatched)

    def test_reconciliation_binds_the_entire_terminal_receipt(self):
        decide = verifier("shadow-integrate", "reconcile_unknown", "decide")
        order = dict(RECEIPT, state="UNKNOWN")
        self.assertEqual(decide(dict(order, inquiry=RECEIPT)), "RECORD_CONFIRMED")
        self.assertEqual(decide(dict(order, inquiry=dict(RECEIPT, state="FAILED"))), "RECORD_FAILED")
        for field, wrong in (("operation_id", "other"), ("account", "other"), ("currency", "USD"),
                             ("provider_tx_id", "other"), ("amount_minor", 50000.0), ("amount_minor", True)):
            with self.subTest(field=field, wrong=wrong):
                self.assertEqual(decide(dict(order, inquiry=dict(RECEIPT, **{field: wrong}))), "MANUAL_RECONCILIATION")
                missing = {key: value for key, value in RECEIPT.items() if key != field}
                self.assertEqual(decide(dict(order, inquiry=missing)), "MANUAL_RECONCILIATION")

        replay = dict.fromkeys(("provider_guarantee_verified", "same_account", "same_key", "same_payload",
                                "same_operation", "inside_window", "retry_budget_available"), True)
        self.assertEqual(decide(dict(order, inquiry_supported=True, deduplication=replay)), "QUERY_STATUS")
        self.assertEqual(decide(dict(order, inquiry_supported=False, deduplication=replay)), "ELIGIBLE_FOR_SAME_KEY_REPLAY")
        for flag in MALFORMED_FLAGS:
            self.assertEqual(decide(dict(order, inquiry_supported=flag, deduplication=replay)), "MANUAL_RECONCILIATION")

    def test_dmarc_requires_alignment_evidence(self):
        check = verifier("shadow-email", "email_deliverability_verifier", "validate_dns_auth")
        self.assertTrue(check(DNS_AUTH)["passed"])
        child = dict(DNS_AUTH, dkim_domain="mail.example.test")
        self.assertFalse(check(child)["passed"])
        self.assertFalse(check(dict(child, dmarc_record="v=DMARC1; p=reject; adkim=r"))["passed"])
        relaxed = dict(child, dmarc_record="v=DMARC1; p=reject; adkim=r",
                       organizational_domains={"example.test": "example.test", "mail.example.test": "example.test"})
        self.assertTrue(check(relaxed)["passed"])
        self.assertFalse(check(dict(relaxed, dmarc_record=DNS_AUTH["dmarc_record"]))["passed"])
        self.assertFalse(check(dict(relaxed, dkim_domain="exampl3.test"))["passed"])
        self.assertFalse(check(dict(DNS_AUTH, dmarc_record="v=DMARC1; sp=reject"))["passed"])
        self.assertFalse(check(dict(DNS_AUTH, dmarc_record="v=DMARC1; p=reject; adkim=x"))["passed"])
        self.assertFalse(check(dict(DNS_AUTH, dmarc_record="v=dmarc1; p=reject"))["passed"])
        self.assertFalse(check(dict(DNS_AUTH, dmarc_record="v=DMARC1; p=reject; sp=bogus"))["passed"])
        self.assertTrue(check(dict(child, return_path_domain="example.test"))["passed"])

    def test_spf_counts_nested_terms_and_handles_unknown_paths(self):
        check = verifier("shadow-email", "email_deliverability_verifier", "validate_dns_auth")
        records = {"_spf.example.test": "v=spf1 redirect=_next.example.test",
                   "_next.example.test": "v=spf1 " + " ".join(f"a:a{i}.example.test" for i in range(8)) + " -all"}
        nested = dict(DNS_AUTH, spf_record="v=spf1 include:_spf.example.test -all", spf_records=records)
        self.assertTrue(check(nested)["passed"])
        self.assertFalse(check(dict(nested, spf_records={}))["passed"])
        records["_next.example.test"] = records["_next.example.test"].replace(" -all", " mx -all")
        exceeded = check(nested)
        self.assertFalse(exceeded["passed"])
        self.assertTrue(any("SPF_DNS_LOOKUP_EXCEEDED" in error for error in exceeded["errors"]))
        records["_next.example.test"] = "v=spf1 include:_spf.example.test -all"
        self.assertTrue(any("SPF_RECURSION_CYCLE" in error for error in check(nested)["errors"]))
        self.assertTrue(check(dict(DNS_AUTH, spf_record="v=spf1 redirect=missing.example.test -all"))["passed"])
        self.assertTrue(check(dict(DNS_AUTH, spf_record="v=spf1 future-modifier=value -all"))["passed"])
        for record in ("v=spf1 all", "v=spf1 +all", "v=spf1 include/foo:example.test -all",
                       "v=spf1 ip4/foo:192.0.2.1 -all", "v=spf1 exists -all"):
            with self.subTest(record=record):
                self.assertFalse(check(dict(DNS_AUTH, spf_record=record))["passed"])

    def test_empty_or_placeholder_evidence(self):
        assess = verifier("shadow-modernize", "modernize_forensics_engine", "evaluate_modernization_options")
        positive = {"risk_dimensions": {"operations_slo": {"score": 2.0, "evidence_refs": ["E1"]}}}
        self.assertIn("recommended_strategy", assess(positive))
        for invalid in ({}, {"risk_dimensions": {"operations_slo": {"evidence_refs": ["E1"]}}},
                        dict(positive, dimension_weights={"operations_slo": 0})):
            with self.assertRaises(InvalidInput):
                assess(invalid)

        cost = verifier("shadow-presales", "presales_commercial_engine", "compute_tco_and_commercial")
        self.assertTrue(cost({"annual_opex_items": [{"annual_cost": 10}]})["tco_multi_year"]["numerical_reconciled"])
        for invalid in ({}, {"annual_opex_items": [{"annual_cost": 0}]},
                        {"infra_capex_items": [{"qty": True, "unit_price": 100}]},
                        {"infra_capex_items": [{"qty": 1, "unit_price": -100}]}):
            with self.assertRaises(InvalidInput):
                cost(invalid)

        audit = verifier("shadow-grc", "grc_assurance_engine", "validate_audit_findings")
        fields = ("criteria", "condition", "cause", "effect", "recommendation", "evidence_ref")
        self.assertTrue(audit([dict.fromkeys(fields, "evidence")], as_of_date="2026-11-26")["valid"])
        self.assertFalse(audit([], as_of_date="2026-11-26")["valid"])
        self.assertFalse(audit([dict.fromkeys(fields, None)], as_of_date="2026-11-26")["valid"])

        score = verifier("shadow-eval", "ai_eval_gate", "score_rag_dataset")
        abstain = {"sample_id": "none", "sample_type": "abstain", "language": "id", "tenant_id": "A",
                   "retrieved_chunks": [], "abstained": True}
        self.assertEqual(score([abstain])["status"], "INCOMPLETE")
        answer = {"tenant_id": "A", "expected_chunk_ids": ["doc"], "answer_citations": ["doc"],
                  "retrieved_chunks": [{"id": "doc", "tenant_id": "A"}]}
        self.assertEqual(score([answer, abstain])["status"], "PASS")

    def test_docker_flags_cannot_come_from_prose_or_container_arguments(self):
        check = verifier("shadow-test", "suite_hygiene_verifier", "check_test_hygiene")
        def validate(code: str):
            return check({"test_snippets": [{"language": "bash", "code": code}]})
        clean = "trap 'docker rm -f -v fixture' EXIT\ndocker run --rm --label=shadow.ephemeral=true --name fixture postgres"
        self.assertEqual(validate(clean), [])
        named_trap = "cleanup() { docker rm -f -v fixture; }\\ntrap cleanup EXIT\\n" + clean.splitlines()[-1]
        self.assertEqual(validate(named_trap), [])
        power_shell = "try { docker run -d --rm --label shadow.ephemeral=true --name fixture postgres } finally { docker rm -f -v fixture }"
        self.assertEqual(validate(power_shell), [])
        for bad in ("docker run postgres # --rm --label shadow.ephemeral=true finally docker rm -f -v fixture",
                    "docker run -d postgres --rm --label shadow.ephemeral=true",
                    "docker run --rm -e shadow.ephemeral=true postgres",
                    "docker run --rm --label shadow.ephemeral=true --rm=false postgres"):
            with self.subTest(command=bad):
                self.assertIn("DOCKER_MISSING_EPHEMERAL_FLAGS", {item["code"] for item in validate(bad)})

        run = "docker run --rm --label shadow.ephemeral=true --name fixture postgres"
        for bad in (";# finally { docker rm -f -v fixture }",
                    "; echo 'finally { docker rm -f -v fixture }'",
                    "; try {} finally { echo docker rm -f -v fixture }",
                    "; try {} finally {}\\ndocker rm -f -v fixture",
                    "; try {} finally { docker rm -f -v other }",
                    "; try {} finally { docker rm -f fixture }"):
            with self.subTest(cleanup=bad):
                codes = {item["code"] for item in validate(run + bad)}
                self.assertIn("DOCKER_MISSING_GUARANTEED_TEARDOWN", codes)


if __name__ == "__main__":
    unittest.main()
