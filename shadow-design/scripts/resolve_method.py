"""Resolve a design method to packaged evidence and an owner without side effects."""
import argparse
import hashlib
import json
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
FLOWS = ("ai-chat", "app-shell", "auth", "checkout", "empty-states", "errors", "forms",
         "navigation", "onboarding", "paywall", "permissions", "search", "settings", "sharing", "tables")
CHAPTERS = ("discovery-and-evidence", "story-to-flow", "state-machine-and-edge-cases",
            "information-architecture-and-patterns", "existing-system-guardian",
            "accessibility-responsive-content", "privacy-security-and-ethics", "async-and-ai-ux",
            "ux-evaluation-and-gates", "handoff-and-measurement", "external-projects-and-trust")


def resolve_method(method, *, decision=None, flows=(), chapter=None, output="chat", package=PACKAGE):
    """Only return references which match the trusted, installed provenance manifest."""
    package = Path(package).resolve()
    methods = json.loads((package / "references/methods.json").read_text(encoding="utf-8"))
    matches = [row for row in methods if row["method"] == method]
    if not matches:
        return {"status": "UNSUPPORTED", "method": method}
    if len(matches) > 1 and decision is None:
        return {"status": "NEEDS_DECISION", "method": method,
                "choices": [row["decision"] for row in matches]}
    selected = [row for row in matches if decision is None or row["decision"] == decision]
    if len(selected) != 1:
        return {"status": "UNSUPPORTED", "method": method, "decision": decision}
    row = selected[0]
    result = {key: row[key] for key in ("method", "decision", "owner", "evidence", "procedure", "acceptance")}
    if output not in ("chat", "html") or (chapter and method != "ai-product-designer") or (flows and method != "userflow"):
        return {**result, "status": "UNSUPPORTED", "reason": "Option does not apply to this method"}
    if output == "html" and method != "userflow":
        return {**result, "status": "UNSUPPORTED", "reason": "HTML option applies to userflow"}
    if chapter is not None and chapter not in CHAPTERS:
        return {**result, "status": "UNSUPPORTED", "reason": "Unknown chapter"}
    if any(flow not in FLOWS for flow in flows):
        return {**result, "status": "UNSUPPORTED", "reason": "Unknown flow"}
    manifest = json.loads((package / "UPSTREAM_PROVENANCE.json").read_text(encoding="utf-8-sig"))
    pinned = {record["vendored_path"]: record for record in manifest["files"]}
    paths = [row["path"]]
    if method == "ai-product-designer" and chapter:
        index = CHAPTERS.index(chapter) + 1
        paths.append((Path(row["path"]).parent / f"{index:02d}-{chapter}.md").as_posix())
    if method == "userflow":
        if not flows:
            return {**result, "status": "NEEDS_DECISION", "choices": FLOWS}
        directory = Path(row["path"]).parents[1].as_posix()
        paths.extend(f"{directory}/flow-{flow}/SKILL.md" for flow in dict.fromkeys(flows))
    resources = []
    for relative in paths:
        record = pinned.get(relative)
        source = (package / relative).resolve()
        if not source.is_relative_to(package) or not record or record.get("status") != "SAFE" or not source.is_file():
            return {**result, "status": "UNAVAILABLE", "resource": relative}
        actual = hashlib.sha256(source.read_bytes()).hexdigest()
        if actual != record["sha256"]:
            return {**result, "status": "UNAVAILABLE", "resource": relative, "reason": "Pin mismatch"}
        pack = manifest["vendored_packs"][record["pack_name"]]
        resources.append({"path": relative, "package": record["pack_name"], "revision": pack["git_commit"],
                          "sha256": actual})
    result["provenance"] = resources
    if row.get("handoff"):
        sibling = package.parent / row["owner"] / "SKILL.md"
        if not sibling.is_file():
            return {**result, "status": "UNAVAILABLE", "reason": "Engineering owner not installed"}
        return {**result, "status": "HANDOFF", "read": [f"../{row['owner']}/SKILL.md"]}
    if method == "userflow" and output == "html":
        # Only audited Markdown and license files are shipped in the T1 flow pack.
        return {**result, "status": "NEEDS_DECISION", "reason": "No verified HTML template in this package",
                "choices": ["Use a compatible project template", "Return the flow in chat"]}
    read = paths[1:] if len(paths) > 1 else paths
    return {**result, "status": "READY", "read": read}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("method", help="Method name from the design skill")
    parser.add_argument("--decision", help="Outcome sought when two providers use the same method name")
    parser.add_argument("--flow", action="append", choices=FLOWS, default=[])
    parser.add_argument("--chapter", choices=CHAPTERS)
    parser.add_argument("--output", choices=("chat", "html"), default="chat")
    args = parser.parse_args()
    try:
        report = resolve_method(args.method, decision=args.decision, flows=args.flow,
                                chapter=args.chapter, output=args.output)
    except (KeyError, ValueError, OSError, TypeError) as error:
        report = {"status": "UNAVAILABLE", "reason": str(error)}
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if report["status"] in ("READY", "HANDOFF") else 2


if __name__ == "__main__":
    raise SystemExit(main())
