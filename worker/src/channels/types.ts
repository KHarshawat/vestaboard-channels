import type { Grid } from "../board/characters";

export interface Env {
  VESTABOARD_TOKEN: string;
  TRANSIT_511_API_KEY?: string;
  ADMIN_TOKEN?: string;
}

export type FetchJson = (url: string, init?: RequestInit) => Promise<any>;

export interface RenderCtx {
  now: Date;
  env: Env;
  fetchJson: FetchJson;
}

export interface ChannelOpts {
  /** Override "today" (YYYY-MM-DD, Pacific) for date-driven channels. */
  date?: string;
  /** Channel-specific page/sequence selector (weather). */
  page?: string;
}

export interface Page {
  name: string;
  grid: Grid;
}

export interface RenderResult {
  pages: Page[];
  skipped: { name: string; reason: string }[];
}

export interface Channel {
  name: string;
  description: string;
  render(ctx: RenderCtx, opts: ChannelOpts): Promise<RenderResult>;
}
