from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from visual_refinement_audit import audit_html


DES_09_COMPETING_NOTE = """<!doctype html>
<html lang="en">
<body>
  <main>
    <h1>Shipment #4821</h1>
    <div id="batch-note" class="cta bg-accent">Batch 14: verify pallet count</div>
    <button id="approve-btn" class="cta bg-accent" type="button">Approve shipment</button>
  </main>
</body>
</html>
"""

DES_09_REFINED = """<!doctype html>
<html lang="en">
<body>
  <main>
    <h1>Shipment #4821</h1>
    <div id="batch-note" class="note-muted">Batch 14: verify pallet count</div>
    <button id="approve-btn" class="cta bg-accent" type="button">Approve shipment</button>
  </main>
</body>
</html>
"""

DES_10_ALARM_USEFUL = """<!doctype html>
<html lang="en">
<body>
  <main>
    <div id="high-water" role="alert" class="alarm bg-accent">High-water alarm: Basin 3 above 92%</div>
    <button id="inspect-sensor" class="cta" type="button">Inspect sensor B3</button>
  </main>
</body>
</html>
"""

DES_10_ALARM_COLOR_ONLY = """<!doctype html>
<html lang="en">
<body>
  <main>
    <div id="high-water" role="alert" class="alarm bg-accent"></div>
    <button id="inspect-sensor" class="cta" type="button">Inspect sensor B3</button>
  </main>
</body>
</html>
"""

DES_11_KEYBOARD_REGRESSION = """<!doctype html>
<html lang="en">
<body>
  <main>
    <h1>Shipment #4821</h1>
    <div id="batch-note" class="note-muted">Batch 14: verify pallet count</div>
    <button id="approve-btn" class="cta bg-accent" type="button" tabindex="-1">Approve shipment</button>
  </main>
</body>
</html>
"""


class VisualRefinementAuditTests(unittest.TestCase):
    def test_des09_detects_competing_non_interactive_cue_and_passes_after_demotion(self) -> None:
        before = audit_html(DES_09_COMPETING_NOTE, primary_id="approve-btn")
        self.assertEqual(before["verdict"], "REVISE")
        codes = [f["code"] for f in before["findings"]]
        self.assertIn("COMPETING_NON_INTERACTIVE_EMPHASIS", codes)
        self.assertTrue(before["primary_control"]["reachable"])

        after = audit_html(DES_09_REFINED, primary_id="approve-btn")
        self.assertEqual(after["verdict"], "PASS")
        self.assertEqual(after["findings"], [])
        self.assertTrue(after["primary_control"]["reachable"])

    def test_des10_preserves_explicit_alarm_emphasis_and_flags_color_only_alarm(self) -> None:
        ok = audit_html(DES_10_ALARM_USEFUL, primary_id="inspect-sensor")
        self.assertEqual(ok["verdict"], "PASS")
        self.assertEqual(len(ok["preserved_cues"]), 1)
        self.assertEqual(ok["preserved_cues"][0]["code"], "ALARM_EMPHASIS_PRESERVED")

        bad = audit_html(DES_10_ALARM_COLOR_ONLY, primary_id="inspect-sensor")
        self.assertEqual(bad["verdict"], "REVISE")
        self.assertEqual(bad["findings"][0]["code"], "ALARM_COLOR_ONLY_NO_TEXT")

    def test_des11_blocks_candidate_when_primary_action_loses_keyboard_focus(self) -> None:
        regressed = audit_html(DES_11_KEYBOARD_REGRESSION, primary_id="approve-btn")
        self.assertEqual(regressed["verdict"], "REJECT")
        self.assertFalse(regressed["primary_control"]["reachable"])
        self.assertEqual(regressed["findings"][0]["code"], "PRIMARY_ACTION_UNREACHABLE_BY_KEYBOARD")
        self.assertEqual(regressed["focusable_count"], 0)

    def test_cli_exit_codes_and_error_handling(self) -> None:
        script = ROOT / "scripts" / "visual_refinement_audit.py"
        with tempfile.TemporaryDirectory() as tmp:
            good_file = Path(tmp) / "good.html"
            bad_file = Path(tmp) / "bad.html"
            good_file.write_text(DES_09_REFINED, encoding="utf-8")
            bad_file.write_text(DES_11_KEYBOARD_REGRESSION, encoding="utf-8")

            p_good = subprocess.run(
                [sys.executable, str(script), str(good_file), "--primary-id", "approve-btn"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(p_good.returncode, 0)
            self.assertEqual(json.loads(p_good.stdout)["verdict"], "PASS")

            p_bad = subprocess.run(
                [sys.executable, str(script), str(bad_file), "--primary-id", "approve-btn"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(p_bad.returncode, 1)
            self.assertEqual(json.loads(p_bad.stdout)["verdict"], "REJECT")

            p_missing = subprocess.run(
                [sys.executable, str(script), str(Path(tmp) / "missing.html")],
                capture_output=True,
                text=True,
            )
            self.assertEqual(p_missing.returncode, 2)


if __name__ == "__main__":
    unittest.main()
