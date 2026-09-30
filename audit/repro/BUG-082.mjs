// BUG-082: Scope 1 GWP label hard-coded "IPCC AR6 (CH4:28, N2O:265)" while settings/records are AR5. Needs UI :5191 / API :5056.
import { start, UI } from "./k_uilib.mjs";
const { browser, page, log } = await start("admin");
await page.goto(UI + "/emissions?scope=scope1"); await page.waitForTimeout(9000);
const label = await page.getByText(/GWP Standard: IPCC/).first().innerText();
const s = log.resps.find(r => r.u.includes("/auth/settings"));
const std = s ? (JSON.parse(s.body).gwp_standard || "AR5") : "AR5";
console.log("active standard:", std, "| label:", label);
const vals = { AR5: "CH₄:28, N₂O:265", AR6: "CH₄:29.8, N₂O:273", AR4: "CH₄:25, N₂O:298" }[std];
const ok = label.includes(std) && (!vals || label.includes(vals));
await browser.close(); process.exit(ok ? 0 : 1);
