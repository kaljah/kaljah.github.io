import { launch, session, shot, UI, sleep } from "./lib.mjs";
const b = await launch();
for (const role of ["admin", "user"]) {
  const { ctx, page, log } = await session(b, role);
  for (const r of ["/methane-intensity", "/methane-explorer", "/reports", "/carbon-intensity", "/uncertainty", "/sbti", "/reference-data", "/qa-dashboard", "/audit-trail", "/settings"]) {
    const n0 = log.api.length, e0 = log.errors.length;
    await page.goto(UI + r); await sleep(4500);
    const txt = await page.locator("body").innerText();
    const bad = log.api.slice(n0).filter(a => a.status >= 400).map(a => `${a.status} ${a.url.slice(0, 90)}`);
    const errs = log.errors.slice(e0).filter(e => !/401/.test(e)).map(e => e.slice(0, 160));
    const flags = ["Something went wrong", "NaN", "undefined", "Infinity", "null tCO", "[object Object]"].filter(f => txt.includes(f));
    console.log(role, r, "->", page.url().replace(UI, ""), "| bad api:", JSON.stringify(bad), "| console:", JSON.stringify(errs.slice(0, 2)), "| flags:", flags.join(","));
    if (flags.length) await shot(page, `w20_${role}_${r.slice(1)}`, true);
  }
  await ctx.close();
}
await b.close();
