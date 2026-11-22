# 03. Injection & Input-Boundary Defenses

## 1. Purpose & Activation Conditions
Eliminate injection vulnerability classes structurally — SQL injection, NoSQL injection, OS command injection, server-side template injection (SSTI), path traversal, prototype pollution, and unsafe deserialization. Load when auditing data queries, shell invocations, file-path handling, or untrusted input parsers.

## 2. Prerequisites
- Typed schema validation library (`Zod`, `Valibot`, `Pydantic`, `go-playground/validator`) at every external ingress boundary.

## 3. Technical Principles & Constraints
- **Structural Separation of Code vs Data (Never Rely on String Blacklists):**
  - **SQL Injection (`CWE-89`):** ALWAYS use parameterized queries (`$1, $2`, `?`, ORM query builders with bound params). NEVER concatenate or template-interpolate variables into SQL (`$queryRawUnsafe`, `f"SELECT ... {user}"`, `ORDER BY ${sort}`) — map dynamic identifiers (`ORDER BY` columns/directions) strictly through static compile-time allowlists!
  - **OS Command Injection (`CWE-78`):** Prefer native language APIs over spawning subprocesses. When a binary truly must run (e.g., `ffmpeg`, `pdfinfo`), ALWAYS pass an explicit **argument array** (`execFile` / `subprocess.run([...], shell=False)`) — NEVER `exec()`, `shell=True`, or `sh -c "..."`, and guard leading-dash argument injection (`--`)!
  - **Path Traversal (`CWE-22`):** NEVER pass raw user filenames to `fs.readFile(path.join(base, userFile))`. Generate opaque server UUID storage keys, OR resolve canonical paths via `path.resolve` + verify `resolved.startsWith(canonicalBase + path.sep)` (and reject NUL bytes + symlinks escaping root).
  - **NoSQL / Prototype Pollution / Deserialization:** Reject raw object operators (`$ne`, `$where`, `$gt`) via strict primitive Zod/Pydantic types; block `__proto__`/`constructor`/`prototype` keys during object merges; NEVER deserialize untrusted input with Python `pickle.loads`, `yaml.load` (use `yaml.safe_load`), Java `ObjectInputStream`, or PHP `unserialize()`.
  - **ReDoS Prevention:** Avoid nested-quantifier regexes `(a+)+$` on untrusted strings; cap input string lengths BEFORE running any regex!

## 4. Architecture & Implementation
```typescript
import { execFile } from 'node:child_process';
import path from 'node:path';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);

// 1. Safe canonical path containment (blocks ../../etc/passwd and sibling prefix tricks like /uploads-evil)
export function resolveContainedFilePath(baseDir: string, untrustedRelativeName: string): string {
  if (untrustedRelativeName.includes('\0')) {
    throw new Error('PATH_TRAVERSAL_NULL_BYTE');
  }
  const canonicalBase = path.resolve(baseDir);
  const resolved = path.resolve(canonicalBase, untrustedRelativeName);
  const baseWithSep = canonicalBase.endsWith(path.sep) ? canonicalBase : `${canonicalBase}${path.sep}`;
  if (!resolved.startsWith(baseWithSep)) {
    throw new Error('PATH_TRAVERSAL_BLOCKED');
  }
  return resolved;
}

// 2. Shell-less subprocess invocation with '--' argument-injection terminator and strict timeout
export async function inspectPdfMetadataSafe(baseDir: string, safeFileName: string): Promise<string> {
  const fullPath = resolveContainedFilePath(baseDir, safeFileName);
  const { stdout } = await execFileAsync('pdfinfo', ['--', fullPath], {
    shell: false,
    timeout: 5000,
    maxBuffer: 256 * 1024,
  });
  return stdout;
}
```
Allowlisted dynamic SQL sort pattern (zero SQLi even when user selects sort order):
```sql
-- Never interpolate sort column! Map enum in app code to one of exact static SQL clauses:
SELECT id, title, created_at
FROM documents
WHERE tenant_id = $1 AND title ILIKE $2 ESCAPE '\'
ORDER BY created_at DESC, id DESC
LIMIT $3;
```

## 5. Platform / Vendor Variations
| Language | Dangerous Sink (Audit Grep Target) | Safe Replacement |
| :--- | :--- | :--- |
| **TypeScript / Node** | `$queryRawUnsafe`, `exec()`, `eval()`, `new Function()`, `vm.runInNewContext` | `$queryRaw` tagged template / bound `$1`, `execFile(..., { shell: false })`, `JSON.parse` |
| **Python** | `cursor.execute(f"...")`, `subprocess.run(..., shell=True)`, `pickle.loads`, `yaml.load` | `cursor.execute("... %s", (val,))`, `subprocess.run([...], shell=False)`, `yaml.safe_load` |
| **Go** | `fmt.Sprintf("SELECT ... %s", x)`, `exec.Command("sh", "-c", ...)` | `db.QueryContext(ctx, "SELECT ... $1", x)`, `exec.Command("pdfinfo", "--", path)` |
| **PHP / Laravel** | `DB::raw("... $input")`, `unserialize($raw)`, `shell_exec()` | `DB::select('... ?', [$input])`, `json_decode()`, `Symfony Process([...])` |

## 6. Decision Matrix & Trade-Offs
| Input Scenario | Wrong "Quick Fix" | Correct Structural Defense |
| :--- | :--- | :--- |
| User searches by keyword | Strip `'` and `--` with `.replace()` | Parameterized `$1` binding + escape LIKE wildcards `%`/`_` |
| User chooses sort field | Interpolate `req.query.sort` | Static enum dictionary -> fixed SQL column string |
| User downloads uploaded file | `path.join(uploads, req.params.file)` | Lookup opaque UUID key in DB scoped to `tenant_id` + `resolveContainedFilePath` |

## 7. Real Production Scenario
A document service validates `resolved.startsWith(canonicalBase)` WITHOUT appending `path.sep`. An attacker requests `../uploads-backups/dump.sql`, which resolves to `/srv/uploads-backups/dump.sql` — passing `startsWith('/srv/uploads')`! Appending `path.sep` (`baseWithSep`) in `resolveContainedFilePath` AND looking up assets strictly by DB-mapped UUID keys eliminates sibling-directory path traversal completely.

## 8. Failure Modes & Edge Cases
- **WRONG:** Escaping SQL or shell characters manually via regex blacklists while still using string concatenation or `shell: true`.
- **RIGHT:** Use driver-level parameterized queries and `shell: false` argument arrays with `--` option terminator.
- **WRONG:** Passing raw JSON objects straight into MongoDB `collection.findOne({ email: req.body.email })` without validating `typeof email === 'string'` (an attacker sends `{ "email": { "$ne": null } }` -> NoSQL auth bypass!).
- **RIGHT:** Parse every request payload through strict typed schemas (`Zod`/`Pydantic`) validating primitive types before DB queries.

## 9. Testing & Verification
- Add negative injection unit/integration tests per sink: `' OR 1=1 --`, `../../etc/passwd`, `../uploads-evil/x`, `; id`, `{ "$ne": null }`, `__proto__` payload — assert clean `400`/`422` rejection or harmless literal handling with zero command/SQL execution.

## 10. Operational Considerations
- Enforce SAST rules (`semgrep`, `eslint-plugin-security`, `bandit`) in CI blocking `$queryRawUnsafe`, `child_process.exec`, `eval`, `pickle`, and `yaml.load` on every PR.

## 11. Authoritative References
- OWASP ASVS v5.0.0 — *V1 Encoding and Sanitization* & *V2 Validation* (`https://asvs.owasp.org/`).
- OWASP Injection Prevention Cheat Sheet (`https://cheatsheetseries.owasp.org/cheatsheets/Injection_Prevention_Cheat_Sheet.html`).

## 12. Limitations & When NOT to Use
- Parameterized queries do not protect against unauthorized access to valid IDs (`IDOR`/`BOLA`) — always pair injection safety with server-side tenant/role authorization (`shadow-auth`).
