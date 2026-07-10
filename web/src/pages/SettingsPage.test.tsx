import { MantineProvider } from "@mantine/core";
import { Notifications } from "@mantine/notifications";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SettingsPage } from "./SettingsPage";

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MantineProvider>
      <Notifications />
      <QueryClientProvider client={queryClient}>
        <SettingsPage />
      </QueryClientProvider>
    </MantineProvider>,
  );
}

function stubSettingsApi() {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/config/test-plex")) {
      return jsonResponse({ ok: true, message: "Connected successfully.", serverName: "Plex" });
    }
    return jsonResponse({
      configuration: {
        plexConfigured: true,
        plexUrl: "http://plex:32400/",
        plexTokenConfigured: true,
        plexTokenMasked: "************oken",
        aiProvider: "openai",
        aiModel: "gpt-5.5",
        openaiApiKeyConfigured: true,
        openaiApiKeyMasked: "************1234",
        discogsConfigured: false,
        lastfmConfigured: false,
        maxPromptCharacters: 20000,
        savedMethod: init?.method,
      },
    });
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

describe("SettingsPage", () => {
  it("renders provider and Plex configuration forms without exposing secrets", async () => {
    stubSettingsApi();

    renderPage();

    expect((await screen.findAllByLabelText("AI Provider"))[0]).toBeInTheDocument();
    expect(screen.getByLabelText("AI Modell")).toBeInTheDocument();
    expect(screen.getByLabelText("OpenAI API Key")).toBeInTheDocument();
    expect((await screen.findAllByText((content) => content.endsWith("1234")))[0]).toBeInTheDocument();
    expect(screen.queryByText("openai-secret")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "Plex" }));

    expect(await screen.findByLabelText("Plex URL")).toHaveValue("http://plex:32400/");
    expect(screen.getByLabelText("Plex Token")).toBeInTheDocument();
    expect(screen.queryByText("plex-token")).not.toBeInTheDocument();
  });

  it("saves provider configuration through the REST API", async () => {
    const fetchMock = stubSettingsApi();
    const user = userEvent.setup();

    renderPage();

    expect(await screen.findByLabelText("AI Modell")).toHaveValue("gpt-5.5");
    await user.type(screen.getAllByLabelText("OpenAI API Key")[0], "new-openai-secret");
    await user.click(screen.getByRole("button", { name: "Provider speichern" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/config",
        expect.objectContaining({ method: "PUT" }),
      );
    });
    const putCall = fetchMock.mock.calls.find(([url, init]) => {
      const request = init as RequestInit | undefined;
      return String(url).endsWith("/config") && request?.method === "PUT";
    });
    expect(JSON.parse(String((putCall?.[1] as RequestInit).body))).toMatchObject({
      aiProvider: "openai",
      aiModel: "gpt-5.5",
      openaiApiKey: "new-openai-secret",
    });
  });

  it("tests Plex connectivity without persisting settings", async () => {
    const fetchMock = stubSettingsApi();

    renderPage();
    fireEvent.click(await screen.findByRole("tab", { name: "Plex" }));
    fireEvent.click(await screen.findByRole("button", { name: "Verbindung testen" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/config/test-plex",
        expect.objectContaining({ method: "POST" }),
      );
    });
    expect(await screen.findByText("Connected successfully. (Plex)")).toBeInTheDocument();
  });
});
