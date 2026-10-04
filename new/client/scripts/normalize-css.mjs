// Maps raw border-radius, neutral box-shadow and font-size values onto the design tokens.
// Usage: node scripts/normalize-css.mjs [--write] [--only radius,shadow,font]
import fs from "node:fs";
import path from "node:path";
import postcss from "postcss";

const write = process.argv.includes("--write");
const onlyArg = process.argv.find((a) => a.startsWith("--only="));
const only = onlyArg ? onlyArg.slice(7).split(",") : ["radius", "shadow", "font"];
const walk = (dir, out = []) => {
  for (const n of fs.readdirSync(dir)) {
    if (n === "__tests__" || n === "node_modules") continue;
    const p = path.join(dir, n);
    fs.statSync(p).isDirectory() ? walk(p, out) : out.push(p);
  }
  return out;
};
const css = walk("src").filter((f) => f.endsWith(".css") && !/styles[\/](tokens|base)\.css$/.test(f));

const toPx = (v) => {
  const m = /^(-?\d*\.?\d+)(px|rem)$/.exec(v.trim());
  if (!m) return null;
  return m[2] === "rem" ? parseFloat(m[1]) * 16 : parseFloat(m[1]);
};
const radiusTok = (v) => {
  const px = toPx(v);
  if (px === null) return v;
  if (px === 0) return v;
  if (px > 40) return v; // pills and circles
  if (px <= 7) return "var(--radius-sm)";
  if (px <= 13) return "var(--radius-md)";
  return "var(--radius-lg)";
};
const fontTok = (v) => {
  const px = toPx(v);
  if (px === null) return v;
  const r = px / 16;
  if (r < 0.73) return "var(--text-xs)";
  if (r < 0.83) return "var(--text-sm)";
  if (r < 0.91) return "var(--text-base)";
  if (r < 1.075) return "var(--text-md)";
  if (r < 1.3) return "var(--text-lg)";
  if (r < 1.8) return "var(--text-xl)";
  if (r < 2.05) return "var(--text-2xl)";
  return "var(--text-3xl)";
};
const shadowTok = (v) => {
  if (/inset|var\(|none|!important/.test(v)) return v;
  const parts = v.split(/,(?![^(]*\))/).map((s) => s.trim());
  // keep rings and colored (brand/status) glows; only neutral slate/black elevation shadows are mapped
  const neutral = parts.every((p) => /rgba\(\s*(0|15|17|2|30)\s*,/.test(p) || /rgba\(\s*0\s*,\s*0\s*,\s*0/.test(p));
  if (!neutral) return v;
  const blur = Math.max(...parts.map((p) => toPx((p.match(/^\S+\s+\S+\s+(\S+)/) || [])[1] || "") ?? 0));
  if (blur <= 6) return "var(--shadow-xs)";
  if (blur <= 24) return "var(--shadow-card)";
  if (blur <= 40) return "var(--shadow-raised)";
  return "var(--shadow-overlay)";
};

let n = 0;
for (const f of css) {
  const root = postcss.parse(fs.readFileSync(f, "utf8"));
  root.walkDecls((d) => {
    const prev = d.value;
    if (only.includes("radius") && d.prop === "border-radius" && !/var\(|%|\//.test(prev)) {
      d.value = prev.trim().split(/\s+/).map(radiusTok).join(" ");
    } else if (only.includes("font") && d.prop === "font-size") {
      d.value = fontTok(prev);
    } else if (only.includes("shadow") && d.prop === "box-shadow") {
      d.value = shadowTok(prev);
    }
    if (d.value !== prev) n++;
  });
  if (write) fs.writeFileSync(f, root.toString());
}
console.log(`${write ? "changed" : "would change"} ${n} declarations`);
