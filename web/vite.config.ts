import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "../src/plex_music_enhancer/web/static",
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks: {
          mantine: ["@mantine/core", "@mantine/hooks", "@mantine/notifications"],
          monaco: ["@monaco-editor/react"],
          query: ["@tanstack/react-query"],
          router: ["react-router-dom"],
        },
      },
    },
  },
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8080",
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    hookTimeout: 15000,
    setupFiles: "./vitest.setup.ts",
    testTimeout: 15000,
  },
});
