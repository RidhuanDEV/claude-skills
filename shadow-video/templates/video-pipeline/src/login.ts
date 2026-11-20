import { existsSync } from "node:fs";
import { mkdir } from "node:fs/promises";
import { createInterface } from "node:readline/promises";
import { chromium } from "playwright";
import { baseUrl, credentials, launchOptions, PATHS, resolveUrl, settings } from "./config.ts";
import { project } from "./project.ts";

/** Login path and selectors come from video.config.json `login`, traced from the app source (read lazily). */
const SEL = () => project().login;

const leftLogin = (url: string) => {
  const p = new URL(url).pathname;
  return !p.startsWith(SEL().path) && !SEL().alsoUnauthenticated.some((prefix) => p.startsWith(prefix));
};

/** Headed browser; the human logs in (captcha/OTP), then storageState is saved. */
export async function manualLogin(): Promise<void> {
  const url = resolveUrl(baseUrl(), SEL().path);
  await mkdir(PATHS.auth, { recursive: true });
  const browser = await chromium.launch(launchOptions(false));
  try {
    const context = await browser.newContext({ viewport: { width: 1366, height: 820 } }); // no locale emulation (Turnstile 600010)
    const page = await context.newPage();
    await page.goto(url, { waitUntil: "domcontentloaded" });
    const email = credentials.email();
    if (email) await page.locator(SEL().username).fill(email).catch(() => undefined); // convenience only; not recorded
    console.log(`[login] Browser opened at ${url}`);
    console.log("[login] Log in by hand (solve captcha / OTP). The session is saved automatically once you leave /login,");
    console.log("[login] or press Enter here to save the current state now.");

    const rl = createInterface({ input: process.stdin, output: process.stdout });
    const ac = new AbortController();
    const viaEnter = rl.question("", { signal: ac.signal }).then(() => "enter" as const).catch(() => "aborted" as const);
    const viaNav = page
      .waitForURL((u) => leftLogin(u.toString()), { timeout: 10 * 60_000 })
      .then(async () => {
        await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => undefined);
        return "navigated" as const;
      })
      .catch(() => "timeout" as const);
    const how = await Promise.race([viaEnter, viaNav]);
    ac.abort();
    rl.close();
    if (how === "timeout") throw new Error("Manual login timed out after 10 minutes; nothing saved.");
    await context.storageState({ path: PATHS.storageState });
    console.log(`[login] Saved session (${how}) -> ${PATHS.storageState}  (contains tokens: keep private, git-ignored)`);
  } finally {
    await browser.close();
  }
}

/** Headed (Turnstile), un-recorded login with .env credentials. Fails clearly when captcha/OTP blocks it. */
export async function autoLogin(): Promise<void> {
  const email = credentials.email();
  const password = credentials.password();
  if (!email || !password) throw new Error("LOGIN_EMAIL / LOGIN_PASSWORD missing in .env (or use manual: npm run login)");
  const url = resolveUrl(baseUrl(), SEL().path);
  await mkdir(PATHS.auth, { recursive: true });
  // Headed secara bawaan (Turnstile menolak headless); RECORD_LOGIN_HEADED=0 untuk aplikasi tanpa captcha.
  const browser = await chromium.launch(launchOptions(!(settings.headed() || settings.recordLoginHeaded())));
  try {
    const context = await browser.newContext({ viewport: { width: 1366, height: 820 } }); // no locale emulation (Turnstile 600010)
    const page = await context.newPage();
    await page.goto(url, { waitUntil: "domcontentloaded" });
    await page.locator(SEL().username).fill(email, { timeout: 20_000 }); // not recorded => fill() is fine here
    await page.locator(SEL().password).fill(password);
    const submit = page.locator(SEL().submit);
    try {
      await submit.click({ timeout: 45_000 }); // waits until Turnstile enables the button
    } catch {
      throw new Error(
        "Login button stayed disabled (most likely Cloudflare Turnstile captcha is enabled on staging). Use manual login: npm run login",
      );
    }
    try {
      await page.waitForURL((u) => leftLogin(u.toString()), { timeout: 30_000 });
    } catch {
      throw new Error("Still on /login after submit (wrong credentials, captcha, or OTP step). Use manual login: npm run login");
    }
    await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => undefined);
    await context.storageState({ path: PATHS.storageState });
    console.log(`[login] Auto login OK as ${email} -> ${PATHS.storageState}`);
  } finally {
    await browser.close();
  }
}

export async function ensureStorageState(): Promise<string> {
  if (existsSync(PATHS.storageState)) return PATHS.storageState;
  console.log("[login] No saved session; trying automatic login...");
  await autoLogin();
  return PATHS.storageState;
}

export { leftLogin };
