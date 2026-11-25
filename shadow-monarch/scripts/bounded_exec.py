#!/usr/bin/env python3
"""
Shadow Monarch Cross-Platform Bounded Script Executor & No-Output Watchdog (bounded_exec.py)

Prevents long-running, silent, or hung CLI / SSH / Docker / test scripts from getting stuck:
- Hard wall-clock timeout (`--timeout`, default 120s).
- Idle / no-output watchdog (`--idle-timeout`, default 45s): kills hung processes producing 0 output.
- Periodic heartbeat (`--heartbeat`, default 15s) to stderr showing elapsed, idle, and byte counts.
- Safe exact-PID process-tree termination (Windows `taskkill /PID <pid> /T /F`, POSIX `killpg`),
  NEVER issuing blanket image kills (`taskkill /IM node.exe` / `pkill`).
- Optional `--ssh-safe` mode injecting non-blocking SSH keepalive & connect timeouts.
- Zero external dependencies (Python stdlib only).
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import queue
import signal
import subprocess
import sys
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any

SSH_SAFE_OPTIONS = [
    "-o", "BatchMode=yes",
    "-o", "ConnectTimeout=10",
    "-o", "ServerAliveInterval=15",
    "-o", "ServerAliveCountMax=2",
]


def inject_ssh_safe_flags(cmd: list[str]) -> list[str]:
    """Safely inject keepalive/batch flags immediately after `ssh` binary without touching other commands."""
    if not cmd:
        return cmd
    exe_name = Path(cmd[0]).name.lower()
    if exe_name not in {"ssh", "ssh.exe"}:
        return list(cmd)
    existing = " ".join(cmd[1:]).lower()
    injected: list[str] = [cmd[0]]
    pairs = [
        ("batchmode=", ["-o", "BatchMode=yes"]),
        ("connecttimeout=", ["-o", "ConnectTimeout=10"]),
        ("serveraliveinterval=", ["-o", "ServerAliveInterval=15"]),
        ("serveralivecountmax=", ["-o", "ServerAliveCountMax=2"]),
    ]
    for marker, flags in pairs:
        if marker not in existing:
            injected.extend(flags)
    injected.extend(cmd[1:])
    return injected


def _terminate_process_tree(proc: subprocess.Popen[bytes], grace_sec: float = 2.0) -> None:
    """Terminate ONLY the exact spawned child process tree; never issue blanket image kills."""
    if proc.poll() is not None:
        return
    if platform.system() == "Windows":
        try:
            proc.terminate()
        except OSError:
            pass
        deadline = time.monotonic() + max(0.2, grace_sec)
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                return
            time.sleep(0.05)
        if proc.poll() is None:
            subprocess.run(
                ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                capture_output=True,
                check=False,
            )
    else:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except OSError:
            try:
                proc.terminate()
            except OSError:
                pass
        deadline = time.monotonic() + max(0.2, grace_sec)
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                return
            time.sleep(0.05)
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                try:
                    proc.kill()
                except OSError:
                    pass


def run_bounded(
    cmd: list[str],
    *,
    timeout: float = 120.0,
    idle_timeout: float = 45.0,
    heartbeat: float = 15.0,
    kill_grace: float = 2.0,
    cwd: str | None = None,
    ssh_safe: bool = False,
    stream_output: bool = True,
    tail_lines: int = 20,
) -> dict[str, Any]:
    """Execute `cmd` with hard wall timeout, idle no-output watchdog, and exact-PID tree teardown."""
    if not cmd:
        raise ValueError("Command must be non-empty.")
    if timeout <= 0:
        raise ValueError("--timeout must be > 0.")
    if idle_timeout < 0:
        raise ValueError("--idle-timeout must be >= 0 (0 disables idle watchdog).")

    final_cmd = inject_ssh_safe_flags(cmd) if ssh_safe else list(cmd)
    popen_kwargs: dict[str, Any] = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "stdin": subprocess.DEVNULL,
        "cwd": cwd,
    }
    if platform.system() == "Windows":
        popen_kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        popen_kwargs["start_new_session"] = True

    start = time.monotonic()
    last_activity = start
    last_heartbeat = start
    stdout_bytes = 0
    stderr_bytes = 0
    tail_buf: deque[str] = deque(maxlen=max(1, tail_lines))
    events: queue.Queue[tuple[str, bytes]] = queue.Queue()

    proc = subprocess.Popen(final_cmd, **popen_kwargs)

    def _reader(stream_name: str, stream: Any) -> None:
        try:
            while True:
                chunk = stream.readline()
                if not chunk:
                    break
                events.put((stream_name, chunk))
        finally:
            try:
                stream.close()
            except OSError:
                pass
            events.put((f"{stream_name}_eof", b""))

    t_out = threading.Thread(target=_reader, args=("stdout", proc.stdout), daemon=True)
    t_err = threading.Thread(target=_reader, args=("stderr", proc.stderr), daemon=True)
    t_out.start()
    t_err.start()

    status = "RUNNING"
    eof_count = 0

    try:
        while True:
            try:
                kind, chunk = events.get(timeout=0.1)
                if kind.endswith("_eof"):
                    eof_count += 1
                else:
                    last_activity = time.monotonic()
                    if kind == "stdout":
                        stdout_bytes += len(chunk)
                        if stream_output:
                            sys.stdout.buffer.write(chunk)
                            sys.stdout.buffer.flush()
                    else:
                        stderr_bytes += len(chunk)
                        if stream_output:
                            sys.stderr.buffer.write(chunk)
                            sys.stderr.buffer.flush()
                    decoded = chunk.decode("utf-8", errors="replace").rstrip("\r\n")
                    if decoded:
                        tail_buf.append(f"[{kind}] {decoded}")
            except queue.Empty:
                pass

            now = time.monotonic()
            elapsed = now - start
            idle = now - last_activity

            if proc.poll() is not None and eof_count >= 2 and events.empty():
                status = "PASS" if proc.returncode == 0 else "FAIL"
                break

            if elapsed >= timeout:
                status = "WALL_TIMEOUT"
                if stream_output:
                    sys.stderr.write(
                        f"[watchdog] WALL_TIMEOUT after {elapsed:.1f}s (limit={timeout:.1f}s) — terminating pid={proc.pid}\n"
                    )
                    sys.stderr.flush()
                _terminate_process_tree(proc, grace_sec=kill_grace)
                break

            if idle_timeout > 0 and idle >= idle_timeout:
                status = "IDLE_TIMEOUT"
                if stream_output:
                    sys.stderr.write(
                        f"[watchdog] IDLE_TIMEOUT after {idle:.1f}s without output (limit={idle_timeout:.1f}s) — terminating pid={proc.pid}\n"
                    )
                    sys.stderr.flush()
                _terminate_process_tree(proc, grace_sec=kill_grace)
                break

            if heartbeat > 0 and (now - last_heartbeat) >= heartbeat:
                last_heartbeat = now
                if stream_output:
                    sys.stderr.write(
                        f"[watchdog] alive pid={proc.pid} elapsed={elapsed:.0f}s idle={idle:.0f}s "
                        f"stdout={stdout_bytes}B stderr={stderr_bytes}B\n"
                    )
                    sys.stderr.flush()
    finally:
        if proc.poll() is None:
            _terminate_process_tree(proc, grace_sec=kill_grace)
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            pass
        t_out.join(timeout=1.0)
        t_err.join(timeout=1.0)

    exit_code = proc.returncode if proc.returncode is not None else -1
    if status == "WALL_TIMEOUT":
        exit_code = 124
    elif status == "IDLE_TIMEOUT":
        exit_code = 125

    return {
        "status": status,
        "exit_code": exit_code,
        "pid": proc.pid,
        "command": final_cmd,
        "elapsed_sec": round(time.monotonic() - start, 3),
        "idle_sec": round(time.monotonic() - last_activity, 3),
        "stdout_bytes": stdout_bytes,
        "stderr_bytes": stderr_bytes,
        "tail": list(tail_buf),
    }


def run_self_test() -> int:
    # 1. Fast successful command
    r_ok = run_bounded([sys.executable, "-c", "print('hello-watchdog')"], timeout=10, idle_timeout=5, heartbeat=0, stream_output=False)
    assert r_ok["status"] == "PASS" and r_ok["exit_code"] == 0 and r_ok["stdout_bytes"] > 0

    # 2. Non-zero failing command preserved
    r_fail = run_bounded([sys.executable, "-c", "import sys; sys.exit(7)"], timeout=10, idle_timeout=5, heartbeat=0, stream_output=False)
    assert r_fail["status"] == "FAIL" and r_fail["exit_code"] == 7

    # 3. Silent hung process caught by IDLE_TIMEOUT well before WALL_TIMEOUT
    r_idle = run_bounded([sys.executable, "-c", "import time; time.sleep(15)"], timeout=12, idle_timeout=0.6, heartbeat=0, kill_grace=0.3, stream_output=False)
    assert r_idle["status"] == "IDLE_TIMEOUT" and r_idle["exit_code"] == 125 and r_idle["elapsed_sec"] < 5.0

    # 4. Chatty infinite process caught by WALL_TIMEOUT
    r_wall = run_bounded(
        [sys.executable, "-c", "import time, sys\nwhile True:\n print('tick', flush=True)\n time.sleep(0.15)"],
        timeout=0.9,
        idle_timeout=5.0,
        heartbeat=0,
        kill_grace=0.3,
        stream_output=False,
    )
    assert r_wall["status"] == "WALL_TIMEOUT" and r_wall["exit_code"] == 124 and r_wall["stdout_bytes"] > 0

    # 5. SSH safe flag injection precision & recall
    injected = inject_ssh_safe_flags(["ssh", "vps-lab", "uptime"])
    assert "BatchMode=yes" in " ".join(injected) and "ServerAliveInterval=15" in " ".join(injected)
    non_ssh = inject_ssh_safe_flags(["python", "app.py"])
    assert non_ssh == ["python", "app.py"]

    print(json.dumps({"tool": "bounded_exec.py", "status": "PASS", "probes": 5}))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run any script/CLI/SSH command with hard wall timeout, idle no-output watchdog, and exact-PID tree cleanup."
    )
    parser.add_argument("--timeout", type=float, default=120.0, help="Hard wall-clock timeout in seconds (default: 120)")
    parser.add_argument("--idle-timeout", type=float, default=45.0, help="Max silent seconds before IDLE_TIMEOUT kill; 0 disables (default: 45)")
    parser.add_argument("--heartbeat", type=float, default=15.0, help="Heartbeat interval in seconds to stderr; 0 disables (default: 15)")
    parser.add_argument("--kill-grace", type=float, default=2.0, help="Graceful terminate wait before force kill in seconds (default: 2)")
    parser.add_argument("--cwd", help="Optional working directory")
    parser.add_argument("--ssh-safe", action="store_true", help="Inject BatchMode/ConnectTimeout/ServerAlive flags when running ssh")
    parser.add_argument("--json-summary", action="store_true", help="Print JSON summary to stderr on exit")
    parser.add_argument("--quiet", action="store_true", help="Suppress live child streaming (still captures summary tail)")
    parser.add_argument("--self-test", action="store_true", help="Run built-in positive and negative watchdog probes")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to execute (prefix with `--` to separate flags)")
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()

    cmd = list(args.command)
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        parser.error("Provide a command after `--` (e.g. `bounded_exec.py --timeout 60 -- ssh vps-lab uptime`), or use --self-test.")

    result = run_bounded(
        cmd,
        timeout=args.timeout,
        idle_timeout=args.idle_timeout,
        heartbeat=args.heartbeat,
        kill_grace=args.kill_grace,
        cwd=args.cwd,
        ssh_safe=args.ssh_safe,
        stream_output=not args.quiet,
    )
    if args.json_summary or args.quiet:
        sys.stderr.write(json.dumps(result, indent=2) + "\n")
        sys.stderr.flush()
    return int(result["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
