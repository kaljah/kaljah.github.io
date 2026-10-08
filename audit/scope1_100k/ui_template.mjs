// Template + saved-mapping flow through the real wizard (headless Chromium):
//  1. template section: tier 3, pick processes, download the Excel and CSV templates
//  2. the CSV template uploaded as downloaded: example rows reported, nothing imported
//  3. the Excel template with its examples copied to Data Entry (prepared by ui_template_prep.py): mapping shown, 0 skipped
//  4. an export with its own column names: map, save the mapping; the next upload opens with it applied
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { createRequire } from "node:module";

const { chromium } = createRequire(path.join(process.cwd(), "package.json"))("playwright");
const BASE = process.env.UI_BASE || "http://127.0.0.1:5173";
const OUT = process.env.OUT_DIR || ".";
const HERE = path.dirname(new URL(import.meta.url).pathname);
const log = [];
const say = (...a) => { console.log(...a); log.push(a.join(" ")); };

const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH || "/opt/pw-browsers/chromium" });
const ctx = await browser.newContext({ viewport: { width: 1500, height: 1000 }, acceptDownloads: true });
const page = await ctx.newPage();
const shot = (n) => page.screenshot({ path: path.join(OUT, `tpl_${n}.png`) });

await page.goto(`${BASE}/login`);
await page.waitForTimeout(1500);
if (await page.locator(".skip-intro-btn").count()) { await page.locator(".skip-intro-btn").click(); await page.waitForTimeout(1500); }
await page.getByPlaceholder("Email Address").fill(process.env.ADMIN_EMAIL);
await page.getByPlaceholder("Password").fill(process.env.ADMIN_PASSWORD);
await page.locator('button[type="submit"]').first().click();
await page.waitForURL((u) => !u.pathname.startsWith("/login"), { timeout: 30000 });

async function openWizard(tierText) {
  const close = page.locator(".s1w-close");
  if (await close.count()) await close.click();
  await page.goto(`${BASE}/emissions`);
  await page.getByRole("heading", { name: "Scope 1" }).first().click();
  await page.getByRole("button", { name: /Bulk Import \(Wizard\)/ }).click();
  await page.locator(".s1w-modal").waitFor();
  await page.getByText(tierText).click();
  await page.locator(".s1w-btn-primary", { hasText: "Next" }).click();
}

async function pick(file) {
  await page.locator('.s1w-modal input[type="file"]').setInputFiles(file);
  await page.locator(".s1w-check-title, .s1w-check--error").first().waitFor({ timeout: 120000 });
  await page.waitForTimeout(800);
}

// 1. template section
await openWizard("Tier 3 — Engineering");
await page.locator(".s1w-chip", { hasText: /^Flaring$/ }).click();
await page.locator(".s1w-chip", { hasText: /^Tank Flashing$/ }).click();
await shot("1_template_section");
const [xl] = await Promise.all([page.waitForEvent("download"), page.locator(".s1w-template-btn", { hasText: "Excel template" }).click()]);
const xlPath = path.join(OUT, xl.suggestedFilename());
await xl.saveAs(xlPath);
const [cv] = await Promise.all([page.waitForEvent("download"), page.locator(".s1w-template-btn", { hasText: "CSV template" }).click()]);
const csvPath = path.join(OUT, cv.suggestedFilename());
await cv.saveAs(csvPath);
say("downloaded", path.basename(xlPath), path.basename(csvPath), "| CSV header:", fs.readFileSync(csvPath, "utf8").split("\n")[0]);

// 2. CSV template as downloaded (examples only)
await openWizard("Per row — mixed tiers");
await pick(csvPath);
await shot("2_csv_template_untouched_check");
say("CSV as downloaded | check:", (await page.locator(".s1w-check").first().innerText()).replace(/\s+/g, " ").slice(0, 400));

// 3. Excel with the examples copied into Data Entry
const filled = path.join(OUT, "filled_template.xlsx");
execFileSync("python3", [path.join(HERE, "ui_template_prep.py"), xlPath, filled, "Hassi Messaoud Gas Plant", "2024-02"]);
await openWizard("Per row — mixed tiers");
await pick(filled);
await page.locator(".s1w-saved-map").waitFor({ timeout: 30000 });   // the mapping appears once the check read the columns
await shot("3_excel_filled_check");
say("Excel filled | check:", (await page.locator(".s1w-check").first().innerText()).replace(/\s+/g, " ").slice(0, 300),
  "| matched:", await page.locator(".s1w-auto-badge").innerText());
await page.locator(".s1w-btn-primary", { hasText: /Import/ }).first().click();
await page.locator(".up-card-lbl", { hasText: "Rows Imported" }).or(page.getByText(/No rows were saved|failed/i)).first().waitFor({ timeout: 120000 });
await page.waitForTimeout(1000);
await shot("3_excel_filled_result");
say("Excel filled | result:", (await page.locator(".s1w-modal").innerText()).replace(/\s+/g, " ").slice(0, 300));

// 4. an export with its own column names: map once, save, reuse
const exp = path.join(OUT, "erp_export.csv");
fs.writeFileSync(exp, "Periode,Usine,Proc,Combustible,Volume,UoM\n" +
  "2024-03,Hassi Messaoud Gas Plant,combustion,Natural Gas,1200,MMBtu\n" +
  "2024-03,In Amenas CPF,combustion,Diesel (No. 2 Fuel Oil),800,gal\n");
await openWizard("Tier 1 — Standard");
await page.locator('.s1w-modal input[type="file"]').setInputFiles(exp);
await page.locator(".s1w-saved-map").waitFor();
async function mapField(label, column) {
  const row = page.locator(".s1w-map-row", { has: page.locator(".s1w-map-field-label", { hasText: new RegExp(`^${label}`) }) }).first();
  await row.locator("select").selectOption(column);
}
await mapField("Date", "Periode");
await mapField("Facility", "Usine");
await mapField("Process Type", "Proc");
await mapField("Activity / Fuel", "Combustible");
await mapField("Quantity", "Volume");
await mapField("Unit", "UoM");
await page.locator(".s1w-saved-save").click();
await page.locator(".s1w-saved-input").fill("ERP monthly export");
await page.locator(".s1w-btn-small", { hasText: "Save" }).click();
await page.getByText("Using your saved mapping").waitFor();
await shot("4_mapping_saved");
say("saved:", await page.locator(".s1w-saved-map").innerText());

await openWizard("Tier 1 — Standard");
await pick(exp);
await shot("4_mapping_reused");
say("next upload:", await page.locator(".s1w-saved-map").innerText(), "|", await page.locator(".s1w-auto-badge").innerText(),
  "| check:", (await page.locator(".s1w-check").first().innerText()).replace(/\s+/g, " ").slice(0, 200));

fs.writeFileSync(path.join(OUT, "ui_template_log.txt"), log.join("\n") + "\n");
await browser.close();
