import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { BatchPage } from "./BatchPage";

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MantineProvider>
      <QueryClientProvider client={queryClient}>
        <BatchPage />
      </QueryClientProvider>
    </MantineProvider>,
  );
}

function stubBatchApi() {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/batch/status")) {
      return jsonResponse({
        running: true,
        cancelled: false,
        progress: 50,
        active: { id: "1", target: "artist", plexId: "100", name: "Nina Simone", artist: "Nina Simone", status: "running", progress: 50 },
        queue: [{ id: "1", target: "artist", plexId: "100", name: "Nina Simone", artist: "Nina Simone", status: "running", progress: 50 }],
        pending: 1,
        completed: 2,
        failed: 1,
        skipped: 0,
        total: 4,
        estimatedRemainingSeconds: 90,
      });
    }
    if (url.endsWith("/batch/history")) {
      return jsonResponse({
        history: [{ id: "h1", target: "album", plexId: "200", name: "Pastel Blues", artist: "Nina Simone", album: "Pastel Blues", status: "completed", progress: 100, runtimeSeconds: 12 }],
      });
    }
    if (url.endsWith("/batch/cancel") || url.endsWith("/batch/clear")) {
      return jsonResponse({ running: false, cancelled: true, progress: 100, queue: [], pending: 0, completed: 0, failed: 0, skipped: 0, total: 0 });
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

describe("BatchPage", () => {
  it("renders queue status, history and cancel action", async () => {
    const fetchMock = stubBatchApi();

    renderPage();

    expect(await screen.findByRole("heading", { name: "Batch" })).toBeInTheDocument();
    expect(await screen.findAllByText("Nina Simone")).toHaveLength(2);
    expect(screen.getByText("Pastel Blues")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/batch/cancel",
        expect.objectContaining({ method: "POST" }),
      );
    });
  });
});
