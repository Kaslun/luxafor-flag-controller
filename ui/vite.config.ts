import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The engine serves the built app from ui/dist and exposes the API on
// 127.0.0.1:54741. In dev, proxy /api to the running engine so `npm run
// dev` works alongside `python -m engine`.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:54741",
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
