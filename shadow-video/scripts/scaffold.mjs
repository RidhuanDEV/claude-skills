#!/usr/bin/env node
/**
 * Copy the shadow-video engine into a project, or refresh the engine of an existing pipeline.
 *
 *   node scaffold.mjs <project-dir>                 # creates <project-dir>/video-pipeline (refuses if it exists)
 *   node scaffold.mjs <project-dir> --update-engine # overwrites ENGINE files only, after a dry-run listing
 *   node scaffold.mjs <project-dir> --update-engine --apply
 *
 * Engine files: src/**, tools/naskah.py, tools/login-chrome.ts, tools/chrome-cdp.ts, tsconfig.json.
 * Never touched: video.config.json, .env, scenes/, tutorial/, assets/, auth/, cache/, output/, tools/build-*.py,
 * package.json and package-lock.json (dependency changes are reported, not applied).
 * Uses only Node built-ins, so it runs the same on every agent host (Windows, macOS, Linux).
 */
import { cpSync, existsSync, mkdirSync, readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const TEMPLATE = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "templates", "video-pipeline");
const ENGINE = ["src", "tools/naskah.py", "tools/login-chrome.ts", "tools/chrome-cdp.ts", "tsconfig.json"];
const SKIP = new Set(["node_modules", "cache", "output", "auth", ".env", "__pycache__"]);

const args = process.argv.slice(2);
const projectDir = args.find((a) => !a.startsWith("--"));
const update = args.includes("--update-engine");
const apply = args.includes("--apply");

if (!projectDir) {
  console.error("Usage: node scaffold.mjs <project-dir> [--update-engine [--apply]]");
  process.exit(2);
}
const target = path.resolve(projectDir, "video-pipeline");

function files(dir, base = dir) {
  return readdirSync(dir).flatMap((name) => {
    if (SKIP.has(name)) return [];
    const full = path.join(dir, name);
    return statSync(full).isDirectory() ? files(full, base) : [path.relative(base, full)];
  });
}

if (!update) {
  if (existsSync(target)) {
    console.error(`REFUSED: ${target} already exists. Use --update-engine to refresh engine files only.`);
    process.exit(1);
  }
  cpSync(TEMPLATE, target, { recursive: true, filter: (src) => !SKIP.has(path.basename(src)) });
  mkdirSync(path.join(target, "assets", "brand"), { recursive: true });
  console.log(`Created ${target} (${files(target).length} files).`);
  console.log(`Next:
  1. cd "${target}"
  2. npm ci
  3. copy .env.example to .env, fill BASE_URL (local/staging), BLOCKED_HOSTS (production host), demo accounts
  4. edit video.config.json: appName, brand logos, login selectors traced from the app source, rolePrefixes
  5. npm run doctor ; npm run typecheck ; npm run selftest -- --e2e`);
  process.exit(0);
}

if (!existsSync(target)) {
  console.error(`REFUSED: ${target} does not exist. Run without --update-engine to create it.`);
  process.exit(1);
}
const changed = [];
for (const entry of ENGINE) {
  const src = path.join(TEMPLATE, entry);
  const list = statSync(src).isDirectory() ? files(src).map((f) => path.join(entry, f)) : [entry];
  for (const rel of list) {
    const from = path.join(TEMPLATE, rel);
    const to = path.join(target, rel);
    const same = existsSync(to) && readFileSync(to).equals(readFileSync(from));
    if (!same) changed.push(rel);
  }
}
const tplPkg = JSON.parse(readFileSync(path.join(TEMPLATE, "package.json"), "utf8"));
const pkgFile = path.join(target, "package.json");
const pkg = existsSync(pkgFile) ? JSON.parse(readFileSync(pkgFile, "utf8")) : { dependencies: {}, devDependencies: {}, scripts: {} };
const depNotes = [];
for (const field of ["dependencies", "devDependencies"]) {
  for (const [name, version] of Object.entries(tplPkg[field] ?? {})) {
    if ((pkg[field] ?? {})[name] !== version) depNotes.push(`${field}.${name}: project ${(pkg[field] ?? {})[name] ?? "(missing)"} -> template ${version}`);
  }
}
for (const [name, cmd] of Object.entries(tplPkg.scripts ?? {})) {
  if ((pkg.scripts ?? {})[name] !== cmd) depNotes.push(`scripts.${name}: "${(pkg.scripts ?? {})[name] ?? "(missing)"}" -> "${cmd}"`);
}
console.log(changed.length ? `Engine files that differ (${changed.length}):\n  ${changed.join("\n  ")}` : "Engine files already match the template.");
if (depNotes.length) console.log(`package.json differences (apply by hand, then npm install):\n  ${depNotes.join("\n  ")}`);
if (!existsSync(path.join(target, "video.config.json"))) {
  console.log("NOTE: video.config.json is missing. The refreshed engine needs it: copy it from the template and fill it in.");
}
if (!apply) {
  console.log("Dry run only. Review the list (project-specific edits in these files would be lost), then add --apply.");
  process.exit(0);
}
for (const rel of changed) {
  mkdirSync(path.dirname(path.join(target, rel)), { recursive: true });
  cpSync(path.join(TEMPLATE, rel), path.join(target, rel));
}
console.log(`Updated ${changed.length} engine file(s). Run: npm run typecheck ; npm run selftest -- --e2e`);
