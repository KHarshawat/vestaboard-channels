/** Letter of the Day: cycles A-Z deterministically by date, with kid-friendly words. */

import { blankGrid, setRow } from "../board/render";
import type { Grid } from "../board/characters";
import { localDate, parseDateKey, pyOrdinal, type CivilDate } from "../time";
import WORDS from "./letter-words.json";
import type { Channel } from "./types";

export function letterFor(day: CivilDate): string {
  return String.fromCharCode(65 + (pyOrdinal(day) % 26));
}

export function buildGrid(day: CivilDate): Grid {
  const letter = letterFor(day);
  const words = [...(WORDS as Record<string, string[]>)[letter]].sort(
    (a, b) => a.length - b.length || (a < b ? -1 : a > b ? 1 : 0),
  );
  const g = blankGrid();
  setRow(g, 1, "THE LETTER OF THE", "center");
  setRow(g, 2, `DAY IS {blue}${letter}{blue}`, "center");
  setRow(g, 4, "{yellow}" + words.join("{yellow}") + "{yellow}", "center");
  return g;
}

export const letter: Channel = {
  name: "letter",
  description: "Letter of the day with words",
  async render(ctx, opts) {
    const day = opts.date ? parseDateKey(opts.date) : localDate(ctx.now);
    return { pages: [{ name: letterFor(day), grid: buildGrid(day) }], skipped: [] };
  },
};
