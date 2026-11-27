"""Claude Code PreToolUse hook: enforce the Shadow Army's hard rules on shell commands.

It reads the hook JSON from stdin. For a Bash or PowerShell call whose command publishes,
destroys or escapes scope, it prints a PreToolUse decision:

* "ask": the user must confirm. Used for git commit/push/merge/rebase/reset --hard/clean,
  recursive deletes, global installs, infrastructure destroys, destructive SQL and blanket
  process kills. These need the Monarch's explicit approval, which the prompt collects.
* "deny": never allowed. Used for piping a downloaded script into a shell, and for recursive
  deletes of the filesystem root or home directory.

Every other command produces no output, so the normal permission flow applies. Malformed
input also produces no output: the hook never approves anything by itself.

Activate it in settings.json (see docs/claude-code-hooks.example.json); it is not enabled by
installing the skill.
"""

from __future__ import annotations

import json
import re
import shlex
import sys

SEGMENT_SPLIT = re.compile(r"\s*(?:&&|\|\||;|\|)\s*")
GIT_ASK = {
    "push": "publishes commits", "commit": "creates a commit", "merge": "merges branches",
    "rebase": "rewrites history", "cherry-pick": "rewrites history", "am": "applies patches as commits",
}
SQL_DESTRUCTIVE = re.compile(r"\b(?:DROP\s+(?:TABLE|DATABASE|SCHEMA)|TRUNCATE\s+TABLE?|DELETE\s+FROM\s+\w+\s*(?:;|$|'|\"))", re.IGNORECASE)
REMOTE_PIPE = re.compile(r"\b(?:curl|wget|iwr|Invoke-WebRequest|irm|Invoke-RestMethod)\b[^|]*\|\s*(?:sh|bash|zsh|iex|Invoke-Expression|python\d?|node)\b", re.IGNORECASE)
ROOT_DELETE = re.compile(r"\brm\s+-[a-z]*r[a-z]*f?[a-z]*\s+(?:/|~|\$HOME|/\*)(?:\s|$)", re.IGNORECASE)
BLANKET_KILL = re.compile(
    r"\btaskkill\b.*\s/IM\s+(?:node|python|java|claude)\S*|\bpkill\s+(?:-f\s+)?(?:node|python|java)\b|"
    r"\bkillall\s+(?:node|python|java)\b|\bStop-Process\b.*-Name\s+(?:node|python|java)\b",
    re.IGNORECASE,
)


def _words(segment: str) -> list[str]:
    try:
        return shlex.split(segment, posix=True)
    except ValueError:
        return segment.split()


def _git_reason(words: list[str]) -> str | None:
    sub: str | None = None
    rest = iter(words[1:])
    for word in rest:
        if word in {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}:
            next(rest, None)  # these global options take a value
            continue
        if word.startswith("-"):
            continue
        sub = word
        break
    if sub in GIT_ASK:
        return f"git {sub} {GIT_ASK[sub]}"
    if sub == "reset" and "--hard" in words:
        return "git reset --hard discards local work"
    if sub == "clean" and any(re.fullmatch(r"-[a-zA-Z]*f[a-zA-Z]*", word) for word in words):
        return "git clean -f deletes untracked files"
    if sub == "checkout" and "--" in words:
        return "git checkout -- discards local changes"
    if sub == "branch" and any(word in {"-D", "--delete", "-d"} for word in words):
        return "git branch delete removes a branch"
    if sub == "tag" and any(word in {"-d", "--delete"} for word in words):
        return "git tag delete removes a tag"
    if sub == "stash" and any(word in {"drop", "clear"} for word in words):
        return "git stash drop/clear deletes saved work"
    return None


def _segment_reason(segment: str) -> str | None:
    words = _words(segment)
    if not words:
        return None
    head = words[0].rsplit("/", 1)[-1].rsplit("\\", 1)[-1].lower().removesuffix(".exe")
    if head == "git":
        return _git_reason(words)
    if head in {"rm", "rmdir"} and any(re.fullmatch(r"-[a-zA-Z]*[rR][a-zA-Z]*", word) for word in words[1:]):
        return "recursive delete"
    if head in {"remove-item", "rd", "del"} and any(word.lower() in {"-recurse", "/s"} for word in words[1:]):
        return "recursive delete"
    if head in {"npm", "pnpm", "yarn"} and any(word in {"-g", "--global", "global"} for word in words[1:]):
        return "global package install changes the machine"
    if head in {"pip", "pip3"} and "install" in words and "--user" not in words and not any(
        word in {"-r", "-e", "."} for word in words
    ):
        return "pip install adds a dependency; confirm the package and environment"
    if head == "docker" and len(words) > 1 and (
        (words[1] == "system" and "prune" in words) or (words[1] in {"volume", "image", "network"} and "prune" in words)
        or (words[1] == "volume" and "rm" in words)
    ):
        return "docker prune/volume removal deletes shared data"
    if head == "terraform" and len(words) > 1 and words[1] in {"apply", "destroy", "import"}:
        return f"terraform {words[1]} changes infrastructure"
    if head == "kubectl" and len(words) > 1 and words[1] in {"delete", "apply", "replace", "drain", "scale"}:
        return f"kubectl {words[1]} changes a cluster"
    if head in {"psql", "mysql", "sqlite3", "sqlcmd"} and SQL_DESTRUCTIVE.search(segment):
        return "destructive SQL"
    return None


def decide(payload: object) -> dict[str, object] | None:
    """Return the hook output for one PreToolUse payload, or None to stay silent."""
    if not isinstance(payload, dict) or payload.get("hook_event_name", "PreToolUse") != "PreToolUse":
        return None
    if payload.get("tool_name") not in {"Bash", "PowerShell"}:
        return None
    tool_input = payload.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(command, str) or not command.strip():
        return None
    if REMOTE_PIPE.search(command) or ROOT_DELETE.search(command):
        return _output("deny", "Shadow guard: piping a downloaded script into a shell, or deleting the root/home directory, is never allowed.")
    if BLANKET_KILL.search(command):
        return _output("ask", "Shadow guard: a blanket process kill can stop other projects and live MCP sessions. Kill by PID or port instead, or confirm.")
    reasons = [reason for segment in SEGMENT_SPLIT.split(command) if (reason := _segment_reason(segment))]
    if reasons:
        unique = list(dict.fromkeys(reasons))
        return _output("ask", "Shadow guard: " + "; ".join(unique) + ". This needs the Monarch's explicit approval for this task.")
    return None


def _output(decision: str, reason: str) -> dict[str, object]:
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": decision, "permissionDecisionReason": reason,
    }}


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "null")
    except json.JSONDecodeError:
        return 0
    result = decide(payload)
    if result is not None:
        sys.stdout.write(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
