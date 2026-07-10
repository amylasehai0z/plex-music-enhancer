import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AlbumsPage } from "./AlbumsPage";

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MantineProvider>
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AlbumsPage />
        </MemoryRouter>
      </QueryClientProvider>
    </MantineProvider>,
  );
}

function stubAlbumsApi() {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/reviews/generate/201") && init?.method === "POST") {
      return jsonResponse({ status: "started", albumId: "201" });
    }
    if (url.endsWith("/albums/200")) {
      return jsonResponse({
        ratingKey: "200",
        title: "Pastel Blues",
        artist: "Nina Simone",
        artistId: "100",
        library: "Music",
        year: 1965,
        trackCount: 2,
        genres: ["Jazz"],
        reviewStatus: "present",
        summaryPresent: true,
        plannedAction: null,
        tracks: ["1. Be My Husband", "2. Sinnerman"],
        review: storedReview("200", "Pastel Blues", 88),
      });
    }
    if (url.endsWith("/albums/201")) {
      return jsonResponse({
        ratingKey: "201",
        title: "Wild Is the Wind",
        artist: "Nina Simone",
        artistId: "100",
        library: "Music",
        year: 1966,
        trackCount: 1,
        genres: [],
        reviewStatus: "missing",
        summaryPresent: false,
        plannedAction: null,
        tracks: ["1. Wild Is the Wind"],
        review: null,
      });
    }
    if (url.endsWith("/albums")) {
      return jsonResponse([
        {
          ratingKey: "200",
          title: "Pastel Blues",
          artist: "Nina Simone",
          artistId: "100",
          library: "Music",
          year: 1965,
          trackCount: 2,
          genres: ["Jazz"],
          reviewStatus: "present",
          summaryPresent: true,
          plannedAction: null,
        },
        {
          ratingKey: "201",
          title: "Wild Is the Wind",
          artist: "Nina Simone",
          artistId: "100",
          library: "Music",
          year: 1966,
          trackCount: 1,
          genres: [],
          reviewStatus: "missing",
          summaryPresent: false,
          plannedAction: null,
        },
      ]);
    }
    if (url.endsWith("/reviews")) {
      return jsonResponse({ albums: [], generatedReviews: 0, averageRating: null });
    }
    return jsonResponse({});
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function storedReview(albumId: string, album: string, rating: number) {
  return {
    albumId,
    artist: "Nina Simone",
    album,
    year: 1965,
    tracks: ["1. Be My Husband"],
    content: {
      summary: "Eine fokussierte Kritik.",
      rating,
      genres: ["Jazz"],
      strengths: ["Stimme"],
      weaknesses: [],
      recommendedFor: "Jazz-Hörer.",
      finalVerdict: "Starkes Album.",
    },
    provider: "dummy",
    model: "dummy-v1",
    promptName: "album_review",
    promptVersion: "1.0",
    createdAt: "2026-01-01T00:00:00Z",
  };
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

describe("AlbumsPage", () => {
  it("renders synced albums with search, detail data and review generation", async () => {
    const fetchMock = stubAlbumsApi();

    renderPage();

    expect(await screen.findByRole("heading", { name: "Alben" })).toBeInTheDocument();
    expect(await screen.findByText("Pastel Blues")).toBeInTheDocument();
    expect(screen.getAllByText("Nina Simone").length).toBeGreaterThan(0);
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/v1/albums/200", undefined);
    });
    expect(await screen.findByText("1. Be My Husband")).toBeInTheDocument();
    expect(screen.getByText("88/100")).toBeInTheDocument();
    expect(screen.getByText("Starkes Album.")).toBeInTheDocument();

    fireEvent.change(screen.getByRole("textbox", { name: "Album suchen" }), {
      target: { value: "Wild" },
    });

    await waitFor(() => {
      expect(screen.getByText("Wild Is the Wind")).toBeInTheDocument();
      expect(screen.queryByText("Pastel Blues")).not.toBeInTheDocument();
    });
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/v1/albums/201", undefined);
    });
    expect(await screen.findByText("1. Wild Is the Wind")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Review erzeugen" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/reviews/generate/201",
        expect.objectContaining({ method: "POST" }),
      );
    });
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/albums", undefined);
  });
});
