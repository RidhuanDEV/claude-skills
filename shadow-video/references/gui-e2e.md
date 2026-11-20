# GUI E2E with scene files

`npm run e2e` runs the actions of a scene file in a real browser without recording, TTS, or the fake cursor.
It is the selector proof before every recording and a click-through regression test on its own.

```
npm run e2e -- 02a-usulan            # headless, stops at the first failure
npm run e2e -- 02a-usulan --headed   # visible browser, 150 ms slow-mo (E2E_SLOWMO_MS) so a person can follow
npm run e2e -- 02a-usulan --shots    # screenshot at the end of every scene (layout evidence)
npm run e2e -- 02a-usulan --trace    # Playwright trace: npx playwright show-trace output/e2e/<id>/trace.zip
npm run e2e                          # every scenes/*.json except 00-*, in name order
npm run selftest -- --e2e            # offline engine check on built-in local pages (no BASE_URL needed)
```

Output per run in `output/e2e/<id>/`: `report.json`, `report.md` (one row per action: PASS, FAIL, SKIP, ms),
`FAIL-<scene>-a<n>.png` on failure, scene screenshots with `--shots`, `trace.zip` with `--trace`.
Exit code 1 when any non-optional action fails, so CI or another agent can gate on it.

## Semantics (identical to the recorder where it matters)

- Strict locators: more than one match without `nth` is a FAIL, as in recording.
- `hover` works on disabled elements (`force`), as the recorder only moves the cursor there.
- `upload` really uploads, so validation and save steps after it are tested.
- `waitFor url` uses the recorder's matcher (substring or `/regex/flags`).
- `pause` is shortened to 300 ms. Recording-only actions (`maskText`, `capture`, `fetchMail`, `manual`) are
  reported as SKIP; scenes that depend on a captured value need it in `cache/vars.json` from an earlier run.
- `type` uses `fill`: fast, but it does not prove per-key handlers (input masks that react to keydown). Watch
  those fields in the preview recording.
- After the first FAIL the run stops; later steps would only fail as a consequence.

## Using it as a regression suite

- E2E mutates data exactly like the recording. Run it against the recording database or a resettable staging
  snapshot, never against data people use.
- Order matters for dependent modules: run them in the same order as recording, from the documented data state.
- For CI: `npm ci`, `npx playwright install chromium`, `BROWSER_CHANNEL=chromium`, a seeded test backend, then
  `npm run e2e`. Turnstile-protected logins cannot run headless in CI; use a session prepared outside CI or a
  staging build without the captcha.
- A PASS proves the selectors and flow work at that moment. It does not prove visual layout; use `--shots` or
  `--headed` and look, and say "Not measured" when you did not.
