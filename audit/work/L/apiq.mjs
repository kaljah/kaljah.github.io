import { launch, session } from "./lib.mjs";
const [,, role, ...paths] = process.argv;
const b = await launch(); const { page } = await session(b, role);
for (const p of paths) {
  const r = await page.evaluate(async p => { const r = await fetch("/api" + p, { credentials: "include" }); return [r.status, await r.text()]; }, p);
  console.log("==", p, r[0], r[1].slice(0, +(process.env.N || 1500)));
}
await b.close();
