import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig(({ mode }) => {
  // The local proxy target can be overridden without changing the shared default.
  const env = loadEnv(mode, process.cwd(), "");
  return {
    plugins: [react(), tailwindcss()],
    server: {
      host: "localhost",
      port: 5173,
      strictPort: true,
      proxy: {
        "/api": {
          target: env.DEV_BACKEND_URL || "http://127.0.0.1:8000",
          changeOrigin: true,
        },
      },
    },
    preview: { host: "localhost", port: 4173, strictPort: true },
  };
});
