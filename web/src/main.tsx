import "@mantine/core/styles.css";
import "@mantine/notifications/styles.css";
import "./styles/app.css";

import { MantineProvider, createTheme } from "@mantine/core";
import { Notifications } from "@mantine/notifications";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import ReactDOM from "react-dom/client";

import { App } from "./App";
import { DeveloperModeProvider } from "./stores/developerMode";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

const theme = createTheme({
  primaryColor: "teal",
  fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
  headings: {
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
  },
  radius: {
    md: "6px",
    lg: "8px",
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <MantineProvider defaultColorScheme="dark" theme={theme}>
      <Notifications position="top-right" />
      <QueryClientProvider client={queryClient}>
        <DeveloperModeProvider>
          <App />
        </DeveloperModeProvider>
      </QueryClientProvider>
    </MantineProvider>
  </React.StrictMode>,
);
