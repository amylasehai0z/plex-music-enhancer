import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiClient, ApiError, ReviewApi } from "./client";

describe("ApiClient", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("uses the central API prefix for requests", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ status: "ok" }), { status: 200 })),
    );
    const client = new ApiClient("/api/v1");

    await client.get("/system/health");

    expect(fetch).toHaveBeenCalledWith("/api/v1/system/health", undefined);
  });

  it("maps failed JSON responses to ApiError", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(JSON.stringify({ message: "Review failed" }), {
            status: 422,
            headers: { "content-type": "application/json" },
          }),
      ),
    );
    const client = new ApiClient("/api/v1");

    await expect(client.get("/review/artist")).rejects.toBeInstanceOf(ApiError);
  });
});

describe("ReviewApi", () => {
  it("dispatches review calls by target without exposing fetch to components", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ document: {}, applyAllowed: true, messages: [] }), { status: 200 })),
    );
    const review = new ReviewApi(new ApiClient("/api/v1"));

    await review.review({ target: "album", artist: "Jennifer Rush", album: "Credo" });

    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/review/album",
      expect.objectContaining({ method: "POST" }),
    );
  });
});
