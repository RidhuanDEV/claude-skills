import { existsSync, readdirSync } from "node:fs";
import path from "node:path";
import { chromium } from "playwright";
import { baseUrl, bins, PATHS } from "./config.ts";
import { autoLogin, ensureStorageState, manualLogin } from "./login.ts";
import { run } from "./media.ts";
import { loadTimeline, merge } from "./merge.ts";
import { record } from "./recorder.ts";
import { loadTutorial, type Tutorial } from "./schema.ts";
import { selftest, selftestE2e } from "./selftest.ts";
import { concatModules, writeYoutubeChapters } from "./concat.ts";
import { buildBranding, chapterSlug, readyChapters, readyGuides } from "./branding.ts";
import { copyFile, mkdir } from "node:fs/promises";
import { getProvider, loadManifest, runTts } from "./tts/index.ts";
import { e2e, e2eOptions } from "./e2e.ts";
import { project, projectFile } from "./project.ts";
import { snapshot } from "./snapshot.ts";
import { verify } from "./verify.ts";

const [cmd, ...rest] = process.argv.slice(2);
const flags = new Set(rest.filter((a) => a.startsWith("--")));
const positional = rest.filter((a) => !a.startsWith("--"));
const target = positional[0];

function needTarget(): string {
  if (!target) throw new Error(`Usage: npm run ${cmd} -- <tutorial-id>   e.g. npm run ${cmd} -- 00-sample`);
  return target;
}

async function sessionFile(t: Tutorial): Promise<string> {
  if (t.session === "storageState") return ensureStorageState();
  const f = path.join(PATHS.auth, `${t.session}.json`);
  if (!existsSync(f)) throw new Error(`Session "${t.session}" missing (${f}). Record the tutorial that saves it first.`);
  return f;
}

async function doRecord(t: Tutorial) {
  const manifest = await loadManifest(t);
  const storageState = t.recordLogin ? undefined : await sessionFile(t);
  return record(t, manifest, { baseUrl: baseUrl(), storageState });
}

async function doctor() {
  const line = (ok: boolean, name: string, info: string) => console.log(`${ok ? "OK  " : "MISS"} ${name.padEnd(10)} ${info}`);
  line(true, "node", process.version);
  for (const [name, bin, args] of [
    ["ffmpeg", bins.ffmpeg(), ["-version"]],
    ["ffprobe", bins.ffprobe(), ["-version"]],
  ] as const) {
    try {
      const r = await run(bin, [...args], { timeoutMs: 15_000 });
      line(r.code === 0, name, r.stdout.split(/\r?\n/)[0] ?? "");
    } catch (e) {
      line(false, name, `${(e as Error).message}  ->  winget install --id Gyan.FFmpeg -e`);
    }
  }
  try {
    line(true, "tts", await getProvider().check());
  } catch (e) {
    line(false, "tts", (e as Error).message.split("\n")[0] ?? "");
  }
  const exe = chromium.executablePath();
  line(existsSync(exe), "chromium", existsSync(exe) ? exe : "npx playwright install chromium");
  line(existsSync(path.join(PATHS.root, ".env")), ".env", existsSync(path.join(PATHS.root, ".env")) ? "present" : "Copy-Item .env.example .env");
  try {
    line(true, "BASE_URL", baseUrl());
  } catch (e) {
    line(false, "BASE_URL", (e as Error).message);
  }
  try {
    const p = project();
    line(true, "config", `${p.appName}: ${p.chapters.length} chapter(s), ${p.guides.length} guide(s), roles ${p.rolePrefixes.join("/")}`);
  } catch (e) {
    line(false, "config", (e as Error).message.replace(/\s*\n\s*/g, " | ") || projectFile);
  }
  line(existsSync(PATHS.storageState), "session", existsSync(PATHS.storageState) ? PATHS.storageState : "npm run login");
}

async function main() {
  switch (cmd) {
    case "doctor":
      return doctor();
    case "validate": {
      const ids = target ? [target] : readdirSync(PATHS.scenes).filter((f) => f.endsWith(".json")).map((f) => f.replace(/\.json$/, ""));
      for (const id of ids) {
        const t = loadTutorial(id);
        console.log(`OK ${t.id}: ${t.scenes.length} scene(s), viewport ${t.viewport.width}x${t.viewport.height}`);
      }
      return;
    }
    case "tts":
      await runTts(loadTutorial(needTarget()), { force: flags.has("--force") });
      return;
    case "record":
      await doRecord(loadTutorial(needTarget()));
      return;
    case "merge": {
      const t = loadTutorial(needTarget());
      await merge(await loadTimeline(t.id), await loadManifest(t));
      return;
    }
    case "build": {
      const t = loadTutorial(needTarget());
      const manifest = await runTts(t, { force: flags.has("--force") });
      const storageState = t.recordLogin ? undefined : await sessionFile(t);
      const tl = await record(t, manifest, { baseUrl: baseUrl(), storageState });
      await merge(tl, manifest);
      return;
    }
    case "login":
      return flags.has("--auto") ? autoLogin() : manualLogin();
    case "selftest":
      // --e2e: GUI E2E only (no TTS/ffmpeg). Without it: tts -> record -> merge of the local pages.
      if (flags.has("--e2e")) {
        process.exitCode = (await selftestE2e(e2eOptions(flags))) ? 0 : 1;
        return;
      }
      return selftest();
    case "e2e": {
      // npm run e2e -- <id> [--headed] [--shots] [--trace]; without <id>: every scenes/*.json except 00-*
      const ids = target ? [target] : readdirSync(PATHS.scenes).filter((f) => f.endsWith(".json") && !f.startsWith("00-")).map((f) => f.replace(/\.json$/, "")).sort();
      const opts = e2eOptions(flags);
      let failed = 0;
      for (const id of ids) if ((await e2e(loadTutorial(id), opts)).status === "FAIL") failed++;
      process.exitCode = failed ? 1 : 0;
      return;
    }
    case "snapshot":
      return snapshot(target ?? "LOGIN", positional[1] ?? project().login.landing, positional.slice(2));
    case "verify": {
      const ids = target ? [target] : readdirSync(PATHS.scenes).filter((f) => f.endsWith(".json") && !f.startsWith("00-")).map((f) => f.replace(/\.json$/, "")).sort();
      let failed = 0;
      for (const id of ids) if (!(await verify(loadTutorial(id)))) failed++;
      process.exitCode = failed ? 1 : 0;
      return;
    }
    case "concat": {
      // npm run concat [-- 01-a,02-b,...]  default: every scenes/*.json except 00-*, in name order
      const ids = target ? target.split(",") : readdirSync(PATHS.scenes).filter((f) => f.endsWith(".json") && !f.startsWith("00-")).map((f) => f.replace(/\.json$/, "")).sort();
      return concatModules(ids);
    }
    case "final": {
      // npm run final -> kartu judul + thumbnail, satu video per modul, lalu satu video lengkap per guide
      // di video.config.json beserta SRT dan penanda bab YouTube.
      await buildBranding();
      await mkdir(path.join(PATHS.output, "modul"), { recursive: true });
      for (const c of readyChapters()) {
        const slug = chapterSlug(c);
        await concatModules([`branding/intro-${c.no}`, ...c.videos], `modul/${slug}`);
        await copyFile(path.join(PATHS.output, "branding", `thumbnail-${c.no}.png`), path.join(PATHS.output, "modul", `${slug}-thumbnail.png`));
      }
      for (const guide of readyGuides()) {
        await concatModules(guide.ids, guide.slug);
        await writeYoutubeChapters(guide.slug, guide.chapters);
      }
      return;
    }
    default:
      console.log("Commands: doctor | validate [id] | snapshot <ROLE> <route> [steps] | e2e [id] [--headed] [--shots] [--trace] | tts <id> [--force] | record <id> | merge <id> | build <id> | verify [id] | concat [ids] | final | login [--auto] | selftest [--e2e]");
      process.exitCode = cmd ? 1 : 0;
  }
}

main().catch((e: unknown) => {
  console.error(`\nERROR: ${e instanceof Error ? e.message : String(e)}`);
  process.exitCode = 1;
});
