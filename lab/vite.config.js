import { svelte } from "@sveltejs/vite-plugin-svelte";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [svelte()],
  build: {
    outDir: "../src/agent_consistency/lab_static",
    assetsDir: "assets"
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8765"
    }
  }
});
