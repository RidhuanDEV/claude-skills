import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { bins } from "../config.ts";
import { run, runOrThrow } from "../media.ts";
import type { TtsProvider, TtsRequest } from "./provider.ts";

/** Calls the `edge-tts` Python package as `python -m edge_tts` (no PATH/Scripts dir dependency). */
export class EdgeTtsProvider implements TtsProvider {
  readonly id = "edge-tts";

  async check(): Promise<string> {
    const r = await run(bins.python(), ["-m", "edge_tts", "--version"], { timeoutMs: 30_000 });
    if (r.code !== 0) {
      throw new Error(
        `edge-tts not available for "${bins.python()}". Install with:\n  python -m pip install edge-tts\n${r.stderr.trim()}`,
      );
    }
    return (r.stdout || r.stderr).trim();
  }

  async synthesize(req: TtsRequest): Promise<void> {
    // Text goes through a UTF-8 file, not argv: avoids Windows quoting issues with quotes/em-dashes.
    const dir = await mkdtemp(path.join(tmpdir(), "edge-tts-"));
    const textFile = path.join(dir, "text.txt");
    try {
      await writeFile(textFile, req.text, "utf8");
      await runOrThrow(
        bins.python(),
        [
          "-m", "edge_tts",
          "--voice", req.voice,
          `--rate=${req.rate}`, // "=" form: values start with +/- and must not be parsed as flags
          `--pitch=${req.pitch}`,
          "--file", textFile,
          "--write-media", req.outFile,
        ],
        `edge-tts (${req.voice})`,
        120_000,
      );
    } finally {
      await rm(dir, { recursive: true, force: true });
    }
  }
}
