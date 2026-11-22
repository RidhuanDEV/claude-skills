# Recording environment

## Target and safety

- `BASE_URL`: local frontend (proxied to a test backend) or staging with a test database. Never production.
- `BLOCKED_HOSTS`: comma-separated production hosts. `baseUrl()` refuses to start when the host matches, so set it
  even when you "know" the URL is staging.
- Prefer a **dedicated recording database** separate from the development database (for example a Docker
  container with a named volume, reset to a baseline plus demo accounts before a session). Named SQL snapshots of
  data states ("before revision", "ready for report") let any module be re-recorded without replaying earlier ones.
- Data created while recording uses the `Demo – ` prefix so it can be found and removed.
- Cleanup of demo data on shared staging is destructive: dry-run first, list exactly what will be deleted, and
  delete only demo-prefixed or listed demo ids after the Monarch approves.

## Accounts and sessions

- Demo accounts live in `.env` as `<PREFIX>_EMAIL` / `<PREFIX>_PASSWORD`; prefixes are declared in
  `video.config.json` `rolePrefixes`. Use realistic display names ("Dr. Andi Pratama"), never accounts called
  "admin1" or "dosen" that would appear in search results on screen.
- A user with several roles may land on a role picker. Use single-role demo accounts per tutorial actor.
- `npm run login -- --auto` stores `auth/storageState.json`; the login tutorial itself uses `"recordLogin": true`
  and `"saveSession": "storageState"`. The recorder saves the session again after every recording because apps
  rotate refresh tokens: do not use the same account elsewhere while recording.
- `npm run snapshot` keeps its own per-role sessions in `cache/snapshot-auth/` (login rate limits).

## Captcha, OTP and email

- Cloudflare Turnstile rejects Playwright Chromium (headless and headed), headless Chrome, and locale/timezone
  emulation (error 600010). It accepts installed Google Chrome, headed, without the automation flag. That is the
  default (`BROWSER_CHANNEL=chrome`, `RECORD_LOGIN_HEADED=1`). Apps without a captcha can use
  `BROWSER_CHANNEL=chromium` and `RECORD_LOGIN_HEADED=0`.
- When Turnstile also blocks launched Chrome: `npx tsx tools/login-chrome.ts` (normal Chrome, manual login, saved
  session) or `npx tsx tools/chrome-cdp.ts start` then `CDP_URL=http://127.0.0.1:9334` for the recording.
- OTP or verification links: `fetchMail` against a staging mail catcher (Mailpit, `MAILPIT_URL`), then `type` the
  `{{OTP}}` or `openUrl` the `{{LINK}}`. A human-only step uses `manual`; its waiting time is cut.

## Display

- Videos are 1920x1080 at 25 fps, H.264 yuv420p + AAC 48 kHz. Headed runs force device scale factor 1 so Windows
  display scaling (125%) does not zoom the page. Do not touch the mouse or the Chrome window during a headed run.
- Browser UI language follows `BROWSER_LANG` (default `id-ID`) so native controls read "Pilih File".

## TTS and licence

- Default `TTS_PROVIDER=azure` (Azure AI Speech REST, licensed for commercial use). The Free F0 tier is enough for
  tutorials and refuses rather than bills when the monthly quota runs out; add a budget alert anyway.
- `TTS_PROVIDER=edge` uses the unofficial edge-tts client: internal previews only, never a delivered video.
- Microsoft's AI Code of Conduct requires disclosure of synthetic voices: keep "Narasi menggunakan suara sintetis
  (AI)" in `cardFooter`.
- No open-source Indonesian TTS with a clear commercial licence was found (2026-10 survey: MMS-TTS is CC-BY-NC,
  Piper `id_ID` data provenance unclear). Ask legal before switching.
- Audio is cached by provider + voice + rate + pitch + text; editing narration re-synthesises only changed scenes.

## Teardown after recording (Zero Lingering Servers)

- Stop every process spawned for the recording session (`tools/video-env.cjs` frontend + backend, `tools/chrome-cdp.ts`, Playwright browser instances, and ephemeral recording Docker DBs) inside `try/finally` or immediately after `npm run verify` / `npm run final` completes.
- Register task-owned PIDs via `shadow-monarch/scripts/resource_cleanup.py --register` and release them with `--cleanup-owned` (or explicit PID tree stop) so zero recording servers remain active when switching projects.
- Never run blanket `taskkill /IM node.exe /F` or touch dev servers belonging to other repositories/ports or active host MCP sessions.
