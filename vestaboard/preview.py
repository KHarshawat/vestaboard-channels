"""Print a grid to stdout so layouts can be checked without posting."""

import sys

from .characters import CODE_TO_CHAR, COLOR_CODES
from .render import validate

# ANSI background colors for colored tiles (used when stdout is a TTY)
_ANSI_BG = {
    "red": "41",
    "orange": "48;5;208",
    "yellow": "43",
    "green": "42",
    "blue": "44",
    "violet": "45",
    "white": "47",
    "black": "40",
    "filled": "100",
}
_CODE_TO_COLOR = {code: name for name, code in COLOR_CODES.items()}


def _cell(code: int, use_ansi: bool) -> str:
    if code in _CODE_TO_COLOR:
        name = _CODE_TO_COLOR[code]
        if use_ansi:
            return f"\x1b[{_ANSI_BG[name]}m \x1b[0m"
        return name[0].lower()  # lowercase letter = color tile (board text is uppercase)
    return CODE_TO_CHAR.get(code, "?")


def print_grid(grid: list[list[int]], use_ansi: bool | None = None) -> None:
    """Render a 6x22 grid as ASCII art. Colored tiles print as ANSI color
    blocks on a TTY, otherwise as a lowercase color initial (r, o, y, ...)."""
    validate(grid)
    if use_ansi is None:
        use_ansi = sys.stdout.isatty()
    border = "+" + "-" * len(grid[0]) + "+"
    print(border)
    for row in grid:
        print("|" + "".join(_cell(code, use_ansi) for code in row) + "|")
    print(border)
