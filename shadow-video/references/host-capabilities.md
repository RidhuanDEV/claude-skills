# Host capabilities and consistent results across agents

Claude Code, Codex, Antigravity/Gemini CLI and other agents get the same results from this skill because the
work is done by the engine, not by the agent: fixed commands, fixed codec settings, schema validation, narration
lint, E2E reports, and `verify`. The agent's job is research, scripting, and judgement.

## What every host needs

| Need | Check | Notes |
|---|---|---|
| Shell that can run Node >= 20.12 and Python 3.10+ | `node -v`, `python --version` | Windows PowerShell, Git Bash, macOS and Linux shells all work |
| ffmpeg + ffprobe on PATH or `FFMPEG_PATH` | `npm run doctor` | Windows: `winget install --id Gyan.FFmpeg -e` |
| Playwright browsers | `npm run doctor` (chromium line) | `npx playwright install chromium`; Google Chrome for Turnstile |
| Network to staging and to Azure Speech | `npm run doctor` (tts, BASE_URL lines) | Sandboxed hosts may block both; report BLOCKED, do not work around |
| A way to look at images | open `output/e2e/*/*.png`, extracted frames | Hosts that cannot view images report visual review as NOT_RUN |

## Capability routing

| Host situation | Do | Report |
|---|---|---|
| Full shell + network + display | Whole pipeline, headed runs allowed | All evidence lines |
| Shell + network, no display (cloud/CI) | `e2e` headless, `build:video` with `RECORD_LOGIN_HEADED=0` when no captcha | Headed-only steps BLOCKED |
| Shell, no network to staging | Scaffold, typecheck, `selftest -- --e2e`, scripts and scenes, `validate` | e2e/record NOT_RUN with reason |
| No shell (chat only) | Write `tools/build-NN.py` and the script table from code; give exact commands | Everything executed NOT_RUN |

## Determinism checklist

- Pin the engine: projects carry a copy of `templates/video-pipeline`; `scripts/scaffold.mjs --update-engine`
  shows differences before applying. Playwright is pinned (`1.63.0`) and `package-lock.json` is committed.
- Same voice, rate, and pitch per project in `.env`; TTS cache makes re-runs identical for unchanged narration.
- Same viewport and canvas per tutorial (scene file), same `OUTPUT_FPS`, `X264_CRF`, `X264_PRESET`.
- Generated files (`tutorial/*.md`, `scenes/*.json`) come from build scripts, so two agents running the same
  script produce byte-identical files.
- "Done" means the evidence lines in SKILL.md, not an agent's impression.

## Extracting a frame for visual review

```
ffmpeg -v error -ss 12 -i output/<id>.mp4 -frames:v 1 -vf scale=960:-1 output/<id>-12s.png
```

Check at least: first scene, every dialog or upload, the closing frame, and any scene with `maskText` (the
secret must be blurred).
