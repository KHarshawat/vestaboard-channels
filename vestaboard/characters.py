"""Vestaboard character code table.

Source: https://docs.vestaboard.com/docs/characterCodes
"""

ROWS = 6
COLS = 22

BLANK = 0

# code -> printable character
CODE_TO_CHAR: dict[int, str] = {
    0: " ",
    **{i: chr(ord("A") + i - 1) for i in range(1, 27)},  # 1-26 = A-Z
    **{26 + i: str(i) for i in range(1, 10)},  # 27-35 = 1-9
    36: "0",
    37: "!",
    38: "@",
    39: "#",
    40: "$",
    41: "(",
    42: ")",
    44: "-",
    46: "+",
    47: "&",
    48: "=",
    49: ";",
    50: ":",
    52: "'",
    53: '"',
    54: "%",
    55: ",",
    56: ".",
    59: "/",
    60: "?",
    62: "°",  # degree sign (Flagship)
}

# printable character -> code (letters matched case-insensitively via upper())
CHAR_TO_CODE: dict[str, int] = {ch: code for code, ch in CODE_TO_CHAR.items()}

# Colored tiles. "filled" is contrast-inverted (board-dependent).
COLOR_CODES: dict[str, int] = {
    "red": 63,
    "orange": 64,
    "yellow": 65,
    "green": 66,
    "blue": 67,
    "violet": 68,
    "white": 69,
    "black": 70,
    "filled": 71,
}
