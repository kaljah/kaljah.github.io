import { pathToFileURL } from "url";
const CLIENT = "C:/Users/samsung/Desktop/H2/new/client";
const { chromium } = await import(pathToFileURL(CLIENT + "/node_modules/playwright/index.mjs").href);
export const UI = "http://127.0.0.1:5191";
export const OUT = "C:/Users/samsung/Desktop/H2/audit/work/K/";
const EMAIL = { admin: "audit_admin@audit.local", superuser: "audit_superuser@audit.local", user: "audit_user@audit.local", it_admin: "audit_itadmin@audit.local" };
export async function start(role = "admin", opts = {}) {
  const browser = await chromium.launch({ executablePath: process.env.USERPROFILE + "/AppData/Local/ms-playwright/chromium-1208/chrome-win64/chrome.exe" });
  const ctx = await browser.newContext({ viewport: opts.viewport || { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  const log = { errors: [], reqs: [], resps: [] };
  page.on("console", m => m.type() === "error" && log.errors.push(m.text().slice(0, 300)));
  page.on("pageerror", e => log.errors.push("PAGEERROR " + e.message.slice(0, 300)));
  page.on("request", r => { if (r.url().includes("/api/")) log.reqs.push({ m: r.method(), u: r.url().replace(UI, ""), body: r.postData() }); });
  page.on("response", async r => { if (r.url().includes("/api/")) { let b = null; try { b = await r.text(); } catch {} log.resps.push({ s: r.status(), u: r.url().replace(UI, ""), body: b }); } });
  await page.goto(UI + "/login");
  await page.waitForTimeout(1500);
  const skip = page.locator(".skip-intro-btn"); if (await skip.count()) await skip.click().catch(() => {});
  await page.fill('input[placeholder="Email Address"]', EMAIL[role]);
  await page.fill('input[type="password"]', "AuditPass!2026");
  await page.keyboard.press("Enter");
  await page.waitForTimeout(3500);
  return { browser, ctx, page, log };
}
