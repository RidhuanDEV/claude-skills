#!/usr/bin/env python3
"""
Shadow Monarch Task-Scoped Resource Auditor & Ownership-Safe Cleanup (resource_cleanup.py)

Prevents leftover dev servers, video-env stacks, browser instances, and background workers
without EVER killing foreign project servers or active multi-session host/MCP processes.

Permission Boundaries:
- `--audit`        : L0_READ_ONLY (inspect live processes + listening TCP ports, group MCPs by parent session).
- `--register`     : L1_SAFE_VERIFICATION (record PID + creation fingerprint in task ledger).
- `--cleanup-owned`: L1_SAFE_VERIFICATION (terminate ONLY verified OWNED_BY_TASK PIDs in ledger;
                     fails closed on PID reuse or mismatch; NEVER kills foreign/external sessions).
- `--self-test`    : L0_READ_ONLY deterministic precision & recall probes.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any

HOST_SESSION_RE = re.compile(r"\b(?:claude(?:\.exe)?|codex(?:\.exe)?|antigravity(?:\.exe)?|gemini(?:\.exe)?)\b", re.IGNORECASE)
MCP_SERVER_RE = re.compile(
    r"(?:@playwright/mcp|playwright-mcp|shadow-(?:api|db|handoff)-mcp|context7|work-mcp|mcp-server|[\\/_-]mcp(?:[\\/\s.]|$))",
    re.IGNORECASE,
)
DEV_SERVER_RE = re.compile(
    r"(?:\bvite\b|\bnext\s+dev\b|\bwebpack[- ]dev[- ]server\b|\bnuxt\s+dev\b|\bastro\s+dev\b|"
    r"video-env\.cjs|chrome-cdp\.ts|\buvicorn\b|\bphp\s+artisan\s+serve\b|\bnodemon\b|\btsx\s+watch\b|\bstorybook\b)",
    re.IGNORECASE,
)
DEV_RUNTIME_NAME_RE = re.compile(r"^(?:node|bun|deno|python\d*|ruby|php|go)(?:\.exe)?$", re.IGNORECASE)
BROWSER_HEADLESS_RE = re.compile(r"(?:--headless|ms-playwright|--remote-debugging-port=)", re.IGNORECASE)
PORT_RE = re.compile(r"(?:--port(?:=|\s+)|-p\s+|localhost:|127\.0\.0\.1:)(\d{2,5})", re.IGNORECASE)


def _norm_path(value: str | None) -> str:
    if not value:
        return ""
    return value.replace("\\", "/").rstrip("/").lower()


def _extract_port(cmd: str) -> int | None:
    m = PORT_RE.search(cmd or "")
    if not m:
        return None
    try:
        port = int(m.group(1))
        return port if 1 <= port <= 65535 else None
    except ValueError:
        return None


def _is_dev_listening_port(port: int) -> bool:
    return (3000 <= port <= 5999) or (8000 <= port <= 9999)


def _parse_cim_date(raw: str | None) -> str:
    if not raw:
        return ""
    return str(raw).strip()


def snapshot_listening_ports() -> dict[int, list[int]]:
    """Read-only snapshot mapping owning PID -> sorted listening TCP ports."""
    port_map: dict[int, set[int]] = {}
    if platform.system().lower().startswith("win"):
        ps_cmd = (
            "Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | "
            "ForEach-Object { [PSCustomObject]@{ pid = [int]$_.OwningProcess; port = [int]$_.LocalPort } } | "
            "ConvertTo-Json -Compress"
        )
        try:
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                parsed = json.loads(proc.stdout)
                rows = parsed if isinstance(parsed, list) else [parsed]
                for row in rows:
                    if isinstance(row, dict) and "pid" in row and "port" in row:
                        port_map.setdefault(int(row["pid"]), set()).add(int(row["port"]))
        except (OSError, ValueError, subprocess.SubprocessError):
            return {}
        return {pid: sorted(ports) for pid, ports in port_map.items()}

    try:
        proc = subprocess.run(["ss", "-lptnH"], capture_output=True, text=True, timeout=8)
        if proc.returncode == 0:
            for line in proc.stdout.splitlines():
                pm = re.search(r":(\d{2,5})\s", line)
                pidm = re.search(r"pid=(\d+)", line)
                if pm and pidm:
                    port_map.setdefault(int(pidm.group(1)), set()).add(int(pm.group(1)))
    except (OSError, ValueError, subprocess.SubprocessError):
        return {}
    return {pid: sorted(ports) for pid, ports in port_map.items()}


def snapshot_live_processes() -> list[dict[str, Any]]:
    """Read-only snapshot of live OS processes (Windows CIM / POSIX ps)."""
    if platform.system().lower().startswith("win"):
        ps_cmd = (
            "Get-CimInstance Win32_Process | ForEach-Object { "
            "[PSCustomObject]@{ "
            "pid = [int]$_.ProcessId; "
            "ppid = [int]$_.ParentProcessId; "
            "name = [string]$_.Name; "
            "command = [string]$_.CommandLine; "
            "created_at = if ($_.CreationDate) { $_.CreationDate.ToUniversalTime().ToString('o') } else { '' }; "
            "rss_mb = [math]::Round(($_.WorkingSetSize / 1MB), 1) "
            "} } | ConvertTo-Json -Compress"
        )
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return []
        parsed = json.loads(proc.stdout)
        return parsed if isinstance(parsed, list) else [parsed]

    proc = subprocess.run(
        ["ps", "-eo", "pid=,ppid=,rss=,lstart=,comm=,args="],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if proc.returncode != 0:
        return []
    rows: list[dict[str, Any]] = []
    for line in proc.stdout.splitlines():
        parts = line.strip().split(None, 8)
        if len(parts) < 9:
            continue
        pid_s, ppid_s, rss_s = parts[0], parts[1], parts[2]
        created = " ".join(parts[3:8])
        rest = parts[8]
        name = rest.split()[0]
        try:
            rows.append(
                {
                    "pid": int(pid_s),
                    "ppid": int(ppid_s),
                    "name": name,
                    "command": rest,
                    "created_at": created,
                    "rss_mb": round(int(rss_s) / 1024.0, 1),
                }
            )
        except ValueError:
            continue
    return rows


def load_ledger(ledger_path: Path | None) -> dict[str, Any]:
    if ledger_path is None or not ledger_path.is_file():
        return {"version": 1, "workspace": "", "entries": []}
    data = json.loads(ledger_path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("entries"), list):
        raise ValueError(f"Invalid resource ledger schema: {ledger_path}")
    return data


def save_ledger(ledger_path: Path, ledger: dict[str, Any]) -> None:
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")


def _fingerprint_matches(entry: dict[str, Any], proc: dict[str, Any]) -> bool:
    """Verify PID has NOT been reused by an unrelated process."""
    exp_created = _parse_cim_date(entry.get("created_at"))
    obs_created = _parse_cim_date(proc.get("created_at"))
    if exp_created and obs_created and exp_created != obs_created:
        return False
    hint = str(entry.get("command_hint", "")).strip().lower()
    if hint:
        haystack = f"{proc.get('name', '')} {proc.get('command', '')}".lower()
        if hint not in haystack:
            return False
    return True


def _resolve_ports(pid: int, cmd: str, explicit_port: int | None, listening_ports: dict[int, list[int]]) -> list[int]:
    ports: set[int] = set(listening_ports.get(pid, []))
    if explicit_port:
        ports.add(int(explicit_port))
    cli_port = _extract_port(cmd)
    if cli_port:
        ports.add(cli_port)
    return sorted(ports)


def classify_process_snapshot(
    processes: list[dict[str, Any]],
    ledger: dict[str, Any] | None = None,
    current_workspace: str | None = None,
    listening_ports: dict[int, list[int]] | None = None,
) -> dict[str, Any]:
    """
    Pure classifier separating owned task resources from foreign servers & active host MCP sessions.
    Never marks foreign project servers or active host/MCP sessions as auto_cleanup_allowed.
    """
    by_pid: dict[int, dict[str, Any]] = {int(p["pid"]): p for p in processes if "pid" in p}
    port_map: dict[int, list[int]] = listening_ports or {}
    ledger_entries = (ledger or {}).get("entries", [])
    ledger_by_pid: dict[int, dict[str, Any]] = {int(e["pid"]): e for e in ledger_entries if "pid" in e}
    ws_norm = _norm_path(current_workspace or (ledger or {}).get("workspace", ""))

    owned_alive: list[dict[str, Any]] = []
    owned_already_exited: list[dict[str, Any]] = []
    pid_reused_refused: list[dict[str, Any]] = []
    orphaned_mcp: list[dict[str, Any]] = []
    foreign_servers_keep: list[dict[str, Any]] = []
    workspace_untracked_servers: list[dict[str, Any]] = []
    host_sessions: dict[int, dict[str, Any]] = {}

    # 1. Verify every ledger entry strictly (with PID-reuse protection)
    verified_owned_pids: set[int] = set()
    for pid, entry in ledger_by_pid.items():
        proc = by_pid.get(pid)
        if proc is None:
            owned_already_exited.append({"pid": pid, "kind": entry.get("kind", "unknown"), "label": entry.get("label", "")})
            continue
        if not _fingerprint_matches(entry, proc):
            pid_reused_refused.append(
                {
                    "pid": pid,
                    "kind": entry.get("kind", "unknown"),
                    "classification": "PID_REUSED_DO_NOT_TOUCH",
                    "auto_cleanup_allowed": False,
                    "expected_hint": entry.get("command_hint", ""),
                    "observed_name": proc.get("name", ""),
                    "reason": "PID creation time or command hint mismatch; refusing termination to avoid collateral kill.",
                }
            )
            continue
        verified_owned_pids.add(pid)
        ports = _resolve_ports(pid, str(proc.get("command", "")), entry.get("port"), port_map)
        owned_alive.append(
            {
                "pid": pid,
                "kind": entry.get("kind", "unknown"),
                "label": entry.get("label", ""),
                "port": ports[0] if ports else None,
                "ports": ports,
                "rss_mb": float(proc.get("rss_mb", 0.0)),
                "classification": "OWNED_BY_TASK",
                "auto_cleanup_allowed": True,
                "name": proc.get("name", ""),
            }
        )

    # 2. Identify live host sessions (claude.exe, codex, antigravity, gemini)
    for pid, proc in by_pid.items():
        name = str(proc.get("name", ""))
        cmd = str(proc.get("command", ""))
        if HOST_SESSION_RE.search(name) and not MCP_SERVER_RE.search(cmd):
            host_sessions[pid] = {
                "host_pid": pid,
                "name": name,
                "created_at": proc.get("created_at", ""),
                "host_rss_mb": float(proc.get("rss_mb", 0.0)),
                "mcp_children": [],
                "total_group_rss_mb": float(proc.get("rss_mb", 0.0)),
                "classification": "ACTIVE_HOST_SESSION",
                "auto_cleanup_allowed": False,
            }

    # 3. Walk all remaining processes for MCP servers, dev servers & listening runtimes
    for pid, proc in by_pid.items():
        if pid in verified_owned_pids or pid in host_sessions:
            continue
        ppid = int(proc.get("ppid", 0))
        name = str(proc.get("name", ""))
        cmd = str(proc.get("command", ""))
        rss = float(proc.get("rss_mb", 0.0))

        # Check MCP server ancestry (direct or via cmd.exe/npx/node wrapper)
        if MCP_SERVER_RE.search(cmd) or MCP_SERVER_RE.search(name):
            ancestor = ppid
            found_host: int | None = None
            seen: set[int] = {pid}
            while ancestor and ancestor not in seen and ancestor in by_pid:
                seen.add(ancestor)
                if ancestor in host_sessions:
                    found_host = ancestor
                    break
                ancestor = int(by_pid[ancestor].get("ppid", 0))

            if found_host is not None:
                host_sessions[found_host]["mcp_children"].append(
                    {"pid": pid, "name": name, "rss_mb": rss, "command_excerpt": cmd[:120]}
                )
                host_sessions[found_host]["total_group_rss_mb"] = round(
                    host_sessions[found_host]["total_group_rss_mb"] + rss, 1
                )
            elif ppid not in by_pid:
                orphaned_mcp.append(
                    {
                        "pid": pid,
                        "ppid": ppid,
                        "name": name,
                        "rss_mb": rss,
                        "classification": "ORPHANED_MCP_NO_PARENT",
                        "auto_cleanup_allowed": False,
                        "command_excerpt": cmd[:140],
                        "recommendation": "Parent PID no longer exists; ask Monarch before terminating if unused.",
                    }
                )
            else:
                foreign_servers_keep.append(
                    {
                        "pid": pid,
                        "ppid": ppid,
                        "name": name,
                        "rss_mb": rss,
                        "classification": "ACTIVE_EXTERNAL_MCP",
                        "auto_cleanup_allowed": False,
                        "command_excerpt": cmd[:120],
                    }
                )
            continue

        os_ports = port_map.get(pid, [])
        is_listening_dev_runtime = bool(
            DEV_RUNTIME_NAME_RE.match(name) and any(_is_dev_listening_port(pt) for pt in os_ports)
        )
        if DEV_SERVER_RE.search(cmd) or BROWSER_HEADLESS_RE.search(cmd) or is_listening_dev_runtime:
            cmd_norm = _norm_path(cmd)
            ports = _resolve_ports(pid, cmd, None, port_map)
            item = {
                "pid": pid,
                "ppid": ppid,
                "name": name,
                "port": ports[0] if ports else None,
                "ports": ports,
                "rss_mb": rss,
                "command_excerpt": cmd[:160],
                "auto_cleanup_allowed": False,
            }
            if ws_norm and ws_norm in cmd_norm:
                item["classification"] = "UNTRACKED_CURRENT_WORKSPACE_RESOURCE"
                item["recommendation"] = "Matches current workspace but not in task ledger; verify before stopping."
                workspace_untracked_servers.append(item)
            else:
                item["classification"] = "FOREIGN_PROJECT_KEEP"
                item["recommendation"] = "Belongs to another project or pre-existing user session; DO NOT terminate."
                foreign_servers_keep.append(item)

    active_sessions_list = sorted(host_sessions.values(), key=lambda x: x["host_pid"])
    mcp_under_live_hosts = sum(len(s["mcp_children"]) for s in active_sessions_list)
    mcp_total_rss = round(
        sum(sum(c["rss_mb"] for c in s["mcp_children"]) for s in active_sessions_list), 1
    )

    return {
        "tool": "resource_cleanup.py",
        "workspace": ws_norm,
        "summary": {
            "owned_by_task_alive": len(owned_alive),
            "owned_already_exited": len(owned_already_exited),
            "pid_reused_refused": len(pid_reused_refused),
            "active_host_sessions": len(active_sessions_list),
            "mcp_servers_under_active_hosts": mcp_under_live_hosts,
            "mcp_servers_under_active_hosts_rss_mb": mcp_total_rss,
            "orphaned_mcp_no_parent": len(orphaned_mcp),
            "untracked_current_workspace_resources": len(workspace_untracked_servers),
            "foreign_project_resources_protected": len(foreign_servers_keep),
        },
        "owned_by_task_alive": owned_alive,
        "owned_already_exited": owned_already_exited,
        "pid_reused_refused": pid_reused_refused,
        "active_host_sessions": active_sessions_list,
        "orphaned_mcp_no_parent": orphaned_mcp,
        "untracked_current_workspace_resources": workspace_untracked_servers,
        "foreign_project_resources_protected": foreign_servers_keep,
    }


def register_resource(
    ledger_path: Path,
    pid: int,
    kind: str,
    workspace: str,
    port: int | None = None,
    label: str = "",
    processes: list[dict[str, Any]] | None = None,
    listening_ports: dict[int, list[int]] | None = None,
) -> dict[str, Any]:
    """Record a task-spawned PID + creation timestamp fingerprint into the ledger."""
    procs = processes if processes is not None else snapshot_live_processes()
    port_map = listening_ports if listening_ports is not None else snapshot_listening_ports()
    proc = next((p for p in procs if int(p.get("pid", -1)) == pid), None)
    if proc is None:
        raise ValueError(f"PID {pid} is not running; cannot register ownership.")

    ledger = load_ledger(ledger_path)
    ws_norm = _norm_path(str(Path(workspace).resolve()) if workspace else "")
    if not ledger.get("workspace"):
        ledger["workspace"] = ws_norm

    cmd = str(proc.get("command", ""))
    name = str(proc.get("name", ""))
    hint = (cmd.split()[0] if cmd.strip() else name).strip()
    ports = _resolve_ports(pid, cmd, port, port_map)
    entry = {
        "pid": pid,
        "kind": kind,
        "label": label,
        "port": ports[0] if ports else None,
        "workspace": ws_norm,
        "created_at": _parse_cim_date(proc.get("created_at")),
        "command_hint": hint[:80],
    }
    ledger["entries"] = [e for e in ledger["entries"] if int(e.get("pid", -1)) != pid]
    ledger["entries"].append(entry)
    save_ledger(ledger_path, ledger)
    return {"registered": entry, "ledger_path": str(ledger_path)}


def _terminate_pid_tree(pid: int) -> tuple[bool, str]:
    if platform.system().lower().startswith("win"):
        proc = subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        ok = proc.returncode == 0
        return ok, (proc.stdout + proc.stderr).strip()
    try:
        os.kill(pid, signal.SIGTERM)
        return True, f"Sent SIGTERM to PID {pid}"
    except ProcessLookupError:
        return True, f"PID {pid} already exited"
    except OSError as exc:
        return False, str(exc)


def cleanup_owned_resources(
    ledger_path: Path,
    dry_run: bool = False,
    if_ledger_exists: bool = False,
    processes: list[dict[str, Any]] | None = None,
    listening_ports: dict[int, list[int]] | None = None,
    terminator: Any = None,
) -> dict[str, Any]:
    """Terminate ONLY verified OWNED_BY_TASK entries in the ledger (fail-closed on PID reuse)."""
    if if_ledger_exists and not ledger_path.is_file():
        return {
            "tool": "resource_cleanup.py",
            "action": "cleanup_owned",
            "status": "NO_LEDGER_NOTHING_TO_CLEAN",
            "cleaned_count": 0,
            "errors": [],
            "passed": True,
        }

    ledger = load_ledger(ledger_path)
    procs = processes if processes is not None else snapshot_live_processes()
    port_map = listening_ports if listening_ports is not None else snapshot_listening_ports()
    audit = classify_process_snapshot(
        procs, ledger=ledger, current_workspace=ledger.get("workspace"), listening_ports=port_map
    )
    kill_fn = terminator or _terminate_pid_tree

    cleaned: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    remaining_entries: list[dict[str, Any]] = []
    owned_pids = {int(item["pid"]) for item in audit["owned_by_task_alive"]}
    reused_pids = {int(item["pid"]) for item in audit["pid_reused_refused"]}

    for entry in ledger["entries"]:
        pid = int(entry["pid"])
        if pid in reused_pids:
            errors.append({"pid": pid, "status": "REFUSED_PID_REUSED", "reason": "Fingerprint mismatch; left untouched."})
            continue
        if pid not in owned_pids:
            cleaned.append({"pid": pid, "status": "ALREADY_EXITED", "label": entry.get("label", "")})
            continue
        if dry_run:
            cleaned.append({"pid": pid, "status": "DRY_RUN_WOULD_STOP", "label": entry.get("label", "")})
            remaining_entries.append(entry)
            continue
        ok, detail = kill_fn(pid)
        if ok:
            cleaned.append({"pid": pid, "status": "STOPPED", "label": entry.get("label", ""), "detail": detail})
        else:
            errors.append({"pid": pid, "status": "STOP_FAILED", "detail": detail})
            remaining_entries.append(entry)

    if not dry_run:
        ledger["entries"] = remaining_entries
        save_ledger(ledger_path, ledger)

    return {
        "tool": "resource_cleanup.py",
        "action": "cleanup_owned",
        "dry_run": dry_run,
        "cleaned_count": len(cleaned),
        "cleaned": cleaned,
        "errors": errors,
        "refused_pid_reused": audit["pid_reused_refused"],
        "protected_foreign_count": audit["summary"]["foreign_project_resources_protected"],
        "protected_active_host_sessions": audit["summary"]["active_host_sessions"],
        "passed": len(errors) == 0,
    }


def run_self_test() -> dict[str, Any]:
    """Deterministic precision & recall probes modeled on multi-session MCP + foreign Vite + OS port map."""
    synthetic_procs: list[dict[str, Any]] = []
    next_pid = 2000
    for s_idx in range(6):
        host_pid = 1000 + s_idx
        synthetic_procs.append(
            {
                "pid": host_pid,
                "ppid": 500,
                "name": "claude.exe",
                "command": "claude.exe --session",
                "created_at": f"2026-11-22T13:4{s_idx}:00Z",
                "rss_mb": 120.0,
            }
        )
        for mcp_name in ("@playwright/mcp", "shadow-db-mcp", "shadow-api-mcp", "shadow-handoff-mcp", "context7-mcp", "work-mcp"):
            synthetic_procs.append(
                {
                    "pid": next_pid,
                    "ppid": host_pid,
                    "name": "node.exe",
                    "command": f"node {mcp_name}/index.mjs",
                    "created_at": f"2026-11-22T13:4{s_idx}:05Z",
                    "rss_mb": 70.0,
                }
            )
            next_pid += 1

    # Foreign project Vite dev server (port 5174 NOT in CLI args — resolved purely via OS TCP table!)
    synthetic_procs.append(
        {
            "pid": 5174,
            "ppid": 600,
            "name": "node.exe",
            "command": "node D:/Projects/PRPM-SIPRITI/node_modules/vite/bin/vite.js",
            "created_at": "2026-11-22T14:00:00Z",
            "rss_mb": 140.0,
        }
    )
    # Foreign bare Express server listening on port 4000 (detected via OS listening port!)
    synthetic_procs.append(
        {
            "pid": 4000,
            "ppid": 600,
            "name": "node.exe",
            "command": "node D:/Projects/OtherApp/dist/server.js",
            "created_at": "2026-11-22T14:15:00Z",
            "rss_mb": 80.0,
        }
    )
    # Task-owned video-env.cjs in current workspace
    synthetic_procs.append(
        {
            "pid": 7001,
            "ppid": 900,
            "name": "node.exe",
            "command": "node D:/Projects/Notulen/tools/video-env.cjs",
            "created_at": "2026-11-22T18:00:00Z",
            "rss_mb": 95.0,
        }
    )
    # PID reused by an unrelated process
    synthetic_procs.append(
        {
            "pid": 7002,
            "ppid": 900,
            "name": "postgres.exe",
            "command": "postgres.exe -D C:/pgdata",
            "created_at": "2026-11-22T19:30:00Z",
            "rss_mb": 310.0,
        }
    )
    # True orphan MCP whose parent PID 99999 no longer exists
    synthetic_procs.append(
        {
            "pid": 8888,
            "ppid": 99999,
            "name": "node.exe",
            "command": "node shadow-api-mcp/index.mjs",
            "created_at": "2026-11-22T10:00:00Z",
            "rss_mb": 65.0,
        }
    )

    synthetic_ports = {
        5174: [5174],
        4000: [4000],
        7001: [3000, 5173],
    }

    ledger = {
        "version": 1,
        "workspace": "d:/projects/notulen",
        "entries": [
            {
                "pid": 7001,
                "kind": "video_env",
                "label": "notulen-recording-env",
                "port": None,
                "workspace": "d:/projects/notulen",
                "created_at": "2026-11-22T18:00:00Z",
                "command_hint": "video-env.cjs",
            },
            {
                "pid": 7002,
                "kind": "dev_server",
                "label": "old-reused-vite",
                "port": 5173,
                "workspace": "d:/projects/notulen",
                "created_at": "2026-11-22T17:00:00Z",
                "command_hint": "vite",
            },
        ],
    }

    audit = classify_process_snapshot(
        synthetic_procs,
        ledger=ledger,
        current_workspace="D:/Projects/Notulen",
        listening_ports=synthetic_ports,
    )
    summary = audit["summary"]
    foreign_by_pid = {item["pid"]: item for item in audit["foreign_project_resources_protected"]}
    no_ledger_res = cleanup_owned_resources(Path("__nonexistent_shadow_ledger__.json"), if_ledger_exists=True)

    probes = [
        (
            "PRECISION-1: 6 live claude.exe sessions x 6 MCP = 36 active MCPs grouped & protected",
            summary["active_host_sessions"] == 6
            and summary["mcp_servers_under_active_hosts"] == 36
            and all(not s["auto_cleanup_allowed"] for s in audit["active_host_sessions"]),
        ),
        (
            "PRECISION-2: Foreign PRPM/SIPRITI Vite (:5174) & bare node server (:4000) protected with OS ports",
            5174 in foreign_by_pid
            and foreign_by_pid[5174]["port"] == 5174
            and 4000 in foreign_by_pid
            and foreign_by_pid[4000]["port"] == 4000
            and all(not v["auto_cleanup_allowed"] for v in foreign_by_pid.values()),
        ),
        (
            "PRECISION-3: Reused PID 7002 (now postgres.exe) refused with PID_REUSED_DO_NOT_TOUCH",
            summary["pid_reused_refused"] == 1
            and audit["pid_reused_refused"][0]["pid"] == 7002
            and audit["pid_reused_refused"][0]["auto_cleanup_allowed"] is False,
        ),
        (
            "RECALL-1: Task-owned video-env.cjs (PID 7001) identified with OS listening ports [3000, 5173]",
            summary["owned_by_task_alive"] == 1
            and audit["owned_by_task_alive"][0]["pid"] == 7001
            and audit["owned_by_task_alive"][0]["ports"] == [3000, 5173]
            and audit["owned_by_task_alive"][0]["auto_cleanup_allowed"] is True,
        ),
        (
            "RECALL-2: True orphan MCP (PID 8888, dead parent 99999) flagged separately without auto-kill",
            summary["orphaned_mcp_no_parent"] == 1
            and audit["orphaned_mcp_no_parent"][0]["pid"] == 8888
            and audit["orphaned_mcp_no_parent"][0]["auto_cleanup_allowed"] is False,
        ),
        (
            "HOOK-1: --cleanup-owned --if-ledger-exists exits cleanly when no ledger file exists",
            no_ledger_res["passed"] is True and no_ledger_res["status"] == "NO_LEDGER_NOTHING_TO_CLEAN",
        ),
    ]
    results = [{"probe": name, "passed": ok} for name, ok in probes]
    passed = sum(1 for r in results if r["passed"])
    return {
        "tool": "resource_cleanup.py",
        "total_probes": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "all_passed": passed == len(results),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Shadow Monarch Ownership-Safe Resource Auditor & Teardown")
    parser.add_argument("--audit", action="store_true", help="L0 read-only audit of active sessions, MCPs & dev servers")
    parser.add_argument("--register", action="store_true", help="Register a task-spawned PID into a ledger")
    parser.add_argument("--cleanup-owned", action="store_true", help="Stop ONLY verified OWNED_BY_TASK PIDs in ledger")
    parser.add_argument("--self-test", action="store_true", help="Run precision & recall probes")
    parser.add_argument("--ledger", default=None, help="Path to task-scoped JSON ledger file")
    parser.add_argument("--workspace", default=".", help="Current workspace path")
    parser.add_argument("--pid", type=int, default=None, help="PID to register")
    parser.add_argument("--kind", default="dev_server", choices=["dev_server", "video_env", "browser", "worker"])
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--label", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--if-ledger-exists", action="store_true", help="Return rc=0 cleanly if ledger file does not exist (for SessionEnd hooks)")
    args = parser.parse_args()

    if args.self_test:
        res = run_self_test()
        print(json.dumps(res, indent=2))
        return 0 if res["all_passed"] else 1

    if args.register:
        if not args.ledger or args.pid is None:
            print("ERROR: --register requires --ledger and --pid", file=sys.stderr)
            return 2
        res = register_resource(Path(args.ledger), args.pid, args.kind, args.workspace, args.port, args.label)
        print(json.dumps(res, indent=2))
        return 0

    if args.audit:
        ledger = load_ledger(Path(args.ledger)) if args.ledger else None
        procs = snapshot_live_processes()
        ports = snapshot_listening_ports()
        res = classify_process_snapshot(
            procs, ledger=ledger, current_workspace=str(Path(args.workspace).resolve()), listening_ports=ports
        )
        print(json.dumps(res, indent=2))
        return 0

    if args.cleanup_owned:
        if not args.ledger:
            print("ERROR: --cleanup-owned requires --ledger", file=sys.stderr)
            return 2
        res = cleanup_owned_resources(
            Path(args.ledger), dry_run=args.dry_run, if_ledger_exists=args.if_ledger_exists
        )
        print(json.dumps(res, indent=2))
        return 0 if res["passed"] else 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
