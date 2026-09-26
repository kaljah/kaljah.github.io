import { launch, session, UI, sleep, login } from "./lib.mjs";
const b = await launch();
const ctx = await b.newContext(); const page = await ctx.newPage();
await login(page, "superuser");
const cookies = await ctx.cookies();
console.log("logged in at", page.url(), "cookies:", cookies.map(c => c.name));
await page.locator(".user-avatar, .avatar, [class*=avatar]").last().click().catch(() => {}); await sleep(600);
let clicked = false;
for (const sel of ["#logout-btn-drop", ".logout-btn-top", "text=Logout", "text=Log out", "text=Sign out"]) { const l = page.locator(sel).first(); if (await l.count() && await l.isVisible().catch(() => false)) { await l.click(); clicked = true; break; } }
if (!clicked) { await page.evaluate(() => fetch("/api/auth/logout", { method: "POST", credentials: "include" })); console.log("fallback API logout"); }
await sleep(2500);
console.log("after logout url:", page.url(), "clicked UI:", clicked);
const r1 = await ctx.request.get(UI + "/api/auth/me"); console.log("same ctx /me:", r1.status());
const ctx2 = await b.newContext(); await ctx2.addCookies(cookies);
const r2 = await ctx2.request.get(UI + "/api/auth/me"); console.log("replayed pre-logout cookie /me:", r2.status(), (await r2.text()).slice(0, 120));
const r3 = await ctx2.request.get(UI + "/api/emissions?scope=1&limit=1&offset=0"); console.log("replayed cookie data access:", r3.status());
await b.close();
