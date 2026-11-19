import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from compare_action import assess


class ActionTests(unittest.TestCase):
    def setUp(self):
        self.expected = dict(route="/login", role="guest", action="reject invalid credentials",
                             httpStatus=401, visibleState="error alert", sessionPresent=False)
        self.capture = dict(self.expected, environment="reachable")

    def test_expected_rejection(self):
        self.assertEqual(assess(self.expected, self.capture)["status"], "PASS")

    def test_blank_ui_and_wrong_session_type(self):
        self.capture.update(visibleState="blank", sessionPresent=0)
        self.assertEqual(assess(self.expected, self.capture)["failed"], ["sessionPresent", "visibleState"])

    def test_incomplete_capture(self):
        del self.capture["httpStatus"]
        self.assertEqual(assess(self.expected, self.capture)["status"], "BLOCKED")

    def test_wrong_target(self):
        self.capture.update(route="/other")
        self.assertEqual(assess(self.expected, self.capture)["status"], "BLOCKED")

    def test_environment_failure(self):
        self.capture.update(environment="unreachable")
        self.assertEqual(assess(self.expected, self.capture)["status"], "BLOCKED")

    def test_invalid_oracle(self):
        with self.assertRaises(ValueError):
            assess(dict(self.expected, sessionPresent="false"), self.capture)
