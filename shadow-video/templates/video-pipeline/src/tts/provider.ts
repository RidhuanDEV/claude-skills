/**
 * TTS provider boundary. edge-tts is an UNOFFICIAL client of the Microsoft Edge read-aloud
 * service and may break at any time; swap providers by implementing this interface
 * (e.g. Azure Speech SDK, Google Cloud TTS) and returning it from getProvider().
 */
export interface TtsRequest {
  text: string;
  voice: string;
  rate: string; // e.g. "+0%"
  pitch: string; // e.g. "+0Hz"
  outFile: string; // MP3 path to write
}

export interface TtsProvider {
  /** Stable id; part of the cache key so switching providers never reuses stale audio. */
  readonly id: string;
  synthesize(req: TtsRequest): Promise<void>;
  /** Throws with an actionable message if the provider can't run on this machine. */
  check(): Promise<string>;
}
