/** Thin client for the Vestaboard Read/Write API
 * (docs.vestaboard.com/docs/read-write-api/endpoints). */

import { COLS, ROWS, type Grid } from "./characters";

export const API_URL = "https://cloud.vestaboard.com/";
const RATE_LIMIT_MS = 16_000; // board accepts one message per 15 s

export class BoardMutedError extends Error {
  constructor() {
    super("Board is muted (HTTP 423); message rejected.");
  }
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function post(body: Record<string, unknown>, token: string): Promise<void> {
  if (!token) throw new Error("VESTABOARD_TOKEN secret is not set");
  for (let attempt = 0; ; attempt++) {
    const res = await fetch(API_URL, {
      method: "POST",
      headers: { "X-Vestaboard-Token": token, "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (res.status === 429 && attempt === 0) {
      // Another message landed within the last 15 s; wait it out once.
      await sleep(RATE_LIMIT_MS);
      continue;
    }
    if (res.status === 423) throw new BoardMutedError();
    if (!res.ok) throw new Error(`Vestaboard POST failed: HTTP ${res.status} ${await res.text()}`);
    return;
  }
}

export async function postCharacters(grid: Grid, token: string, forced = false): Promise<void> {
  if (grid.length !== ROWS || grid.some((row) => row.length !== COLS)) {
    throw new Error(`grid must be ${ROWS} rows of ${COLS} character codes`);
  }
  const body: Record<string, unknown> = { characters: grid };
  if (forced) body.forced = true;
  await post(body, token);
}

export async function getCurrent(token: string): Promise<unknown> {
  const res = await fetch(API_URL, { headers: { "X-Vestaboard-Token": token } });
  if (!res.ok) throw new Error(`Vestaboard GET failed: HTTP ${res.status}`);
  return res.json();
}
