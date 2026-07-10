import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { App } from "./App";
import { DeveloperModeProvider } from "./stores/developerMode";

vi.mock("@monaco-editor/react", () => ({
  Editor: () => <div>Editor</div>,
  DiffEditor: () => <div>Diff Editor</div>,
}));

describe("App navigation", () => {
  it("shows the desktop navigation", async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <MantineProvider>
        <QueryClientProvider client={queryClient}>
          <DeveloperModeProvider>
            <App />
          </DeveloperModeProvider>
        </QueryClientProvider>
      </MantineProvider>,
    );

    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    expect(screen.getByText("Künstler")).toBeInTheDocument();
    expect(screen.getByText("Alben")).toBeInTheDocument();
    expect(screen.getByText("Prompt Debug")).toBeInTheDocument();
    expect(screen.getByText("Developer")).toBeInTheDocument();
  });
});
