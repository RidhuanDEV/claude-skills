import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GATE = Path(__file__).resolve().parents[1] / "scripts/realtime_transport_verifier.py"


def observed(kind, **fields):
    return {"type": kind, "connection": "s1", **fields}


def recovery_fixture():
    scope = {"tenant": "tenant-A", "stream": "room"}
    def emission(seq):
        return observed("emit", **scope, node="N", seq=seq)
    return {"trace_version": 2, "topology": "single_node", "queue_capacity": 3, "events": [
        observed("connect", **scope, node="N", cursor=9), observed("authorize", **scope),
        emission(10), observed("deliver", **scope, seq=10, applied=True), observed("disconnect"),
        observed("resume", cursor=10, earliest_retained=10, node="N"), observed("authorize", **scope),
        observed("deliver", **scope, seq=10, applied=False), observed("disconnect"),
        observed("resume", cursor=10, earliest_retained=20, node="N"), observed("authorize", **scope),
        observed("snapshot", **scope, cursor=20), emission(21), observed("deliver", **scope, seq=21, applied=True),
        observed("queue", depth=2), observed("revoke"), emission(22), observed("blocked", **scope, seq=22)]}


class RealtimeCli(unittest.TestCase):
    def check(self, trace, expected):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp, "trace.json")
            file.write_text(json.dumps(trace), encoding="utf8")
            p = subprocess.run([sys.executable, str(GATE), "--verify-session", str(file)], capture_output=True, text=True)
        data = json.loads(p.stdout)
        self.assertEqual(data["status"], expected, data)
        self.assertEqual(p.returncode, 0 if expected == "PASS" else 1)
        return data

    def test_recovery_after_expired_cursor(self):
        self.assertEqual(self.check(recovery_fixture(), "PASS")["coverage"]["snapshot"], 1)

    def test_old_snapshot_or_wrong_owner(self):
        for change in ({"cursor": 10}, {"tenant": "tenant-B"}, {"stream": "private"}):
            with self.subTest(change=change):
                trace = recovery_fixture()
                trace["events"][11].update(change)
                self.check(trace, "FAIL")

    def test_partial_snapshot_denies_delivery(self):
        trace = recovery_fixture()
        del trace["events"][11]
        self.check(trace, "FAIL")

    def test_multinode_claim_requires_evidence(self):
        trace = recovery_fixture()
        trace["topology"] = "multi_node"
        self.check(trace, "INCOMPLETE")

    def test_out_of_order_and_truthy_strings(self):
        trace = recovery_fixture()
        trace["events"][3]["applied"] = "false"
        self.check(trace, "FAIL")
        trace = recovery_fixture()
        trace["events"][0]["cursor"] = 8
        self.check(trace, "FAIL")

    def test_legacy_flags_return_no_verified_behavior(self):
        self.check({"supports_cursor_resume": "false", "events": []}, "INCOMPLETE")

    def test_other_tenant_before_revocation(self):
        trace = recovery_fixture()
        for i in (12, 13):
            trace["events"][i]["tenant"] = "tenant-B"
        self.assertGreater(self.check(trace, "FAIL")["unauthorized_events_leaked"], 0)


if __name__ == "__main__":
    unittest.main()
