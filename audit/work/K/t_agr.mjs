import { start, OUT, UI } from "./lib.mjs";
const { browser, page, log } = await start("admin");
await page.goto(UI + "/emissions?scope=scope1"); await page.waitForTimeout(10000);
async function pick(labelText, optText) {
  const grp = page.locator(".input-group, .form-group, div").filter({ has: page.locator("label", { hasText: labelText }) }).last();
  await grp.locator(".dropdown-selected").first().click(); await page.waitForTimeout(500);
  await page.locator(".dropdown-option", { hasText: optText }).first().click(); await page.waitForTimeout(700);
}
await page.locator(".dropdown-selected", { hasText: "Select Region" }).click(); await page.waitForTimeout(500);
await page.locator(".dropdown-option").nth(1).click(); await page.waitForTimeout(800); console.log("region:", await page.locator(".dropdown-selected").first().innerText());
await page.locator(".dropdown-selected", { hasText: "Stationary Combustion" }).click(); await page.waitForTimeout(500);
const opts = await page.locator(".dropdown-option").allInnerTexts(); console.log("process opts:", opts.join(" | "));
await page.locator(".dropdown-option", { hasText: "Acid Gas" }).first().click(); await page.waitForTimeout(1000);
await page.locator(".agr-form input").first().fill("28316800");
await page.locator(".agr-form .dropdown-selected").first().click(); await page.waitForTimeout(400);
await page.locator(".dropdown-option", { hasText: "m³/yr" }).click(); await page.waitForTimeout(400);
const agrInputs = page.locator(".agr-form input");
console.log("agr inputs", await agrInputs.count(), await page.locator(".agr-form label").allInnerTexts());

const grpIn = page.locator(".agr-form .input-group").filter({ has: page.locator("label", { hasText: "Inlet CO2" }) });
await grpIn.locator("input").fill("5");
const grpOut = page.locator(".agr-form .input-group").filter({ has: page.locator("label", { hasText: "Outlet CO2" }) });
await grpOut.locator("input").fill("0.5");
log.reqs.length = 0;
await page.getByText("Calculate & Submit", { exact: false }).click(); await page.waitForTimeout(1200);
console.log("toasts:", await page.locator("[class*=toast]").allInnerTexts()); console.log("reqs", log.reqs.map(r=>r.m+" "+r.u));
const post = log.reqs.find(r => r.m === "POST" && r.u === "/api/emissions");
const resp = log.resps.find(r => r.u === "/api/emissions" && r.body && r.s < 500 && r.body.includes("emission"));
console.log("POST body:", post && post.body);
console.log("RESP:", resp && resp.s, resp && resp.body.slice(0, 1500));
await page.screenshot({ path: OUT + "agr.png", fullPage: true });
await browser.close();
