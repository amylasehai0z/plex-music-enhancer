import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import type { ComponentProps } from "react";
import type { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

type MemoryRouter = ReturnType<typeof createMemoryRouter>;
type MemoryRouterOptions = Parameters<typeof createMemoryRouter>[1];
type RouteObjects = Parameters<typeof createMemoryRouter>[0];
type RouterProviderProps = ComponentProps<typeof RouterProvider>;
type TestRouter = {
  __testOptions?: MemoryRouterOptions;
  __testRoutes: RouteObjects;
};

vi.mock("@monaco-editor/react", () => ({
  Editor: () => <div>Editor</div>,
  DiffEditor: () => <div>Diff Editor</div>,
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  const routerCache = new WeakMap<object, MemoryRouter>();
  const isTestRouter = (router: unknown): router is TestRouter =>
    Boolean(router && typeof router === "object" && "__testRoutes" in router);

  return {
    ...actual,
    createBrowserRouter: (
      routes: Parameters<typeof actual.createBrowserRouter>[0],
      options?: Parameters<typeof actual.createBrowserRouter>[1],
    ) => ({ __testOptions: options as MemoryRouterOptions, __testRoutes: routes }),
    RouterProvider: (props: RouterProviderProps & { router: RouterProviderProps["router"] | TestRouter }) => {
      let router = props.router;
      if (isTestRouter(router)) {
        const cacheKey = router as object;
        const cachedRouter = routerCache.get(cacheKey);
        if (cachedRouter) {
          router = cachedRouter;
        } else {
          router = actual.createMemoryRouter(router.__testRoutes, { ...router.__testOptions, initialEntries: ["/"] });
          routerCache.set(cacheKey, router);
        }
      }
      return <actual.RouterProvider {...props} router={router as RouterProviderProps["router"]} />;
    },
  };
});

function stubDashboardApi() {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    const payload = url.endsWith("/statistics")
      ? { artists: 12, albums: 34, tracks: 99, libraries: 1, cacheEntries: 5 }
      : url.endsWith("/providers")
        ? [{ name: "openai", configured: true, model: "gpt-5.5", details: { type: "ai" } }]
        : url.endsWith("/config")
          ? { configuration: { plexConfigured: true } }
          : url.endsWith("/plex/sync/status")
            ? { running: false, progress: 100, artists: 12, albums: 34, tracks: 99, lastSync: null }
            : url.endsWith("/system/version")
              ? { version: "1.0.0", apiVersion: "v1" }
              : url.endsWith("/debug/review")
                ? { exists: false, sections: {} }
                : {};

    return new Response(JSON.stringify(payload), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  });
  vi.stubGlobal(
    "fetch",
    fetchMock,
  );
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("App navigation", () => {
  it("shows the desktop navigation", async () => {
    const fetchMock = stubDashboardApi();
    const [{ App }, { DeveloperModeProvider }] = await Promise.all([
      import("./App"),
      import("./stores/developerMode"),
    ]);
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
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/statistics", undefined);

    const sidebar = container.querySelector(".sidebar");
    expect(sidebar).not.toBeNull();
    expect(within(sidebar as HTMLElement).getByText("Dashboard")).toBeInTheDocument();
    expect(within(sidebar as HTMLElement).getByText("Künstler")).toBeInTheDocument();
    expect(within(sidebar as HTMLElement).getByText("Alben")).toBeInTheDocument();
    expect(within(sidebar as HTMLElement).getByText("Prompt Debug")).toBeInTheDocument();
    expect(within(sidebar as HTMLElement).getByText("Developer")).toBeInTheDocument();
  });
});
