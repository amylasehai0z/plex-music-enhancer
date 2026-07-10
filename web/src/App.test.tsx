import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import { DeveloperModeProvider } from "./stores/developerMode";

vi.mock("@monaco-editor/react", () => ({
  Editor: () => <div>Editor</div>,
  DiffEditor: () => <div>Diff Editor</div>,
}));

function stubDashboardApi() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      const payload = url.endsWith("/statistics")
        ? { artists: 12, albums: 34, libraries: 1, cacheEntries: 5 }
        : url.endsWith("/providers")
          ? [{ name: "openai", configured: true, model: "gpt-5.5", details: { type: "ai" } }]
          : url.endsWith("/config")
            ? { configuration: { plexConfigured: true } }
            : url.endsWith("/system/version")
              ? { version: "1.0.0", apiVersion: "v1" }
              : url.endsWith("/debug/review")
                ? { exists: false, sections: {} }
                : {};

      return new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("App navigation", () => {
  it("shows the desktop navigation", async () => {
    stubDashboardApi();
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { container } = render(
      <MantineProvider>
        <QueryClientProvider client={queryClient}>
          <DeveloperModeProvider>
            <App />
          </DeveloperModeProvider>
        </QueryClientProvider>
      </MantineProvider>,
    );

    await waitFor(
      () => {
        expect(screen.getByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
      },
      { timeout: 5000 },
    );

    const sidebar = container.querySelector(".sidebar");
    expect(sidebar).not.toBeNull();
    expect(within(sidebar as HTMLElement).getByText("Dashboard")).toBeInTheDocument();
    expect(within(sidebar as HTMLElement).getByText("Künstler")).toBeInTheDocument();
    expect(within(sidebar as HTMLElement).getByText("Alben")).toBeInTheDocument();
    expect(within(sidebar as HTMLElement).getByText("Prompt Debug")).toBeInTheDocument();
    expect(within(sidebar as HTMLElement).getByText("Developer")).toBeInTheDocument();
  });
});
