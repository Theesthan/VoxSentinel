import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8011",
        changeOrigin: true,
      },
      "/health": {
        target: "http://localhost:8011",
        changeOrigin: true,
      },
      "/ws": {
        target: `ws://${process.env.VITE_API_HOST ?? "localhost:8011"}`,
        ws: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
  preview: {
    allowedHosts: true,
  },
});
