import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

// Root Vite config that serves the app from ./frontend
export default defineConfig(async ({ mode }) => {
  const plugins = [react()];

  if (mode === "development") {
    try {
      const { componentTagger } = await import("lovable-tagger");
      plugins.push(componentTagger());
    } catch {
      // lovable-tagger not installed; continue without it
    }
  }

  return {
    root: path.resolve(__dirname, "frontend"),
    plugins,
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
  };
});
