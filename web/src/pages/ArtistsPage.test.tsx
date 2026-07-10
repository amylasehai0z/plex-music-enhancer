import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ArtistsPage } from "./ArtistsPage";

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MantineProvider>
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <ArtistsPage />
        </MemoryRouter>
      </QueryClientProvider>
    </MantineProvider>,
  );
}

function stubArtistsApi() {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/artists/100")) {
      return jsonResponse({
        ratingKey: "100",
        title: "Nina Simone",
        library: "Music",
        albumCount: 2,
        trackCount: 3,
        summaryPresent: false,
        plannedAction: null,
        albums: [
          {
            ratingKey: "200",
            title: "Pastel Blues",
            artist: "Nina Simone",
            library: "Music",
            year: 1965,
            summaryPresent: false,
            plannedAction: null,
          },
        ],
        tracks: ["Be My Husband", "Sinnerman"],
        reviews: [
          {
            albumId: "200",
            artist: "Nina Simone",
            album: "Pastel Blues",
            year: 1965,
            tracks: ["Be My Husband"],
            content: {
              summary: "Eine fokussierte Kritik.",
              rating: 88,
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
          },
        ],
      });
    }
    if (url.endsWith("/artists/101")) {
      return jsonResponse({
        ratingKey: "101",
        title: "ABBA",
        library: "Music",
        albumCount: 8,
        trackCount: 98,
        summaryPresent: false,
        plannedAction: null,
        albums: [
          {
            ratingKey: "210",
            title: "Arrival",
            artist: "ABBA",
            library: "Music",
            year: 1976,
            summaryPresent: false,
            plannedAction: null,
          },
        ],
        tracks: ["Dancing Queen"],
        reviews: [],
      });
    }
    if (url.endsWith("/artists")) {
      return jsonResponse([
        {
          ratingKey: "100",
          title: "Nina Simone",
          library: "Music",
          albumCount: 2,
          trackCount: 3,
          summaryPresent: false,
          plannedAction: null,
        },
        {
          ratingKey: "101",
          title: "ABBA",
          library: "Music",
          albumCount: 8,
          trackCount: 98,
          summaryPresent: false,
          plannedAction: null,
        },
      ]);
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

describe("ArtistsPage", () => {
  it("renders synced artists with search and detail data", async () => {
    const fetchMock = stubArtistsApi();

    renderPage();

    expect(await screen.findByRole("heading", { name: "Künstler" })).toBeInTheDocument();
    expect(await screen.findByText("Nina Simone")).toBeInTheDocument();
    expect(screen.getAllByText("ABBA").length).toBeGreaterThan(0);
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/v1/artists/101", undefined);
    });
    expect(await screen.findByText("Arrival (1976)")).toBeInTheDocument();

    fireEvent.change(screen.getByRole("textbox", { name: "Künstler suchen" }), {
      target: { value: "Nina" },
    });

    expect(await screen.findByText("Pastel Blues (1965)")).toBeInTheDocument();
    expect(screen.getByText("Pastel Blues: 88/100")).toBeInTheDocument();

    fireEvent.change(screen.getByRole("textbox", { name: "Künstler suchen" }), {
      target: { value: "ABBA" },
    });

    await waitFor(() => {
      expect(screen.getAllByText("ABBA").length).toBeGreaterThan(0);
      expect(screen.queryByText("Nina Simone")).not.toBeInTheDocument();
    });
    expect(await screen.findByText("Arrival (1976)")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/artists", undefined);
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/artists/100", undefined);
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/artists/101", undefined);
  });
});
