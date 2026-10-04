import { defineConfig } from "@playwright/test";
import base from "../../playwright.config.js";

// Config for the computed-style probes in this folder. Usage (from new/client, dev server on :5173):
//   PROBE_DIR=out/a npx playwright test -c scripts/probe/playwright.probe.config.js
//   E2E_BASE_URL=http://127.0.0.1:5177 PROBE_DIR=out/b npx playwright test -c scripts/probe/playwright.probe.config.js
// Then diff the two folders; rows are `index|tag|class|x|y|width|height|computed styles...`.
export default defineConfig({
  ...base,
  testDir: ".",
  testMatch: /probe-.*\.spec\.js/,
  retries: 0,
});
