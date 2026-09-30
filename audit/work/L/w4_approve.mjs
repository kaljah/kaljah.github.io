import { launch, session, shot, UI, sleep, dashboard, toasts } from "./lib.mjs";
const b = await launch();
const { page, log } = await session(b, "admin");
let d = await dashboard(page, log, { year: "2025", region: "AUDIT-L Plant" });
const m = t => { const i = t.indexOf("Pending Records"); const j = t.indexOf("GROSS OPERATIONAL"); return t.slice(i, i + 250).replace(/\n+/g, " | ") + " || " + t.slice(j, j + 120).replace(/\n+/g, " | "); };
console.log("BEFORE:", m(d.txt));
console.log("pending_stats", JSON.stringify(d.batch.body.pending_stats));
await page.goto(UI + "/manage-data"); await sleep(3000);
await page.getByText("Pending Review", { exact: false }).first().click(); await sleep(3000);
await shot(page, "w4_pending", true);
const row = page.locator("tr", { hasText: "AUDIT-L" });
console.log("pending rows for AUDIT-L:", await row.count(), (await row.first().innerText().catch(() => "")).replace(/\s+/g, " "));
const btns = await row.first().locator("button").allInnerTexts(); console.log("row buttons", btns, await row.first().locator("button").evaluateAll(bs => bs.map(b => b.title || b.getAttribute("aria-label"))));
if (process.argv[2] === "approve") {
  const n0 = log.api.length;
  await row.first().locator("button[title*=pprove], button:has-text('Approve')").first().click(); await sleep(3000);
  console.log("approve calls", log.api.slice(n0).filter(a => a.method !== "GET").map(a => `${a.status} ${a.method} ${a.url} ${JSON.stringify(a.body).slice(0, 200)}`));
  console.log("toast", await toasts(page));
  d = await dashboard(page, log, { year: "2025", region: "AUDIT-L Plant" });
  console.log("AFTER:", m(d.txt));
}
await b.close();
