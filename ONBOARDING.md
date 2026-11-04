# Onboarding / session handoff

Context for picking up work on this repo (last updated 2026-11-04).
Read CLAUDE.md first for board facts and conventions; this file is
project state.

## What's built (channel → script + workflow, times are PST; +1h in PDT)

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

- **GitHub cron fires 4–8 HOURS late in this repo** (observed Nov 3–4).
  Every workflow runs `vestaboard/cron_guard.py` first and skips cleanly
  when the schedule event fired beyond a per-channel grace window
  (letter 180 min, weather 150, muni 45, holidays 240, dinner 180, moon
  240). Manual `workflow_dispatch` always runs and starts in seconds.
- **Proposed real fix (pending Kavi's decision):** external scheduler
  (cron-job.org or Cloudflare Worker cron) calling the GitHub API
  `workflow_dispatch` at exact times with a fine-grained PAT
  (actions:write on this repo). Kavi hasn't created the PAT yet.
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

## Style notes

- Kavi likes: clean centered layouts with breathing room, color-tile
  accents/headers, sunset time on weather, °F, "M SUNNY"-style
  abbreviations are fine.
- Dinner menu updates happen conversationally: edit menu.json, push.
- Test: `python -m channels.<name> --dry-run` (`--date YYYY-MM-DD`
  where supported). Never post during development.
