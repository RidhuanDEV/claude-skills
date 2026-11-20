import { existsSync, mkdirSync } from "node:fs";
import path from "node:path";
import { chromium, type Page } from "playwright";
import { baseUrl, launchOptions, PATHS, resolveUrl } from "./config.ts";
import { project } from "./project.ts";

/**
 * Selector research: log in as a role, open a route through the SPA router, run steps, then print the
 * ARIA snapshot so scripts use real accessible names and roles. No recording, no TTS.
 *
 *   npm run snapshot -- LOGIN /dashboard
 *   npm run snapshot -- ADMIN /users "role=button[name=\"Tambah\"]" "fill:#name::Demo – Budi" "press:Escape"
 *
 * Steps: "<selector>" clicks, "fill:<selector>::<text>", "press:<key>", "upload:<selector>::<file in assets/>".
 * Sessions are cached per role in cache/snapshot-auth/<ROLE>.json. Credentials are never printed.
 * Clicks can create data (drafts); reset the recording database before recording.
 * Git Bash rewrites "/route" arguments: set MSYS_NO_PATHCONV=1.
 */
async function settle(page: Page): Promise<void> {
  await page.waitForLoadState("networkidle").catch(() => undefined);
  await page.waitForTimeout(1200);
}

export async function snapshot(role: string, route: string, steps: string[]): Promise<void> {
  const cfg = project();
  if (!cfg.rolePrefixes.includes(role)) throw new Error(`Role "${role}" is not in video.config.json rolePrefixes (${cfg.rolePrefixes.join(", ")})`);
  const identity = process.env[`${role}_EMAIL`]?.trim();
  const password = process.env[`${role}_PASSWORD`]?.trim();
  if (!identity || !password) throw new Error(`${role}_EMAIL or ${role}_PASSWORD is empty in .env`);
  const base = baseUrl();
  const authFile = path.join(PATHS.snapshotAuth, `${role}.json`);
  const browser = await chromium.launch(launchOptions(true));
  try {
    const context = await browser.newContext({
      viewport: { width: 1920, height: 1080 },
      storageState: existsSync(authFile) ? authFile : undefined,
    });
    const page = await context.newPage();
    await page.goto(resolveUrl(base, cfg.login.landing));
    await settle(page);
    if (new URL(page.url()).pathname.startsWith(cfg.login.path)) {
      await page.goto(resolveUrl(base, cfg.login.path));
      await page.locator(cfg.login.username).fill(identity);
      await page.locator(cfg.login.password).fill(password);
      await page.locator(cfg.login.submit).click();
      await page.waitForURL((u) => !u.pathname.startsWith(cfg.login.path), { timeout: 20_000 });
      await settle(page);
    }
    mkdirSync(PATHS.snapshotAuth, { recursive: true });
    await context.storageState({ path: authFile });

    // SPA navigation: a full reload can let route guards redirect before the session is restored.
    await page.evaluate((target) => {
      window.history.pushState({}, "", target);
      window.dispatchEvent(new PopStateEvent("popstate"));
    }, route);
    await settle(page);
    for (const step of steps) {
      if (step.startsWith("fill:")) {
        const [selector = "", text = ""] = step.slice("fill:".length).split("::");
        await page.locator(selector).fill(text, { timeout: 15_000 });
      } else if (step.startsWith("press:")) {
        await page.keyboard.press(step.slice("press:".length));
      } else if (step.startsWith("upload:")) {
        const [selector = "", file = ""] = step.slice("upload:".length).split("::");
        await page.locator(selector).setInputFiles(path.join(PATHS.assets, file));
      } else {
        await page.locator(step).click({ timeout: 15_000 });
      }
      await page.waitForTimeout(800);
    }
    // Toasts do not always appear in the ARIA tree, so keep a screenshot too.
    const shot = path.join(PATHS.cache, "snapshot.png");
    await page.screenshot({ path: shot });
    console.log(`URL: ${page.url()}\nScreenshot: ${shot}`);
    console.log(await page.locator("body").ariaSnapshot());
  } finally {
    await browser.close();
  }
}
