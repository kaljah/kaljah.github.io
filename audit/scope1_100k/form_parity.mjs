// Manual-entry parity: each case is entered through the real Scope 1 form (headless Chromium) and the
// POST /api/emissions payload + response are saved; form_parity.py imports the same activity by CSV
// and compares the stored records.  node form_parity.mjs <cases.json> <out.json>
import fs from "node:fs";
import { open, openScope1, pick, fill, selectNative, tier, submit } from "./form_lib.mjs";

const [casesFile, outFile] = process.argv.slice(2);
const only = process.env.ONLY ? process.env.ONLY.split(",") : null;
const cases = JSON.parse(fs.readFileSync(casesFile, "utf8")).filter((c) => !only || only.some((o) => c.id.startsWith(o)));
const { browser, page } = await open();
const out = [];
for (const c of cases) {
  const rec = { id: c.id };
  try {
    await openScope1(page);
    await pick(page, "Region", "In Amenas CPF");
    await fill(page, "Year", 2024);
    await selectNative(page, "Month", { label: "Dec" });
    await pick(page, "Process", c.process);
    await tier(page, c.tier);
    for (const [op, a, b] of c.steps) {
      if (op === "pick") await pick(page, a, b);
      else if (op === "fill") await fill(page, a, b);
      else if (op === "select") await selectNative(page, a, { label: b });
      else if (op === "selectv") await selectNative(page, a, b);
      else if (op === "click") await page.getByText(a, { exact: true }).first().click();
      await page.waitForTimeout(150);
    }
    await fill(page, "Equipment ID", c.id);
    if (process.env.SHOT) await page.screenshot({ path: `${process.env.SHOT}/${c.id}.png`, fullPage: true });
    Object.assign(rec, await submit(page));
    await page.waitForTimeout(800);
  } catch (e) {
    rec.error = String(e.message || e).split("\n")[0];
    if (process.env.SHOT) await page.screenshot({ path: `${process.env.SHOT}/${c.id}_err.png`, fullPage: true });
  }
  console.log(c.id, rec.status ?? "", rec.error ?? JSON.stringify(rec.body).slice(0, 160));
  out.push(rec);
}
fs.writeFileSync(outFile, JSON.stringify(out, null, 1));
await browser.close();
