import { spawn } from "node:child_process";
import { bins } from "./config.ts";

export interface RunResult {
  code: number;
  stdout: string;
  stderr: string;
}

/** Spawn without a shell (no quoting/injection issues on Windows). */
export function run(cmd: string, args: string[], opts: { timeoutMs?: number } = {}): Promise<RunResult> {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, { windowsHide: true });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (d: Buffer) => (stdout += d.toString("utf8")));
    child.stderr.on("data", (d: Buffer) => (stderr += d.toString("utf8")));
    const timer = opts.timeoutMs
      ? setTimeout(() => {
          child.kill();
          reject(new Error(`${cmd} timed out after ${opts.timeoutMs} ms`));
        }, opts.timeoutMs)
      : undefined;
    child.on("error", (err: NodeJS.ErrnoException) => {
      if (timer) clearTimeout(timer);
      if (err.code === "ENOENT") reject(new Error(`Executable not found: "${cmd}". Install it or set its *_PATH in .env (see README).`));
      else reject(err);
    });
    child.on("close", (code) => {
      if (timer) clearTimeout(timer);
      resolve({ code: code ?? -1, stdout, stderr });
    });
  });
}

export async function runOrThrow(cmd: string, args: string[], what: string, timeoutMs?: number): Promise<RunResult> {
  const r = await run(cmd, args, { timeoutMs });
  if (r.code !== 0) {
    const tail = r.stderr.trim().split(/\r?\n/).slice(-15).join("\n");
    throw new Error(`${what} failed (exit ${r.code}):\n${tail}`);
  }
  return r;
}

/** Media duration in milliseconds, via ffprobe. */
export async function probeDurationMs(file: string): Promise<number> {
  const r = await runOrThrow(
    bins.ffprobe(),
    ["-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file],
    `ffprobe ${file}`,
    60_000,
  );
  const sec = Number(r.stdout.trim());
  if (!Number.isFinite(sec) || sec <= 0) throw new Error(`ffprobe returned no duration for ${file}: "${r.stdout.trim()}"`);
  return Math.round(sec * 1000);
}

export async function probeVideo(file: string): Promise<{ width: number; height: number; fps: string; bitRate: string; codec: string }> {
  const r = await runOrThrow(
    bins.ffprobe(),
    ["-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name,width,height,r_frame_rate,avg_frame_rate,bit_rate:format=bit_rate", "-of", "json", file],
    `ffprobe ${file}`,
    60_000,
  );
  const j = JSON.parse(r.stdout) as { streams?: Array<Record<string, string | number>>; format?: { bit_rate?: string } };
  const s = j.streams?.[0] ?? {};
  return {
    codec: String(s.codec_name ?? "?"),
    width: Number(s.width ?? 0),
    height: Number(s.height ?? 0),
    fps: String(s.avg_frame_rate ?? s.r_frame_rate ?? "?"),
    bitRate: String(s.bit_rate ?? j.format?.bit_rate ?? "?"),
  };
}
