import { existsSync } from "node:fs";
import { readFile, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { bins, PATHS } from "./config.ts";
import { probeDurationMs, runOrThrow } from "./media.ts";
import { project } from "./project.ts";

/**
 * Berkas penanda bab YouTube (tempel ke deskripsi video): satu baris "MM:SS Judul" per bab.
 * YouTube mewajibkan bab pertama di 00:00, minimal tiga bab, dan tiap bab minimal 10 detik.
 */
export async function writeYoutubeChapters(outName: string, chapters: Array<{ title: string; ids: string[] }>): Promise<void> {
  const lines: string[] = [];
  let offset = 0;
  const stamp = (ms: number) => {
    const total = Math.floor(ms / 1000);
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = String(total % 60).padStart(2, "0");
    return h > 0 ? `${h}:${String(m).padStart(2, "0")}:${s}` : `${String(m).padStart(2, "0")}:${s}`;
  };
  for (const chapter of chapters) {
    lines.push(`${stamp(offset)} ${chapter.title}`);
    for (const id of chapter.ids) offset += await probeDurationMs(path.join(PATHS.output, `${id}.mp4`));
  }
  await writeFile(path.join(PATHS.output, `${outName}.youtube-chapters.txt`), lines.join("\n") + "\n", "utf8");
  console.log(`[concat] penanda bab YouTube -> ${outName}.youtube-chapters.txt`);
}

/**
 * Join finished module videos into one MP4 (+ one SRT with shifted cue times).
 * All module MP4s come from merge.ts with identical codec settings, so the concat demuxer can copy streams.
 */
export async function concatModules(ids: string[], outName = `${project().outputPrefix}-lengkap`): Promise<void> {
  const files = ids.map((id) => path.join(PATHS.output, `${id}.mp4`));
  const missing = files.filter((f) => !existsSync(f));
  if (missing.length) throw new Error(`Missing module video(s): ${missing.join(", ")}`);

  const list = path.join(PATHS.output, `${outName}.txt`);
  await writeFile(list, files.map((f) => `file '${f.replace(/\\/g, "/").replace(/'/g, "'\\''")}'`).join("\n"), "utf8");
  const mp4 = path.join(PATHS.output, `${outName}.mp4`);
  await runOrThrow(bins.ffmpeg(), ["-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", list, "-c", "copy", "-movflags", "+faststart", mp4], "ffmpeg concat", 30 * 60_000);

  // SRT: renumber cues and shift each module by the summed duration of the previous ones.
  const out: string[] = [];
  let offset = 0;
  let n = 1;
  const ts = (ms: number) => {
    const v = Math.max(0, Math.round(ms));
    const p = (x: number, w = 2) => String(x).padStart(w, "0");
    return `${p(Math.floor(v / 3_600_000))}:${p(Math.floor((v % 3_600_000) / 60_000))}:${p(Math.floor((v % 60_000) / 1000))},${p(v % 1000, 3)}`;
  };
  const parse = (t: string) => {
    const [h, m, rest] = t.split(":");
    const [s, ms] = rest!.split(",");
    return ((Number(h) * 60 + Number(m)) * 60 + Number(s)) * 1000 + Number(ms);
  };
  for (const id of ids) {
    const srt = path.join(PATHS.output, `${id}.srt`);
    if (existsSync(srt)) {
      for (const block of (await readFile(srt, "utf8")).split(/\r?\n\r?\n/).filter((b) => b.trim())) {
        const lines = block.split(/\r?\n/);
        const m = /^(\S+) --> (\S+)$/.exec(lines[1] ?? "");
        if (!m) continue;
        out.push(`${n++}\n${ts(parse(m[1]!) + offset)} --> ${ts(parse(m[2]!) + offset)}\n${lines.slice(2).join("\n")}\n`);
      }
    }
    offset += await probeDurationMs(path.join(PATHS.output, `${id}.mp4`));
  }
  await writeFile(path.join(PATHS.output, `${outName}.srt`), out.join("\n"), "utf8");
  await rm(list, { force: true }); // concat list holds local absolute paths; not a deliverable
  console.log(`[concat] ${ids.length} module(s) -> ${mp4} (${(offset / 60000).toFixed(1)} min) + ${outName}.srt`);
}
