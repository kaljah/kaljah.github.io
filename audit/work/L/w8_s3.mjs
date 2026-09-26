import { launch, session, shot, UI, sleep, pick, grpOf, toasts } from "./lib.mjs";
const b = await launch(); const { page, log } = await session(b, "admin");
await page.goto(UI + "/emissions"); await sleep(2500);
await page.getByText("Scope 3", { exact: true }).first().click(); await sleep(3000);
const dds = page.locator(".calc-panel .custom-dropdown .dropdown-selected, .scope-form .custom-dropdown .dropdown-selected");
const n = await page.locator(".custom-dropdown .dropdown-selected").count(); console.log("dropdowns", n);
for (let i = 0; i < n; i++) { const d = page.locator(".custom-dropdown .dropdown-selected").nth(i); const t = await d.innerText(); await d.click(); await sleep(300); const o = await page.locator(".dropdown-portal .dropdown-option").allInnerTexts(); console.log("DD" + i, `[${t}]`, o.length, o.slice(0, 20).map(s => s.replace(/\n/g, " ")).join(" ; ")); await page.mouse.click(5, 500); await sleep(200); }
const lab = l => page.locator("div").filter({ has: page.locator("label", { hasText: l }) }).last();
const idxOf = async txt => { const all = await page.locator(".custom-dropdown .dropdown-selected").allInnerTexts(); return all.findIndex(t => t.includes(txt)); };
await pick(page, "Facility", "AUDIT-L Plant");
await lab("Year").locator("input").fill("2025");
await pick(page, "Category", process.argv[2] || "1");
try { await pick(page, "Activity Type", process.argv[3] || ""); } catch (e) { console.log("activity pick:", e.message.slice(0, 300)); }
await lab("Amount").locator("input").first().fill(process.argv[4] || "1000");
await sleep(800);
console.log("form text:", (await page.locator(".scope-form, .calc-panel").first().innerText()).replace(/\n+/g, " | ").slice(0, 1500));
const n0 = log.api.length;
await page.getByRole("button", { name: /Calculate & Submit|Submit|Add/ }).first().click(); await sleep(3000);
console.log(log.api.slice(n0).filter(a => a.method === "POST").map(a => `${a.status} ${a.url} req=${a.req} resp=${JSON.stringify(a.body).slice(0, 500)}`));
console.log("toast:", (await toasts(page)).replace(/\s+/g, " ").slice(0, 200));
await shot(page, "w8_s3", true);
await b.close();
