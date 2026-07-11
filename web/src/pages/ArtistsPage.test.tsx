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
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/preview") && init?.method === "POST") {
      return jsonResponse(previewResponse());
    }
    if (url.endsWith("/apply") && init?.method === "POST") {
      return jsonResponse(applyResponse());
    }
    if (url.endsWith("/batch/start") && init?.method === "POST") {
      return jsonResponse({ running: true, cancelled: false, progress: 0, queue: [], pending: 1, completed: 0, failed: 0, skipped: 0, total: 1 });
    }
    if (url.endsWith("/artists/100/refresh") && init?.method === "POST") {
      return jsonResponse({
        ratingKey: "100",
        title: "Nina Simone",
        library: "Music",
        albumCount: 2,
        trackCount: 3,
        summaryPresent: true,
        summary: "Aktualisierte Plex-Biografie.",
        reviewCount: 1,
        plexUrl: "http://plex:32400/web/index.html#!/details?key=%2Flibrary%2Fmetadata%2F100",
        plannedAction: null,
        albums: [],
        tracks: [],
        reviews: [],
      });
    }
    if (url.endsWith("/artists/100")) {
      return jsonResponse({
        ratingKey: "100",
        title: "Nina Simone",
        library: "Music",
        albumCount: 2,
        trackCount: 3,
        summaryPresent: true,
        summary: "Existing Plex biography.",
        reviewCount: 1,
        plexUrl: "http://plex:32400/web/index.html#!/details?key=%2Flibrary%2Fmetadata%2F100",
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
        summaryPresent: true,
        summary: "ABBA biography.",
        reviewCount: 0,
        plexUrl: "http://plex:32400/web/index.html#!/details?key=%2Flibrary%2Fmetadata%2F101",
        plannedAction: null,
        albums: [
          {
            ratingKey: "210",
            title: "Arrival",
            artist: "ABBA",
            library: "Music",
            year: 1976,
            summaryPresent: true,
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
          summaryPresent: true,
          summary: "Existing Plex biography.",
          reviewCount: 1,
          plexUrl: "http://plex:32400/web/index.html#!/details?key=%2Flibrary%2Fmetadata%2F100",
          plannedAction: null,
        },
        {
          ratingKey: "101",
          title: "ABBA",
          library: "Music",
          albumCount: 8,
          trackCount: 98,
          summaryPresent: true,
          summary: "ABBA biography.",
          reviewCount: 0,
          plexUrl: "http://plex:32400/web/index.html#!/details?key=%2Flibrary%2Fmetadata%2F101",
          plannedAction: null,
        },
        {
          ratingKey: "102",
          title: "No Bio",
          library: "Music",
          albumCount: 1,
          trackCount: 8,
          summaryPresent: false,
          summary: null,
          reviewCount: 0,
          plexUrl: "http://plex:32400/web/index.html#!/details?key=%2Flibrary%2Fmetadata%2F102",
          plannedAction: null,
        },
      ]);
    }
    return jsonResponse({});
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function reviewDocument() {
  return {
    apiVersion: "v1",
    target: "artist",
    mode: "create",
    artist: "Nina Simone",
    album: null,
    ratingKey: "100",
    currentSummary: "Existing Plex biography.",
    generatedSummary: "Neue deutsche Biografie.",
    proposedSummary: "Neue deutsche Biografie.",
    unifiedDiff: "--- alt\n+++ neu",
    qa: {
      status: "PASS",
      criticalValidation: "PASS",
      editorialValidation: "PASS",
      publishable: true,
      wordCount: 4,
      checks: {},
      warnings: [],
      failures: [],
      overallScore: 91,
      overallLevel: "GOOD",
    },
    editorial: {
      score: 91,
      level: "GOOD",
      recommendations: [],
      missingTopics: [],
      styleMetrics: {},
      editorialMetrics: {},
    },
    verification: {
      verifiedFacts: 1,
      probableFacts: 0,
      weakFacts: 0,
      conflictingFacts: 0,
      unknownFacts: 0,
      coverageScore: 100,
      conflicts: [],
      missingFacts: [],
    },
    prompt: {
      name: "artist_biography",
      version: "1.0",
      characters: 1200,
      estimatedTokens: 300,
      trimmed: false,
      budgetDiagnostics: {},
      decisions: {},
      quality: {},
      utilization: {},
      evidenceRanking: {},
      evidenceCoverage: {},
      editorialCoverage: {},
      editorialBalance: {},
      missedOpportunities: [],
    },
    debug: {
      provider: "dummy",
      model: "dummy-v1",
      generationTimeSeconds: 0,
      tokenUsage: {},
      sourceCount: 1,
      raw: {},
    },
    provider: "dummy",
    model: "dummy-v1",
    edited: false,
    plan: null,
    context: {},
  };
}

function previewResponse() {
  return { document: reviewDocument() };
}

function applyResponse() {
  return {
    status: "SUCCESS",
    artist: "Nina Simone",
    album: "artist",
    ratingKey: "100",
    backupCreated: true,
    writeSuccessful: true,
    verificationPassed: true,
    auditStored: true,
    message: "Plex hat die Änderung bestätigt.",
    review: reviewDocument(),
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

  it("filters artists by biography status", async () => {
    stubArtistsApi();

    renderPage();

    expect(await screen.findByRole("heading", { name: "Künstler" })).toBeInTheDocument();
    expect(await screen.findByText("Nina Simone")).toBeInTheDocument();
    expect(screen.getAllByText("ABBA").length).toBeGreaterThan(0);
    expect(screen.getByLabelText("Aktiver Bio-Filter")).toHaveTextContent("Alle Künstler");

    fireEvent.change(screen.getByLabelText("Bio-Filter"), {
      target: { value: "missing" },
    });

    await waitFor(() => {
      expect(screen.getByLabelText("Aktiver Bio-Filter")).toHaveTextContent("Ohne Bio");
    });
    expect(screen.getByText("No Bio")).toBeInTheDocument();
    expect(screen.queryByText("ABBA")).not.toBeInTheDocument();
    expect(screen.queryByText("Nina Simone")).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Bio-Filter"), {
      target: { value: "present" },
    });

    await waitFor(() => {
      expect(screen.getByLabelText("Aktiver Bio-Filter")).toHaveTextContent("Mit Bio");
    });
    expect(screen.getAllByText("ABBA").length).toBeGreaterThan(0);
    expect(screen.getByText("Nina Simone")).toBeInTheDocument();
    expect(screen.queryByText("No Bio")).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Bio-Filter"), {
      target: { value: "all" },
    });

    await waitFor(() => {
      expect(screen.getByLabelText("Aktiver Bio-Filter")).toHaveTextContent("Alle Künstler");
    });
    expect(screen.getByText("Nina Simone")).toBeInTheDocument();
    expect(screen.getAllByText("ABBA").length).toBeGreaterThan(0);
  });

  it("starts a batch for selected artists", async () => {
    const fetchMock = stubArtistsApi();

    renderPage();

    expect(await screen.findByText("Nina Simone")).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("Nina Simone auswählen"));
    fireEvent.click(screen.getByRole("button", { name: "Batch starten" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/batch/start",
        expect.objectContaining({
          method: "POST",
          body: expect.stringContaining('"target":"artist"'),
        }),
      );
    });
  });

  it("opens a preview for the selected artist", async () => {
    const fetchMock = stubArtistsApi();

    renderPage();

    expect(await screen.findByText("Nina Simone")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("textbox", { name: "Künstler suchen" }), {
      target: { value: "Nina" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Preview" }));

    expect(await screen.findByText("Künstler-Preview")).toBeInTheDocument();
    expect(screen.getByText("Neue deutsche Biografie.")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/preview",
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining('"target":"artist"'),
      }),
    );
  });

  it("applies an artist review only after backend verification and refreshes the artist", async () => {
    const fetchMock = stubArtistsApi();

    renderPage();

    expect(await screen.findByText("Nina Simone")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("textbox", { name: "Künstler suchen" }), {
      target: { value: "Nina" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/apply",
        expect.objectContaining({
          method: "POST",
          body: expect.stringContaining('"target":"artist"'),
        }),
      );
    });
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/artists/100/refresh",
        expect.objectContaining({ method: "POST" }),
      );
    });
  });

  it("opens the selected artist in Plex", async () => {
    const open = vi.spyOn(window, "open").mockImplementation(() => null);
    stubArtistsApi();

    renderPage();

    expect(await screen.findByText("Nina Simone")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("textbox", { name: "Künstler suchen" }), {
      target: { value: "Nina" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Plex" }));

    expect(open).toHaveBeenCalledWith(
      "http://plex:32400/web/index.html#!/details?key=%2Flibrary%2Fmetadata%2F100",
      "_blank",
      "noopener,noreferrer",
    );
  });

  it("refreshes only the active artist from Plex", async () => {
    const fetchMock = stubArtistsApi();

    renderPage();

    expect(await screen.findByText("Nina Simone")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("textbox", { name: "Künstler suchen" }), {
      target: { value: "Nina" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Refresh" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/artists/100/refresh",
        expect.objectContaining({ method: "POST" }),
      );
    });
    expect(fetchMock).not.toHaveBeenCalledWith("/api/v1/plex/sync", expect.anything());
  });
});
