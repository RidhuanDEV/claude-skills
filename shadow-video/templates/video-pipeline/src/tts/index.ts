import { createHash } from "node:crypto";
import { existsSync } from "node:fs";
import { mkdir, readFile, rename, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { PATHS, settings } from "../config.ts";
import { probeDurationMs } from "../media.ts";
import type { Tutorial } from "../schema.ts";
import { AzureSpeechProvider } from "./azure.ts";
import { EdgeTtsProvider } from "./edge-tts.ts";
import type { TtsProvider } from "./provider.ts";

/** TTS_PROVIDER=azure (licensed, commercial use; default) | edge (unofficial, internal previews only). */
export function getProvider(): TtsProvider {
  const name = (process.env.TTS_PROVIDER ?? "azure").trim().toLowerCase();
  if (name === "edge") return new EdgeTtsProvider();
  if (name === "azure") return new AzureSpeechProvider();
  throw new Error(`Unknown TTS_PROVIDER "${name}" (use azure or edge)`);
}

export interface TtsSceneEntry {
  id: string;
  hash: string;
  /** Absolute MP3 path, or null for silent scenes. */
  file: string | null;
  durationMs: number;
  narration: string;
}

export interface TtsManifest {
  tutorialId: string;
  provider: string;
  voice: string;
  rate: string;
  pitch: string;
  createdAt: string;
  scenes: TtsSceneEntry[];
}

export const manifestPath = (tutorialId: string) => path.join(PATHS.ttsCache, `${tutorialId}.manifest.json`);

/** Collapse whitespace so cosmetic JSON edits don't bust the cache. */
const normalize = (text: string) => text.replace(/\s+/g, " ").trim();

async function withRetry<T>(what: string, fn: () => Promise<T>, attempts = 3): Promise<T> {
  let last: unknown;
  for (let i = 1; i <= attempts; i++) {
    try {
      return await fn();
    } catch (e) {
      last = e;
      if (i < attempts) {
        const wait = 1000 * 2 ** (i - 1);
        console.warn(`  ! ${what} failed (attempt ${i}/${attempts}), retrying in ${wait} ms: ${(e as Error).message.split("\n")[0]}`);
        await new Promise((r) => setTimeout(r, wait));
      }
    }
  }
  throw last;
}

export async function runTts(t: Tutorial, opts: { force?: boolean } = {}): Promise<TtsManifest> {
  const provider = getProvider();
  const voice = t.voice ?? settings.voice();
  const rate = t.rate ?? settings.rate();
  const pitch = settings.pitch();
  await mkdir(PATHS.ttsCache, { recursive: true });
  console.log(`[tts] ${t.id}: provider=${provider.id} voice=${voice} rate=${rate} scenes=${t.scenes.length}`);

  const scenes: TtsSceneEntry[] = [];
  for (const scene of t.scenes) {
    const text = normalize(scene.narration);
    const hash = createHash("sha256").update(JSON.stringify([provider.id, voice, rate, pitch, text])).digest("hex").slice(0, 32);
    if (!text) {
      scenes.push({ id: scene.id, hash, file: null, durationMs: 0, narration: "" });
      console.log(`  - ${scene.id}: (silent)`);
      continue;
    }
    const file = path.join(PATHS.ttsCache, `${hash}.mp3`);
    const cached = existsSync(file) && !opts.force;
    if (!cached) {
      const tmp = `${file}.${process.pid}.tmp.mp3`;
      try {
        await withRetry(`tts ${scene.id}`, () => provider.synthesize({ text, voice, rate, pitch, outFile: tmp }));
        await rename(tmp, file); // atomic: a crash never leaves a half-written cache entry
      } finally {
        await rm(tmp, { force: true });
      }
    }
    const durationMs = await probeDurationMs(file);
    scenes.push({ id: scene.id, hash, file, durationMs, narration: text });
    console.log(`  - ${scene.id}: ${(durationMs / 1000).toFixed(2)} s ${cached ? "(cache)" : "(new)"}`);
  }

  const manifest: TtsManifest = { tutorialId: t.id, provider: provider.id, voice, rate, pitch, createdAt: new Date().toISOString(), scenes };
  await writeFile(manifestPath(t.id), JSON.stringify(manifest, null, 2), "utf8");
  console.log(`[tts] manifest -> ${manifestPath(t.id)}`);
  return manifest;
}

/** Load manifest and verify it still matches the scene file (narration edited => re-run tts). */
export async function loadManifest(t: Tutorial): Promise<TtsManifest> {
  const p = manifestPath(t.id);
  if (!existsSync(p)) throw new Error(`No TTS manifest for "${t.id}". Run: npm run tts -- ${t.id}`);
  const m = JSON.parse(await readFile(p, "utf8")) as TtsManifest;
  for (const scene of t.scenes) {
    const entry = m.scenes.find((s) => s.id === scene.id);
    if (!entry || entry.narration !== normalize(scene.narration)) {
      throw new Error(`TTS manifest for "${t.id}" is stale (scene "${scene.id}" changed). Run: npm run tts -- ${t.id}`);
    }
    if (entry.file && !existsSync(entry.file)) throw new Error(`Missing audio ${entry.file}. Run: npm run tts -- ${t.id}`);
  }
  return m;
}
