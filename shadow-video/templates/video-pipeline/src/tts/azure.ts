import { writeFile } from "node:fs/promises";
import type { TtsProvider, TtsRequest } from "./provider.ts";

/**
 * Official Azure AI Speech (REST, no SDK). Same neural voices as edge-tts (e.g. id-ID-GadisNeural) but under a
 * licensed Azure subscription; the free F0 tier covers this project's narration volume.
 * Env: AZURE_SPEECH_KEY, AZURE_SPEECH_REGION (e.g. southeastasia). Never logs the key.
 */
export class AzureSpeechProvider implements TtsProvider {
  readonly id = "azure-speech";

  private cfg() {
    const key = process.env.AZURE_SPEECH_KEY?.trim();
    const region = process.env.AZURE_SPEECH_REGION?.trim();
    if (!key || !region) throw new Error("AZURE_SPEECH_KEY / AZURE_SPEECH_REGION are not set in .env");
    return { key, region };
  }

  private static ssml(req: TtsRequest): string {
    const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    const lang = req.voice.split("-").slice(0, 2).join("-");
    return (
      `<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="${lang}">` +
      `<voice name="${esc(req.voice)}"><prosody rate="${esc(req.rate)}" pitch="${esc(req.pitch)}">${esc(req.text)}</prosody></voice></speak>`
    );
  }

  async synthesize(req: TtsRequest): Promise<void> {
    const { key, region } = this.cfg();
    const res = await fetch(`https://${region}.tts.speech.microsoft.com/cognitiveservices/v1`, {
      method: "POST",
      headers: {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-24khz-96kbitrate-mono-mp3",
        "User-Agent": "shadow-video-pipeline",
      },
      body: AzureSpeechProvider.ssml(req),
    });
    if (!res.ok) {
      const hint = res.status === 401 ? " (check AZURE_SPEECH_KEY / region)" : res.status === 429 ? " (free-tier rate limit; retry later)" : "";
      throw new Error(`Azure TTS HTTP ${res.status}${hint}: ${(await res.text()).slice(0, 200)}`);
    }
    await writeFile(req.outFile, Buffer.from(await res.arrayBuffer()));
  }

  async check(): Promise<string> {
    const { key, region } = this.cfg();
    const res = await fetch(`https://${region}.tts.speech.microsoft.com/cognitiveservices/voices/list`, {
      headers: { "Ocp-Apim-Subscription-Key": key },
    });
    if (!res.ok) throw new Error(`Azure voices/list HTTP ${res.status}`);
    const voices = (await res.json()) as Array<{ ShortName: string }>;
    return `azure-speech (${region}), ${voices.filter((v) => v.ShortName.startsWith("id-ID")).length} id-ID voices`;
  }
}
