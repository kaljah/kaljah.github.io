// Read the Scope 1 table through the real UI: (1) Export CSV button (every record),
// (2) the first N pages via "Next", (3) targeted searches by equipment ID with screenshots.
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

// playwright is resolved from the current directory (run from new/client, which has it installed)
const { chromium } = createRequire(path.join(process.cwd(), "package.json"))("playwright");

const BASE = process.env.UI_BASE || "http://127.0.0.1:5173";
const OUT = process.env.OUT_DIR || ".";
const PAGES = Number(process.env.PAGES || 150);
const targets = process.argv[2] ? JSON.parse(fs.readFileSync(process.argv[2], "utf8")) : [];

const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH || "/opt/pw-browsers/chromium" });
const ctx = await browser.newContext({ viewport: { width: 1900, height: 1100 }, acceptDownloads: true });
const page = await ctx.newPage();
await page.goto(`${BASE}/login`);
await page.waitForTimeout(1500);
if (await page.locator(".skip-intro-btn").count()) {
  await page.locator(".skip-intro-btn").click();
  await page.waitForTimeout(1500);
}
await page.getByPlaceholder("Email Address").fill(process.env.ADMIN_EMAIL);
await page.getByPlaceholder("Password").fill(process.env.ADMIN_PASSWORD);
await page.locator('button[type="submit"]').first().click();
await page.waitForURL((u) => !u.pathname.startsWith("/login"));
await page.goto(`${BASE}/emissions`);
await page.getByRole("heading", { name: "Scope 1" }).first().click();
const table = page.locator("table.excel-table").first();
await table.waitFor();
await page.waitForTimeout(2500);

const readRows = () =>
  table.locator("tbody tr").evaluateAll((trs) => trs.map((tr) => [...tr.querySelectorAll("td")].map((td) => td.innerText.trim())));
const heads = await table.locator("thead th").allInnerTexts();

// (1) Export CSV (all matching records)
const t0 = Date.now();
if (process.env.SKIP_EXPORT !== "1") {
const [download] = await Promise.all([
  page.waitForEvent("download", { timeout: 600000 }),
  page.getByRole("button", { name: /Export CSV/ }).click(),
]);
await download.saveAs(path.join(OUT, "ui_export_all.csv"));
console.log("export saved in", ((Date.now() - t0) / 1000).toFixed(1), "s");
}
await page.waitForTimeout(4000);

// (2) sequential pages
const pages = [];
for (let p = 1; p <= PAGES; p++) {
  const pager = await page.locator("text=/Page \\d+ of \\d+/").first().innerText();
  pages.push({ pager, rows: await readRows() });
  if (p === 1) await page.screenshot({ path: path.join(OUT, "ui_table_page1.png") });
  const next = page.locator("button.action-btn.secondary", { hasText: /^\s*Next\s*$/ });
  if (await next.isDisabled()) break;
  const before = JSON.stringify(pages[pages.length - 1].rows);
  const resp = page.waitForResponse((r) => r.url().includes("/api/emissions?") && r.url().includes(`offset=${p * 10}`));
  await next.click({ force: true });
  await resp;
  try {
    await page.waitForFunction(
      (b) => JSON.stringify([...document.querySelectorAll("table.excel-table tbody tr")].map((tr) =>
        [...tr.querySelectorAll("td")].map((td) => td.innerText.trim()))) !== b,
      before,
      { timeout: 8000 },
    );
  } catch {
    pages[pages.length - 1].next_identical = true;   // the next page rendered exactly the same rows
  }
}
console.log("pages read", pages.length);

// (3) targeted searches
const search = page.locator('input[placeholder="Search..."]').first();
const found = [];
for (const [i, [eq, why]] of targets.entries()) {
  const resp = page.waitForResponse((r) => r.url().includes("/api/emissions?") && r.url().includes(`search=${encodeURIComponent(eq)}`),
    { timeout: 30000 });
  await search.fill(eq);
  try {
    await resp;
    await page.waitForFunction(
      (e) => [...document.querySelectorAll("table.excel-table tbody tr")].some((tr) => tr.innerText.includes(e)),
      eq, { timeout: 8000 });
  } catch {}
  const rows = (await readRows()).filter((r) => r.some((c) => c === eq));
  found.push({ eq, why, rows });
  if (i < 40) {
    const safe = eq.replace(/[^A-Za-z0-9_-]/g, "_");
    await table.screenshot({ path: path.join(OUT, `ui_search_${String(i).padStart(3, "0")}_${safe}.png`) });
  }
}
console.log("targets searched", found.length, "found", found.filter((f) => f.rows.length).length);
fs.writeFileSync(path.join(OUT, "ui_table_read.json"), JSON.stringify({ heads, pages, found }, null, 1));
await browser.close();
