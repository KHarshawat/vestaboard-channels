"""Build 6x22 character-code grids from strings.

Strings may contain any character in the Vestaboard character set plus
``{color}`` placeholders (e.g. ``"{red} HI {red}"``) for colored tiles.
"""

import re

from .characters import BLANK, CHAR_TO_CODE, COLOR_CODES, COLS, ROWS

_PLACEHOLDER = re.compile(r"\{(\w+)\}")


def color(name: str) -> int:
    """Return the tile code for a color name (red, orange, yellow, green,
    blue, violet, white, black, filled)."""
    try:
        return COLOR_CODES[name.lower()]
    except KeyError:
        raise ValueError(
            f"unknown color {name!r}; choose from {', '.join(COLOR_CODES)}"
        ) from None


def encode(text: str) -> list[int]:
    """Convert a string to character codes. ``{color}`` becomes a color tile."""
    codes: list[int] = []
    pos = 0
    while pos < len(text):
        match = _PLACEHOLDER.match(text, pos)
        if match and match.group(1).lower() in COLOR_CODES:
            codes.append(COLOR_CODES[match.group(1).lower()])
            pos = match.end()
            continue
        ch = text[pos].upper()
        if ch not in CHAR_TO_CODE:
            raise ValueError(f"character {text[pos]!r} has no Vestaboard code")
        codes.append(CHAR_TO_CODE[ch])
        pos += 1
    return codes


def text_to_row(text: str, align: str = "left") -> list[int]:
    """Encode a string as one 22-cell row, padded with blanks."""
    codes = encode(text)
    if len(codes) > COLS:
        raise ValueError(f"row is {len(codes)} cells; the board is {COLS} wide: {text!r}")
    pad = COLS - len(codes)
    if align == "left":
        return codes + [BLANK] * pad
    if align == "right":
        return [BLANK] * pad + codes
    if align == "center":
        left = pad // 2
        return [BLANK] * left + codes + [BLANK] * (pad - left)
    raise ValueError(f"align must be left, center, or right, not {align!r}")


def blank_grid() -> list[list[int]]:
    """Return a 6x22 grid of blanks."""
    return [[BLANK] * COLS for _ in range(ROWS)]


def set_row(grid: list[list[int]], row_index: int, text: str, align: str = "left") -> list[list[int]]:
    """Write a string into row ``row_index`` (0-5) of a grid, in place."""
    if not 0 <= row_index < ROWS:
        raise ValueError(f"row_index must be 0-{ROWS - 1}, not {row_index}")
    grid[row_index] = text_to_row(text, align=align)
    return grid


def wrap(text: str, width: int = COLS, max_lines: int = 3) -> list[str]:
    """Word-wrap a string into at most ``max_lines`` lines of ``width``."""
    lines: list[str] = []
    cur = ""
    for word in text.split():
        if len(cur) + bool(cur) + len(word) <= width:
            cur = f"{cur} {word}".strip()
        else:
            lines.append(cur)
            cur = word
    lines.append(cur)
    return lines[:max_lines]


def validate(grid: list[list[int]]) -> None:
    """Raise if a grid is not 6x22 ints within the known character set."""
    if len(grid) != ROWS:
        raise ValueError(f"grid has {len(grid)} rows; expected {ROWS}")
    known = set(CHAR_TO_CODE.values()) | set(COLOR_CODES.values()) | {BLANK}
    for i, row in enumerate(grid):
        if len(row) != COLS:
            raise ValueError(f"row {i} has {len(row)} cells; expected {COLS}")
        for code in row:
            if code not in known:
                raise ValueError(f"row {i} contains unknown character code {code}")
