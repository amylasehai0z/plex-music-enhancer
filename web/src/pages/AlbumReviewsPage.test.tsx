import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AlbumReviewsPage } from "./AlbumReviewsPage";

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MantineProvider>
      <QueryClientProvider client={queryClient}>
        <AlbumReviewsPage />
      </QueryClientProvider>
    </MantineProvider>,
  );
}

function stubReviewApi() {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/reviews/generate/200") && init?.method === "POST") {
      return jsonResponse({ status: "started", albumId: "200" });
    }
    if (url.endsWith("/reviews")) {
      return jsonResponse({
        albums: [
          {
            albumId: "200",
            artist: "Nina Simone",
            album: "Pastel Blues",
            year: 1965,
            trackCount: 2,
            reviewStatus: "present",
            running: false,
            rating: 91,
            summary: "Eine konzentrierte Kritik.",
            review: {
              albumId: "200",
              artist: "Nina Simone",
              album: "Pastel Blues",
              year: 1965,
              tracks: ["1. Be My Husband", "2. Nobody Knows You When You're Down and Out"],
              content: {
                summary: "Eine konzentrierte Kritik.",
                rating: 91,
                genres: ["Blues", "Jazz"],
                strengths: ["Ausdruck"],
                weaknesses: ["Knapp dokumentierte Produktionsdaten"],
                recommendedFor: "Hörer klassischer Vokalalben.",
                finalVerdict: "Ein starkes Vokalalbum.",
              },
              provider: "dummy",
              model: "dummy-v1",
              promptName: "album_review",
              promptVersion: "1.0",
              createdAt: "2026-01-01T00:00:00Z",
            },
          },
        ],
        generatedReviews: 1,
        averageRating: 91,
      });
    }
    return jsonResponse({});
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function jsonResponse(payload: unknown) {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("AlbumReviewsPage", () => {
  it("shows synchronized albums and starts review generation", async () => {
    const fetchMock = stubReviewApi();

    renderPage();

    expect(await screen.findByRole("heading", { name: "Reviews" })).toBeInTheDocument();
    expect(await screen.findByText("Pastel Blues")).toBeInTheDocument();
    expect(screen.getByText("91/100")).toBeInTheDocument();
    expect(screen.getByText("Ein starkes Vokalalbum.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Review generieren" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/reviews/generate/200",
        expect.objectContaining({ method: "POST" }),
      );
    });
  });
});
