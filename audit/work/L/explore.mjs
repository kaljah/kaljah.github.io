import { launch, session, shot, UI, sleep } from "./lib.mjs";
const [,, route, name, role = "admin", clickText] = process.argv;
const b = await launch();
const { ctx, page, log } = await session(b, role);
await page.goto(UI + "/" + route); await sleep(4000);
if (clickText) { for (const t of clickText.split("||")) { await page.getByText(t, { exact: false }).first().click().catch(e => console.log("click fail", t)); await sleep(2000); } }
await shot(page, name, true);
console.log((await page.locator("main, body").first().innerText()).slice(0, 3000));
console.log("API:", log.api.map(a => `${a.status} ${a.method} ${a.url}`).join("\n"));
console.log("ERR:", log.errors.slice(0, 8));
await b.close();
