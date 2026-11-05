import { dinner } from "./dinner";
import { holidays } from "./holidays";
import { letter } from "./letter";
import { moon } from "./moon";
import { muni } from "./muni";
import type { Channel } from "./types";
import { weather } from "./weather";

export const CHANNELS: Record<string, Channel> = Object.fromEntries(
  [letter, weather, muni, holidays, dinner, moon].map((c) => [c.name, c]),
);
