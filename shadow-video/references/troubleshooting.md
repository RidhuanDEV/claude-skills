# Troubleshooting

| Symptom | Most likely cause | Fix |
|---|---|---|
| `strict mode violation: ... resolved to 2 elements` | Hidden responsive copy or repeated label | Add `:visible`, a container prefix (`main >> `), or `nth` |
| Click "does nothing" in the video, next step times out | Click landed during a closing animation or re-render | `pause` 500-800 ms before, or `click` with `expect` |
| `waitFor url` times out after an in-app navigation | SPA route change fires no `load` event | Wait for a text or element of the new page |
| `button:text-is(...)` never matches | Button content includes an icon | `role=button[name="..."]` |
| Login stays on `/login`, button disabled | Cloudflare Turnstile | Headed Chrome (`BROWSER_CHANNEL=chrome`, `RECORD_LOGIN_HEADED=1`), else `tools/login-chrome.ts` |
| Turnstile error 600010 | Locale or timezone emulation | Do not set `locale`/`timezoneId`; use `BROWSER_LANG` instead |
| Page zoomed, grey band at the edge | Windows display scaling, window resized mid-run | Engine forces scale 1; do not touch the window during headed runs |
| Narration out of sync by a constant amount | Audio device or encoder latency | `AV_OFFSET_MS` (+ later, - earlier), then `npm run merge -- <id>` only |
| `TTS manifest ... is stale` | Narration edited after TTS | `npm run tts -- <id>`; re-record only if new audio is longer than the scene slot in `cache/record/<id>/timeline.json` |
| `recorded video ... is shorter than timeline` warning | Playwright closes the video slightly before the last timestamp | Harmless when `verify` duration passes; the last frame is held for narration |
| `Azure TTS HTTP 401` / `429` | Wrong key/region / F0 rate limit | Check `.env`; retry later (the engine already retries 3 times) |
| Same recording fails after a staging deploy | Label or column changed | Read `output/errors/*.png`, re-run `snapshot`, update the build script, follow [UI change sync](ui-change-sync.md) |
| Second recording of a module fails on unique data | Demo data from the first run still exists | Reset the recording database or clean `Demo – ` data, then re-run |
| Function inside `page.evaluate` throws `__name is not defined` | tsx injects a helper into named functions | Send the script as a string |
| Git Bash turns `/route` into `C:/Program Files/Git/route` | MSYS path conversion | `MSYS_NO_PATHCONV=1 npm run snapshot -- LOGIN /route` |

Error screenshots from recordings are in `output/errors/`; from E2E in `output/e2e/<id>/`. Read the screenshot
before changing a selector: most failures are data state, not selectors.
