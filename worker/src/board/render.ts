/** Build 6x22 character-code grids from strings. `{color}` placeholders
 * (e.g. "{red} HI {red}") become colored tiles. */

import { BLANK, CHAR_TO_CODE, COLOR_CODES, COLS, ROWS, type Grid } from "./characters";

export type Align = "left" | "center" | "right";

export function color(name: string): number {
  const code = COLOR_CODES[name.toLowerCase()];
  if (code === undefined) {
    throw new Error(`unknown color ${JSON.stringify(name)}; choose from ${Object.keys(COLOR_CODES).join(", ")}`);
  }
  return code;
}

export function encode(text: string): number[] {
  const codes: number[] = [];
  let pos = 0;
  while (pos < text.length) {
    const m = /^\{(\w+)\}/.exec(text.slice(pos));
    if (m && COLOR_CODES[m[1].toLowerCase()] !== undefined) {
      codes.push(COLOR_CODES[m[1].toLowerCase()]);
      pos += m[0].length;
      continue;
    }
    const ch = text[pos].toUpperCase();
    const code = CHAR_TO_CODE.get(ch);
    if (code === undefined) throw new Error(`character ${JSON.stringify(text[pos])} has no Vestaboard code`);
    codes.push(code);
    pos += 1;
  }
  return codes;
}

export function textToRow(text: string, align: Align = "left"): number[] {
  const codes = encode(text);
  if (codes.length > COLS) {
    throw new Error(`row is ${codes.length} cells; the board is ${COLS} wide: ${JSON.stringify(text)}`);
  }
  const pad = COLS - codes.length;
  const blanks = (n: number) => new Array<number>(n).fill(BLANK);
  if (align === "left") return [...codes, ...blanks(pad)];
  if (align === "right") return [...blanks(pad), ...codes];
  const left = Math.floor(pad / 2);
  return [...blanks(left), ...codes, ...blanks(pad - left)];
}

export function blankGrid(): Grid {
  return Array.from({ length: ROWS }, () => new Array<number>(COLS).fill(BLANK));
}

export function setRow(grid: Grid, rowIndex: number, text: string, align: Align = "left"): Grid {
  if (rowIndex < 0 || rowIndex >= ROWS) throw new Error(`rowIndex must be 0-${ROWS - 1}, not ${rowIndex}`);
  grid[rowIndex] = textToRow(text, align);
  return grid;
}

/** Word-wrap into at most maxLines lines of width (same algorithm as the Python). */
export function wrap(text: string, width: number = COLS, maxLines = 3): string[] {
  const lines: string[] = [];
  let cur = "";
  for (const word of text.split(/\s+/).filter(Boolean)) {
    if (cur.length + (cur ? 1 : 0) + word.length <= width) {
      cur = `${cur} ${word}`.trim();
    } else {
      lines.push(cur);
      cur = word;
    }
  }
  lines.push(cur);
  return lines.slice(0, maxLines);
}

const KNOWN = new Set<number>([BLANK, ...CHAR_TO_CODE.values(), ...Object.values(COLOR_CODES)]);

export function validate(grid: Grid): void {
  if (grid.length !== ROWS) throw new Error(`grid has ${grid.length} rows; expected ${ROWS}`);
  grid.forEach((row, i) => {
    if (row.length !== COLS) throw new Error(`row ${i} has ${row.length} cells; expected ${COLS}`);
    for (const code of row) {
      if (!KNOWN.has(code)) throw new Error(`row ${i} contains unknown character code ${code}`);
    }
  });
}

/** Python-style padding helpers: `{x:<5}` -> padR(x, 5); `{x:>3}` -> padL(x, 3). */
export const padR = (v: string | number, n: number) => String(v).padEnd(n);
export const padL = (v: string | number, n: number) => String(v).padStart(n);
