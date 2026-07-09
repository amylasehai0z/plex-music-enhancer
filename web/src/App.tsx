import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { lazy, Suspense, type ReactNode } from "react";

import { AppLayout } from "./layouts/AppLayout";

const AlbumsPage = lazy(() => import("./pages/AlbumsPage").then((module) => ({ default: module.AlbumsPage })));
const ArtistsPage = lazy(() => import("./pages/ArtistsPage").then((module) => ({ default: module.ArtistsPage })));
const DashboardPage = lazy(() =>
  import("./pages/DashboardPage").then((module) => ({ default: module.DashboardPage })),
);
const PromptDebugPage = lazy(() =>
  import("./pages/PromptDebugPage").then((module) => ({ default: module.PromptDebugPage })),
);
const ReviewPage = lazy(() => import("./pages/ReviewPage").then((module) => ({ default: module.ReviewPage })));
const SettingsPage = lazy(() =>
  import("./pages/SettingsPage").then((module) => ({ default: module.SettingsPage })),
);

function lazyPage(element: ReactNode) {
  return <Suspense fallback={<div className="surface">Lade Ansicht...</div>}>{element}</Suspense>;
}

const router = createBrowserRouter(
  [
    {
      path: "/",
      element: <AppLayout />,
      children: [
        { index: true, element: lazyPage(<DashboardPage />) },
        { path: "artists", element: lazyPage(<ArtistsPage />) },
        { path: "albums", element: lazyPage(<AlbumsPage />) },
        { path: "reviews", element: lazyPage(<ReviewPage />) },
        { path: "prompt-debug", element: lazyPage(<PromptDebugPage />) },
        { path: "settings", element: lazyPage(<SettingsPage />) },
      ],
    },
  ],
  { future: { v7_relativeSplatPath: true } },
);

export function App() {
  return <RouterProvider router={router} future={{ v7_startTransition: true }} />;
}
