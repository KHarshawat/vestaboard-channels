/** Letter of the Day: cycles A-Z deterministically by date, with kid-friendly words. */

import { blankGrid, setRow } from "../board/render";
import type { Grid } from "../board/characters";
import { localDate, parseDateKey, pyOrdinal, type CivilDate } from "../time";
import WORDS from "./letter-words.json";
import type { Channel } from "./types";

const CYCLE = 26; // days per block; every letter appears once per block

/** Tiny seeded PRNG, implemented identically in channels/letter_of_the_day.py. */
function mulberry32(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1) >>> 0;
    t = (t ^ ((t + Math.imul(t ^ (t >>> 7), t | 61)) >>> 0)) >>> 0;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** A shuffled A-Z for the given 26-day block (Fisher-Yates, seeded by block). */
export function blockOrder(block: number): string[] {
  const rand = mulberry32((Math.imul(block, 2654435761) + 42) >>> 0);
  const letters = Array.from({ length: 26 }, (_, i) => String.fromCharCode(65 + i));
  for (let i = 25; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [letters[i], letters[j]] = [letters[j], letters[i]];
  }
  return letters;
}

/** Random-looking but deterministic: each 26-day block is a shuffled A-Z,
 * so no letter repeats within a block and the order differs every block. */
export function letterFor(day: CivilDate): string {
  const ordinal = pyOrdinal(day);
  const block = Math.floor(ordinal / CYCLE);
  const index = ordinal - block * CYCLE;
  const order = blockOrder(block);
  if (index === 0 && blockOrder(block - 1)[25] === order[0]) {
    [order[0], order[1]] = [order[1], order[0]]; // no same letter two days running
  }
  return order[index];
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
