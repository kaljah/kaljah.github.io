import { test } from "@playwright/test";
import fs from "node:fs";

// Scratch probe: dumps geometry and key computed styles for every route and size (compare two builds).
const ROUTES = ["", "carbon-intensity", "methane-intensity", "sbti", "methane-explorer", "emissions", "emissions?scope=scope1", "manage-data", "reference-data", "reports", "uncertainty", "qa-dashboard", "audit-trail", "settings"];
const SIZES = [[1440, 900], [1024, 768], [390, 844]];
test("probe all", async ({ page }) => {
  test.setTimeout(600000);
  fs.mkdirSync(process.env.PROBE_DIR, { recursive: true });
  for (const [w, h] of SIZES) {
    await page.setViewportSize({ width: w, height: h });
    for (const route of ROUTES) {
      await page.goto("/" + route);
      await page.waitForTimeout(2200);
      const r = await page.evaluate(() => {
        const props = ["fontFamily", "fontSize", "fontWeight", "letterSpacing", "lineHeight", "color", "paddingTop", "paddingLeft", "marginTop", "display", "backgroundColor", "borderBottomWidth", "borderTopWidth", "boxShadow", "borderRadius"];
        const out = [];
        document.querySelectorAll("body *").forEach((el, i) => {
          const cs = getComputedStyle(el);
          const rect = el.getBoundingClientRect();
          const cls = (typeof el.className === "string" ? el.className : "").split(/\s+/)[0].slice(0, 40);
          out.push([i, el.tagName, cls, Math.round(rect.x), Math.round(rect.y), Math.round(rect.width), Math.round(rect.height), ...props.map((p) => cs[p])].join("|"));
        });
        return out;
      });
      fs.writeFileSync(`${process.env.PROBE_DIR}/${w}-${route.replace(/[^a-z0-9]/gi, "_") || "home"}.txt`, r.join("\n"));
    }
  }
});
