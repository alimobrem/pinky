import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@pinky/contracts": resolve(__dirname, "../contracts/src"),
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/setup-test.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
