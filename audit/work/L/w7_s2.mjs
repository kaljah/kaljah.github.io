import { launch, session, shot, UI, sleep, pick, grpOf, toasts, lastApi } from "./lib.mjs";
const b = await launch(); const { page, log } = await session(b, process.argv[2] || "admin");
await page.goto(UI + "/emissions"); await sleep(2500);
await page.getByText("Scope 2", { exact: true }).first().click(); await sleep(2500);
const dds = page.locator(".custom-dropdown .dropdown-selected");
for (let i = 0; i < await dds.count(); i++) { await dds.nth(i).click(); await sleep(300); const o = await page.locator(".dropdown-portal .dropdown-option").allInnerTexts(); console.log("DD" + i, o.length, o.slice(0, 25).map(s => s.replace(/\n/g, " ")).join(" ; ")); await page.mouse.click(5, 500); await sleep(200); }
await pick(page, null, "AUDIT-L Plant", { idx: 0 });
await grpOf(page, "Year").locator("input").fill("2025");
await grpOf(page, "Month").locator("select").selectOption("6");
await pick(page, null, process.argv[3] || "Algeria", { idx: 2 });
await page.locator("div").filter({ has: page.locator("label", { hasText: "Usage Amount" }) }).last().locator("input").fill(process.argv[4] || "1000");
if (process.argv[5]) await pick(page, "Unit", process.argv[5], { exact: true });
const n0 = log.api.length;
await page.getByRole("button", { name: /Calculate & Submit/ }).click(); await sleep(3000);
console.log(log.api.slice(n0).filter(a => a.method === "POST").map(a => `${a.status} ${a.url} req=${a.req} resp=${JSON.stringify(a.body).slice(0, 500)}`));
console.log("toast:", (await toasts(page)).replace(/\s+/g, " ").slice(0, 200));
await shot(page, "w7_s2", true);
await b.close();
