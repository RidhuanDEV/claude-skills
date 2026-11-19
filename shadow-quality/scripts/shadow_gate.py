#!/usr/bin/env python3
"""
Shadow Gate (shadow_gate.py) — Deterministic Cross-Model Quality & Rigor Gate

Runs identical static checks regardless of which AI model (Claude, Codex, Gemini, Antigravity)
wrote the code:
1. Strict TypeScript discipline (no `any`, no `as Type` casts except `as const`, no `@ts-ignore`/`@ts-expect-error`)
2. Secret leak detection (private keys, AWS/GitHub/Google/Slack tokens)
3. Heuristic/Regex probe reminder (Rigor Protocol Rule 22 check when regexes change without test updates)
4. Brownfield architecture & convention drift (`codebase_intelligence.py audit_convention_drift`)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from codebase_intelligence import audit_convention_drift, discover_codebase  # noqa: E402

TS_ANY_RE = re.compile(r"(:\s*any\b|<any>|\bas\s+any\b|\bArray<any>)")
TS_CAST_RE = re.compile(r"\bas\s+(?!const\b)[A-Z][A-Za-z0-9_<>,\s|&]*")
TS_SUPPRESS_RE = re.compile(r"@ts-(ignore|expect-error)\b")

SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Private Key Header", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("AWS Access Key ID", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub Personal/App Token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{36,}\b")),
    ("Google API Key", re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b")),
    ("Slack Token", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b")),
]

HEURISTIC_REGEX_RE = re.compile(r"\b(re\.compile|re\.search|re\.match|new\s+RegExp)\s*\(")
TEST_FILE_RE = re.compile(r"((?:^|[/\\])test_|_test\.|\.test\.|\.spec\.|tests?[/\\]|evals\.json)", re.IGNORECASE)
DOCKER_SCRIPT_PATH_RE = re.compile(r"(test|spec|migration|drill|verify)", re.IGNORECASE)
EPHEMERAL_CONTAINER_RE = re.compile(
    r"(?:^|[-_])(?:test-\d{6,}|migration-verification|restore-drill|db-restore-drill|test-db-\d+)(?:$|[-_])",
    re.IGNORECASE,
)
DOCKER_RUN_CMD_RE = re.compile(r"^\s*(?:sudo\s+)?docker\s+run\b(?P<args>[^\n;]*)", re.MULTILINE)
DOCKER_COMPOSE_UP_RE = re.compile(r"^\s*(?:sudo\s+)?docker(?:\s+compose|-compose)\b[^\n;]*\bup\b", re.MULTILINE)
DOCKER_BUILD_TAG_RE = re.compile(r"^\s*(?:sudo\s+)?docker\s+build\b[^\n;]*\s+-t\s+(?P<tag>\S+)", re.MULTILINE)


def get_git_modified_files(repo_root: Path) -> list[Path]:
    """Return modified and untracked files from git status, or empty list if not a git repo."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if proc.returncode != 0:
            return []
        files: list[Path] = []
        for raw_line in proc.stdout.splitlines():
            if len(raw_line) < 4:
                continue
            rel_part = raw_line[3:].strip()
            if " -> " in rel_part:
                rel_part = rel_part.split(" -> ", 1)[1].strip()
            rel_part = rel_part.strip('"')
            candidate = (repo_root / rel_part).resolve()
            if candidate.is_file():
                files.append(candidate)
        return files
    except Exception:
        return []


def is_comment_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*") or stripped.startswith("#")


def check_strict_typescript(file_path: Path, rel_path: str) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    if file_path.suffix not in (".ts", ".tsx") or file_path.name.endswith(".d.ts"):
        return violations

    try:
        lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return violations

    for idx, line in enumerate(lines, start=1):
        if TS_SUPPRESS_RE.search(line):
            violations.append({
                "severity": "CRITICAL",
                "code": "STRICT_TYPING_SUPPRESS",
                "file": f"{rel_path}:{idx}",
                "message": "Compiler suppression (`@ts-ignore` / `@ts-expect-error`) is forbidden.",
                "corrective_action": "Fix the underlying type mismatch instead of suppressing the compiler.",
            })
        if is_comment_line(line):
            continue
        code_part = line.split("//", 1)[0]
        if TS_ANY_RE.search(code_part):
            violations.append({
                "severity": "CRITICAL",
                "code": "STRICT_TYPING_ANY",
                "file": f"{rel_path}:{idx}",
                "message": "Explicit `any` is forbidden by Shadow Army strict typing rules.",
                "corrective_action": "Define an explicit interface/type, or use `unknown` at external boundaries with immediate narrowing.",
            })
        if TS_CAST_RE.search(code_part):
            violations.append({
                "severity": "HIGH",
                "code": "STRICT_TYPING_CAST",
                "file": f"{rel_path}:{idx}",
                "message": "Type assertion (`as Type`) is forbidden (only `as const` is allowed).",
                "corrective_action": "Use a type guard, schema validator, or explicit generic return type instead of casting.",
            })
    return violations


def check_secrets(file_path: Path, rel_path: str) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    if file_path.suffix in (".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".ttf", ".zip", ".pdf", ".docx"):
        return violations
    if TEST_FILE_RE.search(rel_path):
        return violations

    try:
        lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return violations

    for idx, line in enumerate(lines, start=1):
        for label, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                violations.append({
                    "severity": "CRITICAL",
                    "code": "SECRET_LEAK_DETECTED",
                    "file": f"{rel_path}:{idx}",
                    "message": f"Potential hardcoded secret detected ({label}).",
                    "corrective_action": "Move credentials to environment variables or secret manager and rotate if exposed.",
                })
    return violations


def check_docker_test_cleanup(file_path: Path, rel_path: str) -> list[dict[str, Any]]:
    """Verify test/migration/drill scripts tear down ephemeral Docker containers, volumes, and temp images."""
    violations: list[dict[str, Any]] = []
    if file_path.name == "shadow_gate.py":
        return violations
    if file_path.suffix not in (".sh", ".ps1", ".py", ".ts", ".js", ".mjs"):
        return violations
    if not DOCKER_SCRIPT_PATH_RE.search(rel_path):
        return violations

    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return violations

    has_docker_rm = bool(re.search(r"\bdocker\s+(?:container\s+)?rm\b", content))
    has_compose_down = bool(re.search(r"\bdocker(?:\s+compose|-compose)\b[\s\S]*?\bdown\b", content))
    has_image_rm = bool(re.search(r"\bdocker\s+(?:image\s+rm|rmi)\b|--rmi\s+(?:local|all)", content))

    for match in DOCKER_RUN_CMD_RE.finditer(content):
        args_str = match.group("args")
        if "--rm" not in args_str and not has_docker_rm:
            violations.append({
                "severity": "HIGH",
                "code": "DOCKER_TEST_MISSING_CLEANUP",
                "file": rel_path,
                "message": "Test/migration script runs `docker run` without `--rm` and without `docker rm -f -v` teardown.",
                "corrective_action": "Add `--rm --label shadow.ephemeral=true` and wrap in `try/finally` (`trap EXIT`) calling `docker rm -f -v <container>`.",
            })
            break

    if DOCKER_COMPOSE_UP_RE.search(content) and not has_compose_down:
        violations.append({
            "severity": "HIGH",
            "code": "DOCKER_TEST_MISSING_CLEANUP",
            "file": rel_path,
            "message": "Test/migration script runs `docker compose up` without a matching `docker compose down -v --rmi local --remove-orphans` teardown.",
            "corrective_action": "Add `docker compose -p <project>-test down -v --rmi local --remove-orphans` in a `finally` / `trap EXIT` block.",
        })

    if DOCKER_BUILD_TAG_RE.search(content) and not has_image_rm:
        violations.append({
            "severity": "HIGH",
            "code": "DOCKER_TEST_IMAGE_MISSING_CLEANUP",
            "file": rel_path,
            "message": "Test/migration script builds a Docker image (`docker build -t ...`) without removing it after test completion.",
            "corrective_action": "Remove temporary test images in `finally` / `trap EXIT` via `docker image rm -f <tag>` or `docker compose down --rmi local`.",
        })

    return violations


DOCKER_INSPECT_FORMAT = (
    '{"id":{{json .Id}},"name":{{json .Name}},"image":{{json .Config.Image}},'
    '"status":{{json .State.Status}},"ephemeral":{{json (index .Config.Labels "shadow.ephemeral")}},'
    '"repo":{{json (index .Config.Labels "shadow.repo")}},"run":{{json (index .Config.Labels "shadow.run")}}}'
)


def docker_command(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=8, check=False)


def inspect_owned_container(cid: str, repo_label: str, run_id: str) -> dict[str, str] | None:
    proc = docker_command("container", "inspect", "--format", DOCKER_INSPECT_FORMAT, cid)
    if proc.returncode:
        error = proc.stderr.strip().lower().removeprefix("error response from daemon: ").removeprefix("error: ")
        if error in {f"no such container: {cid}", f"no such object: {cid}"}:
            return None
        raise ValueError(f"Cannot inspect container {cid}.")
    row = json.loads(proc.stdout)
    if (not isinstance(row, dict) or row.get("id") != cid or row.get("repo") != repo_label
            or row.get("run") != run_id or row.get("ephemeral") != "true"):
        raise ValueError(f"Ownership mismatch for container {cid}.")
    if not all(isinstance(row.get(k), str) and row[k] for k in ("name", "image", "status")):
        raise ValueError(f"Incomplete inspection of container {cid}.")
    return {"id": cid, "name": row["name"].lstrip("/"), "image": row["image"], "status": row["status"]}


def inspect_or_cleanup_docker_leaks(
    cleanup: bool = False, *, repo_root: Path | None = None,
    run_id: str | None = None, ledger_path: Path | None = None,
) -> dict[str, Any]:
    """Check resources recorded by the selected job against immutable Docker IDs and labels."""
    leaked: list[dict[str, str]] = []
    cleaned: list[str] = []
    report: dict[str, Any] = {"status": "BLOCKED", "docker_available": None, "leaked_count": 0,
              "leaked_containers": leaked, "cleaned_count": 0, "cleaned_containers": cleaned,
              "remaining_count": 0, "errors": []}
    if run_id is None and ledger_path is None and not cleanup:
        report.update(status="NOT_RUN", reason="No Docker run selected; container ownership was not measured.")
        return report
    try:
        if repo_root is None or ledger_path is None or not run_id or not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", run_id):
            raise ValueError("Provide a repository, run ID and trusted ledger for this job.")
        repo_label = repo_root.resolve(strict=True).as_posix()
        ledger = json.loads(ledger_path.read_text(encoding="utf-8-sig"))
        if (not isinstance(ledger, dict) or type(ledger.get("version")) is not int
                or ledger["version"] != 1 or ledger.get("repo") != repo_label or ledger.get("run_id") != run_id):
            raise ValueError("Ledger version, canonical repository or run ID mismatch.")
        ids = ledger.get("container_ids")
        if not isinstance(ids, list) or not all(isinstance(cid, str) and re.fullmatch(r"[0-9a-f]{64}", cid) for cid in ids):
            raise ValueError("Ledger must contain a list of full lowercase Docker container IDs.")
        report["docker_available"] = False
        proc = docker_command("ps", "-a", "--no-trunc", "--filter", f"label=shadow.repo={repo_label}",
                              "--filter", f"label=shadow.run={run_id}", "--format", "{{.ID}}")
        if proc.returncode:
            raise ValueError("Docker inventory unavailable.")
        report["docker_available"] = True
        unregistered = set(proc.stdout.splitlines()) - set(ids)
        if unregistered:
            raise ValueError("Run inventory has containers missing from its ledger; reconcile ownership before cleanup.")
        for cid in sorted(set(ids)):
            row = inspect_owned_container(cid, repo_label, run_id)
            if row is not None:
                leaked.append(row)
                report["remaining_count"] = len(leaked)
        remaining = {row["id"] for row in leaked}
        report["remaining_count"] = len(remaining)
        if cleanup:
            for row in leaked:
                if row["status"] not in {"exited", "dead"}:
                    continue
                cid = row["id"]
                current = inspect_owned_container(cid, repo_label, run_id)
                if current is None:
                    remaining.discard(cid)
                elif current["status"] in {"exited", "dead"}:
                    # Non-forced removal refuses a container restarted since the final inspection.
                    if docker_command("rm", cid).returncode:
                        raise ValueError(f"Removal of {cid} was not confirmed; inspect the same run again.")
                    cleaned.append(row["name"])
                    remaining.discard(cid)
                report["remaining_count"] = len(remaining)
        report["status"] = "FAIL" if remaining else "PASS"
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        report["errors"].append(str(exc))
    report.update(leaked_count=len(leaked), cleaned_count=len(cleaned))
    return report


def run_shadow_gate(
    repo_root: Path,
    changed_files: list[Path] | None = None,
    probes_verified: bool = False,
) -> dict[str, Any]:
    root = repo_root.resolve()
    files = changed_files if changed_files is not None else get_git_modified_files(root)

    violations: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    has_test_file = any(
        TEST_FILE_RE.search(str(f.relative_to(root)) if f.is_relative_to(root) else f.name)
        for f in files
    )
    heuristic_files: list[str] = []

    for f in files:
        if not f.is_file():
            continue
        rel = str(f.relative_to(root)) if f.is_relative_to(root) else str(f)
        violations.extend(check_strict_typescript(f, rel))
        violations.extend(check_secrets(f, rel))
        violations.extend(check_docker_test_cleanup(f, rel))

        if f.suffix in (".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".php") and not TEST_FILE_RE.search(rel):
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
                if HEURISTIC_REGEX_RE.search(text):
                    heuristic_files.append(rel)
            except Exception:
                pass

    if heuristic_files and not has_test_file and not probes_verified:
        warnings.append({
            "severity": "MEDIUM",
            "code": "UNPROBED_HEURISTIC_CHANGE",
            "files": heuristic_files,
            "message": "Regex/heuristic patterns detected in modified code without accompanying test file changes.",
            "corrective_action": "Execute Rigor Protocol Rule 22: run >=5 precision probes (must NOT match) and >=3 recall probes (MUST match), add negative test cases, or pass --probes-verified after pasting probe output.",
        })

    if files:
        profile = discover_codebase(root)
        drift_result = audit_convention_drift(root, files, profile)
        violations.extend(drift_result.get("violations", []))

    approval_gate_verified: bool | None = None
    approval_gate_script = root / "shadow-monarch" / "scripts" / "execution_approval_gate.py"
    if approval_gate_script.is_file():
        try:
            proc = subprocess.run(
                [sys.executable, str(approval_gate_script), "--self-test"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            gate_data = json.loads(proc.stdout) if proc.returncode == 0 and proc.stdout.strip() else {}
            approval_gate_verified = proc.returncode == 0 and bool(gate_data.get("all_passed"))
            if not approval_gate_verified:
                violations.append({
                    "severity": "CRITICAL",
                    "code": "EXECUTION_APPROVAL_GATE_FAILURE",
                    "file": "shadow-monarch/scripts/execution_approval_gate.py",
                    "message": "Execution approval gate negative/positive self-test failed.",
                    "corrective_action": "Fix failing L0-L4 boundary checks in `execution_approval_gate.py --self-test`.",
                })
        except Exception as exc:
            approval_gate_verified = False
            violations.append({
                "severity": "CRITICAL",
                "code": "EXECUTION_APPROVAL_GATE_ERROR",
                "file": "shadow-monarch/scripts/execution_approval_gate.py",
                "message": f"Failed executing approval gate self-test: {exc}",
                "corrective_action": "Inspect Python execution environment and `execution_approval_gate.py`.",
            })

    official_first_verified: bool | None = None
    official_first_script = root / "shadow-monarch" / "scripts" / "official_first_verifier.py"
    if official_first_script.is_file():
        try:
            proc_of = subprocess.run(
                [sys.executable, str(official_first_script), "--self-test"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            of_data = json.loads(proc_of.stdout) if proc_of.returncode == 0 and proc_of.stdout.strip() else {}
            official_first_verified = proc_of.returncode == 0 and bool(of_data.get("all_passed"))
            if not official_first_verified:
                violations.append({
                    "severity": "CRITICAL",
                    "code": "OFFICIAL_FIRST_VERIFIER_FAILURE",
                    "file": "shadow-monarch/scripts/official_first_verifier.py",
                    "message": "Official-first / dependency verification self-test failed.",
                    "corrective_action": "Fix failing checks in `official_first_verifier.py --self-test`.",
                })
        except Exception as exc:
            official_first_verified = False
            violations.append({
                "severity": "CRITICAL",
                "code": "OFFICIAL_FIRST_VERIFIER_ERROR",
                "file": "shadow-monarch/scripts/official_first_verifier.py",
                "message": f"Failed executing official-first verifier self-test: {exc}",
                "corrective_action": "Inspect Python environment and `official_first_verifier.py`.",
            })

    doc_engine_verified: bool | None = None
    doc_orchestrator_script = root / "shadow-doc" / "scripts" / "doc_orchestrator.py"
    if doc_orchestrator_script.is_file():
        try:
            proc_doc = subprocess.run(
                [sys.executable, str(doc_orchestrator_script), "--self-test"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            doc_data = json.loads(proc_doc.stdout) if proc_doc.returncode == 0 and proc_doc.stdout.strip() else {}
            doc_engine_verified = proc_doc.returncode == 0 and bool(doc_data.get("all_passed"))
            if not doc_engine_verified:
                violations.append({
                    "severity": "CRITICAL",
                    "code": "DOCUMENT_ORCHESTRATOR_GATE_FAILURE",
                    "file": "shadow-doc/scripts/doc_orchestrator.py",
                    "message": "Document orchestrator discovery/safety self-test failed.",
                    "corrective_action": "Fix failing checks in `doc_orchestrator.py --self-test`.",
                })
        except Exception as exc:
            doc_engine_verified = False
            violations.append({
                "severity": "CRITICAL",
                "code": "DOCUMENT_ORCHESTRATOR_GATE_ERROR",
                "file": "shadow-doc/scripts/doc_orchestrator.py",
                "message": f"Failed executing doc orchestrator self-test: {exc}",
                "corrective_action": "Inspect Python environment and `doc_orchestrator.py`.",
            })

    blocking = [v for v in violations if v.get("severity") in ("CRITICAL", "HIGH")]
    passed = len(blocking) == 0

    return {
        "gate": "shadow-gate v1.0",
        "repository": str(root),
        "checked_files_count": len(files),
        "execution_approval_gate_verified": approval_gate_verified,
        "official_first_gate_verified": official_first_verified,
        "document_engine_gate_verified": doc_engine_verified,
        "passed": passed,
        "recommended_max_readiness": "VERIFIED-LOCAL" if passed and not warnings else ("IMPLEMENTED" if passed else "BLOCKED"),
        "blocking_violations_count": len(blocking),
        "total_violations_count": len(violations),
        "warnings_count": len(warnings),
        "violations": violations,
        "warnings": warnings,
    }


def install_pre_commit_hook(repo_root: Path) -> Path:
    hooks_dir = repo_root / ".git" / "hooks"
    if not hooks_dir.parent.exists():
        raise RuntimeError(f"Not a git repository: {repo_root}")
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_path = hooks_dir / "pre-commit"
    script_abs = Path(__file__).resolve().as_posix()
    hook_content = (
        "#!/usr/bin/env sh\n"
        "# Auto-installed by Shadow Army shadow_gate.py\n"
        f'python "{script_abs}" --repo .\n'
    )
    hook_path.write_text(hook_content, encoding="utf-8")
    try:
        hook_path.chmod(0o755)
    except Exception:
        pass
    return hook_path


def run_self_test() -> dict[str, Any]:
    """Run Precision & Recall probes on shadow_gate.py itself (Rigor Protocol Rule 22)."""
    results: list[dict[str, Any]] = []

    def record(name: str, passed: bool, detail: str) -> None:
        results.append({"probe": name, "passed": passed, "detail": detail})

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "package.json").write_text('{"name":"probe-app","dependencies":{"zustand":"^4.5.0"}}', encoding="utf-8")
        (root / "tsconfig.json").write_text('{"compilerOptions":{"strict":true}}', encoding="utf-8")
        src = root / "src"
        src.mkdir()

        # --- PRECISION PROBES (5 realistic inputs that must NOT be flagged as violations) ---
        p1 = src / "clean.ts"
        p1.write_text(
            "// Comment mentioning : any and as User should be ignored\n"
            "export const ROLES = ['admin', 'user'] as const;\n"
            "export function parseInput(raw: unknown): string {\n"
            "  return typeof raw === 'string' ? raw : 'default';\n"
            "}\n",
            encoding="utf-8",
        )
        r1 = run_shadow_gate(root, [p1], probes_verified=True)
        record("PRECISION-1: Clean TypeScript with `unknown`, `as const`, and comments with `: any`", r1["passed"] and r1["total_violations_count"] == 0, json.dumps(r1["violations"]))

        p2 = src / "types.d.ts"
        p2.write_text("declare module 'legacy' { const x: any; export default x; }\n", encoding="utf-8")
        r2 = run_shadow_gate(root, [p2], probes_verified=True)
        record("PRECISION-2: Ambient `.d.ts` declaration file is not flagged", r2["passed"], json.dumps(r2["violations"]))

        p3 = src / "zustandStore.ts"
        p3.write_text("import { create } from 'zustand';\nexport const useStore = create(() => ({ count: 0 }));\n", encoding="utf-8")
        r3 = run_shadow_gate(root, [p3], probes_verified=True)
        record("PRECISION-3: Matching established Zustand store is clean", r3["passed"], json.dumps(r3["violations"]))

        p4 = src / "matcher.py"
        p4_test = src / "test_matcher.py"
        p4.write_text("import re\nPAT = re.compile(r'^[a-z]+$')\n", encoding="utf-8")
        p4_test.write_text("def test_pat(): assert True\n", encoding="utf-8")
        r4 = run_shadow_gate(root, [p4, p4_test], probes_verified=False)
        record("PRECISION-4: Regex change accompanied by test file produces 0 heuristic warnings", r4["warnings_count"] == 0, json.dumps(r4["warnings"]))

        p5 = src / "test_fake_secret.spec.ts"
        ex_key = "AKIA" + "IOSFODNN7EXAMPLE"
        p5.write_text(f"export const FAKE = '{ex_key}';\n", encoding="utf-8")
        r5 = run_shadow_gate(root, [p5], probes_verified=True)
        record("PRECISION-5: Test fixture file with example token is not flagged as production secret leak", r5["passed"], json.dumps(r5["violations"]))

        # --- RECALL PROBES (4 realistic bad inputs that MUST be caught) ---
        rc1 = src / "badAny.ts"
        rc1.write_text("export function handle(payload: any) { return (payload as UserData).id; }\n", encoding="utf-8")
        rr1 = run_shadow_gate(root, [rc1], probes_verified=True)
        codes1 = {v["code"] for v in rr1["violations"]}
        record("RECALL-1: Catches both `: any` and `as UserData` cast in TypeScript", not rr1["passed"] and "STRICT_TYPING_ANY" in codes1 and "STRICT_TYPING_CAST" in codes1, json.dumps( list(codes1) ))

        rc2 = src / "badSuppress.ts"
        rc2.write_text("// @ts-ignore\nexport const x: number = 1;\n", encoding="utf-8")
        rr2 = run_shadow_gate(root, [rc2], probes_verified=True)
        codes2 = {v["code"] for v in rr2["violations"]}
        record("RECALL-2: Catches `@ts-ignore` compiler suppression", not rr2["passed"] and "STRICT_TYPING_SUPPRESS" in codes2, json.dumps(list(codes2)))

        rc3 = src / "leakedKey.py"
        ak = "AKIA" + "1234567890ABCDEF"
        rc3.write_text(f"AWS_KEY = '{ak}'\n", encoding="utf-8")
        rr3 = run_shadow_gate(root, [rc3], probes_verified=True)
        codes3 = {v["code"] for v in rr3["violations"]}
        record("RECALL-3: Catches hardcoded AWS Access Key in source file", not rr3["passed"] and "SECRET_LEAK_DETECTED" in codes3, json.dumps(list(codes3)))

        rc4 = src / "unprobedRegex.py"
        rc4.write_text("import re\n_LANJUTAN = re.compile(r'\\\\b\\\\w+nya\\\\b')\n", encoding="utf-8")
        rr4 = run_shadow_gate(root, [rc4], probes_verified=False)
        wcodes4 = {w["code"] for w in rr4["warnings"]}
        record("RECALL-4: Flags unprobed regex heuristic change when no test file is modified", "UNPROBED_HEURISTIC_CHANGE" in wcodes4, json.dumps(list(wcodes4)))

        rc5 = src / "reduxDrift.ts"
        rc5.write_text("import { configureStore } from '@reduxjs/toolkit';\n", encoding="utf-8")
        rr5 = run_shadow_gate(root, [rc5], probes_verified=True)
        codes5 = {v["code"] for v in rr5["violations"]}
        record("RECALL-5: Flags unsolicited Redux store in a Zustand repository", not rr5["passed"] and "UNSOLICITED_STATE_STORE" in codes5, json.dumps(list(codes5)))

        # --- DOCKER TEST CLEANUP PRECISION & RECALL PROBES ---
        p6 = src / "test_db_clean.sh"
        p6.write_text(
            "#!/usr/bin/env bash\n"
            "trap 'docker rm -f -v app-test-db' EXIT\n"
            "docker run -d --rm --label shadow.ephemeral=true --name app-test-db mariadb:10\n",
            encoding="utf-8",
        )
        r6 = run_shadow_gate(root, [p6], probes_verified=True)
        record("PRECISION-6: Test script with `--rm` and `trap docker rm -f -v` is clean", r6["passed"], json.dumps(r6["violations"]))

        non_ephemeral_names = [
            "tejas-v2-app",
            "emanifest-mysql",
            "notulen-api",
            "postgres-latest",
            "contest-service",
            "attestation-worker",
        ]
        false_pos = [n for n in non_ephemeral_names if EPHEMERAL_CONTAINER_RE.search(n)]
        record("PRECISION-7: `EPHEMERAL_CONTAINER_RE` never matches production/dev containers or words containing 'test'", len(false_pos) == 0, json.dumps(false_pos))

        rc6 = src / "verify_migration.sh"
        rc6.write_text(
            "#!/usr/bin/env bash\n"
            "docker run -d --name prpm-prod6nov-test-1793940631107 mariadb:10\n"
            "docker build -t prpm-test:temp .\n",
            encoding="utf-8",
        )
        rr6 = run_shadow_gate(root, [rc6], probes_verified=True)
        codes6 = {v["code"] for v in rr6["violations"]}
        record(
            "RECALL-6: Flags `docker run` without `--rm`/`docker rm` and `docker build -t` without image cleanup in test script",
            not rr6["passed"] and "DOCKER_TEST_MISSING_CLEANUP" in codes6 and "DOCKER_TEST_IMAGE_MISSING_CLEANUP" in codes6,
            json.dumps(list(codes6)),
        )

        ephemeral_names = [
            "prpm-prod6nov-test-1793940631107",
            "prpm-prod6nov-migration-verification",
            "billing-restore-drill-2026",
            "api_test-db-9912",
        ]
        missed = [n for n in ephemeral_names if not EPHEMERAL_CONTAINER_RE.search(n)]
        record("RECALL-7: `EPHEMERAL_CONTAINER_RE` matches leftover test/migration/drill container names", len(missed) == 0, json.dumps(missed))

    all_passed = all(r["passed"] for r in results)
    return {
        "suite": "shadow_gate.py Precision & Recall Self-Test",
        "total_probes": len(results),
        "passed": sum(1 for r in results if r["passed"]),
        "failed": sum(1 for r in results if not r["passed"]),
        "all_passed": all_passed,
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Shadow Gate — Deterministic Multi-Agent Quality & Rigor Gate")
    parser.add_argument("--repo", "--repo-dir", dest="repo", default=".", help="Repository root directory")
    parser.add_argument("--files", "--changed-files", dest="files", nargs="*", default=None, help="Explicit changed files to check")
    parser.add_argument("--probes-verified", action="store_true", help="Confirm Rigor Protocol precision/recall probes were executed")
    parser.add_argument("--check-docker-leaks", action="store_true", help="Check running/stopped Docker containers for leftover test/migration/drill containers")
    parser.add_argument("--cleanup-docker-leaks", action="store_true", help="Remove only ledger-owned terminal containers")
    parser.add_argument("--docker-run-id", help="Job identifier recorded on the container and in its ledger")
    parser.add_argument("--docker-ledger", type=Path, help="Trusted provisioning ledger for the selected Docker job")
    parser.add_argument("--install-hook", action="store_true", help="Install git pre-commit hook in target repository")
    parser.add_argument("--self-test", action="store_true", help="Run precision & recall probe suite on shadow_gate.py")
    args = parser.parse_args()

    if args.self_test:
        summary = run_self_test()
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0 if summary["all_passed"] else 1

    repo_root = Path(args.repo).resolve()
    if args.install_hook:
        hook = install_pre_commit_hook(repo_root)
        print(json.dumps({"status": "installed", "hook": str(hook)}, indent=2))
        return 0

    changed = [Path(f).resolve() for f in args.files] if args.files is not None else None
    report = run_shadow_gate(repo_root, changed, probes_verified=args.probes_verified)

    if args.check_docker_leaks or args.cleanup_docker_leaks:
        docker_report = inspect_or_cleanup_docker_leaks(
            cleanup=args.cleanup_docker_leaks, repo_root=repo_root,
            run_id=args.docker_run_id, ledger_path=args.docker_ledger)
        report["docker_leaks"] = docker_report
        if docker_report["status"] == "NOT_RUN":
            report["warnings"].append({
                "code": "DOCKER_OWNERSHIP_NOT_MEASURED", "severity": "INFO",
                "message": docker_report["reason"],
            })
            report["warnings_count"] += 1
            if report["recommended_max_readiness"] == "VERIFIED-LOCAL":
                report["recommended_max_readiness"] = "IMPLEMENTED"
        elif docker_report["status"] in {"FAIL", "BLOCKED"}:
            report["passed"] = False
            report["recommended_max_readiness"] = "BLOCKED"
            report["blocking_violations_count"] += 1
            report["total_violations_count"] += 1
            report["violations"].append({
                "severity": "HIGH",
                "code": ("DOCKER_EPHEMERAL_CONTAINER_LEAK" if docker_report["status"] == "FAIL"
                         else "DOCKER_OWNERSHIP_CHECK_BLOCKED"),
                "file": "docker-daemon",
                "message": ("; ".join(docker_report["errors"]) or
                            f"{docker_report['remaining_count']} container(s) remain for the selected run."),
                "corrective_action": "Verify run ownership and terminal state using the trusted provisioning ledger.",
            })

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
