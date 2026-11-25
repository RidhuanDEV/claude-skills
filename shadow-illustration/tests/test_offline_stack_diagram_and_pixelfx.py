from __future__ import annotations

import ast
import json
import re
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import build_stack_diagram as bsd


SAMPLE_SPEC = {
    "kicker": "architecture / shadow-army",
    "title": "Modular Order Service <Safe>",
    "subtitle": "Offline engineering stack diagram",
    "groups": [
        {"id": "edge", "label": "Edge", "x": 24, "y": 96, "w": 192, "h": 176, "tone": "blue"},
        {"id": "core", "label": "Core Runtime", "x": 248, "y": 96, "w": 400, "h": 176, "tone": "neutral"},
    ],
    "nodes": [
        {"id": "web", "label": "Web Client", "role": "spa", "icon": "browser", "x": 64, "y": 140},
        {"id": "api", "label": "Order API", "role": "http", "icon": "api", "x": 288, "y": 140},
        {"id": "ledger", "label": "Billing Ledger", "role": "acid db", "icon": "billing-custom", "x": 488, "y": 140},
    ],
    "edges": [
        {"from": "web", "to": "api", "kind": "primary", "label": "HTTPS"},
        {"from": "api", "to": "ledger", "kind": "internal", "label": "SQL"},
    ],
}


class OfflineStackDiagramTests(unittest.TestCase):
    def test_zero_network_imports_in_builder_source(self) -> None:
        source = (SCRIPTS / "build_stack_diagram.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        forbidden_mods = {"urllib", "http", "requests", "subprocess", "socket", "httpx", "aiohttp"}
        self.assertEqual(imported & forbidden_mods, set())
        self.assertNotIn("--no-sandbox", source)
        self.assertNotIn("stacks.caru.moe", source)

    def test_self_test_cli_passes(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / "build_stack_diagram.py"), "--self-test"],
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["status"], "PASS")
        self.assertTrue(payload["offline_only"])

    def test_builds_offline_html_and_svg_with_xss_escaping_and_monogram_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            spec_file = tmp_path / "spec.json"
            html_out = tmp_path / "arch.html"
            svg_out = tmp_path / "arch.svg"
            spec_file.write_text(json.dumps(SAMPLE_SPEC), encoding="utf-8")

            p_html = subprocess.run(
                [sys.executable, str(SCRIPTS / "build_stack_diagram.py"), str(spec_file), "--out", str(html_out)],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertEqual(json.loads(p_html.stdout)["status"], "BUILT")
            html_text = html_out.read_text(encoding="utf-8")
            self.assertIn("data:image/svg+xml;base64,", html_text)
            self.assertIn("&lt;Safe&gt;", html_text)
            self.assertNotIn("<Safe>", html_text)
            self.assertNotIn("http://", html_text)
            self.assertNotIn("https://", html_text)

            p_svg = subprocess.run(
                [sys.executable, str(SCRIPTS / "build_stack_diagram.py"), str(spec_file), "--format", "svg", "--out", str(svg_out)],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertEqual(json.loads(p_svg.stdout)["status"], "BUILT")
            svg_text = svg_out.read_text(encoding="utf-8")
            self.assertIn("&lt;Safe&gt;", svg_text)
            self.assertIn(">BL<", svg_text)  # deterministic monogram for Billing Ledger
            self.assertIsNone(re.search(r"https?://(?!www\.w3\.org/2000/svg\b)", svg_text))

    def test_local_svg_icon_embedding_and_adversarial_rejection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            icons = Path(tmp) / "icons"
            icons.mkdir()
            (icons / "safe-logo.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><circle cx="12" cy="12" r="8" fill="#0072B2"/></svg>',
                encoding="utf-8",
            )
            (icons / "xss-onload.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"><rect width="10" height="10"/></svg>',
                encoding="utf-8",
            )
            (icons / "ext-href.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg"><image href="https://evil.example/a.png"/></svg>',
                encoding="utf-8",
            )

            spec = json.loads(json.dumps(SAMPLE_SPEC))
            spec["nodes"][2]["icon"] = "safe-logo"
            svg = bsd.build_svg(spec, icons_dir=icons)
            self.assertIn('fill="#0072B2"', svg)

            for bad_icon in ("xss-onload", "ext-href", "../escape", "sub/dir"):
                bad_spec = json.loads(json.dumps(SAMPLE_SPEC))
                bad_spec["nodes"][2]["icon"] = bad_icon
                with self.assertRaises(ValueError, msg=f"Should reject {bad_icon}"):
                    bsd.build_svg(bad_spec, icons_dir=icons)

    def test_lore_accurate_brand_marks_nested_vendor_groups_obstacle_detour_and_utf8_bom(self) -> None:
        spec = {
            "kicker": "architecture / lore-accurate",
            "title": "Fintech Cloud Stack",
            "groups": [
                {"id": "aws", "label": "AWS Cloud", "icon": "aws", "x": 24, "y": 96, "w": 660, "h": 192, "tone": "aws", "style": "solid"},
                {"id": "vpc", "label": "Private Subnet", "x": 220, "y": 124, "w": 444, "h": 148, "tone": "neutral", "style": "dashed"},
            ],
            "nodes": [
                {"id": "api", "label": "Order API", "role": "go http", "icon": "go", "x": 64, "y": 148},
                {"id": "worker", "label": "Outbox Worker", "role": "redis", "icon": "redis", "x": 264, "y": 148},
                {"id": "pg", "label": "PostgreSQL", "role": "acid db", "icon": "postgres", "x": 464, "y": 148},
            ],
            "edges": [
                {"from": "api", "to": "pg", "kind": "primary", "label": "SQL"},
                {"from": "api", "to": "worker", "kind": "internal", "label": "Enqueue"},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            spec_bom = Path(tmp) / "bom.json"
            out_svg = Path(tmp) / "out.svg"
            spec_bom.write_text(json.dumps(spec), encoding="utf-8-sig")
            subprocess.run(
                [sys.executable, str(SCRIPTS / "build_stack_diagram.py"), str(spec_bom), "--format", "svg", "--out", str(out_svg)],
                capture_output=True,
                text=True,
                check=True,
            )
            svg = out_svg.read_text(encoding="utf-8")
            self.assertIn('id="dot-grid"', svg)
            self.assertIn("#336791", svg)  # PostgreSQL color mark
            self.assertIn("#DC382D", svg)  # Redis color mark
            self.assertIn("#00ADD8", svg)  # Go color mark
            self.assertIn(" Q ", svg)  # obstacle detour with rounded orthogonal corners
            self.assertIn("primary flow", svg)  # legend footer


class OfflinePixelFxEngineTests(unittest.TestCase):
    def test_zero_network_or_shell_imports_and_zero_math_random(self) -> None:
        raw = (SCRIPTS / "pixelfx_engine.mjs").read_text(encoding="utf-8")
        code_only = re.sub(r"/\*[\s\S]*?\*/|//[^\n]*", "", raw)
        for forbidden in ("node:http", "node:https", "node:net", "child_process", "fetch(", "Math.random", "patch.gg", "curl "):
            self.assertNotIn(forbidden, code_only)

    def test_list_and_check_all_builtin_effects_pass(self) -> None:
        p_list = subprocess.run(
            ["node", str(SCRIPTS / "pixelfx_engine.mjs"), "list"],
            capture_output=True,
            text=True,
            check=True,
        )
        listed = json.loads(p_list.stdout)
        self.assertGreaterEqual(len(listed["effects"]), 6)
        self.assertIn("fire", listed["palettes"])

        p_check = subprocess.run(
            ["node", str(SCRIPTS / "pixelfx_engine.mjs"), "check"],
            capture_output=True,
            text=True,
            check=True,
        )
        checked = json.loads(p_check.stdout)
        self.assertEqual(checked["failed"], 0)
        self.assertEqual(checked["passed"], len(listed["effects"]))

    def test_render_sheet_produces_valid_png_aseprite_json_and_deterministic_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out1 = Path(tmp) / "run1"
            out2 = Path(tmp) / "run2"
            for out_dir in (out1, out2):
                proc = subprocess.run(
                    [
                        "node",
                        str(SCRIPTS / "pixelfx_engine.mjs"),
                        "render",
                        "ice/frost-nova",
                        "--palette",
                        "arcane",
                        "--seed",
                        "7",
                        "--scale",
                        "2",
                        "--sheet",
                        "--out",
                        str(out_dir),
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                self.assertEqual(json.loads(proc.stdout)["status"], "RENDERED")

            sheet1 = (out1 / "ice" / "frost-nova" / "frost-nova.png").read_bytes()
            sheet2 = (out2 / "ice" / "frost-nova" / "frost-nova.png").read_bytes()
            self.assertEqual(sheet1, sheet2, "Same seed must produce bit-for-bit identical PNG")
            self.assertTrue(sheet1.startswith(b"\x89PNG\r\n\x1a\n"))
            w, h = struct.unpack(">II", sheet1[16:24])
            self.assertGreater(w, 0)
            self.assertGreater(h, 0)

            atlas = json.loads((out1 / "ice" / "frost-nova" / "frost-nova.json").read_text(encoding="utf-8"))
            self.assertEqual(atlas["meta"]["pixelfx"]["id"], "ice/frost-nova")
            self.assertEqual(atlas["meta"]["pixelfx"]["palette"], "arcane")
            self.assertEqual(atlas["meta"]["pixelfx"]["seed"], 7)
            self.assertIn("act", atlas["meta"]["pixelfx"])
            self.assertEqual(atlas["meta"]["size"], {"w": w, "h": h})

    def test_rejects_unknown_effect_and_palette(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                ["node", str(SCRIPTS / "pixelfx_engine.mjs"), "render", "nope/missing", "--out", tmp],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(proc.returncode, 0)

    def test_render_preview_emits_offline_self_contained_html_player(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                [
                    "node",
                    str(SCRIPTS / "pixelfx_engine.mjs"),
                    "render",
                    "fire/torch",
                    "--preview",
                    "--scale",
                    "4",
                    "--out",
                    tmp,
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["status"], "RENDERED")
            preview_path = Path(tmp) / "fire" / "torch" / "preview.html"
            self.assertTrue(preview_path.is_file())
            html_text = preview_path.read_text(encoding="utf-8")
            self.assertIn("data:image/png;base64,", html_text)
            self.assertIn("image-rendering: pixelated", html_text)
            self.assertIn('id="play-btn"', html_text)
            self.assertNotIn("http://", html_text)
            self.assertNotIn("https://", html_text)


if __name__ == "__main__":
    unittest.main()
