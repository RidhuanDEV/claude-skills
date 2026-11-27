# 06. MCP Server Engineering & Production Troubleshooting

## 1. Purpose & Activation Conditions
Build, secure, and troubleshoot **Model Context Protocol (MCP)** servers (stdio & Streamable HTTP) and diagnose production AI incidents (TTFT spikes, JSON-RPC framing crashes, prompt-injection alerts, orphan MCP processes). Load when authoring MCP servers or debugging live AI/agent runtime failures.

## 2. Prerequisites
- Tool trust boundaries (`02`), context/streaming controls (`03`, `05`), and task-scoped cleanup discipline (`Rule #29`).

## 3. Technical Principles & Constraints
- **Stdio MCP Protocol Integrity (`stdout` = Protocol ONLY!):**
  - Over `stdio` transport, `stdout` is strictly reserved for newline-delimited **JSON-RPC 2.0** messages! A SINGLE `console.log("Connected...")` or `print("Debug")` to `stdout` corrupts JSON-RPC framing and immediately crashes the host client!
  - Route ALL diagnostics strictly to **`stderr`** (`process.stderr.write(...)` / `sys.stderr`) with fail-closed secret/PII redaction!
  - **Graceful Exit on Parent Close (`Rule #29`):** Listen to `process.stdin.on('end'/'close')`, `SIGINT`, and `SIGTERM` and close DB pools + exit cleanly (`0`) so closed host sessions NEVER leave zombie/orphan MCP servers consuming gigabytes of RAM!
  - Guard CLI entrypoint (`isMainModule`) so unit tests can import server functions cleanly without hanging on `stdin`!
- **Canonical Workspace Containment (Path Jail):** Any MCP tool that reads/writes files MUST resolve canonical paths via `fs.realpathSync` / `Path.resolve()` and verify strict containment inside the authorized root directory (`+ path.sep`) — blocking BOTH `../../etc/passwd` AND symlink escape attacks!
- **Narrow Read-Only vs Mutating Tool Split:** Mark read-only inspection tools clearly (`readOnlyHint: true`, `L0`) and gate mutating/destructive tools behind explicit flags (`allowNewSpec: true`, `confirm: true`) or host approval boundaries — NEVER combine arbitrary SQL write capability inside a read-only DB inspection tool!
- **Structured AI Incident Troubleshooting Tree:**
  1. **High TTFT (`> 3s`):** Inspect 5-stage spans (`rewrite -> embed -> search -> rerank -> llm_ttft`) + `prompt_cache_hit_ratio`.
  2. **Sudden Accuracy / Format Drop:** Diff `prompt_version`, `pinned_model_id`, `corpus_snapshot_id`, and run `/shadow-eval --compare-rag`.
  3. **Suspicious Tool Attempts:** Inspect tool-trace logs for indirect injection payloads inside retrieved docs (`02`, `/shadow-eval`).
  4. **Token Spend Surge:** Check `agent_steps_per_turn`, `cached_input_tokens`, `thinking_budget`, and uncancelled SSE disconnects (`05`, `/shadow-finops`).

## 4. Architecture & Implementation
```typescript
import fs from 'node:fs';
import path from 'node:path';

// 1. Canonical Workspace Path Jail for MCP File Tools (Blocks ../ AND Symlink Escape)
export function resolveJailedWorkspacePath(allowedRootDir: string, requestedRelPath: string): string {
  if (requestedRelPath.includes('\0')) {
    throw new Error('MCP_PATH_JAIL_NULL_BYTE');
  }
  const realRoot = fs.realpathSync(allowedRootDir);
  const candidate = path.resolve(realRoot, requestedRelPath);
  const realCandidate = fs.existsSync(candidate) ? fs.realpathSync(candidate) : candidate;
  const rootWithSep = realRoot.endsWith(path.sep) ? realRoot : `${realRoot}${path.sep}`;
  if (realCandidate !== realRoot && !realCandidate.startsWith(rootWithSep)) {
    throw new Error('MCP_PATH_JAIL_VIOLATION: path escapes authorized workspace root');
  }
  return realCandidate;
}

// 2. Redacted stderr-only logger + graceful stdin-EOF shutdown (prevents JSON-RPC corruption & orphan RAM leaks)
export function logMcpDiagnostic(event: string, details: Readonly<Record<string, string | number | boolean>>): void {
  process.stderr.write(`${JSON.stringify({ ts: new Date().toISOString(), event, ...details })}\n`);
}

export function registerMcpGracefulShutdown(cleanup: () => Promise<void>): void {
  let shuttingDown = false;
  const shutdown = (reason: string): void => {
    if (shuttingDown) return;
    shuttingDown = true;
    logMcpDiagnostic('mcp.shutdown', { reason });
    void cleanup().finally(() => process.exit(0));
  };
  process.stdin.on('end', () => shutdown('stdin_eof'));
  process.stdin.on('close', () => shutdown('stdin_close'));
  process.on('SIGINT', () => shutdown('sigint'));
  process.on('SIGTERM', () => shutdown('sigterm'));
}
```
Offline MCP safety check:
```powershell
python "shadow-ai-eng/scripts/ai_runtime_verifier.py" --check-mcp-config path/to/mcp_cfg.json
```

## 5. Platform / Vendor Variations
| MCP Transport | Best Used For | Key Security & Lifecycle Rule |
| :--- | :--- | :--- |
| **`stdio` (Local Subprocess)** | IDE/CLI developer tools (`shadow-db-mcp`, `shadow-api-mcp`) | Zero `stdout` logging; exit cleanly on `stdin` EOF; workspace path jail |
| **Streamable HTTP (Remote MCP Server)** | Multi-user / enterprise SaaS tool servers | Enforce OAuth 2.1 (still draft-ietf-oauth-v2-1; baseline RFC 9700) + PKCE auth (`shadow-auth`), `Origin` validation (DNS-rebinding defense!), per-tenant RBAC, and TLS |

## 6. Decision Matrix & Trade-Offs
| MCP Tool Granularity | LLM Tool-Selection Accuracy | Safety Surface | Verdict |
| :--- | :---: | :---: | :--- |
| **3–8 Narrow Purpose-Built Tools per Server** | **High** | Tight & auditable | **Recommended standard** |
| **60 Raw 1:1 REST Endpoint Tools Dumped into Context** | Poor (tool confusion + huge token overhead!) | Wide | **Avoid — group into high-level task tools** |

## 7. Real Production Scenario
A team deploys an internal `stdio` MCP server for querying Postgres. A helper dependency logs `dotenv injecting env (14)` straight to `stdout`, breaking Claude/Antigravity MCP handshake on every launch — AND closing sessions leaves 12 orphan Node processes holding open DB connections. Silencing stdout logs (`stderr` only), wiring `registerMcpGracefulShutdown` on `stdin` EOF/`SIGINT`/`SIGTERM`, and enforcing read-only SQL checks fixes both crashes and RAM leaks cleanly.

## 8. Failure Modes & Edge Cases
- **WRONG:** Accepting raw `projectRoot` or `filePath` in an MCP tool without canonical `realpathSync` containment (a prompt injection tricks the agent into reading `~/.ssh/id_rsa` or `.env` outside the workspace!).
- **RIGHT:** Always jail file paths via `resolveJailedWorkspacePath` and exclude secret files (`.env`, `*.pem`, `*.key`) explicitly.
- **WRONG:** Returning a 500 KB unfiltered DB query dump from an MCP tool response (blows up the host agent's entire context window in 1 call!).
- **RIGHT:** Cap MCP tool responses cleanly (`limit <= 100` rows / bounded byte budget + structured summary + pagination hint).

## 9. Testing & Verification
- Run `python shadow-ai-eng/scripts/ai_runtime_verifier.py --self-test` and `python -m unittest discover -s shadow-ai-eng/tests -v`.
- Test stdio MCP cleanly: spawn server, pipe a valid JSON-RPC request (revision 2026-07-28 is stateless with no initialize step, so send `server/discover`; servers that also support the earlier revision 2025-11-25 still need its legacy initialize handshake tested), assert **every single line on `stdout` parses as valid JSON-RPC**, close `stdin`, and assert process exits `0` within `< 2s`!

## 10. Operational Considerations
- Version MCP server tool schemas cleanly; never rename or break existing tool parameters silently while multiple IDE clients depend on them.

## 11. Authoritative References
- Model Context Protocol (MCP) Official Specification (`https://modelcontextprotocol.io/specification/`).
- OWASP MCP & GenAI Tool Security Guidance (`https://genai.owasp.org/`).

## 12. Limitations & When NOT to Use
- Do NOT wrap simple single-app internal backend helpers as a separate MCP server process — MCP adds IPC/protocol overhead justified ONLY when exposing reusable tools across AI hosts/clients or process trust boundaries!
