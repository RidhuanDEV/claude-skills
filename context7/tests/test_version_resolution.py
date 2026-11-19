from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


def resolve_workspace_dependency_major(workspace_root: Path, package_name: str) -> dict[str, object]:
    pkg_json = workspace_root / "package.json"
    if not pkg_json.exists():
        return {"status": "UNRESOLVED", "package": package_name, "major": None}
    data = json.loads(pkg_json.read_text(encoding="utf-8"))
    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
    raw_ver = deps.get(package_name)
    if not raw_ver:
        return {"status": "NOT_INSTALLED", "package": package_name, "major": None}
    digits = "".join(ch if ch.isdigit() or ch == "." else " " for ch in str(raw_ver)).split()
    major = int(digits[0].split(".")[0]) if digits else None
    return {"status": "RESOLVED", "package": package_name, "raw": raw_ver, "major": major}


class Context7VersionResolutionTests(unittest.TestCase):
    def test_c02_multi_major_workspaces_stay_isolated_without_cross_major_mixing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ws_v14 = root / "legacy-web"
            ws_v15 = root / "modern-web"
            ws_v14.mkdir()
            ws_v15.mkdir()
            (ws_v14 / "package.json").write_text(json.dumps({"dependencies": {"next": "^14.2.15"}}), encoding="utf-8")
            (ws_v15 / "package.json").write_text(json.dumps({"dependencies": {"next": "^15.1.0"}}), encoding="utf-8")

            r14 = resolve_workspace_dependency_major(ws_v14, "next")
            r15 = resolve_workspace_dependency_major(ws_v15, "next")
            self.assertEqual(r14["major"], 14)
            self.assertEqual(r15["major"], 15)
            self.assertNotEqual(r14["major"], r15["major"])


if __name__ == "__main__":
    unittest.main()
