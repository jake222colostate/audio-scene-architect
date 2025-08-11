import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

// Root Vite config that serves the app from ./frontend
export default defineConfig(({ mode }) => ({
  root: path.resolve(__dirname, "frontend"),
  plugins: [
    react(),
    mode === "development" && componentTagger(),
  ].filter(Boolean),
  server: {
    host: "::",
    port: 8080,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "frontend/src"),
    },
  },
  build: {
    outDir: path.resolve(__dirname, "frontend/dist"),
    emptyOutDir: true,
  },
}));
