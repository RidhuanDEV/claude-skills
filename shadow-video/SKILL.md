---
name: shadow-video
description: "Flexible Video Production & GUI E2E Recording. Use when producing narrated web tutorials (Playwright + TTS + ffmpeg MP4/SRT), programmatic/motion product videos (Remotion/Canvas/Lottie), mobile app demo captures, lightweight docs GIF/WebM clips, or GUI E2E click-through verification."
---

# Shadow Video

Engine and method for **narrated tutorial videos** and **GUI E2E click-throughs** of web apps. One scene file
drives both: `npm run e2e` proves every selector in a visible or headless browser; `npm run build:video` records
the same steps with a human-like cursor, Indonesian TTS narration and subtitles. Proven on two production
projects (government logistics, university research portal).

## Fixed pipeline (same on every agent host)

```
app source ─► tools/build-NN.py ─► tutorial/NN-*.md  (script, reviewed by the Monarch)
   (traced labels)              └► scenes/NN-*.json  (same narration, Playwright actions)
scenes ─► validate ─► e2e (GUI proof) ─► tts ─► record ─► merge ─► verify ─► final
```

| Step | Command | Gate (stop if it fails) |
|---|---|---|
| Scaffold | `node <skill>/scripts/scaffold.mjs <project>` | refuses to overwrite an existing `video-pipeline/` |
| Readiness | `npm ci`, `npm run doctor`, `npm run typecheck`, `npm run selftest -- --e2e` | every line OK except items the task does not need |
| Research | `npm run snapshot -- <ROLE> <route> [steps]` + read app source | every label/selector cites `file:line` |
| Script | `python tools/build-NN.py` | narration lint passes; Monarch approves the `.md` |
| Proof | `npm run validate`, `npm run e2e -- <id> [--headed] [--shots] [--trace]` | E2E `PASS`; report in `output/e2e/<id>/` |
| Preview | `npm run build:video -- <id>` on ONE short module | Monarch approves cursor pace and A/V sync |
| Produce | `npm run build:video -- <id>` per module, in dependency order | `npm run verify -- <id>` PASS + frames viewed |
| Package | `npm run final` | title cards, thumbnails, per-module and combined MP4 + SRT + YouTube chapters |

Never skip E2E before recording: a failed recording costs minutes and TTS quota; a failed E2E costs seconds.

## Load only what the task needs

| Task | Read |
|---|---|
| Choosing non-tutorial video modes (Remotion/Canvas motion, mobile capture, docs GIF/WebM, multi-language/LUFS audio) | [Multi-mode video workflows](references/multi-mode-video-workflows.md) |
| New project or engine refresh | [Host capabilities](references/host-capabilities.md), template `README.md` |
| Writing or reviewing narration | [Narration style](references/narration-style.md) |
| Writing scenes, choosing selectors | [Scene authoring](references/scene-authoring.md) |
| Environment, accounts, captcha, demo data, TTS licence | [Recording environment](references/recording-environment.md) |
| Using scenes as GUI E2E tests | [GUI E2E](references/gui-e2e.md) |
| A run failed or looks wrong | [Troubleshooting](references/troubleshooting.md) |
| UI changed after videos exist | [UI change sync](references/ui-change-sync.md) |
| Validating this skill itself | [Evaluations](evaluations.md) |

## Non-negotiables

1. **The app source is the source of truth.** Labels, routes, field order, validation and messages come from code
   (cite `file:line`) or `snapshot` output, never from old manuals or guesses. Where the requested flow differs from
   the code, script what the code does and record the difference under `CATATAN PRODUKSI`.
2. **Never production.** `BASE_URL` points to local or staging with a test database; `BLOCKED_HOSTS` must hold the
   production host. Recording creates real data: only on disposable data, prefixed `Demo – `.
3. **Secrets stay out of video, logs and chat.** Credentials only as `{{PREFIX_EMAIL}}` placeholders from `.env`;
   use `maskText`, `capture`, `fetchMail`, `openUrl` so tokens, passwords and inboxes never show. `.env`, `auth/`,
   `cache/` are git-ignored and never copied into this skill or shared.
4. **One source for script and scenes.** `tools/build-NN.py` writes both files; never hand-edit narration in one.
5. **Engine stays generic.** Project specifics live in `video.config.json`, `.env`, `scenes/`, `tutorial/`,
   `tools/build-*.py`. Change `src/` only for a new engine feature, explain it first, then port it back to
   `templates/video-pipeline/` so every project gets it.
6. **Execution approval.** Scaffolding into a repo, recording against staging, TTS spend, and deleting demo data
   are actions the Monarch authorises per project (Shadow Monarch L2/L3). Read-only research and `e2e` on local
   pages are in scope once the task is approved.
7. **Mandatory Recording Stack Teardown.** Whenever a recording or E2E run starts `tools/video-env.cjs` (frontend + backend),
   headed `chrome-cdp.ts` / Playwright browsers, or ephemeral recording DB containers, track their PIDs/containers and stop ONLY
   those task-owned resources in `finally` / immediately after `verify` & `final` complete (`shadow-monarch/scripts/resource_cleanup.py`).
   Never leave `video-env.cjs` or browser processes lingering after a video task finishes, and never kill servers belonging to other projects.

## Reporting

Report per module with separate evidence lines, using `PASS | FAIL | NOT_RUN | BLOCKED`:
`e2e` (report path), `verify` (codec, canvas, fps, audio, duration, SRT, narration current), **visual review**
(which frames or segments were actually watched), and demo data left on staging. A passing `verify` proves the
file is well-formed; it does not prove the video is good. Say "Not measured" for anything not watched.

## Related skills

Shadow Browser owns ad-hoc browser checks and 375px layout audits. Shadow Test owns unit/integration suites.
Shadow Doc owns written manuals (`.docx`), which can embed thumbnails from `output/`. Shadow Monarch defines
scope and execution permissions.
