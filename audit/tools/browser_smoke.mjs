import { pathToFileURL } from "url";
const CLIENT = "C:/Users/samsung/Desktop/H2/new/client";
const { chromium } = await import(pathToFileURL(CLIENT + "/node_modules/playwright/index.mjs").href).catch(async () =>
  await import(pathToFileURL(CLIENT + "/node_modules/@playwright/test/index.mjs").href));
const browser = await chromium.launch({ executablePath: process.env.USERPROFILE + "/AppData/Local/ms-playwright/chromium-1208/chrome-win64/chrome.exe" });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = []; page.on("console", m => m.type() === "error" && errors.push(m.text()));
await page.goto("http://127.0.0.1:5190/login"); const skip = page.locator(".skip-intro-btn"); if (await skip.count()) await skip.click().catch(()=>{});
await page.fill('input[placeholder="Email Address"]', "audit_admin@audit.local");
await page.fill('input[type="password"]', "AuditPass!2026");
await page.keyboard.press("Enter");
await page.waitForTimeout(4000);
console.log("URL after login:", page.url());
await page.screenshot({ path: "C:/Users/samsung/Desktop/H2/audit/work/smoke_dashboard.png" });
console.log("console errors:", errors.slice(0, 5));
await browser.close();
