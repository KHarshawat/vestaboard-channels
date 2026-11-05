/** Render a grid as ASCII art; color tiles print as their lowercase initial
 * (board text is uppercase, so r/o/y/g/b/v/w/k/f are unambiguous). */

import { CODE_TO_CHAR, CODE_TO_COLOR, type Grid } from "./characters";
import { validate } from "./render";

function cell(code: number): string {
  const colorName = CODE_TO_COLOR.get(code);
  if (colorName) return colorName === "black" ? "k" : colorName[0];
  return CODE_TO_CHAR.get(code) ?? "?";
}

export function gridToAscii(grid: Grid): string {
  validate(grid);
  const border = "+" + "-".repeat(grid[0].length) + "+";
  return [border, ...grid.map((row) => "|" + row.map(cell).join("") + "|"), border].join("\n");
}
