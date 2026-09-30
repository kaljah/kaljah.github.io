// BUG-045 repro (browser stack :5190 -> :5055 -> audit/db/browser.db): POST /api/facilities with empty lat/long as the Add Region form sends
import { launch, session } from "../work/L/lib.mjs";
const b = await launch();
const a = await session(b, "admin");
const st = await a.page.evaluate(async () => {
  const t = (await (await fetch("/api/csrf-token", { credentials: "include" })).json()).csrf_token;
  const res = await fetch("/api/facilities", { method: "POST", credentials: "include", headers: { "Content-Type": "application/json", "X-CSRFToken": t },
    body: JSON.stringify({ name: "BUG045 " + Date.now(), activity: "EP", division: "Production", field: "", location: "West", boundary_type: "", boundary_detail: "", equity_share_pct: "", segment: "", latitude: "", longitude: "", boundary_notes: "" }) });
  return res.status;
});
console.log(`expected 201 (or 400), actual ${st}`);
await b.close(); process.exit(st >= 500 ? 1 : 0);
