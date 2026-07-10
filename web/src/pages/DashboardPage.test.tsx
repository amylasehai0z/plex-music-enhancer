import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DashboardPage } from "./DashboardPage";

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MantineProvider>
      <QueryClientProvider client={queryClient}>
        <DashboardPage />
      </QueryClientProvider>
    </MantineProvider>,
  );
}

function stubDashboardApi() {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/plex/sync") && init?.method === "POST") {
      return jsonResponse({
        running: true,
        progress: 10,
        libraries: 1,
        artists: 120,
        albums: 450,
        tracks: 5200,
        lastSync: null,
      });
    }
    if (url.endsWith("/plex/sync/status")) {
      return jsonResponse({
        running: false,
        progress: 100,
        libraries: 1,
        artists: 120,
        albums: 450,
        tracks: 5200,
        lastSync: "2026-07-10T12:00:00Z",
      });
    }
    if (url.endsWith("/statistics")) {
      return jsonResponse({ artists: 120, albums: 450, tracks: 5200, libraries: 1, cacheEntries: 3 });
    }
    if (url.endsWith("/providers")) {
      return jsonResponse([{ name: "openai", configured: true, model: "gpt-5.5", details: { type: "ai" } }]);
    }
    if (url.endsWith("/config")) {
      return jsonResponse({ configuration: { plexConfigured: true, aiProvider: "openai", aiModel: "gpt-5.5" } });
    }
    if (url.endsWith("/system/version")) {
      return jsonResponse({ version: "1.0.2", apiVersion: "v1" });
    }
    if (url.endsWith("/debug/review")) {
      return jsonResponse({ exists: false, sections: {} });
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

describe("DashboardPage", () => {
  it("shows Plex sync status and starts synchronization", async () => {
    const fetchMock = stubDashboardApi();

    renderPage();

    expect(await screen.findByRole("heading", { name: "Plex Synchronisation" })).toBeInTheDocument();
    expect(await screen.findByText("5.200")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Synchronisieren" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/plex/sync",
        expect.objectContaining({ method: "POST" }),
      );
    });
  });
});
