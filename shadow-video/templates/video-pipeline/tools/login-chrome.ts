/**
 * Login fallback when Turnstile rejects Playwright-launched browsers: start a NORMAL Google Chrome
 * process (dedicated profile in auth/chrome-profile, remote debugging on localhost only), let the
 * operator log in by hand, then attach over CDP just to save the session to auth/<name>.json.
 *   npx tsx tools/login-chrome.ts [sessionName=storageState]
 */
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";
import { baseUrl, PATHS } from "../src/config.ts";

const name = process.argv[2] ?? "storageState";
const PORT = 9333;
const candidates = [
  process.env.CHROME_PATH,
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
  path.join(process.env.LOCALAPPDATA ?? "", "Google/Chrome/Application/chrome.exe"),
].filter(Boolean) as string[];
const chrome = candidates.find((p) => existsSync(p));
if (!chrome) throw new Error(`Google Chrome not found. Set CHROME_PATH in .env. Tried: ${candidates.join(", ")}`);

const profile = path.join(PATHS.auth, "chrome-profile");
await mkdir(profile, { recursive: true });
const loginUrl = `${baseUrl()}/login`;
const child = spawn(chrome, [`--remote-debugging-port=${PORT}`, "--remote-debugging-address=127.0.0.1", `--user-data-dir=${profile}`, "--no-first-run", "--new-window", loginUrl], {
  detached: true,
  stdio: "ignore",
});
child.unref();
console.log(`[login-chrome] Chrome opened at ${loginUrl}. Log in by hand (captcha/OTP). Waiting up to 15 minutes...`);

const origin = new URL(baseUrl()).origin;
const deadline = Date.now() + 15 * 60_000;
let saved = false;
while (Date.now() < deadline && !saved) {
  await new Promise((r) => setTimeout(r, 2000));
  let browser;
  try {
    browser = await chromium.connectOverCDP(`http://127.0.0.1:${PORT}`);
  } catch {
    continue; // Chrome still starting
  }
  try {
    const ctx = browser.contexts()[0];
    const page = ctx?.pages().find((p) => p.url().startsWith(origin) && !/\/(login|register)(\b|$)/.test(new URL(p.url()).pathname));
    if (ctx && page) {
      await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => undefined);
      await mkdir(PATHS.auth, { recursive: true });
      const file = path.join(PATHS.auth, `${name}.json`);
      // ctx.storageState() over CDP comes back empty for the default context: build it by hand.
      const localStorage = await page.evaluate(() => Object.entries(window.localStorage).map(([name, value]) => ({ name, value })));
      const cookies = await ctx.cookies(origin);
      if (localStorage.length === 0 && cookies.length === 0) throw new Error("Logged-in page has no localStorage/cookies to save");
      await writeFile(file, JSON.stringify({ cookies, origins: [{ origin, localStorage }] }, null, 2), "utf8");
      console.log(`[login-chrome] captured ${localStorage.length} localStorage key(s), ${cookies.length} cookie(s)`);
      console.log(`[login-chrome] Session saved -> ${file} (tokens: keep private, git-ignored). You can close that Chrome window.`);
      saved = true;
    }
  } finally {
    // Detach only; never close the operator's Chrome window from here.
    await browser.close().catch(() => undefined);
  }
}
if (!saved) {
  console.error("[login-chrome] Timed out after 15 minutes; nothing saved.");
  process.exitCode = 1;
}
