// BUG-029 repro: uses the isolated browser stack (UI :5190 -> API :5055 -> audit/db/browser.db)
import { launch, session, UI, sleep } from "../work/L/lib.mjs";
const b = await launch();
const a = await session(b, "admin");
const [st] = await a.page.evaluate(async () => {
  const t = (await (await fetch("/api/csrf-token", { credentials: "include" })).json()).csrf_token;
  const res = await fetch("/api/facilities", { method: "POST", credentials: "include", headers: { "Content-Type": "application/json", "X-CSRFToken": t }, body: JSON.stringify({ region: "West" }) });
  return [res.status];
});
const u = await session(b, "user");
await u.page.goto(UI + "/manage-data"); await sleep(4000);
const crashed = (await u.page.locator("body").innerText()).includes("Something went wrong");
console.log(`nameless facility POST: expected 400, actual ${st}; manage-data crashed: expected false, actual ${crashed}`);
await b.close();
process.exit(st === 201 ? 1 : 0);
