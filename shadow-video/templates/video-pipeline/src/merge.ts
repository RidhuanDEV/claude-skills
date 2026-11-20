import { existsSync } from "node:fs";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { bins, PATHS, settings } from "./config.ts";
import { probeDurationMs, probeVideo, runOrThrow } from "./media.ts";
import { timelinePath, type Timeline } from "./recorder.ts";
import type { TtsManifest } from "./tts/index.ts";

export async function loadTimeline(id: string): Promise<Timeline> {
  const p = timelinePath(id);
  if (!existsSync(p)) throw new Error(`No recording for "${id}". Run: npm run record -- ${id}`);
  return JSON.parse(await readFile(p, "utf8")) as Timeline;
}

const even = (n: number) => Math.max(2, Math.round(n / 2) * 2);
const sec = (ms: number) => (ms / 1000).toFixed(3);

/** Kept recording ranges: [start, end] minus manual-step cuts. */
function keptSegments(tl: Timeline, startMs: number): Array<[number, number]> {
  const cuts = [...(tl.cuts ?? [])].filter((c) => c.endMs > startMs).sort((a, b) => a.startMs - b.startMs);
  const segs: Array<[number, number]> = [];
  let from = startMs;
  for (const c of cuts) {
    if (c.startMs > from) segs.push([from, c.startMs]);
    from = Math.max(from, c.endMs);
  }
  if (tl.endMs > from) segs.push([from, tl.endMs]);
  return segs;
}

/** Recording time -> output time (pre-roll trimmed, cuts removed). */
export function outputTime(tl: Timeline, startMs: number, t: number): number {
  let removed = startMs;
  for (const c of tl.cuts ?? []) if (c.endMs <= t) removed += c.endMs - c.startMs;
  return t - removed;
}

function videoFilter(tl: Timeline, startMs: number, padMs = 0): string {
  const { width: vw, height: vh } = tl.viewport;
  const c = tl.canvas;
  const segs = keptSegments(tl, startMs);
  const pre: string[] = segs.map(([a, b], i) => `[0:v]trim=start=${sec(a)}:end=${sec(b)},setpts=PTS-STARTPTS[s${i}]`);
  const joined = segs.length > 1 ? `${segs.map((_, i) => `[s${i}]`).join("")}concat=n=${segs.length}:v=1:a=0[vj]` : "";
  const src = segs.length > 1 ? "[vj]" : "[s0]";
  const parts = [`fps=${settings.outputFps()}`];
  if (vw !== c.width || vh !== c.height) {
    const availW = c.width - 2 * c.padding;
    const availH = c.height - 2 * c.padding;
    const s = c.fit === "contain" ? Math.min(availW / vw, availH / vh) : 1;
    const ow = even(vw * s);
    const oh = even(vh * s);
    if (ow !== vw || oh !== vh) parts.push(`scale=${ow}:${oh}:flags=lanczos`);
    parts.push(`pad=${c.width}:${c.height}:(ow-iw)/2:(oh-ih)/2:color=${c.background}`);
  }
  // Hold the last frame when narration (e.g. a re-voiced closing line) runs past the recording.
  if (padMs > 0) parts.push(`tpad=stop_mode=clone:stop_duration=${sec(padMs)}`);
  parts.push("format=yuv420p");
  return [...pre, ...(joined ? [joined] : []), `${src}${parts.join(",")}[v]`].join(";");
}

// ---------- SRT ----------
function srtTime(ms: number): string {
  const v = Math.max(0, Math.round(ms));
  const h = Math.floor(v / 3_600_000);
  const m = Math.floor((v % 3_600_000) / 60_000);
  const s = Math.floor((v % 60_000) / 1000);
  const r = v % 1000;
  const p = (n: number, w = 2) => String(n).padStart(w, "0");
  return `${p(h)}:${p(m)}:${p(s)},${p(r, 3)}`;
}

/** Sentence chunks (<= ~90 chars, split further on commas), timed proportionally to length. */
export function chunkNarration(text: string): string[] {
  const sentences = text.split(/(?<=[.!?…])\s+/).filter(Boolean);
  const out: string[] = [];
  for (const s of sentences) {
    if (s.length <= 90) {
      out.push(s);
      continue;
    }
    let buf = "";
    for (const part of s.split(/(?<=[,;:])\s+/)) {
      if (buf && (buf + " " + part).length > 90) {
        out.push(buf);
        buf = part;
      } else buf = buf ? `${buf} ${part}` : part;
    }
    if (buf) out.push(buf);
  }
  return out;
}

export function buildSrt(tl: Timeline, manifest: TtsManifest, startMs: number, offsetMs: number): string {
  const cues: string[] = [];
  let n = 1;
  for (const scene of tl.scenes) {
    const entry = manifest.scenes.find((s) => s.id === scene.id);
    if (!entry || !entry.narration || entry.durationMs <= 0) continue;
    const chunks = chunkNarration(entry.narration);
    const total = chunks.reduce((a, c) => a + c.length, 0);
    let t = outputTime(tl, startMs, scene.startMs) + offsetMs;
    for (const chunk of chunks) {
      const d = (entry.durationMs * chunk.length) / total;
      cues.push(`${n++}\n${srtTime(t)} --> ${srtTime(t + d - 40)}\n${chunk}\n`);
      t += d;
    }
  }
  return cues.join("\n");
}

// ---------- merge ----------
export async function merge(tl: Timeline, manifest: TtsManifest): Promise<{ mp4: string; srt: string }> {
  if (!existsSync(tl.video)) throw new Error(`Recorded video missing: ${tl.video}. Run: npm run record -- ${tl.tutorialId}`);
  await mkdir(PATHS.output, { recursive: true });
  const startMs = tl.firstSceneStartMs; // trims about:blank / loading pre-roll
  const offsetMs = settings.avOffsetMs();
  const recordedMs = outputTime(tl, startMs, tl.endMs);
  const narrationEndMs = Math.max(
    0,
    ...tl.scenes.map((sc) => outputTime(tl, startMs, sc.startMs) + offsetMs + (manifest.scenes.find((m) => m.id === sc.id)?.durationMs ?? 0) + 600),
  );
  const padMs = Math.max(0, narrationEndMs - recordedMs);
  const totalMs = recordedMs + padMs;
  const videoMs = await probeDurationMs(tl.video);
  if (videoMs + 500 < tl.endMs) {
    console.warn(`  ! recorded video (${videoMs} ms) is shorter than timeline (${tl.endMs} ms); end may be cut`);
  }

  const args = ["-y", "-hide_banner", "-loglevel", "error", "-i", tl.video];
  const audioLabels: string[] = [];
  const filters = [videoFilter(tl, startMs, padMs)];
  let input = 1;
  for (const scene of tl.scenes) {
    const entry = manifest.scenes.find((s) => s.id === scene.id);
    if (!entry?.file) continue;
    args.push("-i", entry.file);
    const delay = Math.max(0, Math.round(outputTime(tl, startMs, scene.startMs) + offsetMs));
    filters.push(`[${input}:a]aresample=48000,aformat=channel_layouts=stereo,adelay=${delay}:all=1[a${input}]`);
    audioLabels.push(`[a${input}]`);
    input++;
  }
  if (audioLabels.length === 0) {
    filters.push(`anullsrc=r=48000:cl=stereo,atrim=0:${sec(totalMs)}[a]`);
  } else if (audioLabels.length === 1) {
    filters.push(`${audioLabels[0]}apad,atrim=0:${sec(totalMs)}[a]`);
  } else {
    filters.push(`${audioLabels.join("")}amix=inputs=${audioLabels.length}:normalize=0:dropout_transition=0,apad,atrim=0:${sec(totalMs)}[a]`);
  }

  const mp4 = path.join(PATHS.output, `${tl.tutorialId}.mp4`);
  args.push(
    "-filter_complex", filters.join(";"),
    "-map", "[v]", "-map", "[a]",
    "-c:v", "libx264", "-preset", settings.preset(), "-crf", String(settings.crf()), "-pix_fmt", "yuv420p", "-profile:v", "high",
    "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
    "-t", sec(totalMs),
    "-movflags", "+faststart",
    mp4,
  );
  console.log(`[merge] ${tl.tutorialId}: trim ${sec(startMs)}s pre-roll, ${(tl.cuts ?? []).length} cut(s), ${audioLabels.length} narration clip(s), length ${sec(totalMs)}s`);
  await runOrThrow(bins.ffmpeg(), args, "ffmpeg merge", 30 * 60_000);

  const srt = path.join(PATHS.output, `${tl.tutorialId}.srt`);
  await writeFile(srt, buildSrt(tl, manifest, startMs, offsetMs), "utf8");

  const info = await probeVideo(mp4);
  console.log(`[merge] -> ${mp4} (${info.codec} ${info.width}x${info.height} @ ${info.fps})\n[merge] -> ${srt}`);
  return { mp4, srt };
}
