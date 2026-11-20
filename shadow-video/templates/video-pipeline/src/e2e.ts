import { existsSync } from "node:fs";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { chromium, type Page } from "playwright";
import { baseUrl, launchOptions, PATHS, resolveUrl, settings } from "./config.ts";
import { urlMatches } from "./recorder.ts";
import type { Action, Tutorial } from "./schema.ts";
import { resolvePlaceholders } from "./vars.ts";

/**
 * GUI end-to-end run of a scene file: the same actions as the video, without recording, TTS or the fake
 * cursor. Proves every selector and every waitFor before a recording, and doubles as a click-through
 * E2E test. Recording-only actions (maskText, capture, fetchMail, manual) are skipped and reported as SKIP.
 * Locators are strict like the recorder: more than one match without `nth` fails.
 */
const DEFAULT_TIMEOUT = 15_000;

export interface E2eOptions {
  headed: boolean;
  /** Screenshot at the end of every scene (layout evidence), not only on failure. */
  shots: boolean;
  /** Save a Playwright trace (open with: npx playwright show-trace <file>). */
  trace: boolean;
  /** Milliseconds between Playwright operations, so a person can follow a headed run. */
  slowMo: number;
}

type Status = "PASS" | "FAIL" | "SKIP";
interface StepResult {
  scene: string;
  index: number;
  type: Action["type"];
  status: Status;
  detail: string;
  ms: number;
}
export interface E2eReport {
  tutorialId: string;
  baseUrl: string;
  startedAt: string;
  headed: boolean;
  status: "PASS" | "FAIL";
  passed: number;
  failed: number;
  skipped: number;
  steps: StepResult[];
  screenshots: string[];
  trace?: string;
}

const RECORDING_ONLY = new Set<Action["type"]>(["maskText", "capture", "fetchMail", "manual"]);

async function runAction(page: Page, base: string, action: Action): Promise<string> {
  const timeout = "timeout" in action && action.timeout !== undefined ? action.timeout : DEFAULT_TIMEOUT;
  switch (action.type) {
    case "goto":
    case "openUrl":
      await page.goto(resolveUrl(base, resolvePlaceholders(action.url)), { waitUntil: "domcontentloaded", timeout });
      return action.url;
    case "click": {
      const target = action.nth === undefined ? page.locator(action.selector) : page.locator(action.selector).nth(action.nth);
      await target.click({ timeout });
      if (action.expect) await page.locator(action.expect).first().waitFor({ state: "visible", timeout: DEFAULT_TIMEOUT });
      return action.selector;
    }
    case "type": {
      const target = action.nth === undefined ? page.locator(action.selector) : page.locator(action.selector).nth(action.nth);
      if (action.atCaret) {
        await target.waitFor({ state: "visible", timeout });
        await page.keyboard.type(resolvePlaceholders(action.text));
      } else {
        if (action.clear) await target.fill("", { timeout });
        await target.fill(resolvePlaceholders(action.text), { timeout });
      }
      if (action.pressEnter) await page.keyboard.press("Enter");
      return action.selector; // never the typed text: it may be a credential
    }
    case "hover": {
      // Same as the recorder: the cursor may point at a disabled control while it is explained.
      const target = action.nth === undefined ? page.locator(action.selector) : page.locator(action.selector).nth(action.nth);
      await target.waitFor({ state: "visible", timeout });
      await target.hover({ force: true, timeout });
      return action.selector;
    }
    case "scroll":
      if (action.to) {
        await page.locator(action.to).scrollIntoViewIfNeeded({ timeout });
        return action.to;
      }
      if (action.within) await page.locator(action.within).hover({ timeout });
      await page.mouse.wheel(0, action.deltaY ?? 0);
      return `deltaY ${action.deltaY ?? 0}`;
    case "select": {
      const target = action.nth === undefined ? page.locator(action.selector) : page.locator(action.selector).nth(action.nth);
      await target.selectOption(action.value ?? { label: action.label ?? "" }, { timeout });
      return action.selector;
    }
    case "setValue":
      await page.locator(action.selector).nth(action.nth ?? 0).fill(resolvePlaceholders(action.value), { timeout });
      return action.selector;
    case "waitFor":
      if (action.selector) await page.locator(action.selector).waitFor({ state: action.state ?? "visible", timeout });
      if (action.url) {
        const pattern = action.url;
        await page.waitForURL((u) => urlMatches(u.toString(), pattern), { timeout });
      }
      if (action.networkIdle) await page.waitForLoadState("networkidle", { timeout }).catch(() => undefined);
      return action.selector ?? action.url ?? "networkIdle";
    case "press":
      await page.keyboard.press(action.key);
      return action.key;
    case "pause":
      await page.waitForTimeout(Math.min(action.ms, 300));
      return `${action.ms} ms (shortened to 300 ms)`;
    case "upload": {
      // Real upload, so the validation and save steps after it are exercised too.
      const files = action.files.map((file) => path.resolve(PATHS.assets, file));
      const missing = files.filter((f) => !existsSync(f));
      if (missing.length) throw new Error(`upload file(s) missing in assets/: ${missing.join(", ")}`);
      if (action.trigger) {
        const [chooser] = await Promise.all([
          page.waitForEvent("filechooser", { timeout }),
          page.locator(action.trigger).click({ timeout }),
        ]);
        await chooser.setFiles(files);
      } else if (action.selector) {
        await page.locator(action.selector).setInputFiles(files, { timeout });
      }
      return action.files.join(", ");
    }
    default:
      return action.type;
  }
}

const firstLine = (e: unknown) => (e instanceof Error ? e.message : String(e)).split("\n")[0] ?? "";

export async function e2e(t: Tutorial, opts: E2eOptions, base: string = baseUrl()): Promise<E2eReport> {
  const dir = path.join(PATHS.e2e, t.id);
  await mkdir(dir, { recursive: true });
  const report: E2eReport = {
    tutorialId: t.id, baseUrl: base, startedAt: new Date().toISOString(), headed: opts.headed,
    status: "PASS", passed: 0, failed: 0, skipped: 0, steps: [], screenshots: [],
  };
  const browser = await chromium.launch({ ...launchOptions(!opts.headed), slowMo: opts.slowMo });
  try {
    const useSession = !t.recordLogin;
    const session = t.session === "storageState" ? PATHS.storageState : path.join(PATHS.auth, `${t.session}.json`);
    if (useSession && !existsSync(session)) throw new Error(`Session ${session} missing. Run: npm run login -- --auto`);
    const context = await browser.newContext({
      viewport: { width: t.viewport.width, height: t.viewport.height },
      isMobile: t.viewport.isMobile,
      hasTouch: t.viewport.hasTouch,
      ...(useSession ? { storageState: session } : {}),
    });
    if (Object.keys(t.localStorage).length) {
      await context.addInitScript((entries: Record<string, string>) => {
        for (const [k, v] of Object.entries(entries)) window.localStorage.setItem(k, v);
      }, t.localStorage);
    }
    if (opts.trace) await context.tracing.start({ screenshots: true, snapshots: true });
    const page = await context.newPage();
    let stop = false;
    for (const scene of t.scenes) {
      if (stop) break;
      for (const [index, action] of scene.actions.entries()) {
        const started = Date.now();
        const push = (status: Status, detail: string) => {
          report.steps.push({ scene: scene.id, index, type: action.type, status, detail, ms: Date.now() - started });
          console.log(`${status.padEnd(4)} ${scene.id} #${index} ${action.type} ${detail}`);
        };
        if (RECORDING_ONLY.has(action.type)) {
          report.skipped++;
          push("SKIP", "recording-only action");
          continue;
        }
        try {
          push("PASS", await runAction(page, base, action));
          report.passed++;
        } catch (e: unknown) {
          if (action.optional) {
            report.skipped++;
            push("SKIP", `optional: ${firstLine(e)}`);
            continue;
          }
          report.failed++;
          push("FAIL", `${firstLine(e)} @ ${page.url().replace(/([?&]token=)[^&]+/, "$1***")}`);
          const shot = path.join(dir, `FAIL-${scene.id}-a${index}.png`);
          await page.screenshot({ path: shot }).catch(() => undefined);
          report.screenshots.push(shot);
          // Later steps depend on this one; continuing would only produce follow-up failures.
          stop = true;
          break;
        }
      }
      if (opts.shots && !stop) {
        const shot = path.join(dir, `${scene.id}.png`);
        await page.screenshot({ path: shot }).catch(() => undefined);
        report.screenshots.push(shot);
      }
    }
    if (opts.trace) {
      report.trace = path.join(dir, "trace.zip");
      await context.tracing.stop({ path: report.trace });
    }
  } finally {
    await browser.close();
  }
  report.status = report.failed === 0 ? "PASS" : "FAIL";
  await writeFile(path.join(dir, "report.json"), JSON.stringify(report, null, 2), "utf8");
  const md = [
    `# E2E ${t.id}: ${report.status}`,
    "",
    `- Base URL: ${base}`,
    `- Started: ${report.startedAt} (${report.headed ? "headed" : "headless"})`,
    `- PASS ${report.passed}, FAIL ${report.failed}, SKIP ${report.skipped}`,
    ...(report.trace ? [`- Trace: ${report.trace}`] : []),
    "",
    "| Scene | # | Action | Status | Detail | ms |",
    "| --- | ---: | --- | --- | --- | ---: |",
    ...report.steps.map((s) => `| ${s.scene} | ${s.index} | ${s.type} | ${s.status} | ${s.detail.replace(/\|/g, "\\|")} | ${s.ms} |`),
    "",
  ].join("\n");
  await writeFile(path.join(dir, "report.md"), md, "utf8");
  console.log(`[e2e] ${t.id}: ${report.status} (PASS ${report.passed}, FAIL ${report.failed}, SKIP ${report.skipped}) -> ${dir}`);
  return report;
}

export function e2eOptions(flags: Set<string>): E2eOptions {
  const headed = flags.has("--headed") || settings.headed();
  const slowMo = Number(process.env.E2E_SLOWMO_MS ?? (headed ? 150 : 0));
  return { headed, shots: flags.has("--shots"), trace: flags.has("--trace"), slowMo: Number.isFinite(slowMo) ? slowMo : 0 };
}

