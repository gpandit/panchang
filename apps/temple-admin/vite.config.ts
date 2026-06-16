import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": "/src" },
  },
  server: {
    port: 3002,
    proxy: {
      "/temple": "http://localhost:8000",
      "/v1": "http://localhost:8000",
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["src/test-setup.ts"],
    globals: true,
  },
});
