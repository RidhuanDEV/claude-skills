"""Replay the same decision probes against a Git revision and the working tree."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ROUTER = "shadow-monarch/scripts/skill_router.py"


def evaluate(path, arguments):
    run = subprocess.run([sys.executable, str(path), *arguments], capture_output=True, text=True, encoding="utf-8")
    if run.returncode:
        raise RuntimeError(run.stderr or run.stdout)
    return json.loads(run.stdout)


def routing_cases(router):
    cases = [
        ("Bootstrap a new project for an offline CLI.", True),
        ("Adjust Bootstrap CSS spacing in existing project.", False),
    ]
    results = []
    for prompt, expected in cases:
        record = evaluate(router, ["--route", prompt])["routing_decision"]
        observed = record.get("primary_skill") == "shadow-bootstrap"
        results.append({"prompt": prompt, "expected_bootstrap": expected, "observed_primary": record["primary_skill"], "pass": expected == observed})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", default="HEAD")
    args = parser.parse_args()
    revision = subprocess.check_output(["git", "rev-parse", "--verify", args.baseline + "^{commit}"], cwd=ROOT, text=True).strip()
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "skill_router.py"
        path.write_bytes(subprocess.check_output(["git", "show", revision + ":" + ROUTER], cwd=ROOT))
        before = routing_cases(path)
    after = routing_cases(ROOT / ROUTER)
    print(json.dumps({"baseline_revision": revision, "baseline": before, "candidate": after}, indent=2))
    return 0 if all(case["pass"] for case in after) else 1


if __name__ == "__main__":
    sys.exit(main())
