import { launch, session, UI, sleep } from "./lib.mjs";
const b = await launch(); const { page } = await session(b, "admin");
await page.goto(UI + "/sbti"); await sleep(4000);
if (!(await page.getByText("Hide Target Settings").count())) await page.getByText("Configure Target").first().click(); await sleep(1000);
const inp = page.locator("div").filter({ hasText: "SBTi Corporate Target Setup" }).filter({ has: page.locator("input") }).last().locator("input");
console.log(await inp.evaluateAll(es => es.map(e => ({ type: e.type, min: e.min, max: e.max, required: e.required }))));
await inp.nth(3).fill("-5");
console.log("validity:", await inp.nth(3).evaluate(e => [e.checkValidity(), e.validationMessage]));
await b.close();
