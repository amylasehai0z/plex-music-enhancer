import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AlbumsPage } from "./AlbumsPage";

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MantineProvider>
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AlbumsPage />
          <LocationProbe />
        </MemoryRouter>
      </QueryClientProvider>
    </MantineProvider>,
  );
}

function LocationProbe() {
  const location = useLocation();
  return <div data-testid="location">{`${location.pathname}${location.search}`}</div>;
}

function stubAlbumsApi() {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/batch/start") && init?.method === "POST") {
      return jsonResponse({ running: true, cancelled: false, progress: 0, queue: [], pending: 1, completed: 0, failed: 0, skipped: 0, total: 1 });
    }
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
        coverUrl: "/covers/pastel-blues.jpg",
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
        coverUrl: null,
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
          coverUrl: "/covers/pastel-blues.jpg",
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
          coverUrl: null,
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
  it("renders synced albums with detail data and review navigation", async () => {
    const fetchMock = stubAlbumsApi();

    renderPage();

    expect(await screen.findByRole("heading", { name: "Alben" })).toBeInTheDocument();
    expect(await screen.findByText("Pastel Blues")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getAllByRole("img", { name: "Pastel Blues Cover" }).length).toBeGreaterThan(0);
    });
    expect(screen.getAllByText("Nina Simone").length).toBeGreaterThan(0);
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/v1/albums/200", undefined);
    });
    expect(await screen.findByText("1. Be My Husband")).toBeInTheDocument();
    expect(screen.getByText("88/100")).toBeInTheDocument();
    expect(screen.getByText("Starkes Album.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Review öffnen" }));

    await waitFor(() => {
      expect(screen.getByTestId("location")).toHaveTextContent(
        "/review-workflow?target=album&artist=Nina%20Simone&album=Pastel%20Blues&run=1",
      );
    });
  });

  it("searches albums and starts review generation", async () => {
    const fetchMock = stubAlbumsApi();

    renderPage();

    expect(await screen.findByRole("heading", { name: "Alben" })).toBeInTheDocument();

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

  it("filters albums by review status", async () => {
    stubAlbumsApi();

    renderPage();

    expect(await screen.findByText("Pastel Blues")).toBeInTheDocument();
    expect(screen.getByLabelText("Aktiver Review-Filter")).toHaveTextContent("Alle Alben");

    fireEvent.change(screen.getByRole("combobox", { name: "Review-Filter" }), {
      target: { value: "missing" },
    });

    await waitFor(() => {
      expect(screen.getByText("Wild Is the Wind")).toBeInTheDocument();
      expect(screen.queryByText("Pastel Blues")).not.toBeInTheDocument();
    });
    expect(screen.getByLabelText("Aktiver Review-Filter")).toHaveTextContent("Ohne Review");

    fireEvent.change(screen.getByRole("combobox", { name: "Review-Filter" }), {
      target: { value: "present" },
    });

    await waitFor(() => {
      expect(screen.getAllByText("Pastel Blues").length).toBeGreaterThan(0);
      expect(screen.queryByText("Wild Is the Wind")).not.toBeInTheDocument();
    });
    expect(screen.getByLabelText("Aktiver Review-Filter")).toHaveTextContent("Mit Review");

    fireEvent.change(screen.getByRole("combobox", { name: "Review-Filter" }), {
      target: { value: "all" },
    });

    await waitFor(() => {
      expect(screen.getAllByText("Pastel Blues").length).toBeGreaterThan(0);
      expect(screen.getByText("Wild Is the Wind")).toBeInTheDocument();
    });
  });

  it("starts a batch for selected albums", async () => {
    const fetchMock = stubAlbumsApi();

    renderPage();

    expect(await screen.findByText("Pastel Blues")).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("Pastel Blues auswählen"));
    fireEvent.click(screen.getByRole("button", { name: "Batch starten" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/batch/start",
        expect.objectContaining({
          method: "POST",
          body: expect.stringContaining('"target":"album"'),
        }),
      );
    });
  });
});
