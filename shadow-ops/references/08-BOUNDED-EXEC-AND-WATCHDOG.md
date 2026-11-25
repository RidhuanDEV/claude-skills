# Bounded Script Execution, Idle Watchdogs & Anti-Stuck Guardrails

Use this playbook whenever executing potentially blocking CLI scripts, SSH remote commands, container builds/pulls, package installs, migrations, or long test runs so commands **never hang silently** and always clean up their exact spawned process tree.

---

## 1. Two-Timer Anti-Stuck Rule (Wall Timeout + Idle Watchdog)

A single hard timeout is often either too short (kills healthy slow builds) or too long (waits 10 minutes on a dead SSH pipe). Always pair **two independent timers**:

| Timer | Default | Purpose | Exit Code (`bounded_exec.py`) |
| --- | --- | --- | --- |
| **Hard Wall Timeout (`--timeout`)** | `120s` (adjust per task) | Caps total runtime even when the process keeps printing output (catches infinite retry loops) | `124` (`WALL_TIMEOUT`) |
| **Idle / No-Output Watchdog (`--idle-timeout`)** | `45s` (`0` to disable) | Kills hung processes that emit **0 stdout/stderr bytes** (catches dead SSH sockets, stalled prompts, deadlocked locks) | `125` (`IDLE_TIMEOUT`) |
| **Live Heartbeat (`--heartbeat`)** | `15s` | Emits `[watchdog] alive pid=... elapsed=... idle=...` to stderr so operators distinguish real work from hangs | — |

---

## 2. Cross-Platform Runner (`shadow-monarch/scripts/bounded_exec.py`)

Use [`shadow-monarch/scripts/bounded_exec.py`](../../shadow-monarch/scripts/bounded_exec.py) (Python stdlib only, Windows + Linux/macOS):

```powershell
# Run any local script with 90s hard wall limit and 30s silent-hang watchdog
python shadow-monarch/scripts/bounded_exec.py --timeout 90 --idle-timeout 30 --heartbeat 10 -- python scripts/sync.py

# Run remote SSH command with automatic non-interactive keepalive flags + watchdog
python shadow-monarch/scripts/bounded_exec.py --ssh-safe --timeout 60 --idle-timeout 20 -- ssh vps-lab "docker ps -a"

# Emit machine-readable JSON summary on exit
python shadow-monarch/scripts/bounded_exec.py --timeout 30 --idle-timeout 15 --json-summary -- node tools/check.mjs

# Verify watchdog probes locally
python shadow-monarch/scripts/bounded_exec.py --self-test
```

### Safe Process-Tree Teardown (No Blanket Kills)
- **Windows:** Creates a dedicated process group (`CREATE_NEW_PROCESS_GROUP`), sends graceful `terminate()`, then runs `taskkill /PID <exact-child-pid> /T /F` ONLY on the spawned child PID tree.
- **Linux/macOS:** Starts a new session (`start_new_session=True`), sends `SIGTERM` to the process group (`os.killpg`), waits `--kill-grace`, then sends `SIGKILL`.
- **NEVER** run `taskkill /IM node.exe /F`, `pkill -f python`, or kill foreign project/host processes (`resource_cleanup.py`).

---

## 3. Native Shell & SSH Anti-Stuck Patterns

### SSH (Mandatory Non-Blocking Flags for Automated Runs)
Always set these options in `~/.ssh/config` or CLI flags (`--ssh-safe` injects them automatically):
```text
-o BatchMode=yes
-o ConnectTimeout=10
-o ServerAliveInterval=15
-o ServerAliveCountMax=2
```
- `BatchMode=yes` fails immediately instead of hanging forever on an unexpected password/passphrase/host-key prompt.
- `ServerAliveInterval=15` + `ServerAliveCountMax=2` closes a dead TCP tunnel in `~30s` instead of waiting for OS TCP timeouts.

### Linux / Docker / Bash
- Wrap single remote commands with GNU `timeout --kill-after=5s 60s <cmd>` so orphaned remote commands also self-terminate if the SSH client disconnects.
- Avoid buffering entire multi-minute streams behind `| tail -n 20` without `stdbuf -oL` or periodic progress prints — otherwise stdout appears silent and triggers idle watchdogs prematurely.

### PowerShell (Windows)
- Never use `Start-Sleep` loops to poll stuck jobs; use `bounded_exec.py` or `Wait-Job -Timeout <sec>` + `Stop-Job` / `Remove-Job` in `finally`.
- Always check `$LASTEXITCODE` after native executables (`$ErrorActionPreference = "Stop"` does not stop on native non-zero exit codes in Windows PowerShell 5.1).
