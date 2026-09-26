import { launch, session, shot, UI, sleep } from "./lib.mjs";
const b = await launch();
const routes = ["/", "/emissions", "/manage-data", "/qa-dashboard", "/reports", "/carbon-intensity", "/methane-intensity", "/sbti", "/uncertainty", "/reference-data", "/audit-trail", "/user-management", "/settings"];
for (const role of ["admin", "superuser", "user", "it_admin"]) {
  const { ctx, page, log } = await session(b, role);
  console.log("==", role, "landed", page.url());
  const nav = await page.$$eval("nav a, aside a", as => as.map(a => a.getAttribute("href")));
  console.log(" nav:", [...new Set(nav)].join(" "));
  await shot(page, `w1_${role}_landing`);
  const res = {};
  for (const r of routes) {
    await page.goto(UI + r); await sleep(1500);
    res[r] = page.url().replace(UI, "");
  }
  console.log(" route->final:", JSON.stringify(res));
  const bad = log.api.filter(a => a.status >= 400).map(a => `${a.status} ${a.method} ${a.url}`);
  console.log(" api errors:", [...new Set(bad)].slice(0, 20));
  console.log(" console errs:", log.errors.slice(0, 5));
  await ctx.close();
}
// wrong password + logout + session expiry
{
  const { ctx, page, log } = await session(b, null);
  await page.goto(UI + "/login"); await sleep(800);
  const skip = page.locator(".skip-intro-btn"); if (await skip.count()) await skip.click().catch(() => {});
  await page.fill('input[placeholder="Email Address"]', "audit_admin@audit.local");
  await page.fill('input[type="password"]', "wrong");
  await page.keyboard.press("Enter"); await sleep(2500);
  await shot(page, "w1_badpw");
  console.log("bad pw url", page.url(), "text:", (await page.locator("body").innerText()).slice(0, 300).replace(/\n/g, " | "));
  await ctx.close();
}
{
  const { ctx, page, log } = await session(b, "admin");
  // expire session by clearing cookies
  await ctx.clearCookies();
  await page.goto(UI + "/emissions"); await sleep(3000);
  console.log("after cookie clear ->", page.url());
  await shot(page, "w1_expired");
  await ctx.close();
}
await b.close();
