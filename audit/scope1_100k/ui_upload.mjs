// Upload CSV files through the real UI (Scope 1 > Bulk Import (Wizard)) with headless Chromium.
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

// playwright is resolved from the current directory (run from new/client, which has it installed)
const { chromium } = createRequire(path.join(process.cwd(), "package.json"))("playwright");

const BASE = process.env.UI_BASE || "http://127.0.0.1:5173";
const OUT = process.env.OUT_DIR || ".";
const files = process.argv.slice(2);
const results = [];

const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH || "/opt/pw-browsers/chromium" });
const ctx = await browser.newContext({ viewport: { width: 1600, height: 1000 }, acceptDownloads: true });
const page = await ctx.newPage();
const apiLog = [];
const postedMappings = [];
page.on("request", (req) => {
  if (req.url().includes("/api/emissions/upload/start")) {
    const body = req.postDataBuffer();
    if (body) {
      const txt = body.toString("latin1");
      const pick = (name) => {
        const m = txt.match(new RegExp(`name="${name}"\\r\\n\\r\\n([^\\r]*)`));
        return m ? m[1] : null;
      };
      postedMappings.push({ global_factor_type: pick("global_factor_type"), overwrite: pick("overwrite_duplicates"),
        column_mapping: pick("column_mapping") });
    }
  }
});
page.on("response", (r) => {
  if (r.url().includes("/api/emissions/upload")) apiLog.push({ status: r.status(), url: r.url().replace(BASE, "") });
});

async function shot(name) {
  await page.screenshot({ path: path.join(OUT, `${name}.png`), fullPage: false });
}

await page.goto(`${BASE}/login`);
await page.waitForTimeout(1500);
if (await page.locator(".skip-intro-btn").count()) {
  await page.locator(".skip-intro-btn").click();
  await page.waitForTimeout(1500);
}
await page.getByPlaceholder("Email Address").fill(process.env.ADMIN_EMAIL);
await page.getByPlaceholder("Password").fill(process.env.ADMIN_PASSWORD);
await page.locator('button[type="submit"]').first().click();
await page.waitForURL((u) => !u.pathname.startsWith("/login"), { timeout: 30000 });

async function openScope1() {
  await page.goto(`${BASE}/emissions`);
  await page.getByRole("heading", { name: "Scope 1" }).first().click();
  await page.getByRole("button", { name: /Bulk Import \(Wizard\)/ }).waitFor({ timeout: 30000 });
}

for (const [i, file] of files.entries()) {
  const tag = `ui_${i + 1 + Number(process.env.TAG_OFFSET || 0)}_${path.basename(file, ".csv")}`;
  const t0 = Date.now();
  await openScope1();
  await page.getByRole("button", { name: /Bulk Import \(Wizard\)/ }).click();
  await page.locator(".s1w-modal").waitFor();
  // Step 1: calculation - per row (rows carry their own factor_type)
  await page.getByText("Per row — mixed tiers").click();
  await shot(`${tag}_step1_tier`);
  await page.locator(".s1w-btn-primary", { hasText: "Next" }).click();
  // Step 2: file (the former "process scope" step is gone)
  await page.locator('.s1w-modal input[type="file"]').setInputFiles(file);
  // Step 3: check & map - wait for the file check (or a refusal before upload)
  const importBtn = page.locator(".s1w-btn-primary", { hasText: /Start Import|^.*Import .* rows/ });
  const refused = page.locator(".s1w-inline-error");
  await Promise.race([importBtn.waitFor({ timeout: 60000 }), refused.waitFor({ timeout: 60000 })]);
  if (await refused.count()) {
    const msg = await refused.innerText();
    await shot(`${tag}_refused_on_pick`);
    results.push({ file, seconds: (Date.now() - t0) / 1000, resultText: "REFUSED BEFORE UPLOAD: " + msg });
    console.log(tag, "refused before upload:", msg);
    continue;
  }
  const checkT0 = Date.now();
  await page.locator(".s1w-check-title, .s1w-check--error").first().waitFor({ timeout: 600000 });
  const checkSeconds = (Date.now() - checkT0) / 1000;
  await page.waitForTimeout(500);
  await shot(`${tag}_step4_mapping`);
  const mappingText = await page.locator(".s1w-modal").innerText();
  fs.writeFileSync(path.join(OUT, `${tag}_mapping.txt`), mappingText);
  const checkText = await page.locator(".s1w-check").first().innerText();
  fs.writeFileSync(path.join(OUT, `${tag}_check.txt`), checkText);
  console.log(tag, `check ${checkSeconds.toFixed(1)} s |`, checkText.replace(/\s+/g, " ").slice(0, 300));
  await importBtn.first().click();
  // progress screen sample (rows + time left)
  await page.waitForTimeout(8000);
  await shot(`${tag}_step5_progress`);
  // Step 5: progress until completed / error
  const done = page.locator(".up-card-lbl", { hasText: "Rows Imported" }).or(page.getByText(/No rows were saved|Import failed|failed/i));
  await done.first().waitFor({ timeout: 900000 });
  await page.waitForTimeout(1500);
  await shot(`${tag}_step5_result`);
  const resultText = await page.locator(".s1w-modal").innerText();
  fs.writeFileSync(path.join(OUT, `${tag}_result.txt`), resultText);
  // download the skipped-rows CSV offered by the UI, when there is one
  let skippedCsv = null;
  const dl = page.getByRole("button", { name: /Download/i });
  if (await dl.count()) {
    try {
      const [download] = await Promise.all([page.waitForEvent("download", { timeout: 60000 }), dl.first().click()]);
      skippedCsv = path.join(OUT, `${tag}_skipped.csv`);
      await download.saveAs(skippedCsv);
    } catch (e) {
      skippedCsv = `download failed: ${e.message}`;
    }
  }
  results.push({ file, seconds: (Date.now() - t0) / 1000, resultText, skippedCsv });
  console.log(tag, ((Date.now() - t0) / 1000).toFixed(1), "s |", resultText.replace(/\s+/g, " ").slice(0, 400));
  // close the wizard
  const close = page.locator(".s1w-close");
  if (await close.count()) await close.click();
}

fs.writeFileSync(path.join(OUT, "ui_upload_results.json"), JSON.stringify({ results, apiLog, postedMappings }, null, 1));
await browser.close();
