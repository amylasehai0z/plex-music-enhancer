import { MantineProvider } from "@mantine/core";
import { Notifications } from "@mantine/notifications";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";

import { DeveloperModeProvider } from "../stores/developerMode";
import { ReviewPage } from "./ReviewPage";

vi.mock("@monaco-editor/react", () => ({
  Editor: () => <div>Editor</div>,
  DiffEditor: () => <div>Diff Editor</div>,
}));

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MantineProvider>
      <Notifications />
      <QueryClientProvider client={queryClient}>
        <DeveloperModeProvider>
          <MemoryRouter future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
            <ReviewPage />
          </MemoryRouter>
        </DeveloperModeProvider>
      </QueryClientProvider>
    </MantineProvider>,
  );
}

describe("ReviewPage", () => {
  it("renders the review form and submits album reviews", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(
            JSON.stringify({
              document: {
                apiVersion: "v1",
                target: "album",
                mode: "create",
                artist: "Jennifer Rush",
                album: "Credo",
                currentSummary: "Alt",
                generatedSummary: "Neu",
                proposedSummary: "Neu",
                unifiedDiff: "--- old",
                qa: {
                  status: "PASS",
                  criticalValidation: "PASS",
                  editorialValidation: "PASS",
                  publishable: true,
                  wordCount: 120,
                  checks: {},
                  warnings: [],
                  failures: [],
                },
                editorial: { recommendations: [], missingTopics: [], styleMetrics: {}, editorialMetrics: {} },
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
                  name: "album_summary",
                  version: "1.0",
                  characters: 100,
                  estimatedTokens: 25,
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
                  provider: "openai",
                  model: "gpt-5.5",
                  generationTimeSeconds: 0.2,
                  tokenUsage: {},
                  sourceCount: 1,
                  raw: {},
                },
                provider: "openai",
                model: "gpt-5.5",
                edited: false,
                context: {},
              },
              applyAllowed: true,
              messages: [],
            }),
            { status: 200, headers: { "content-type": "application/json" } },
          ),
      ),
    );
    renderPage();

    await userEvent.click(screen.getByRole("button", { name: /review erzeugen/i }));

    expect(await screen.findByText("Neu")).toBeInTheDocument();
    expect(screen.getByText("Aktuelle Plex-Beschreibung")).toBeInTheDocument();
    expect(screen.getByText("Neu generierte Beschreibung")).toBeInTheDocument();
    expect(screen.getByText("Analyse")).toBeInTheDocument();
  });
});
