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
      input: resolve(import.meta.dirname, "src/LineageAtlasApp.jsx"),
      output: {
        entryFileNames: "lineage-atlas.bundle.js",
        assetFileNames: "lineage-atlas.bundle.[ext]",
        chunkFileNames: "lineage-atlas.[hash].js",
        inlineDynamicImports: true,
      },
    },
  },
});
