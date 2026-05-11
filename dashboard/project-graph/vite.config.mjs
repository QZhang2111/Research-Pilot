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
      input: resolve(import.meta.dirname, "src/ProjectGraphApp.jsx"),
      output: {
        entryFileNames: "project-graph.bundle.js",
        assetFileNames: "project-graph.bundle.[ext]",
        chunkFileNames: "project-graph.[hash].js",
        inlineDynamicImports: true,
      },
    },
  },
});
