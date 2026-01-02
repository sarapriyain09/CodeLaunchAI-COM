import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  // Important: preview is served from /preview/{projectId}/, not from domain root.
  // Using a relative base ensures built asset URLs resolve correctly under that subpath.
      base: "./",
  plugins: [react()],
  server: { port: 5173 },
});
