import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["favicon.svg"],
      manifest: {
        name: "Lumen",
        short_name: "Lumen",
        description: "AI-powered math + DSA visualization tool",
        theme_color: "#1A1A1A",
        background_color: "#1A1A1A",
        display: "standalone",
        start_url: "/",
        scope: "/",
        icons: [
          {
            src: "favicon.svg",
            sizes: "any",
            type: "image/svg+xml",
            purpose: "any maskable",
          },
        ],
      },
      workbox: {
        // Don't precache massive Monaco workers (7+ MB each) and lazy-route
        // chunks — they'd blow the offline cache. Cap individual asset size
        // to 1 MB just in case anything else slips through.
        maximumFileSizeToCacheInBytes: 1024 * 1024,
        globPatterns: ["**/*.{js,css,html,svg,png,ico,webmanifest}"],
        globIgnores: [
          "**/monaco-*",
          "**/katex-*",
          "**/PasteProblemPage-*",
          "**/LibraryPage-*",
          "**/*.worker-*",     // Monaco's TS/JSON/HTML/CSS workers
          "**/KaTeX_*",        // KaTeX font assets
        ],
        // Runtime cache for the API so re-opens work offline.
        runtimeCaching: [
          {
            urlPattern: /\/api\/topics$/,
            handler: "StaleWhileRevalidate",
            options: { cacheName: "api-topics" },
          },
        ],
      },
    }),
  ],
  server: {
    port: 5173,
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          monaco: ["@monaco-editor/react", "monaco-editor"],
          katex: ["katex", "react-katex"],
        },
      },
    },
  },
});
