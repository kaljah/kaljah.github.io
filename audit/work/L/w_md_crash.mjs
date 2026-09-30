import { launch, session, shot, UI, sleep } from "./lib.mjs";
const b = await launch();
const { ctx, page, log } = await session(b, "user");
// create nameless facility through the real API as admin in separate context
const a = await session(b, "admin");
const r = await a.page.evaluate(async () => {
  const t = (await (await fetch("/api/csrf-token", { credentials: "include" })).json()).csrf_token;
  const res = await fetch("/api/facilities", { method: "POST", credentials: "include", headers: { "Content-Type": "application/json", "X-CSRFToken": t }, body: JSON.stringify({ region: "West" }) });
  return [res.status, await res.text()];
});
console.log("POST /api/facilities {region:West} ->", r[0], r[1].slice(0, 200));
for (const role of ["user"]) {
  await page.goto(UI + "/manage-data"); await sleep(4000);
  const txt = await page.locator("body").innerText();
  console.log(role, "manage-data crashed:", txt.includes("Something went wrong"));
  await shot(page, "md_crash_" + role);
}
console.log(log.errors.filter(e => e.includes("toLowerCase")).slice(0, 1));
await b.close();
