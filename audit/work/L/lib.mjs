import { pathToFileURL } from "url";
const CLIENT = "C:/Users/samsung/Desktop/H2/new/client";
const { chromium } = await import(pathToFileURL(CLIENT + "/node_modules/playwright/index.mjs").href);
export const UI = "http://127.0.0.1:5190";
export const OUT = "C:/Users/samsung/Desktop/H2/audit/work/L/";
export const ACCTS = {
  admin: "audit_admin@audit.local", superuser: "audit_superuser@audit.local",
  user: "audit_user@audit.local", it_admin: "audit_itadmin@audit.local",
};
export async function launch() {
  return chromium.launch({ executablePath: process.env.USERPROFILE + "/AppData/Local/ms-playwright/chromium-1208/chrome-win64/chrome.exe" });
}
export async function session(browser, role = "admin", opts = {}) {
  const fs = await import("fs");
  const sf = OUT + `state_${role}.json`;
  const ctxOpts = { viewport: { width: 1440, height: 1000 }, acceptDownloads: true };
  if (role && fs.existsSync(sf)) ctxOpts.storageState = sf;
  const ctx = await browser.newContext(ctxOpts);
  const page = await ctx.newPage();
  const log = { errors: [], api: [], failed: [] };
  page.on("console", m => m.type() === "error" && log.errors.push(m.text().slice(0, 300)));
  page.on("pageerror", e => log.errors.push("PAGEERROR " + String(e).slice(0, 300)));
  page.on("response", async r => {
    const u = r.url();
    if (!u.includes("/api/")) return;
    let body = null;
    try { const ct = r.headers()["content-type"] || ""; if (ct.includes("json")) body = await r.json(); } catch {}
    log.api.push({ method: r.request().method(), url: u.replace(UI, ""), status: r.status(), body, req: r.request().postData() });
  });
  page.on("dialog", d => { log.errors.push("DIALOG " + d.message()); d.accept().catch(() => {}); });
  if (role) {
    let ok = false;
    if (ctxOpts.storageState) { const r = await ctx.request.get(UI + "/api/auth/me"); ok = r.status() === 200 && ((await r.json()).email || (await r.json()).user?.email || "").startsWith(ACCTS[role].split("@")[0]); }
    if (!ok) { await login(page, role); await ctx.storageState({ path: sf }); }
    else { await page.goto(UI + "/"); await page.waitForTimeout(1500); }
  }
  return { ctx, page, log };
}
export async function login(page, role) {
  await page.goto(UI + "/login");
  await page.waitForTimeout(800);
  const skip = page.locator(".skip-intro-btn"); if (await skip.count()) await skip.click().catch(() => {});
  await page.fill('input[placeholder="Email Address"]', ACCTS[role] || role);
  await page.fill('input[type="password"]', "AuditPass!2026");
  await page.keyboard.press("Enter");
  for (let i = 0; i < 40 && page.url().includes("/login"); i++) await page.waitForTimeout(250);
  await page.waitForTimeout(1500);
  if (page.url().includes("/login")) console.log("LOGIN FAILED for", role, (await page.locator("body").innerText()).slice(0, 200).replace(/\s+/g, " "));
}
export const shot = (page, name, full = false) => page.screenshot({ path: OUT + name + ".png", fullPage: full });
export function lastApi(log, frag, method) {
  return [...log.api].reverse().find(a => a.url.includes(frag) && (!method || a.method === method));
}
export const sleep = ms => new Promise(r => setTimeout(r, ms));
// pick an option from a CustomDropdown located in the .input-group whose <label> contains labelText
export async function pick(page, labelText, optionText, { exact = false, idx = 0 } = {}) {
  let dd;
  if (labelText) {
    const grp = page.locator(".input-group, .form-group, div").filter({ has: page.locator("label", { hasText: labelText }) }).last();
    dd = grp.locator(".custom-dropdown .dropdown-selected").first();
  } else dd = page.locator(".custom-dropdown .dropdown-selected").nth(idx);
  await dd.scrollIntoViewIfNeeded(); await dd.click(); await sleep(400);
  const opts = page.locator(".dropdown-portal .dropdown-option");
  const texts = await opts.allInnerTexts();
  const i = texts.findIndex(t => exact ? t.split(/\n| ±/)[0].trim() === optionText : t.toLowerCase().includes(optionText.toLowerCase()));
  if (i < 0) { await page.keyboard.press("Escape"); await page.mouse.click(5, 5); throw new Error(`option '${optionText}' not in [${texts.slice(0, 60).join(" ; ")}]`); }
  await opts.nth(i).click(); await sleep(500);
  return texts[i];
}
export async function ddOptions(page, labelText) {
  const grp = page.locator(".input-group, .form-group, div").filter({ has: page.locator("label", { hasText: labelText }) }).last();
  const dd = grp.locator(".custom-dropdown .dropdown-selected").first();
  await dd.click(); await sleep(400);
  const t = await page.locator(".dropdown-portal .dropdown-option").allInnerTexts();
  await dd.click(); await sleep(300);
  return t;
}
export const grpOf = (page, l) => page.locator("div").filter({ has: page.locator("label", { hasText: l }) }).last();
export async function openS1(page) {
  await page.goto(UI + "/emissions"); await sleep(2500);
  await page.getByText("Scope 1", { exact: true }).first().click(); await sleep(2500);
}
// o: {facility, year, month, process, processIdx, tier, factor, qty, unit, fill: {label: value}, submit: 'submit'|'draft'|null}
export async function fillS1(page, o) {
  if (o.facility) await pick(page, null, o.facility, { idx: 0 });
  if (o.year) await grpOf(page, "Year").locator("input").fill(String(o.year));
  if (o.month) await grpOf(page, "Month").locator("select").selectOption(String(o.month));
  if (o.process) {
    const dd = page.locator(".custom-dropdown .dropdown-selected").nth(2);
    await dd.click(); await sleep(300);
    const opts = page.locator(".dropdown-portal .dropdown-option");
    const t = await opts.allInnerTexts(); const hits = t.map((x, i) => x.trim() === o.process ? i : -1).filter(i => i >= 0);
    await opts.nth(hits[o.processIdx || 0]).click(); await sleep(700);
  }
  if (o.tier) { await page.locator(".tier-selector-btn", { hasText: o.tier }).click(); await sleep(700); }
  if (o.factor) await pick(page, null, o.factor, { idx: 3, exact: true });
  if (o.qty !== undefined) await grpOf(page, "Fuel / Activity Quantity").locator("input").fill(String(o.qty));
  if (o.unit) await pick(page, "Unit", o.unit, { exact: true });
  for (const [l, v] of Object.entries(o.fill || {})) {
    const inp = grpOf(page, l).locator("input, select").first();
    if ((await inp.evaluate(e => e.tagName)) === "SELECT") await inp.selectOption(String(v)); else await inp.fill(String(v));
  }
  await sleep(800);
}
export async function submitS1(page, log, draft = false) {
  const n0 = log.api.length;
  await page.getByRole("button", { name: draft ? /Save as Draft/ : /Calculate & Submit/ }).click();
  for (let i = 0; i < 30; i++) { await sleep(300); if (log.api.slice(n0).some(a => a.method === "POST" && /\/api\/emissions\/?$/.test(a.url.split("?")[0]))) break; }
  await sleep(1500);
  return log.api.slice(n0).find(a => a.method === "POST" && /\/api\/emissions\/?$/.test(a.url.split("?")[0]));
}
export async function toasts(page) { return (await page.locator(".toast, [class*=toast]").allInnerTexts().catch(() => [])).join(" | "); }
export async function dashboard(page, log, { year, region, gwp } = {}) {
  await page.goto(UI + "/"); await sleep(3500);
  if (year) await pick(page, null, String(year), { idx: 0, exact: true }), await sleep(2500);
  if (region) await pick(page, null, region, { idx: 4 }), await sleep(3000);
  if (gwp) { await page.getByText(gwp, { exact: true }).first().click(); await sleep(3000); }
  const txt = await page.locator("main, body").first().innerText();
  const batch = lastApi(log, "/api/dashboard/batch-all");
  return { txt, batch };
}
