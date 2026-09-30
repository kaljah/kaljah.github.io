import { launch, session, sleep, dashboard } from "./lib.mjs";
const b = await launch(); const { page, log } = await session(b, "admin");
for (const [y, r] of [[null, null], ["2025", null], ["2025", "AUDIT-L Plant"]]) {
  const d = await dashboard(page, log, { year: y, region: r });
  const i = d.txt.indexOf("Pending Records");
  console.log(y, r, "banner:", i >= 0 ? d.txt.slice(i, i + 160).replace(/\n+/g, " | ") : "ABSENT", "api:", JSON.stringify(d.batch?.body?.pending_stats), d.batch?.url);
}
await b.close();
