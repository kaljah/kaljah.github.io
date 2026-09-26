import { launch, session, shot, UI, sleep, lastApi } from "./lib.mjs";
const b = await launch();
const { page, log } = await session(b, "admin");
await page.goto(UI + "/manage-data"); await sleep(3000);
await page.getByText("Regions", { exact: true }).first().click(); await sleep(2000);
const grp = l => page.locator("div").filter({ has: page.locator("label", { hasText: l }) }).last();
// submit empty first (validation)
await page.getByRole("button", { name: "Add Region" }).click(); await sleep(1000);
console.log("empty submit toast:", (await page.locator("body").innerText()).match(/Name, Activity[^\n]*/)?.[0]);
await grp("Region Name").locator("input").fill(process.argv[2] || "AUDIT-L Plant");
const actSel = grp("Activity").locator("select");
const acts = await actSel.locator("option").allInnerTexts(); console.log("activities:", acts);
await actSel.selectOption({ index: 1 }); await sleep(500);
const divSel = grp("Division").locator("select");
console.log("divisions:", await divSel.locator("option").allInnerTexts());
await divSel.selectOption({ index: 1 });
await grp("Location (Wilaya)").locator("input").fill("West");
await grp("Field / Block").locator("input").fill("AUDIT-L Field");
if (process.argv[3]) { await grp("Latitude").locator("input").fill("31.5"); await grp("Longitude").locator("input").fill("5.2"); }
await page.getByRole("button", { name: "Add Region" }).click(); await sleep(2500);
const p = lastApi(log, "/api/facilities", "POST");
console.log("POST", p?.status, p?.req, JSON.stringify(p?.body));
await shot(page, "w2_fac");
console.log("errors", log.errors.slice(0, 3));
await b.close();
