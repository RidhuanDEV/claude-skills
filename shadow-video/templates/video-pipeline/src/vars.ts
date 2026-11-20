import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { credentials, PATHS } from "./config.ts";
import { isRoleVar } from "./project.ts";

/**
 * {{NAME}} placeholders for scene `text` / `value` / `goto.url`:
 *  - LOGIN_EMAIL, LOGIN_PASSWORD and <PREFIX>_* for every prefix in video.config.json rolePrefixes, from .env (never logged)
 *  - TOMORROW_DATE / TOMORROW_0800         computed (local time), for date & datetime-local inputs
 *  - NOW_PLUS_1H, NOW_PLUS_2H              computed datetime-local
 *  - anything stored by a `capture` action (cache/vars.json, e.g. DRIVER_URL)
 * Captured values may be secrets (tokens in links); they are never printed.
 */
const varsFile = path.join(PATHS.cache, "vars.json");
const PLACEHOLDER = /\{\{\s*([A-Z][A-Z0-9_]*)\s*\}\}/g;

function readVars(): Record<string, string> {
  if (!existsSync(varsFile)) return {};
  return JSON.parse(readFileSync(varsFile, "utf8")) as Record<string, string>;
}

export function saveVar(name: string, value: string): void {
  const all = readVars();
  all[name] = value;
  mkdirSync(path.dirname(varsFile), { recursive: true });
  writeFileSync(varsFile, JSON.stringify(all, null, 2), "utf8");
}

const p2 = (n: number) => String(n).padStart(2, "0");
const ymd = (d: Date) => `${d.getFullYear()}-${p2(d.getMonth() + 1)}-${p2(d.getDate())}`;
const local = (d: Date) => `${ymd(d)}T${p2(d.getHours())}:${p2(d.getMinutes())}`;

function builtin(name: string): string | undefined {
  const now = new Date();
  const tomorrow = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 8, 0);
  switch (name) {
    case "LOGIN_EMAIL": return credentials.email();
    case "LOGIN_PASSWORD": return credentials.password();
    case "TOMORROW_DATE": return ymd(tomorrow);
    case "TOMORROW_0800": return local(tomorrow);
    case "NOW_PLUS_1H": return local(new Date(now.getTime() + 3_600_000));
    case "NOW_PLUS_2H": return local(new Date(now.getTime() + 7_200_000));
    default:
      // Extra demo accounts (e.g. ADMIN_EMAIL / ADMIN_PASSWORD) come from .env, never from scene files.
      return isRoleVar(name) ? process.env[name]?.trim() || undefined : undefined;
  }
}

export function resolvePlaceholders(text: string): string {
  let stored: Record<string, string> | undefined;
  return text.replace(PLACEHOLDER, (_m, name: string) => {
    const v = builtin(name) ?? (stored ??= readVars())[name];
    if (!v) {
      throw new Error(
        isRoleVar(name)
          ? `{{${name}}} used but ${name} is empty in .env`
          : `Unknown or empty placeholder {{${name}}}. Built-ins: LOGIN_EMAIL, LOGIN_PASSWORD, TOMORROW_DATE, TOMORROW_0800, NOW_PLUS_1H, NOW_PLUS_2H; or record the tutorial that captures it first.`,
      );
    }
    return v;
  });
}
