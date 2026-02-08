import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { TanStackRouterVite } from "@tanstack/router-plugin/vite";
import path from "node:path";

/**
 * Vite config for running/building the APX UI directly.
 *
 * APX also orchestrates Vite internally, but having an explicit config makes
 * the build deterministic from a clean checkout and enables `vite build`
 * outside of APX if needed.
 */
export default defineConfig({
  root: "src/payment_analysis/ui",
  plugins: [
    TanStackRouterVite({
      routesDirectory: "./routes",
      generatedRouteTree: "./types/routeTree.gen.ts",
    }),
    react(),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src/payment_analysis/ui"),
    },
  },
  define: {
    __APP_NAME__: JSON.stringify("payment-analysis"),
  },
  build: {
    // Output to the Python package static assets folder
    outDir: path.resolve(__dirname, "src/payment_analysis/__dist__"),
    emptyOutDir: true,
  },
});

