import { existsSync } from "node:fs";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { bins, PATHS, settings } from "./config.ts";
import { probeDurationMs, probeVideo, runOrThrow } from "./media.ts";
import { loadTimeline } from "./merge.ts";
import type { Tutorial } from "./schema.ts";
import { loadManifest } from "./tts/index.ts";

/**
 * Evidence check of a finished module video. Every agent runs the same checks, so "done" means the same thing
 * on every host: codec and size, audio present, length close to the recorded timeline, subtitles present, and
 * the narration in the MP4 still matching the scene file. Visual quality is NOT measured here: watch the video.
 */
interface Check {
  name: string;
  ok: boolean;
  info: string;
}

async function audioCodec(file: string): Promise<string> {
  const r = await runOrThrow(
    bins.ffprobe(),
    ["-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_name", "-of", "default=noprint_wrappers=1:nokey=1", file],
    `ffprobe audio ${file}`,
    60_000,
  );
  return r.stdout.trim() || "none";
}

export async function verify(t: Tutorial): Promise<boolean> {
  const checks: Check[] = [];
  const add = (name: string, ok: boolean, info: string) => checks.push({ name, ok, info });
  const mp4 = path.join(PATHS.output, `${t.id}.mp4`);
  const srt = path.join(PATHS.output, `${t.id}.srt`);

  try {
    const manifest = await loadManifest(t);
    add("tts-current", true, `${manifest.scenes.length} scene(s), voice ${manifest.voice}, provider ${manifest.provider}`);
  } catch (e: unknown) {
    add("tts-current", false, e instanceof Error ? e.message : String(e));
  }

  if (!existsSync(mp4)) {
    add("mp4", false, `missing ${mp4}. Run: npm run build:video -- ${t.id}`);
  } else {
    const info = await probeVideo(mp4);
    add("video-codec", info.codec === "h264", info.codec);
    add("canvas", info.width === t.canvas.width && info.height === t.canvas.height, `${info.width}x${info.height} (expected ${t.canvas.width}x${t.canvas.height})`);
    const [num = "0", den = "1"] = info.fps.split("/");
    const fps = Number(num) / Number(den || "1");
    add("fps", Math.abs(fps - settings.outputFps()) < 0.5, `${fps.toFixed(2)} (expected ${settings.outputFps()})`);
    const audio = await audioCodec(mp4);
    add("audio", audio === "aac", audio);
    const durationMs = await probeDurationMs(mp4);
    try {
      const tl = await loadTimeline(t.id);
      const cutMs = (tl.cuts ?? []).reduce((sum, c) => sum + (c.endMs - c.startMs), 0);
      const recordedMs = tl.endMs - tl.firstSceneStartMs - cutMs;
      // merge.ts may hold the last frame while the closing narration finishes, so allow a longer MP4.
      add("duration", durationMs >= recordedMs - 1000, `${(durationMs / 1000).toFixed(1)} s (recorded ${(recordedMs / 1000).toFixed(1)} s)`);
      add("scenes-recorded", tl.scenes.length === t.scenes.length, `${tl.scenes.length}/${t.scenes.length} scene(s) in timeline`);
    } catch (e: unknown) {
      add("timeline", false, e instanceof Error ? e.message : String(e));
    }
  }

  const narrated = t.scenes.filter((s) => s.narration.trim()).length;
  if (!existsSync(srt)) {
    add("srt", narrated === 0, narrated === 0 ? "no narration" : `missing ${srt}`);
  } else {
    const cues = (await readFile(srt, "utf8")).split(/\r?\n\r?\n/).filter((b) => / --> /.test(b)).length;
    add("srt", cues >= narrated, `${cues} cue(s) for ${narrated} narrated scene(s)`);
  }

  for (const c of checks) console.log(`${c.ok ? "PASS" : "FAIL"} ${c.name.padEnd(16)} ${c.info}`);
  const ok = checks.every((c) => c.ok);
  console.log(`[verify] ${t.id}: ${ok ? "PASS" : "FAIL"} (visual review of the MP4 is still required)`);
  return ok;
}
