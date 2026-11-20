import { existsSync } from "node:fs";
import { mkdir, rename, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { chromium, type Browser, type BrowserContext, type Page } from "playwright";
import { launchOptions, PATHS, resolveUrl, SCENE_GAP_MS, settings } from "./config.ts";
import { Human } from "./human.ts";
import { leftLogin } from "./login.ts";
import { overlayInitScript } from "./overlay.ts";
import type { Action, Tutorial } from "./schema.ts";
import type { TtsManifest } from "./tts/index.ts";
import { resolvePlaceholders, saveVar } from "./vars.ts";

export interface TimelineScene {
  id: string;
  startMs: number; // relative to recording start (page creation)
  endMs: number;
  actionMs: number;
  audioMs: number;
}

/** Recording ranges removed from the final video (manual captcha/OTP waits). */
export interface Cut {
  startMs: number;
  endMs: number;
}

export interface Timeline {
  tutorialId: string;
  video: string;
  viewport: { width: number; height: number };
  canvas: Tutorial["canvas"];
  firstSceneStartMs: number;
  endMs: number;
  cuts: Cut[];
  recordedAt: string;
  scenes: TimelineScene[];
}

export const timelinePath = (id: string) => path.join(PATHS.recordCache, id, "timeline.json");

const DEFAULT_TIMEOUT = 15_000;
/** Human-readable action description. Never contains resolved secrets (placeholders stay literal). */
function describe(a: Action): string {
  switch (a.type) {
    case "goto": return `goto ${a.url}`;
    case "type": return `type ${a.selector} "${/\{\{/.test(a.text) ? a.text : a.text.length > 40 ? a.text.slice(0, 40) + "…" : a.text}"`;
    case "pause": return `pause ${a.ms}ms`;
    case "scroll": return a.to ? `scroll to ${a.to}` : `scroll ${a.deltaY}px${a.within ? ` within ${a.within}` : ""}`;
    case "waitFor": return `waitFor ${[a.selector, a.state, a.url && `url~${a.url}`, a.networkIdle && "networkidle"].filter(Boolean).join(" ")}`;
    case "upload": return `upload ${a.files.join(", ")} via ${a.trigger ?? a.selector}`;
    case "select": return `select ${a.selector} = ${a.value ?? a.label}`;
    case "manual": return `manual: ${a.message}`;
    case "capture": return `capture {{${a.name}}} from ${a.from}${a.selector ? ` ${a.selector}` : ""}`;
    case "setValue": return `setValue ${a.selector} = ${a.value}`;
    case "press": return `press ${a.key}`;
    case "maskText": return `maskText ${a.text}`;
    case "fetchMail": return `fetchMail {{${a.name}}} (${a.extract}) for ${a.to}`;
    case "openUrl": return `openUrl ${/\{\{/.test(a.url) ? a.url : "(literal url)"}`;
    default: return `${a.type} ${a.selector}`;
  }
}

export function urlMatches(url: string, pattern: string): boolean {
  const m = /^\/(.+)\/([dgimsuy]*)$/.exec(pattern); // "/a/b" is a path, "/a.b/i" a regex
  return m ? new RegExp(m[1]!, m[2]).test(url) : url.includes(pattern);
}

async function settle(page: Page, timeout = 10_000) {
  await page.waitForLoadState("load", { timeout }).catch(() => undefined);
  await page.waitForLoadState("networkidle", { timeout }).catch(() => undefined);
  await page.evaluate(() => document.fonts?.ready.then(() => true)).catch(() => undefined);
}

async function runAction(page: Page, human: Human, a: Action, ctx: { cuts: Cut[]; now: () => number; headed: boolean; startedAt: number }): Promise<void> {
  const timeout = "timeout" in a && a.timeout ? a.timeout : DEFAULT_TIMEOUT;
  const loc = (sel: string, nth?: number) => (nth === undefined ? page.locator(sel) : page.locator(sel).nth(nth));
  switch (a.type) {
    case "goto":
      throw new Error("goto is only allowed as the first action"); // validated by schema; defensive
    case "click": {
      if (!a.expect) return human.click(loc(a.selector, a.nth), timeout);
      const tries = 1 + (a.retries ?? 2);
      for (let i = 1; i <= tries; i++) {
        await human.click(loc(a.selector, a.nth), timeout);
        const ok = await loc(a.expect).first().waitFor({ state: "visible", timeout: 5000 }).then(() => true, () => false);
        if (ok) return;
        if (i < tries) console.log(`      (click had no effect, retry ${i}/${tries - 1})`);
      }
      throw new Error(`click ${a.selector}: expected ${a.expect} never appeared`);
    }
    case "hover":
      return human.hover(loc(a.selector, a.nth), timeout, a.ms);
    case "type":
      return human.type(loc(a.selector, a.nth), resolvePlaceholders(a.text), timeout, { clear: a.clear, pressEnter: a.pressEnter, atCaret: a.atCaret });
    case "select": {
      const l = loc(a.selector, a.nth);
      await human.hover(l, timeout);
      await human.fakePress(); // native <select> popups are not captured in video; show the press instead
      await l.selectOption(a.value !== undefined ? { value: a.value } : { label: a.label! }, { timeout });
      return human.wait(350);
    }
    case "scroll": {
      if (a.within) await human.hover(loc(a.within), timeout, 150);
      if (a.to) {
        const l = loc(a.to);
        await l.waitFor({ state: "attached", timeout });
        await human.scrollIntoView(l);
        return human.waitStable(l);
      }
      return human.wheel(a.deltaY!);
    }
    case "waitFor": {
      if (a.selector) await loc(a.selector).waitFor({ state: a.state ?? "visible", timeout });
      if (a.url) await page.waitForURL((u) => urlMatches(u.toString(), a.url!), { timeout });
      if (a.networkIdle) await page.waitForLoadState("networkidle", { timeout });
      return;
    }
    case "pause":
      return human.wait(a.ms);
    case "upload": {
      const files = a.files.map((f) => path.resolve(PATHS.assets, f));
      for (const f of files) if (!existsSync(f)) throw new Error(`upload file not found: ${f}`);
      if (a.trigger) {
        // The native dialog is intercepted (never shown, never recorded); a blurred fake picker stands in for it.
        const [chooser] = await Promise.all([page.waitForEvent("filechooser", { timeout }), human.click(loc(a.trigger), timeout)]);
        await fakeFilePicker(page, human, files.map((f) => path.basename(f)));
        await chooser.setFiles(files);
      } else {
        await fakeFilePicker(page, human, files.map((f) => path.basename(f)));
        await loc(a.selector!).setInputFiles(files, { timeout });
      }
      return human.wait(400);
    }
    case "manual": {
      if (!ctx.headed) throw new Error("manual step needs a headed browser (set HEADED=1, or recordLogin: true with RECORD_LOGIN_HEADED=1)");
      const cutStart = ctx.now();
      console.log(`
  >>> OPERATOR: ${a.message}
      (waiting up to ${Math.round((a.timeout ?? 600_000) / 1000)} s; this segment is cut from the video)
`);
      const wait = a.timeout ?? 600_000;
      if (a.untilUrl) await page.waitForURL((u) => urlMatches(u.toString(), a.untilUrl!), { timeout: wait });
      if (a.untilSelector) await loc(a.untilSelector).waitFor({ state: "visible", timeout: wait });
      await settle(page);
      await human.syncCursor();
      await human.wait(a.settleMs ?? 800);
      ctx.cuts.push({ startMs: cutStart, endMs: ctx.now() });
      return;
    }
    case "capture": {
      let value: string | null | undefined;
      if (a.from === "clipboard") value = await page.evaluate(() => navigator.clipboard.readText());
      else if (a.from === "url") value = page.url();
      else if (a.from === "text") value = await loc(a.selector!).first().innerText({ timeout });
      else value = await loc(a.selector!).first().getAttribute(a.attr!, { timeout });
      if (!value?.trim()) throw new Error(`capture {{${a.name}}}: empty value`);
      saveVar(a.name, value.trim());
      console.log(`      captured {{${a.name}}} (${value.trim().length} chars, value hidden)`);
      return;
    }
    case "setValue": {
      const l = loc(a.selector, a.nth);
      await human.click(l, timeout);
      await l.fill(resolvePlaceholders(a.value), { timeout }); // documented exception: native date/time inputs
      return human.wait(rand(300, 500));
    }
    case "press":
      await page.keyboard.press(a.key);
      return human.wait(350);
    case "fetchMail": {
      const cutStart = ctx.now();
      const value = await fetchMailValue(a, timeout === DEFAULT_TIMEOUT ? 120_000 : timeout, ctx.startedAt);
      saveVar(a.name, value);
      console.log(`      captured {{${a.name}}} from mail (${value.length} chars, value hidden)`);
      ctx.cuts.push({ startMs: cutStart, endMs: ctx.now() });
      return;
    }
    case "openUrl": {
      const cutStart = ctx.now();
      await page.goto(resolvePlaceholders(a.url), { waitUntil: "domcontentloaded", timeout: a.timeout ?? 45_000 });
      await settle(page);
      await human.syncCursor();
      await human.wait(600);
      ctx.cuts.push({ startMs: cutStart, endMs: ctx.now() });
      return;
    }
    case "maskText": {
      const secret = resolvePlaceholders(a.text);
      // Sent as a string: tsx/esbuild would inject __name() helpers into a serialized function.
      await page.evaluate(`(() => {
        const needle = ${JSON.stringify(secret)};
        const blur = (root) => {
          const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
          const hits = [];
          for (let n = walker.nextNode(); n; n = walker.nextNode()) {
            if (n.data.includes(needle) && !(n.parentElement && n.parentElement.closest("[data-pw-mask]"))) hits.push(n);
          }
          for (const t of hits) {
            const target = t.splitText(t.data.indexOf(needle));
            target.splitText(needle.length);
            const span = document.createElement("span");
            span.dataset.pwMask = "1";
            span.style.cssText = "filter:blur(7px);display:inline-block;";
            target.replaceWith(span);
            span.appendChild(target);
          }
        };
        blur(document.body);
        new MutationObserver(() => blur(document.body)).observe(document.body, { subtree: true, childList: true, characterData: true });
      })()`);
      return;
    }
  }
}

const rand = (min: number, max: number) => min + Math.random() * (max - min);

/**
 * Stand-in for the OS file dialog: a picker window whose folder list is blurred (no local paths or
 * file names leak), only the chosen file name is readable. Cursor glides to "Buka" and presses it.
 */
async function fakeFilePicker(page: Page, human: Human, names: string[]): Promise<void> {
  await page.evaluate((fileNames) => {
    const rows = Array.from({ length: 9 }, (_, i) =>
      `<div style="display:flex;gap:10px;align-items:center;padding:7px 10px;border-radius:6px;${i === 4 ? "background:#dbeafe" : ""}">` +
      `<div style="width:18px;height:16px;border-radius:3px;background:${i < 3 ? "#f5c451" : "#1d6f42"}"></div>` +
      `<div style="height:10px;border-radius:5px;background:#cbd5e1;width:${140 + ((i * 53) % 160)}px"></div>` +
      `<div style="margin-left:auto;height:10px;width:70px;border-radius:5px;background:#e2e8f0"></div></div>`,
    ).join("");
    const wrap = document.createElement("div");
    wrap.id = "__pw-picker";
    wrap.setAttribute("aria-hidden", "true");
    wrap.innerHTML =
      `<div style="position:fixed;inset:0;z-index:2147483640;background:rgba(15,23,42,.35);display:flex;align-items:center;justify-content:center;pointer-events:none;font-family:Segoe UI,system-ui,sans-serif;animation:__pwpk .18s ease-out">` +
      `<div style="width:720px;background:#fff;border-radius:10px;box-shadow:0 20px 60px rgba(0,0,0,.35);overflow:hidden">` +
      `<div style="padding:12px 16px;border-bottom:1px solid #e5e7eb;font-size:14px;color:#111827;font-weight:600">Buka</div>` +
      `<div style="display:flex;min-height:300px"><div style="width:170px;border-right:1px solid #e5e7eb;padding:12px;filter:blur(5px)">${rows.slice(0, 5)}</div>` +
      `<div style="flex:1;padding:12px;filter:blur(6px)">${rows}</div></div>` +
      `<div style="display:flex;gap:10px;align-items:center;padding:12px 16px;border-top:1px solid #e5e7eb;font-size:13px;color:#374151">` +
      `<span>Nama file:</span><div style="flex:1;border:1px solid #9ca3af;border-radius:4px;padding:6px 8px;color:#111827">${fileNames.map((n) => n.replace(/</g, "&lt;")).join(", ")}</div>` +
      `<div id="__pw-picker-open" style="padding:7px 22px;border-radius:4px;background:#2563eb;color:#fff;font-weight:600">Buka</div>` +
      `<div style="padding:7px 18px;border-radius:4px;border:1px solid #d1d5db">Batal</div></div></div></div>` +
      `<style>@keyframes __pwpk{from{opacity:0}to{opacity:1}}</style>`;
    document.documentElement.appendChild(wrap);
  }, names);
  await human.wait(900);
  await human.hover(page.locator("#__pw-picker-open"), 5000, 350);
  await human.fakePress();
  await human.wait(250);
  await page.evaluate(() => document.getElementById("__pw-picker")?.remove());
}

/** Poll the staging mail catcher (Mailpit REST API) for the newest matching message and extract an OTP or link. */
async function fetchMailValue(
  a: { to: string; subject?: string; extract: "otp" | "link"; linkContains?: string },
  timeoutMs: number,
  sinceEpochMs: number,
): Promise<string> {
  const base = process.env.MAILPIT_URL?.trim().replace(/\/+$/, "");
  if (!base) throw new Error("MAILPIT_URL is not set in .env");
  const to = resolvePlaceholders(a.to).toLowerCase();
  const since = sinceEpochMs - 5_000; // any mail since the recording started (allow a little clock skew)
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const list = (await (await fetch(`${base}/api/v1/messages?limit=30`)).json()) as {
      messages?: Array<{ ID: string; Created: string; Subject: string; To?: Array<{ Address: string }> }>;
    };
    const hit = (list.messages ?? []).find(
      (m) =>
        Date.parse(m.Created) >= since &&
        (m.To ?? []).some((t) => t.Address.toLowerCase() === to) &&
        (!a.subject || m.Subject.toLowerCase().includes(a.subject.toLowerCase())),
    );
    if (hit) {
      const msg = (await (await fetch(`${base}/api/v1/message/${hit.ID}`)).json()) as { Text?: string; HTML?: string };
      const decode = (x: string) =>
        x.replace(/&#x([0-9a-f]+);/gi, (_m, h: string) => String.fromCharCode(parseInt(h, 16)))
          .replace(/&#(\d+);/g, (_m, d: string) => String.fromCharCode(Number(d)))
          .replace(/&amp;/g, "&");
      const html = decode(msg.HTML ?? "");
      // Prefer real hrefs from the HTML part; the text part wraps links as "[url]" / "(url)".
      const hrefs = [...html.matchAll(/href="([^"]+)"/g)].map((m) => m[1]!);
      const body = `${msg.Text ?? ""}
${html}`;
      if (a.extract === "otp") {
        const m = /\b(\d{6})\b/.exec(msg.Text ?? "") ?? /\b(\d{6})\b/.exec(body);
        if (m) return m[1]!;
      } else {
        const links = [...hrefs, ...(body.match(/https?:\/\/[^\s"'<>()\[\]]+/g) ?? [])];
        const link = links.find((l) => !a.linkContains || l.includes(a.linkContains));
        if (link) return link;
      }
      throw new Error(`mail "${hit.Subject}" found but no ${a.extract} in it`);
    }
    await new Promise((r) => setTimeout(r, 2000));
  }
  throw new Error(`no mail to ${to}${a.subject ? ` with subject ~"${a.subject}"` : ""} within ${Math.round(timeoutMs / 1000)} s`);
}

export class SceneError extends Error {
  constructor(message: string, readonly screenshot?: string) {
    super(message);
  }
}

export interface RecordOptions {
  baseUrl: string;
  storageState?: string;
}

export async function record(t: Tutorial, manifest: TtsManifest, opts: RecordOptions): Promise<Timeline> {
  const dir = path.join(PATHS.recordCache, t.id);
  await rm(dir, { recursive: true, force: true });
  await mkdir(dir, { recursive: true });
  const vp = { width: t.viewport.width, height: t.viewport.height };
  const audio = new Map(manifest.scenes.map((s) => [s.id, s.durationMs]));
  console.log(`[record] ${t.id}: viewport ${vp.width}x${vp.height}${t.viewport.isMobile ? " (mobile)" : ""}, session=${opts.storageState ? "storageState" : "fresh"}`);

  let browser: Browser | undefined;
  let context: BrowserContext | undefined;
  try {
    // Recording the login itself hits Turnstile, which only passes in headed real Chrome,
    // unless RECORD_LOGIN_HEADED=0 (apps without a captcha).
    // CDP_URL: attach to a normally started Chrome (tools/login-chrome.ts style) when Turnstile rejects launched browsers.
    const cdp = process.env.CDP_URL?.trim();
    const headed = settings.headed() || (t.recordLogin && settings.recordLoginHeaded());
    browser = cdp ? await chromium.connectOverCDP(cdp) : await chromium.launch(launchOptions(!headed));
    context = await browser.newContext({
      viewport: vp,
      screen: vp,
      deviceScaleFactor: 1,
      isMobile: t.viewport.isMobile ?? false,
      hasTouch: t.viewport.hasTouch ?? false,
      recordVideo: { dir, size: vp },
      storageState: opts.storageState,
      // No locale/timezoneId emulation: Turnstile flags the mismatch with the OS (error 600010). Uses the OS values.
      colorScheme: "light",
      acceptDownloads: true,
    });
    // "Link Pengemudi" copies via navigator.clipboard; `capture from clipboard` reads it back.
    await context.grantPermissions(["clipboard-read", "clipboard-write"], { origin: new URL(opts.baseUrl).origin });
    // tsx (esbuild keepNames) injects __name() into serialized functions; provide a no-op in the page.
    const overlay = `(() => { const __name = (f) => f; (${overlayInitScript.toString()})(${JSON.stringify({
      background: t.backgroundColor,
      hideScrollbars: t.hideScrollbars,
      cursor: t.cursor,
      start: t.cursorStart,
    })}); })();`;
    await context.addInitScript({ content: overlay });
    if (Object.keys(t.localStorage).length > 0) {
      await context.addInitScript({
        content: `(() => { try { const kv = ${JSON.stringify(t.localStorage)}; for (const k in kv) localStorage.setItem(k, kv[k]); } catch {} })();`,
      });
    }

    const page = await context.newPage();
    const t0 = performance.now(); // video starts at page creation; scene times are relative to this
    const now = () => Math.round(performance.now() - t0);
    const human = new Human(page, { x: Math.round(vp.width * t.cursorStart.x), y: Math.round(vp.height * t.cursorStart.y) });
    page.on("domcontentloaded", () => void human.syncCursor());

    // Pre-roll (trimmed from the final video): the only goto.
    const first = t.scenes[0]!.actions[0]!;
    if (first.type !== "goto") throw new Error("first action must be goto");
    const url = resolveUrl(opts.baseUrl, resolvePlaceholders(first.url));
    console.log(`  pre-roll: goto ${/\{\{/.test(first.url) ? first.url : url}`); // never print captured tokens
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: first.timeout ?? 45_000 });
    await settle(page);
    if (!t.recordLogin && opts.storageState && leftLogin(url) && !leftLogin(page.url())) {
      throw new Error(`Redirected to ${page.url()}: saved session expired. Run: npm run login`);
    }
    await human.syncCursor();
    await human.wait(500);

    const scenes: TimelineScene[] = [];
    const cuts: Cut[] = [];
    const startedAt = Date.now(); // wall clock, for mail-catcher lookups
    for (const [si, scene] of t.scenes.entries()) {
      const startMs = now();
      const audioMs = audio.get(scene.id) ?? 0;
      console.log(`  scene ${scene.id} @ ${(startMs / 1000).toFixed(2)}s (audio ${(audioMs / 1000).toFixed(2)}s)`);
      for (const [ai, action] of scene.actions.entries()) {
        if (si === 0 && ai === 0) continue; // goto already done in pre-roll
        console.log(`    > ${describe(action)}`);
        try {
          await runAction(page, human, action, { cuts, now, headed, startedAt });
        } catch (e) {
          if ("optional" in action && action.optional) {
            console.log(`      (optional, skipped: ${(e as Error).message.split("\n")[0]})`);
            continue;
          }
          const shot = path.join(PATHS.errors, `${t.id}__${scene.id}__a${ai}__${new Date().toISOString().replace(/[:.]/g, "-")}.png`);
          await mkdir(PATHS.errors, { recursive: true });
          await page.screenshot({ path: shot }).catch(() => undefined);
          throw new SceneError(
            `Scene "${scene.id}" action #${ai} (${describe(action)}) failed on ${page.url().replace(/([?&]token=)[^&]+/, "$1***")}\n  ${(e as Error).message.split("\n")[0]}\n  screenshot: ${shot}`,
            shot,
          );
        }
      }
      const actionMs = now() - startMs;
      // Time inside this scene that will be cut from the video does not count as narration time.
      const cutMs = cuts.filter((c) => c.startMs >= startMs).reduce((sum, c) => sum + (c.endMs - c.startMs), 0);
      // Scene length = max(action, audio) + gap; cursor stays still while narration finishes.
      await new Promise((r) => setTimeout(r, Math.max(0, audioMs - (actionMs - cutMs)) + SCENE_GAP_MS));
      scenes.push({ id: scene.id, startMs, endMs: now(), actionMs, audioMs });
    }
    await new Promise((r) => setTimeout(r, 700)); // tail
    const endMs = now();

    // The app rotates its refresh token on use: write the reused session back, or the next tutorial starts logged out.
    if (!t.recordLogin && opts.storageState) await context.storageState({ path: opts.storageState });
    if (t.saveSession) {
      await mkdir(PATHS.auth, { recursive: true });
      const file = path.join(PATHS.auth, `${t.saveSession}.json`);
      await context.storageState({ path: file });
      console.log(`[record] session saved -> ${file} (tokens: keep private, git-ignored)`);
    }
    const video = page.video();
    await context.close(); // finalizes the .webm
    context = undefined;
    const raw = video ? await video.path() : undefined;
    if (!raw || !existsSync(raw)) throw new Error("Playwright produced no video file");
    const videoFile = path.join(dir, "raw.webm");
    await rename(raw, videoFile);

    const timeline: Timeline = {
      tutorialId: t.id,
      video: videoFile,
      viewport: vp,
      canvas: t.canvas,
      firstSceneStartMs: scenes[0]!.startMs,
      endMs,
      cuts,
      recordedAt: new Date().toISOString(),
      scenes,
    };
    await writeFile(timelinePath(t.id), JSON.stringify(timeline, null, 2), "utf8");
    console.log(`[record] video -> ${videoFile}\n[record] timeline -> ${timelinePath(t.id)}`);
    return timeline;
  } finally {
    // Also on failure: keep the rotated tokens so a re-run is still logged in.
    if (context && !t.recordLogin && opts.storageState) await context.storageState({ path: opts.storageState }).catch(() => undefined);
    await context?.close().catch(() => undefined);
    await browser?.close().catch(() => undefined);
  }
}
