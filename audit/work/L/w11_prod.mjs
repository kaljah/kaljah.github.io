import { launch, session, shot, UI, sleep, pick, toasts } from "./lib.mjs";
const b = await launch(); const { page, log } = await session(b, "admin");
await page.goto(UI + "/manage-data"); await sleep(3000);
await page.getByText("Production Data", { exact: true }).first().click(); await sleep(2500);
const lab = l => page.locator("div").filter({ has: page.locator("label", { hasText: l }) }).last();
const cases = JSON.parse(process.argv[2]);
for (const c of cases) {
  if (c.act) { const sel = lab("Activity").locator("select").first(); console.log("act opts", await sel.locator("option").evaluateAll(o => o.map(x => x.value))); await sel.selectOption(c.act); await sleep(400);
    const ds = lab("Division").locator("select").first(); console.log("div opts", await ds.locator("option").evaluateAll(o => o.map(x => x.value))); await ds.selectOption(c.div); await sleep(400); }
  if (c.fac) { const all = await page.locator(".custom-dropdown .dropdown-selected").allInnerTexts(); console.log("dds", all);
    let done = false; for (let i = 0; i < all.length && !done; i++) { if (!/Region/.test(all[i])) continue; try { await pick(page, null, c.fac, { idx: i }); done = true; } catch (e) {} } console.log("fac picked", done); }
  if (c.month) await lab("Month").locator("select").selectOption(String(c.month));
  if (c.year !== undefined) await lab("Year").locator("input").fill(String(c.year));
  for (const [k, v] of Object.entries(c.f || {})) await lab(k).locator("input").first().fill(String(v));
  const n0 = log.api.length;
  await page.getByRole("button", { name: "Save Record" }).click(); await sleep(2500);
  console.log(c.tag, log.api.slice(n0).filter(a => a.method === "POST").map(a => `${a.status} ${a.url} req=${a.req} resp=${JSON.stringify(a.body).slice(0, 200)}`), "toast:", (await toasts(page)).replace(/\s+/g, " ").slice(0, 120));
}
await shot(page, "w11_prod", true);
await b.close();
