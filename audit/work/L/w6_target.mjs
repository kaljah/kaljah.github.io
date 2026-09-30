import { launch, session, shot, UI, sleep, toasts, grpOf } from "./lib.mjs";
const b = await launch(); const { page, log } = await session(b, "admin");
await page.goto(UI + "/sbti"); await sleep(5000);
console.log("url", page.url(), (await page.locator("body").innerText()).slice(0, 200).replace(/\s+/g, " "));
const open = async () => {
  await page.goto(UI + "/sbti"); await sleep(4000);
  if (!(await page.getByText("Hide Target Settings").count())) await page.getByText("Configure Target", { exact: false }).first().click();
  await sleep(1200);
};
const ORDER = { "Base Year": 0, "Base Year Baseline": 1, "Net-Zero Target Year": 2, "Annual Reduction Rate": 3 };
const setv = async (l, v) => page.locator("div").filter({ hasText: "SBTi Corporate Target Setup" }).filter({ has: page.locator("input") }).last().locator("input").nth(ORDER[l]).fill(String(v));
const save = async (tag) => {
  const n0 = log.api.length; await page.getByRole("button", { name: /Save SBTi Target/ }).click(); await sleep(2500);
  const w = log.api.slice(n0).filter(a => a.method !== "GET");
  console.log(tag, w.map(a => `${a.status} ${a.method} ${a.url} req=${a.req} resp=${JSON.stringify(a.body).slice(0, 200)}`), "|toast:", (await toasts(page)).replace(/\s+/g, " ").slice(0, 200));
};
const cases = process.argv[2] === "restore" ? [["restore", 2024, 750000, 2030, 4.2]] : [
  ["targetYear<base", 2024, 750000, 2020, 4.2], ["negRate", 2024, 750000, 2030, -5], ["zeroBaseline", 2024, 0, 2030, 4.2],
  ["emptyBaseline", 2024, "", 2030, 4.2], ["rate100", 2024, 750000, 2030, 100], ["valid", 2024, 800000, 2035, 3.0]];
for (const [tag, by, bl, ty, rr] of cases) {
  await open(); await setv("Base Year", by); await setv("Base Year Baseline", bl); await setv("Net-Zero Target Year", ty); await setv("Annual Reduction Rate", rr); await save(tag);
}
await page.reload(); await sleep(4000);
const t = await page.locator("main, body").first().innerText();
const i = t.indexOf("BASE YEAR BASELINE"); console.log("AFTER RELOAD:", t.slice(i, i + 400).replace(/\n+/g, " | "));
const tr = [...log.api].reverse().find(a => a.url.includes("sbti-trajectory"));
console.log("API:", JSON.stringify(tr?.body).slice(0, 400));
await shot(page, "w6_after", true);
await b.close();
