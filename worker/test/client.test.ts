import { afterEach, describe, expect, it, vi } from "vitest";
import { BoardMutedError, postCharacters } from "../src/board/client";
import { blankGrid } from "../src/board/render";

describe("vestaboard client", () => {
  afterEach(() => vi.restoreAllMocks());

  it("sends the grid with the token header", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("ok", { status: 200 }));
    await postCharacters(blankGrid(), "tok");
    const [url, init] = spy.mock.calls[0];
    expect(url).toBe("https://cloud.vestaboard.com/");
    expect((init!.headers as Record<string, string>)["X-Vestaboard-Token"]).toBe("tok");
    expect(JSON.parse(init!.body as string).characters).toHaveLength(6);
  });

  it("waits out the 15 s rate limit once on 429", async () => {
    vi.useFakeTimers();
    const spy = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response("slow down", { status: 429 }))
      .mockResolvedValueOnce(new Response("ok", { status: 200 }));
    const p = postCharacters(blankGrid(), "tok");
    await vi.advanceTimersByTimeAsync(16_000);
    await p;
    expect(spy).toHaveBeenCalledTimes(2);
    vi.useRealTimers();
  });

  it("raises BoardMutedError on 423", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("muted", { status: 423 }));
    await expect(postCharacters(blankGrid(), "tok")).rejects.toBeInstanceOf(BoardMutedError);
  });

  it("refuses to post without a token", async () => {
    await expect(postCharacters(blankGrid(), "")).rejects.toThrow(/VESTABOARD_TOKEN/);
  });
});
