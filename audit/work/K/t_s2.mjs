import { start, OUT, UI } from "./lib.mjs";
const { browser, page, log } = await start("admin");
await page.goto(UI + "/emissions?scope=scope2"); await page.waitForTimeout(9000);
await page.locator(".dropdown-selected", { hasText: /Select (Region|Facility)/ }).first().click(); await page.waitForTimeout(500);
await page.locator(".dropdown-option").nth(1).click(); await page.waitForTimeout(800);
const grp = (t) => page.locator(".input-group").filter({ has: page.locator("label", { hasText: t }) }).last();
await grp("Source Type").locator(".dropdown-selected").click(); await page.waitForTimeout(300);
await page.locator(".dropdown-option", { hasText: process.argv[2] === "cogen" ? "CHP" : "Indirect Steam" }).click(); await page.waitForTimeout(600);
const unitShown = await page.locator(".input-group").filter({ has: page.locator("label", { hasText: /^Unit$/ }) }).locator(".dropdown-selected").innerText();
console.log("unit displayed:", JSON.stringify(unitShown));
if (process.argv[2] === "cogen") {
  await grp("Heat Output").locator("input").fill("100"); await grp("Power Output").locator("input").fill("100");
  await grp("Total Facility Emissions").locator("input").fill("1000");
} else {
  await grp("Boiler Efficiency").locator("input").fill("0.8"); await grp("Transmission Loss").locator("input").fill("0");
  await grp("Usage Amount").locator("input").fill("1000");
}
log.reqs.length = 0;
await page.getByRole("button", { name: /Calculate|Submit|Add/ }).last().click(); await page.waitForTimeout(3000);
const post = log.reqs.find(r => r.m === "POST" && r.u.startsWith("/api/scope2"));
const resp = log.resps.find(r => r.u === "/api/scope2" && r.body && r.body.startsWith("{"));
console.log("POST:", post && post.body); console.log("RESP:", resp && resp.s, resp && resp.body.slice(0, 400));
console.log("toasts", await page.locator("[class*=toast]").allInnerTexts());
await page.screenshot({ path: OUT + "s2.png", fullPage: true });
await browser.close();
