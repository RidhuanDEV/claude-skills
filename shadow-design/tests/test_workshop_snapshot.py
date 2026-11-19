import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from workshop_snapshot import plan_poll, qa_draft


class WorkshopSnapshotTests(unittest.TestCase):
    def test_draft_and_unknown_outcome_have_different_next_steps(self):
        snapshot = {"request_id": "r", "create_attempted": False, "observed_polls": []}
        self.assertEqual(plan_poll(snapshot)["status"], "DRAFT")
        snapshot["create_attempted"] = True
        self.assertEqual(plan_poll(snapshot)["status"], "HOLD")

    def test_lost_ack_and_repeated_page_reuse_one_resource(self):
        poll = {"request_id": "r", "poll_id": "123", "state": "draft"}
        snapshot = {"request_id": "r", "create_attempted": True, "observed_polls": [poll, poll]}
        self.assertEqual(plan_poll(snapshot), {"status": "RECONCILED", "poll_id": "123", "state": "draft"})
        snapshot["observed_polls"].append(dict(poll, poll_id="321"))
        self.assertEqual(plan_poll(snapshot)["status"], "HOLD")

    def test_private_content_and_host_links_do_not_enter_two_page_draft(self):
        public = {"id": "q1", "approved_for_draft": True, "public_question": "Can this be exported?",
                  "owner": "product owner", "due": "2026-11-26"}
        private = {"id": "q2", "approved_for_draft": False, "raw": "Private details"}
        second = {"id": "q3", "approved_for_draft": True, "public_question": "When?",
                  "public_answer": "Next month", "host_url": "private-admin-url"}
        pages = [{"cursor": None, "next_cursor": "c2", "questions": [public, private]},
                 {"cursor": "c2", "next_cursor": None, "questions": [public, second]}]
        out = qa_draft({"pages": pages})
        self.assertEqual(out["withheld"], 1)
        self.assertEqual([q["id"] for q in out["questions"]], ["q1", "q3"])
        self.assertNotIn("private-admin-url", json.dumps(out))
        self.assertNotIn("Private details", json.dumps(out))
        self.assertEqual(out["questions"][0]["owner"], "product owner")
        self.assertEqual(qa_draft({"pages": pages[:1]})["status"], "INCOMPLETE")

    def test_withdrawal_overrides_previously_shareable_record(self):
        pages = [{"cursor": None, "next_cursor": None, "questions": [
            {"id": "q", "approved_for_draft": True, "public_question": "Q", "public_answer": "A"},
            {"id": "q", "approved_for_draft": False}]}]
        self.assertEqual(qa_draft({"pages": pages})["questions"], [])

    def test_missing_page_or_multiple_terminal_pages_fail_closed(self):
        one = {"cursor": None, "next_cursor": "missing", "questions": []}
        with self.assertRaises(ValueError):
            qa_draft({"pages": [one, dict(one, cursor="wrong", next_cursor=None)]})
        done = dict(one, next_cursor=None)
        with self.assertRaises(ValueError):
            qa_draft({"pages": [done, done]})


if __name__ == "__main__":
    unittest.main()
