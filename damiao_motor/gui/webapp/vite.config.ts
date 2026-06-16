import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Built assets use relative paths so Flask can serve them from any mount point.
// In dev, proxy the REST API and the WebSocket stream to the Python monitor server.
const API_TARGET = process.env.MONITOR_API || "http://127.0.0.1:5001";

export default defineConfig({
  plugins: [react()],
  base: "./",
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      "/api/monitor/stream": { target: API_TARGET.replace("http", "ws"), ws: true },
      "/api": { target: API_TARGET, changeOrigin: true },
    },
  },
});
