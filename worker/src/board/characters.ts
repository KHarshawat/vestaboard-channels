/** Vestaboard character code table (docs.vestaboard.com/docs/characterCodes). */

export const ROWS = 6;
export const COLS = 22;
export const BLANK = 0;

export type Grid = number[][];

const PUNCT: Record<number, string> = {
  37: "!", 38: "@", 39: "#", 40: "$", 41: "(", 42: ")", 44: "-", 46: "+",
  47: "&", 48: "=", 49: ";", 50: ":", 52: "'", 53: '"', 54: "%", 55: ",",
  56: ".", 59: "/", 60: "?", 62: "°",
};

/** code -> printable character */
export const CODE_TO_CHAR: Map<number, string> = new Map([[0, " "]]);
for (let i = 1; i <= 26; i++) CODE_TO_CHAR.set(i, String.fromCharCode(64 + i)); // A-Z
for (let i = 1; i <= 9; i++) CODE_TO_CHAR.set(26 + i, String(i)); // 1-9
CODE_TO_CHAR.set(36, "0");
for (const [code, ch] of Object.entries(PUNCT)) CODE_TO_CHAR.set(Number(code), ch);

/** printable character (uppercase) -> code */
export const CHAR_TO_CODE: Map<string, number> = new Map();
for (const [code, ch] of CODE_TO_CHAR) CHAR_TO_CODE.set(ch, code);

/** Colored tiles. "filled" is contrast-inverted (board-dependent). */
export const COLOR_CODES: Record<string, number> = {
  red: 63, orange: 64, yellow: 65, green: 66, blue: 67, violet: 68,
  white: 69, black: 70, filled: 71,
};
export const CODE_TO_COLOR: Map<number, string> = new Map(
  Object.entries(COLOR_CODES).map(([name, code]) => [code, name]),
);
