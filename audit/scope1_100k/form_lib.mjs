// Shared helpers for driving the real Scope 1 manual-entry form with headless Chromium.
import path from "node:path";
import { createRequire } from "node:module";

const { chromium } = createRequire(path.join(process.cwd(), "package.json"))("playwright");
export const BASE = process.env.UI_BASE || "http://127.0.0.1:5173";

export async function open() {
  const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH || "/opt/pw-browsers/chromium" });
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 1100 } });
  const page = await ctx.newPage();
  await page.goto(`${BASE}/login`);
  await page.waitForTimeout(1500);
  if (await page.locator(".skip-intro-btn").count()) {
    await page.locator(".skip-intro-btn").click();
    await page.waitForTimeout(1200);
  }
  await page.getByPlaceholder("Email Address").fill(process.env.ADMIN_EMAIL || "audit.admin@ghg.test");
  await page.getByPlaceholder("Password").fill(process.env.ADMIN_PASSWORD || "Audit-Passw0rd!2026");
  await page.locator('button[type="submit"]').first().click();
  await page.waitForURL((u) => !u.pathname.startsWith("/login"), { timeout: 30000 });
  return { browser, page };
}

export async function openScope1(page) {
  await page.goto(`${BASE}/emissions`);
  await page.getByRole("heading", { name: "Scope 1" }).first().click();
  await page.waitForTimeout(1500);
}

// visible labels / inputs / selects / buttons in the form area, for exploration
export async function dump(page, root = "body") {
  return page.evaluate((root) => {
    const el = document.querySelector(root) || document.body;
    const vis = (e) => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
    const out = [];
    for (const e of el.querySelectorAll("label, input, select, button, [role=button], .custom-dropdown, .dropdown-trigger")) {
      if (!vis(e)) continue;
      const t = (e.innerText || e.value || e.placeholder || "").trim().replace(/\s+/g, " ").slice(0, 70);
      out.push(`${e.tagName.toLowerCase()}${e.className ? "." + String(e.className).split(" ")[0] : ""}${e.type ? "[" + e.type + "]" : ""} ${e.placeholder ? "ph=" + e.placeholder : ""} | ${t}`);
    }
    return out;
  }, root);
}

const lab = (label) => `xpath=//label[starts-with(normalize-space(), ${JSON.stringify(label)})]`;

// open the custom dropdown that follows a label (or whose button shows `label` when no such label exists)
// and click the option whose first line equals `option` (else the first option containing it)
export async function pick(page, label, option, { nth = 0 } = {}) {
  let btn = page.locator(`${lab(label)}/following::button[contains(@class,'dropdown-selected')][1]`).nth(nth);
  if (!(await btn.count())) btn = page.locator("button.dropdown-selected").filter({ hasText: label }).first();
  await btn.click();
  const portal = page.locator(".dropdown-portal").last();
  await portal.waitFor({ timeout: 5000 });
  const opts = portal.locator(".dropdown-option");
  const texts = await opts.allInnerTexts();
  const first = (t) => t.trim().split("\n")[0].trim();
  let i = texts.findIndex((t) => first(t) === option);
  if (i < 0) i = texts.findIndex((t) => t.includes(option));
  if (i < 0) throw new Error(`no option '${option}' in ${label}: ${texts.map(first).slice(0, 15).join(" / ")}`);
  await opts.nth(i).click();
  await page.waitForTimeout(250);
}

export async function fill(page, label, value, { nth = 0 } = {}) {
  const inp = page.locator(`${lab(label)}/following::input[1]`).nth(nth);
  await inp.fill(String(value));
}

export async function selectNative(page, label, value) {
  await page.locator(`${lab(label)}/following::select[1]`).first().selectOption(value);
}

export async function tier(page, name) {
  await page.locator("button.tier-selector-btn").filter({ hasText: name }).first().click();
  await page.waitForTimeout(300);
}

// submit and return the POST /api/emissions payload and response
export async function submit(page) {
  const [req] = await Promise.all([
    page.waitForRequest((r) => /\/api\/emissions\/?(\?.*)?$/.test(r.url()) && r.method() === "POST", { timeout: 15000 }),
    page.locator("button.btn-add-activity").click(),
  ]);
  const resp = await req.response();
  let body = null;
  try { body = await resp.json(); } catch { body = await resp.text(); }
  return { payload: JSON.parse(req.postData() || "{}"), status: resp.status(), body };
}
