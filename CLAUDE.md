# vestaboard-channels

Python 3.11+ scripts that post content to a Vestaboard Flagship split-flap
display via the Read/Write API, scheduled with GitHub Actions.

## Board facts

- 6 rows × 22 columns. Character codes: 0 = blank, 1–26 = A–Z, 27–36 = 1–0,
  punctuation up to 62, colored tiles 63–71. Full table in
  `vestaboard/characters.py` (source: docs.vestaboard.com/docs/characterCodes).
- API: POST/GET https://cloud.vestaboard.com/ with `X-Vestaboard-Token`.
  Rate limit: one message per 15 seconds. Blank messages are rejected.
  POST returns 423 when the board is muted (the client exits non-zero).

## Conventions

- One channel = one script in `channels/` + one workflow in
  `.github/workflows/` with the same name.
- **Nothing posts to the board without an explicit `--post` flag** (or being
  run from a workflow, which passes `--post`). The default for every channel
  is a dry-run ASCII preview via `vestaboard.preview.print_grid`.
- Shared code lives in `vestaboard/` (client, render helpers, preview).
  Keep dependencies minimal — `requests` only.
- GitHub cron is UTC; Pacific-time schedules shift an hour with DST
  (accepted; note it in the workflow file).
- Test channels with `python -m channels.<name> --dry-run` (supports
  `--date YYYY-MM-DD` where applicable). Never post during development.
