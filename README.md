# vestaboard-channels

Custom channels for a Vestaboard Flagship (6 rows × 22 columns). The board is
driven by a Cloudflare Worker in `worker/` (TypeScript) that fires every
minute and posts whatever the Pacific-time schedule says is due. The original
Python channels in `channels/` remain as a manual fallback and as the
reference the TypeScript port is tested against.

## How it runs

- `worker/src/schedule.ts` is the daily schedule in Pacific wall-clock time
  (DST-correct). A slot with `at` posts once; a block with `from`/`until`
  re-renders the channel every minute, cycling its pages (the morning
  weather block; muni refreshes its arrival times this way too).
- `worker/src/channels/*.ts` build 6×22 grids. `menu.json` and the holiday
  calendar are bundled into the Worker at deploy time.
- `.github/workflows/deploy_worker.yml` deploys on every push to `main` that
  touches `worker/` or `menu.json`. Push-triggered Actions start within
  seconds; GitHub's `schedule` trigger (4–8 h late) is no longer used.

## Setup

1. Vestaboard Read/Write API key from https://web.vestaboard.com.
2. Cloudflare account (free plan is enough). From the dashboard note the
   Account ID and create an API token with the **Edit Cloudflare Workers**
   template (My Profile → API Tokens).
3. Repo secrets (Settings → Secrets and variables → Actions):
   `VESTABOARD_TOKEN`, `TRANSIT_511_API_KEY`, `CLOUDFLARE_API_TOKEN`,
   `CLOUDFLARE_ACCOUNT_ID`, `ADMIN_TOKEN` (any long random string; it
   protects the manual-post endpoint).
4. Push to `main` (or run the *Deploy Worker* workflow). The deploy uploads
   the board/511/admin secrets to the Worker.

## Worker endpoints

The Worker is at `https://vestaboard-channels.<your-subdomain>.workers.dev`.

```
GET  /                                   schedule + what this minute would post
GET  /preview/<channel>?date=YYYY-MM-DD   ASCII dry run (never posts)
GET  /preview/weather?page=morning|evening|all|today|timeline|forecast|tomorrow|rain|heat|alerts|aqi
POST /run/<channel>?page=..&index=..     post now (header: Authorization: Bearer <ADMIN_TOKEN>)
```

Channels: `letter`, `weather`, `muni`, `holidays`, `dinner`, `moon`.

## Develop

```sh
cd worker
npm install
npm test            # parity tests against grids produced by the Python channels
npm run typecheck
npm run dev         # local Worker on http://localhost:8787 (+ /__scheduled?cron=*+*+*+*+*&time=<ms>)
npm run tail        # live logs from the deployed Worker (needs wrangler login or CLOUDFLARE_API_TOKEN)
```

The parity fixtures come from `python worker/test/gen_parity.py` (run from the
repo root); regenerate them if the Python channels change.

## Change the schedule

Edit `worker/src/schedule.ts` and push to `main`. Times are Pacific.

## Add a channel

1. `worker/src/channels/<name>.ts` exporting a `Channel` (see `letter.ts`
   for the smallest example) and register it in `worker/src/channels/index.ts`.
2. Add a slot in `worker/src/schedule.ts`.
3. Preview with `npm run dev` and `curl localhost:8787/preview/<name>`.

## Python fallback

```sh
pip install -r requirements.txt
python -m channels.letter_of_the_day --dry-run   # ASCII preview, posts nothing
python -m channels.letter_of_the_day --post      # actually posts to the board
```

Each Python channel still has a `workflow_dispatch`-only GitHub workflow.
`channels/election.py` (election-night live results) is Python-only and runs
from its workflow on demand.
