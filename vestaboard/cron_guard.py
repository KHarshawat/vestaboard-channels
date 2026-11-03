"""Freshness guard for scheduled workflows.

GitHub Actions cron events can fire hours late; a delayed run would post
stale content at the wrong time of day (often into the board's quiet
hours, where it 423s). Given the cron spec that triggered the run, print
"yes" if we are within the grace window of the intended time, else "no".

Usage (in a workflow):
    python -m vestaboard.cron_guard "${{ github.event.schedule }}" [max_late_minutes]
"""

import datetime
import sys


def main() -> int:
    minute, hour = (int(f) for f in sys.argv[1].split()[:2])
    max_late = int(sys.argv[2]) if len(sys.argv) > 2 else 120
    now = datetime.datetime.now(datetime.UTC)
    intended = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if intended > now:
        intended -= datetime.timedelta(days=1)
    late = (now - intended).total_seconds() / 60
    fresh = late <= max_late
    print("yes" if fresh else "no")
    print(f"cron intended {intended:%H:%M} UTC, fired {late:.0f} min late "
          f"(grace {max_late} min) -> {'run' if fresh else 'SKIP'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
