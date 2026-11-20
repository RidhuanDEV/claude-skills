# Evaluations

Run these after changing the template or the scaffold script. Use a throwaway directory, never a project.

```
node scripts/scaffold.mjs <tmp>            # creates <tmp>/video-pipeline
cd <tmp>/video-pipeline && npm ci
npm run typecheck                          # expect: no output, exit 0
npm run validate                           # expect: OK 00-sample
npm run selftest -- --e2e                  # expect: PASS 11, FAIL 0, SKIP 0
npm run selftest                           # needs TTS; expect output/selftest.mp4 + .srt
# write scenes/selftest.json from SELFTEST_SCENES, then:
npm run verify -- selftest                 # expect all PASS
node <skill>/scripts/scaffold.mjs <tmp>    # expect REFUSED (already exists)
node <skill>/scripts/scaffold.mjs <tmp> --update-engine   # expect "already match", dry run only
```

## Falsification probes (must FAIL or refuse)

| Probe | Expected |
|---|---|
| Scene with a selector matching two buttons | E2E `FAIL ... strict mode violation`, exit 1, `FAIL-*.png` written |
| Same failing action with `optional: true` | `SKIP`, run continues |
| `BLOCKED_HOSTS` contains the `BASE_URL` host | `Refusing to run`, exit 1, no browser started |
| `video.config.json` guide referencing an unknown chapter, `rolePrefixes` without `LOGIN` | `doctor` prints `MISS config Invalid video.config.json` with both issues |
| Narration edited after TTS | `verify` → `FAIL tts-current ... stale`, exit 1 |
| SRT removed | `verify` → `FAIL srt missing` |
| `naskah.lint("Klik tombol 2 kali.")` | `['digit atau simbol']`; `lint("Klik tombol Simpan.")` → `[]` |

## Recorded results

2026-11-21, Windows 11, Node 24.22.1, ffmpeg 9.0.2, Playwright 1.63.0:
- typecheck PASS; validate PASS; `selftest -- --e2e` PASS 11/0/0 on both `chromium` and `chrome` channels.
- Full `selftest` (Azure TTS) produced a 30.7 s 1920x1080 H.264/AAC MP4; `verify` all PASS; frame at 8 s viewed
  (cursor overlay and page correct).
- `final` with three chapters and one guide produced intros, thumbnails (viewed), per-module MP4s, a combined
  MP4, SRT and YouTube chapters (00:00, 00:34, 01:08).
- All falsification probes above behaved as expected.
- `scaffold.mjs`: second create REFUSED; `--update-engine` dry run listed one locally edited file; `--apply`
  restored it. `--trace` wrote `trace.zip` (46 KB).
- Router: `skill_router.py --self-test` RECALL-VIDEO-1 and NEG-VIDEO-1 PASS. A prompt that also mentions login
  routes primary to shadow-auth with shadow-video as supporting skill.
- Not measured: real staging app, Turnstile login, `manual`/`fetchMail`/`capture` actions, mobile viewport,
  macOS/Linux hosts, Codex and Antigravity hosts loading the skill.
