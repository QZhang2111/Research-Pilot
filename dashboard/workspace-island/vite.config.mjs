import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";

export default defineConfig({
  plugins: [react()],
  root: resolve(import.meta.dirname),
  build: {
    outDir: resolve(import.meta.dirname, ".."),
    emptyOutDir: false,
    sourcemap: false,
    rollupOptions: {
      input: resolve(import.meta.dirname, "src/WorkspaceIslandApp.jsx"),
      output: {
        entryFileNames: "workspace-island.bundle.js",
        assetFileNames: "workspace-island.bundle.[ext]",
        chunkFileNames: "workspace-island.[hash].js",
        inlineDynamicImports: true,
      },
    },
  },
});
