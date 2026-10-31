# vestaboard-channels

Custom channels for a Vestaboard Flagship (6 rows × 22 columns). Each channel
is a Python script in `channels/` that builds a message and posts it to the
board, run on a schedule by a GitHub Actions workflow.

## Setup

1. Get a Read/Write API key from https://web.vestaboard.com.
2. Add it as a repo secret named `VESTABOARD_TOKEN`
   (Settings → Secrets and variables → Actions → New repository secret).
3. For local runs: `cp .env.example .env`, fill in the token, and
   `export VESTABOARD_TOKEN=...` (or use your favorite .env loader).

## Run locally

```sh
pip install -r requirements.txt
python -m channels.letter_of_the_day --dry-run   # ASCII preview, posts nothing
python -m channels.letter_of_the_day --post      # actually posts to the board
```

Channels never post unless given `--post`; the default is a dry-run preview.

## Add a new channel

1. Create `channels/my_channel.py`. Build a grid with the helpers in
   `vestaboard/` (`blank_grid`, `set_row`, `text_to_row`, `color`), preview it
   with `print_grid`, and post it with `post_characters` only when `--post`
   is passed (copy the argparse block from `letter_of_the_day.py`).
2. Create `.github/workflows/my_channel.yml` — copy
   `letter_of_the_day.yml`, change the name, cron, and script path. Cron is
   UTC; 7am Pacific ≈ `0 14 * * *` (shifts an hour with DST).
3. Test with `python -m channels.my_channel --dry-run` before merging.
