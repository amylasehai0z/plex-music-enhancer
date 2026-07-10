import { MantineProvider } from "@mantine/core";
import { notifications, Notifications } from "@mantine/notifications";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";

import { DeveloperModeProvider } from "../stores/developerMode";
import { ReviewPage } from "./ReviewPage";

vi.mock("@monaco-editor/react", () => ({
  Editor: () => <div>Editor</div>,
  DiffEditor: () => <div>Diff Editor</div>,
}));

afterEach(() => {
  notifications.clean();
  vi.unstubAllGlobals();
});

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
    const fetchMock = vi.fn(
      async () =>
        new Response(
          JSON.stringify(reviewResponse()),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
    );
    vi.stubGlobal(
      "fetch",
      fetchMock,
    );
    renderPage();

    const submitButton = await screen.findByRole("button", { name: /review erzeugen/i });
    const form = submitButton.closest("form");
    expect(form).not.toBeNull();
    fireEvent.submit(form as HTMLFormElement);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/review/album",
        expect.objectContaining({ method: "POST" }),
      );
    });

    expect(await screen.findByRole("heading", { name: "Credo" })).toBeInTheDocument();
    expect(screen.getByText("Aktuelle Plex-Beschreibung")).toBeInTheDocument();
    expect(screen.getByText("Neu generierte Beschreibung")).toBeInTheDocument();
    expect(
      within(screen.getByText("Neu generierte Beschreibung").closest(".description-pane")!).getByText("Neu"),
    ).toBeInTheDocument();
    expect(screen.getByText("Analyse")).toBeInTheDocument();
  });

  it("shows success only after Plex write and verification are confirmed", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/apply")) {
        return new Response(JSON.stringify(applyResponse({ status: "SUCCESS" })), {
          status: 200,
          headers: { "content-type": "application/json" },
        });
      }
      return new Response(JSON.stringify(reviewResponse()), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    renderPage();

    const submitButton = await screen.findByRole("button", { name: /review erzeugen/i });
    fireEvent.submit(submitButton.closest("form") as HTMLFormElement);
    await screen.findByRole("heading", { name: "Credo" });

    fireEvent.click(screen.getByRole("button", { name: "Apply" }));

    expect(await screen.findAllByText("Plex-Verifikation erfolgreich.")).not.toHaveLength(0);
    expect(screen.getByText("Review erfolgreich übernommen.")).toBeInTheDocument();
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/v1/apply", expect.objectContaining({ method: "POST" }));
    });
  });

  it("shows an error when Plex verification is not confirmed", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/apply")) {
        return new Response(
          JSON.stringify(applyResponse({ message: "Plex-Verifikation fehlgeschlagen.", status: "FAILED" })),
          { status: 200, headers: { "content-type": "application/json" } },
        );
      }
      return new Response(JSON.stringify(reviewResponse()), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    renderPage();

    const submitButton = await screen.findByRole("button", { name: /review erzeugen/i });
    fireEvent.submit(submitButton.closest("form") as HTMLFormElement);
    await screen.findByRole("heading", { name: "Credo" });

    fireEvent.click(screen.getByRole("button", { name: "Apply" }));

    expect(await screen.findAllByText("Plex-Verifikation fehlgeschlagen.")).not.toHaveLength(0);
    expect(screen.queryByText("Review erfolgreich übernommen.")).not.toBeInTheDocument();
  });
});

function reviewResponse() {
  return {
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
  };
}

function applyResponse({ message = "Summary written and verified successfully.", status }: { message?: string; status: string }) {
  return {
    ...reviewResponse(),
    status,
    artist: "Jennifer Rush",
    album: "Credo",
    ratingKey: "42",
    backupCreated: true,
    writeSuccessful: status === "SUCCESS",
    verificationPassed: status === "SUCCESS",
    auditStored: true,
    message,
    review: reviewResponse().document,
  };
}
