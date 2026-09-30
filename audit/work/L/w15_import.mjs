import { launch, session, shot, UI, sleep, openS1 } from "./lib.mjs";
const b = await launch(); const { page, log } = await session(b, process.argv[2] || "admin");
await openS1(page);
await page.getByRole("button", { name: /Bulk Import \(Wizard\)/ }).click(); await sleep(1500);
for (let s = 0; s < 2; s++) { await page.locator(".s1w-modal").getByRole("button", { name: /Next|Continue/ }).last().click(); await sleep(800); }
await shot(page, "w15_step3");
console.log("step3 text:", (await page.locator(".s1w-modal").innerText()).replace(/\n+/g, " | ").slice(0, 600));
// template download
const [dl] = await Promise.all([page.waitForEvent("download", { timeout: 10000 }).catch(() => null), page.locator(".s1w-template-btn").nth(1).click()]);
if (dl) { const p = "C:/Users/samsung/Desktop/H2/audit/work/L/tmpl.csv"; await dl.saveAs(p); console.log("template saved", dl.suggestedFilename()); }
await page.locator("input[type=file]").setInputFiles("C:/Users/samsung/Desktop/H2/audit/work/L/" + (process.argv[3] || "imp1.csv")); await sleep(2000);
const rows = page.locator(".s1w-map-row");
const n = await rows.count(); const auto = {};
for (let i = 0; i < n; i++) { const lab = (await rows.nth(i).locator(".s1w-map-field-label").innerText()).trim(); const v = await rows.nth(i).locator("select").inputValue().catch(() => ""); if (v) auto[lab] = v; }
console.log("auto-mapped:", JSON.stringify(auto));
console.log("banner:", (await page.locator(".s1w-warn-banner").allInnerTexts()).join(" | "));
const setMap = async (label, col) => { for (let i = 0; i < n; i++) { const lab = (await rows.nth(i).locator(".s1w-map-field-label").innerText()).trim(); if (lab === label) { await rows.nth(i).locator("select").selectOption(col); return; } } console.log("no row", label); };
for (const [l, c] of JSON.parse(process.argv[4] || '[["Region / Facility","Site"],["Quantity","Qty"],["Unit","UOM"]]')) await setMap(l, c);
await sleep(500);
console.log("banner after:", (await page.locator(".s1w-warn-banner").allInnerTexts()).join(" | "));
await shot(page, "w15_mapping", true);
const btn = page.locator(".s1w-modal").getByRole("button", { name: /Upload|Import|Submit|Start/ }).last();
console.log("submit enabled:", await btn.isEnabled(), await btn.innerText());
const n0 = log.api.length;
await btn.click(); await sleep(2000);
const st = log.api.slice(n0).find(a => a.url.includes("upload/start"));
console.log("start:", st?.status, JSON.stringify(st?.body));
for (let i = 0; i < 20; i++) { await sleep(1500); const t = await page.locator(".s1w-modal").innerText().catch(() => ""); if (/complete|failed|error|finished|done/i.test(t)) break; }
console.log("progress text:", (await page.locator(".s1w-modal").innerText().catch(() => "")).replace(/\n+/g, " | ").slice(0, 1500));
const jobs = log.api.filter(a => a.url.includes("upload/status") || a.url.includes("/jobs/") || a.url.includes("job"));
console.log("last job api:", jobs.slice(-1).map(a => `${a.status} ${a.url} ${JSON.stringify(a.body).slice(0, 1500)}`));
await shot(page, "w15_done", true);
await b.close();
