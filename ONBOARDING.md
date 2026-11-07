# Onboarding / session handoff

Context for picking up work on this repo (last updated 2026-11-05).
Read CLAUDE.md first for board facts and conventions; this file is
project state.

## Current state (2026-11-05): moving the scheduler to Cloudflare

GitHub cron fired every scheduled run 4–8 hours late (Oct 31 – Nov 4, every
workflow, no exceptions; see the Nov 4 note below). Kavi chose to run
everything from a Cloudflare Worker instead, TypeScript, with the morning
weather pages cycling one per minute over the half hour. Election stays
Python/manual. Quiet hours are Kavi's to handle in the Vestaboard app.

Built on branch `claude/code-onboarding-iksojp` (not yet merged/deployed):

- `worker/` — Cloudflare Worker. Cron `* * * * *`; `src/schedule.ts` maps
  Pacific wall-clock minutes to posts (DST-correct via Intl). Channels
  ported: letter, weather (all 8 pages), muni, holidays, dinner, moon.
  `GET /preview/<channel>` dry-run, `POST /run/<channel>` with ADMIN_TOKEN.
- `worker/test/` — vitest parity suite: `gen_parity.py` runs the Python
  channels on fixed dates/fixtures and the TS port must match cell for cell
  (369 holiday days, 215 moon dates, 3 weather scenarios, muni, dinner,
  letter). All green. Verified under workerd with `wrangler dev`.
- `.github/workflows/deploy_worker.yml` — deploys on push to main
  (worker/** or menu.json) via cloudflare/wrangler-action, uploading
  VESTABOARD_TOKEN / TRANSIT_511_API_KEY / ADMIN_TOKEN as Worker secrets.
- GitHub `schedule:` triggers removed from all channel workflows (now
  `workflow_dispatch` only, manual fallback). `vestaboard/cron_guard.py`
  deleted.

**Waiting on Kavi** (then merge to main = first deploy):
1. Cloudflare dashboard: Account ID; API token (Edit Cloudflare Workers
   template); open Workers & Pages once so a workers.dev subdomain exists.
2. Repo secrets: CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID, ADMIN_TOKEN.
3. Optional, for Claude to deploy/tail directly from a session: the same
   two Cloudflare values as environment secrets, and allow
   api.cloudflare.com + developers.cloudflare.com in the session network.

Schedule now (Pacific, DST-correct): 7:00 letter; 7:15–7:45 weather pages
cycling one per minute; 8:00–8:15 muni refreshed every minute; 8:15 + 12:00 holidays; 4:30pm dinner;
5:00pm moon; 8:30pm tomorrow; 8:33pm NWS alert if active.

## What was built on GitHub Actions (times are PST; +1h in PDT) — now manual fallback

| Slot | Channel | Notes |
|---|---|---|
| 7:00am | letter_of_the_day | "THE LETTER OF THE DAY IS [X]" + words, blue/yellow tiles |
| 7:15–7:55 | weather (morning) | today → timeline → 5-day, 10 min apart, then conditional pages: rain ≥40%, heat risk ≥2, NWS alert, AQI >100 |
| 8:00am | muni | N Judah east 17318 / west 17252 via 511.org (needs TRANSIT_511_API_KEY) |
| 8:15am + noon | fun_holidays | 674 fixed + 27 floating rules (Easter computus incl.); lists all of a day's holidays with color-tile bullets |
| 4:30pm | dinner_menu | reads menu.json (ISO date → meal); unset days skip; update = edit file + push |
| 5:00pm | moon_phase | phase + traditional moon name countdown + ( ) illumination tile bar |
| 8:30pm | weather (evening) | tomorrow view (incl. 8am temp) + alerts if active |
| manual | election | NYT results feeds, --watch loops 60s in one long job, --until hard stop |

Weather data: NWS gridpoint MTR/84,105 (Duboce Triangle, 53 Walter St).
Sunset computed locally (NOAA equation). AQI: Open-Meteo (keyless).

## Critical operational knowledge

- **GitHub cron fired 4–8 HOURS late in this repo** (every scheduled run
  Oct 31 – Nov 4). The cron_guard workaround skipped late runs; the real
  fix is the Cloudflare Worker above. Manual `workflow_dispatch` always
  started in seconds. Dispatching two channels within 15 s of each other
  gets a 429 from the board (happened Nov 4); the Worker client retries.
- **The board has overnight quiet hours** (exact window unknown; mutes
  observed ~11pm–7am). A muted board returns HTTP 423 and the client
  exits non-zero. Kavi also runs native Vestaboard-app channels that
  post on their own schedule — no API exists to view or control them;
  a board-audit workflow (poll GET every 15 min, log what's showing)
  was proposed but not built.
- DST: crons are UTC, so Pacific times shift an hour between PST/PDT
  (accepted; noted per workflow file).

## Secrets (repo Actions secrets, already set)

- `VESTABOARD_TOKEN` — Read/Write API key
- `TRANSIT_511_API_KEY` — 511.org open-data key (muni)

## Backlog (Kavi-approved, not yet built)

1. Morning dashboard (weather + muni + sunset combined)
2. Tides & sunset (NOAA CO-OPS, Ocean Beach)
3. Family calendar (Google Calendar, needs auth)
4. Recology bin-night reminder (need Kavi's pickup day)
5. Guest welcome script (no schedule)
6. Enphase solar/battery (blocked: Kavi needs a developer.enphase.com
   account for OAuth; local Envoy API is LAN-only, unreachable from CI)
Excluded by Kavi: sports scores, kid trivia, countdowns.

## Work log (chronological, with reasoning)

- **Oct 30-31 — repo setup.** Built `vestaboard/` package (client,
  render, preview, characters table fetched from official docs), letter
  channel, workflows, README/CLAUDE.md. Convention established: nothing
  posts without `--post`; dry-run ASCII preview is the default. Secret
  added via github.com settings. First manual workflow run posted
  letter "M" successfully.
- **Nov 1 — letter redesign** to Kavi's mockup: "THE LETTER OF THE /
  DAY IS [X]" with blue tiles around the letter, words length-sorted
  with yellow tile separators. All 26 letters verified to fit.
- **Nov 1 — weather channel** (replaced plan for commercial APIs with
  NWS per Kavi's microclimate rationale). Resolved 53 Walter St →
  gridpoint MTR/84,105 live (Kavi's source had said 86,126 — wrong).
  Kavi supplied a reference layout image (NOW/LIKE/HIGH/LOW left
  column; RAIN/WIND/UV/SET right); we replaced the clock row with a
  fog/"CLEARING BY" line and UV with SKY% (NWS has no UV layer). Then
  expanded same day to 5 suggested pages: hour-by-hour fog/sun tile
  timeline, conditional rain-timing/heat/NWS-alert pages, evening
  "tomorrow" sequence. Sunset bug fixed (NOAA equation needs integer
  days since J2000; was 12h off).
- **Nov 1 — moon phase** ported from tidbyt/community (pure math, no
  API; verified against 2024 solar + 2025 lunar eclipses). Kavi then
  requested the ( ) illumination bar (white fills waxing, drains
  waning) and traditional moon names incl. BLUE for second-full-moon-
  in-month; "nearest full" naming fixed so full-moon night doesn't
  show next month's name; TONIGHT window widened 1.3d for model drift.
- **Nov 1 — dinner menu** (menu.json, 4:30pm, skip when unset — Kavi's
  choices). Seeded Coconut Lentil Soup Nov 2-5. wrap() promoted to
  vestaboard.render.
- **Nov 2 — muni.** Kavi's stops east 17318 / west 17252, 8am post.
  Verified the old NextBus/UmoIQ feed no longer serves sf-muni;
  researched and confirmed 511.org is the sanctioned source (SFMTA's
  own predictions; NextGen revamp will flow through it). 511 responses
  carry a UTF-8 BOM (decode utf-8-sig).
- **Nov 2 — fun holidays.** Kavi supplied three lists (wacky days,
  national days, Wikipedia food days) merged with dedupe; floating
  rules + Easter computus. Kavi then asked to list ALL of a day's
  holidays (color-tile bullets, shortest-first packing) instead of
  rotating one. Added morning 8:15 slot in addition to noon. Data
  judgment calls: kept Pirate Day Sep 19 (a list wrongly said 16),
  skipped World Egg Day (mangled source date).
- **Nov 3 — the cron saga.** Kavi reported missing posts. Found GitHub
  firing crons 4-8h late; late posts landed in quiet hours → 423
  failures (dinner meant for 4:30pm ran 11:04pm). Built cron_guard
  (skip if late), later per-channel grace windows. Also moved the
  morning block per Kavi: letter 7:00, weather 7:15-7:55 (10-min gaps),
  muni 8:00.
- **Nov 3 — election night channel** (same-day request). NYT feeds
  discovered live and keyless; one-board layout per Kavi's spec: House
  and Senate each a numbers line + 22-tile bar (blue Dem left, red GOP
  right, white uncalled). Ran as a 60s-loop dispatched job (GitHub
  cron can't do minutes), posted only on count changes, hard stop
  11pm (Kavi's call). Worked end to end on election night.
- **Nov 4 — morning sequence missed again** (crons 4-8h late, guard
  skipped). Dispatched manually, widened grace per channel, proposed
  external scheduler as the real fix (pending PAT from Kavi).
- **Nov 5 — Cloudflare port.** Pulled the Actions run history to show
  Kavi every cron was 4–8 h late. Options laid out (self-chaining
  workflow, Cloudflare-as-clock, full port); Kavi chose the full
  TypeScript port on Cloudflare, with the weather pages cycling one per
  minute over the morning half hour, election left as-is, quiet hours
  handled in the app. Built `worker/` + parity tests + deploy workflow,
  removed GitHub schedules. Design choices: every-minute cron + Pacific
  slot table (one trigger, fixes DST, no sleeps); no KV cache — each
  weather minute refetches NWS (3 parallel GETs, well under the free
  plan's 10 ms CPU); if logs ever show CPU limit errors, the $5 paid plan
  is the fix. NWS calls send the repo User-Agent.

## Style notes

- Kavi likes: clean centered layouts with breathing room, color-tile
  accents/headers, sunset time on weather, °F, "M SUNNY"-style
  abbreviations are fine.
- Dinner menu updates happen conversationally: edit menu.json, push.
- Test: `python -m channels.<name> --dry-run` (`--date YYYY-MM-DD`
  where supported). Never post during development.
