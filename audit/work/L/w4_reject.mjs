import { launch, session, shot, UI, sleep, toasts } from "./lib.mjs";
const b = await launch(); const { page, log } = await session(b, "admin");
await page.goto(UI + "/manage-data"); await sleep(3000);
await page.getByText("Pending Review", { exact: false }).first().click(); await sleep(3000);
const row = page.locator("tr", { hasText: "#753" });
await row.first().locator("button[title*=Reject]").click(); await sleep(1000);
await shot(page, "w4_reject_modal");
const modal = await page.locator("body").innerText(); const k = modal.indexOf("Reject Emission"); console.log(modal.slice(k, k + 500).replace(/\n+/g, " | "));
// try confirm with empty reason
const n0 = log.api.length;
console.log("confirm disabled with empty reason:", await page.getByRole("button", { name: "Confirm Rejection" }).isDisabled());
console.log("empty reason ->", log.api.slice(n0).filter(a => a.method !== "GET").map(a => a.status + " " + a.url), await toasts(page));
await page.locator("textarea").first().fill("Audit L: wrong quantity");
await page.getByRole("button", { name: "Confirm Rejection" }).click(); await sleep(2500);
console.log("reject ->", log.api.slice(n0).filter(a => a.method !== "GET").map(a => a.status + " " + a.url + " " + JSON.stringify(a.body)), await toasts(page));
await b.close();
