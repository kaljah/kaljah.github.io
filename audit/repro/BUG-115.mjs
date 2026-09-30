// BUG-115 repro (browser stack :5190): negative production -> server message vs toast text
import { launch, session, sleep, UI, pick } from "../work/L/lib.mjs";
const b = await launch(); const { page, log } = await session(b, "admin");
await page.goto(UI + "/manage-data"); await sleep(3000);
await page.getByText("Production Data", { exact: true }).first().click(); await sleep(2500);
const lab = l => page.locator("div").filter({ has: page.locator("label", { hasText: l }) }).last();
await lab("Activity").locator("select").first().selectOption("EP"); await sleep(300);
await lab("Division").locator("select").first().selectOption("Production"); await sleep(300);
const all = await page.locator(".custom-dropdown .dropdown-selected").allInnerTexts();
await pick(page, null, "AUDIT-L Plant", { idx: all.findIndex(t => /Region/.test(t)) });
await lab("Month").locator("select").selectOption("8"); await lab("Year").locator("input").fill("2025");
await lab("Oil (bbl)").locator("input").first().fill("-5000");
const n0 = log.api.length;
await page.getByRole("button", { name: "Save Record" }).click(); await sleep(2500);
const resp = log.api.slice(n0).find(a => a.method === "POST");
const toast = (await page.locator("[class*=toast]").allInnerTexts()).join(" ");
const shown = resp?.body?.error && toast.includes(resp.body.error);
console.log(`server: ${resp?.status} "${resp?.body?.error}"; toast: "${toast.replace(/\s+/g, " ").slice(0, 80)}"; server reason shown: ${shown}`);
await b.close(); process.exit(shown ? 0 : 1);
