# Multi-Mode Video Production Workflows

> Select the video workflow that matches the user's actual medium and objective instead of forcing every request through one hardcoded tutorial pipeline.

## 1. Core Concepts
Every video pipeline shares three engineering stages: **Deterministic Capture/Render** (reproducible source scripts or simulators), **Broadcast-Compliant Mastering** (`yuv420p` H.264 video + LUFS-normalized audio), and **Objective Media Verification** (`ffprobe` stream inspection + visual contact sheets). Picking the right capture mode eliminates brittle screen-recording hacks and giant unplayable exports.

## 2. Technical Rules & Decision Matrix

| Mode | Best For | Primary Stack | Audio / Captions |
| :--- | :--- | :--- | :--- |
| **Mode 1: Narrated Web Tutorial (Default)** | Step-by-step web app walkthroughs + reusable GUI E2E | `video-pipeline/` (Playwright + cursor + TTS + FFmpeg) | Synchronized TTS + `.srt` + chapters |
| **Mode 2: Programmatic / Motion Video** | Product launches, animated UI teasers, explainers | **Remotion** (React -> MP4), **Canvas/SVG frames -> FFmpeg**, **Manim**, or **Lottie-to-MP4** | Optional voiceover + `-18dB` to `-22dB` ducked music bed |
| **Mode 3: Mobile App Demo Video** | Android / iOS / Flutter / RN app walkthroughs | `adb shell screenrecord` / `xcrun simctl io booted recordVideo` + FFmpeg frame overlay | Optional narration + `.srt` |
| **Mode 4: Lightweight PR / Docs Clip** | README demos, PR proof, changelog snippets | Playwright `recordVideo` -> **MP4 (`yuv420p`)**, **WebM (VP9)**, or **GIF** (`palettegen`) | Silent (zero TTS cost; small payload) |

### Flexible Voice & Loudness Targets
- Support Azure Speech, OpenAI/ElevenLabs TTS, offline local TTS (`Piper`/`Kokoro`), or human-recorded `.wav`/`.mp3` tracks in any requested locale without locking to one vendor.
- Normalize voice mixes to **`-14 LUFS`** (social/YouTube) or **`-16 LUFS`** (web docs/LMS) with **`-1.5 dBTP`** true peak ceiling.

## 3. Implementation Examples

### Universal Safari/Mobile MP4 + LUFS Normalization + 3x3 Visual QA
```powershell
# 1. Produce universally playable MP4 (H.264 yuv420p + -14 LUFS audio + faststart)
ffmpeg -y -i raw_video.mp4 -i narration.wav `
  -c:v libx264 -pix_fmt yuv420p -preset medium -crf 20 -movflags +faststart `
  -af "loudnorm=I=-14:TP=-1.5:LRA=11" -c:a aac -b:a 192k `
  -shortest final_release.mp4

# 2. High-quality docs GIF with 2-pass custom palette (clean typography, smaller bytes)
ffmpeg -y -i raw_clip.mp4 -vf "fps=12,scale=960:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse=dither=bayer" demo.gif

# 3. Inspect stream metadata & extract 3x3 contact sheet for visual verification
ffprobe -v error -show_entries stream=codec_name,pix_fmt,width,height,r_frame_rate -of json final_release.mp4
ffmpeg -y -i final_release.mp4 -vf "fps=0.5,scale=480:-1,tile=3x3" -frames:v 1 qa_contact_sheet.png
```

## 4. Best Practices
- Check scene configs, Remotion components, and FFmpeg build commands into Git while `.gitignore`-ing heavy rendered `.mp4`/`.wav` artifacts.
- Set `-movflags +faststart` on every web MP4 so browsers begin streaming immediately before downloading the entire `moov` atom.
- Keep silent PR GIFs/MP4s under `5 MB` by capping frame rate (`12–15 fps` for docs GIFs, `30 fps` for standard product tutorials).

## 5. Anti-Patterns (`WRONG` vs `RIGHT`)
- **WRONG (`yuv444p` encode from lossless PNG/Canvas frames):** Passing raw RGB frames to `libx264` without `-pix_fmt yuv420p` (plays in VLC, shows solid black or green frames in Safari, iOS, Slack, and WhatsApp!).
  **RIGHT:** Always specify `-c:v libx264 -pix_fmt yuv420p -movflags +faststart`.
- **WRONG (Naive FFmpeg GIF conversion & unnormalized TTS clipping):** Running `ffmpeg -i in.mp4 out.gif` (256-color default banding & 40 MB bloat) or shipping raw TTS volume spikes.
  **RIGHT:** Use `palettegen`/`paletteuse` for GIFs and apply `loudnorm` to `-14`/`-16 LUFS` (`-1.5 dBTP`).

## 6. Production Considerations
- **Privacy & Security:** Run recordings strictly against seeded demo tenants; scrub tokens, emails, and secrets before rendering frames.
- **Verification Gate:** Never declare a render finished from FFmpeg exit code `0` alone — confirm codec/pixel format via `ffprobe` and inspect `qa_contact_sheet.png` visually for frozen cursors, cut-off subtitles, or blank frames.
