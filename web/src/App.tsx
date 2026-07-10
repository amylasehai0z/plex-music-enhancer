import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { lazy, Suspense, type ReactNode } from "react";

import { AppLayout } from "./layouts/AppLayout";
import { DashboardPage } from "./pages/DashboardPage";

const AlbumsPage = lazy(() => import("./pages/AlbumsPage").then((module) => ({ default: module.AlbumsPage })));
const ArtistsPage = lazy(() => import("./pages/ArtistsPage").then((module) => ({ default: module.ArtistsPage })));
const DeveloperPage = lazy(() =>
  import("./pages/DeveloperPage").then((module) => ({ default: module.DeveloperPage })),
);
const LiveLogPage = lazy(() =>
  import("./pages/LiveLogPage").then((module) => ({ default: module.LiveLogPage })),
);
const PromptDebugPage = lazy(() =>
  import("./pages/PromptDebugPage").then((module) => ({ default: module.PromptDebugPage })),
);
const RestExplorerPage = lazy(() =>
  import("./pages/RestExplorerPage").then((module) => ({ default: module.RestExplorerPage })),
);
const ReviewPage = lazy(() => import("./pages/ReviewPage").then((module) => ({ default: module.ReviewPage })));
const SettingsPage = lazy(() =>
  import("./pages/SettingsPage").then((module) => ({ default: module.SettingsPage })),
);

function lazyPage(element: ReactNode) {
  return <Suspense fallback={<div className="app-loading">Ansicht wird geladen...</div>}>{element}</Suspense>;
}

const router = createBrowserRouter(
  [
    {
      path: "/",
      element: <AppLayout />,
      children: [
        { index: true, element: <DashboardPage /> },
        { path: "artists", element: lazyPage(<ArtistsPage />) },
        { path: "albums", element: lazyPage(<AlbumsPage />) },
        { path: "reviews", element: lazyPage(<ReviewPage />) },
        { path: "prompt-debug", element: lazyPage(<PromptDebugPage />) },
        { path: "live-log", element: lazyPage(<LiveLogPage />) },
        { path: "developer", element: lazyPage(<DeveloperPage />) },
        { path: "rest-explorer", element: lazyPage(<RestExplorerPage />) },
        { path: "settings", element: lazyPage(<SettingsPage />) },
      ],
    },
  ],
  { future: { v7_relativeSplatPath: true } },
);

export function App() {
  return <RouterProvider router={router} future={{ v7_startTransition: true }} />;
}
