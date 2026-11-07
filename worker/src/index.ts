/** Cloudflare Worker entry point.
 *
 *   scheduled  every minute: look up the Pacific-time slot and post it
 *   fetch      GET  /                      schedule + what would post now
 *              GET  /preview/<channel>     ASCII dry-run (never posts)
 *              POST /run/<channel>         post now; needs ADMIN_TOKEN bearer
 *                   ?date=YYYY-MM-DD       date override for date-driven channels
 *                   ?page=<name>           weather page/sequence (see weather.ts)
 *                   ?index=<n>             which rendered page to post (default 0)
 */

import { postCharacters } from "./board/client";
import { gridToAscii } from "./board/preview";
import { CHANNELS } from "./channels/index";
import type { ChannelOpts, Env, FetchJson, RenderCtx, RenderResult } from "./channels/types";
import { SCHEDULE, describe, slotAt } from "./schedule";
import { localParts } from "./time";

const fetchJson: FetchJson = async (url, init) => {
  const res = await fetch(url, init);
  if (!res.ok) throw new Error(`GET ${url.split("?")[0]} -> HTTP ${res.status}`);
  const text = await res.text();
  return JSON.parse(text.replace(/^﻿/, "")); // 511.org sends a BOM
};

function render(name: string, ctx: RenderCtx, opts: ChannelOpts): Promise<RenderResult> {
  const channel = CHANNELS[name];
  if (!channel) throw new Error(`unknown channel ${JSON.stringify(name)}; choose from ${Object.keys(CHANNELS).join(", ")}`);
  return channel.render(ctx, opts);
}

function describeResult(r: RenderResult): string {
  const out: string[] = [];
  for (const s of r.skipped) out.push(`[${s.name}] skipped - ${s.reason}`);
  for (const p of r.pages) out.push(`[${p.name}]`, gridToAscii(p.grid));
  return out.join("\n");
}

export default {
  async scheduled(event: ScheduledController, env: Env, _ctx: ExecutionContext): Promise<void> {
    const now = new Date(event.scheduledTime);
    const local = localParts(now);
    const match = slotAt(local.hhmm);
    if (!match) return;
    const { slot, offset } = match;
    const tag = `${local.dateKey} ${local.hhmm} ${slot.channel}${slot.page ? `/${slot.page}` : ""}`;
    const result = await render(slot.channel, { now, env, fetchJson }, { page: slot.page });
    for (const s of result.skipped) console.log(`${tag}: [${s.name}] skipped - ${s.reason}`);
    if (result.pages.length === 0) {
      console.log(`${tag}: nothing to post`);
      return;
    }
    const page = result.pages[offset % result.pages.length];
    await postCharacters(page.grid, env.VESTABOARD_TOKEN);
    const cycle = slot.from && result.pages.length > 1 ? ` (${offset % result.pages.length + 1}/${result.pages.length} in cycle)` : "";
    console.log(`${tag}: posted [${page.name}]${cycle}`);
  },

  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const text = (body: string, status = 200) =>
      new Response(body + "\n", { status, headers: { "content-type": "text/plain; charset=utf-8" } });
    const now = new Date();
    const local = localParts(now);
    const opts: ChannelOpts = {
      date: url.searchParams.get("date") ?? undefined,
      page: url.searchParams.get("page") ?? undefined,
    };
    const ctx: RenderCtx = { now, env, fetchJson };

    try {
      if (url.pathname === "/") {
        const match = slotAt(local.hhmm);
        const lines = [
          `vestaboard-channels worker. Pacific time now: ${local.dateKey} ${local.hhmm}`,
          `This minute: ${match ? describe(match.slot) : "nothing scheduled"}`,
          "",
          "Schedule (Pacific):",
          ...SCHEDULE.map((s) => "  " + describe(s)),
          "",
          "Channels: " + Object.values(CHANNELS).map((c) => `${c.name} - ${c.description}`).join("; "),
          "",
          "GET /preview/<channel>?date=YYYY-MM-DD&page=<page>   dry-run ASCII preview",
          "POST /run/<channel>?page=<page>&index=<n>            post to the board (Authorization: Bearer ADMIN_TOKEN)",
        ];
        return text(lines.join("\n"));
      }

      const preview = /^\/preview\/([a-z]+)$/.exec(url.pathname);
      if (preview && request.method === "GET") {
        const result = await render(preview[1], ctx, opts);
        return text(describeResult(result) + "\n\nDry run - nothing was posted.");
      }

      const run = /^\/run\/([a-z]+)$/.exec(url.pathname);
      if (run && request.method === "POST") {
        const auth = request.headers.get("authorization") ?? "";
        if (!env.ADMIN_TOKEN || auth !== `Bearer ${env.ADMIN_TOKEN}`) return text("unauthorized", 401);
        const result = await render(run[1], ctx, opts);
        if (result.pages.length === 0) return text(describeResult(result) + "\n\nNothing to post.");
        const index = Number(url.searchParams.get("index") ?? 0);
        const page = result.pages[index];
        if (!page) return text(`no page at index ${index}; rendered ${result.pages.length}`, 400);
        await postCharacters(page.grid, env.VESTABOARD_TOKEN);
        return text(`[${page.name}]\n${gridToAscii(page.grid)}\n\nPosted to the board.`);
      }

      return text("not found", 404);
    } catch (e) {
      return text(`error: ${(e as Error).message}`, 500);
    }
  },
};
