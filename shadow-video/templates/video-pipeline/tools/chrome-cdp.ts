/**
 * Start a NORMAL Google Chrome with remote debugging (localhost only) and a throwaway profile, for
 * recordings whose login hits Cloudflare Turnstile (Playwright-launched browsers are rejected).
 *   npx tsx tools/chrome-cdp.ts start   -> prints CDP_URL to use:  $env:CDP_URL="http://127.0.0.1:9334"; npm run build:video -- 01-login-orientasi
 *   npx tsx tools/chrome-cdp.ts stop    -> closes that Chrome
 */
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { mkdir, rm } from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";
import { PATHS } from "../src/config.ts";

const PORT = 9334;
const url = `http://127.0.0.1:${PORT}`;
const profile = path.join(PATHS.cache, "chrome-cdp-profile");
const cmd = process.argv[2] ?? "start";

if (cmd === "stop") {
  const b = await chromium.connectOverCDP(url).catch(() => undefined);
  if (b) await (await b.newBrowserCDPSession()).send("Browser.close").catch(() => undefined);
  await rm(profile, { recursive: true, force: true }).catch(() => undefined);
  console.log("[chrome-cdp] stopped");
} else {
  const chrome = [process.env.CHROME_PATH, "C:/Program Files/Google/Chrome/Application/chrome.exe", "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"]
    .filter(Boolean)
    .find((p) => existsSync(p!));
  if (!chrome) throw new Error("Google Chrome not found (set CHROME_PATH)");
  await rm(profile, { recursive: true, force: true }).catch(() => undefined);
  await mkdir(profile, { recursive: true });
  spawn(chrome, [`--remote-debugging-port=${PORT}`, "--remote-debugging-address=127.0.0.1", `--user-data-dir=${profile}`, "--no-first-run", "--window-size=1920,1080", "about:blank"], {
    detached: true,
    stdio: "ignore",
  }).unref();
  for (let i = 0; i < 30; i++) {
    const b = await chromium.connectOverCDP(url).catch(() => undefined);
    if (b) {
      await b.close();
      console.log(`[chrome-cdp] ready: CDP_URL=${url}`);
      process.exit(0);
    }
    await new Promise((r) => setTimeout(r, 1000));
  }
  throw new Error("Chrome did not open the debugging port");
}
