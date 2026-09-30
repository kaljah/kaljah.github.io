// Column mapping helpers shared by the bulk import wizards.

// Header as compared: template tags ("[Required] date") and unit notes ("Bleed Rate (scf/hr)")
// are dropped, then lower case words
export function normHeader(h) {
  return String(h ?? "")
    .replace(/^\s*(\[[^\]]*\]\s*)+/, "")
    .replace(/\([^)]*\)/g, " ")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

const hasWord = (text, term) => term && new RegExp(`(^| )${term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}( |$)`).test(text);

// Field -> header. An exact name (field key or label) wins; otherwise a header that contains the
// whole field name. Each header is used once, so a column such as "Type" or "Unit" is not
// assigned to every field whose label contains that word.
export function autoDetectMapping(headers, fields) {
  const mapping = {};
  const used = new Set();
  const norm = headers.map((h) => [h, normHeader(h)]);
  const terms = (f) => [normHeader(f.key.replace(/_/g, " ")), normHeader(f.label)].filter(Boolean);

  fields.forEach((f) => {
    const hit = norm.find(([h, n]) => !used.has(h) && terms(f).includes(n));
    if (hit) {
      mapping[f.key] = hit[0];
      used.add(hit[0]);
    }
  });
  // longer field names first, so "Tank Control Eff" is matched before "Control Eff"
  [...fields]
    .filter((f) => !mapping[f.key])
    .sort((a, b) => Math.max(...terms(b).map((t) => t.length)) - Math.max(...terms(a).map((t) => t.length)))
    .forEach((f) => {
      const hit = norm.find(([h, n]) => !used.has(h) && terms(f).some((t) => t.length > 2 && hasWord(n, t)));
      if (hit) {
        mapping[f.key] = hit[0];
        used.add(hit[0]);
      }
    });
  // a short header ("Facility") that is a word of exactly one field name ("Region / Facility")
  norm
    .filter(([h, n]) => !used.has(h) && n.length >= 4)
    .forEach(([h, n]) => {
      const cands = fields.filter((f) => terms(f).some((t) => hasWord(t, n)));
      if (cands.length === 1 && !mapping[cands[0].key]) {
        mapping[cands[0].key] = h;
        used.add(h);
      }
    });
  return mapping;
}

// Required fields that are not mapped. The period is a date column OR year and month columns.
export function missingRequiredFields(fields, mapping) {
  const has = (k) => Boolean(mapping[k]);
  const withDate = fields.some((f) => f.key === "date");
  const periodOk = has("date") || (has("year") && has("month"));
  return fields
    .filter((f) => {
      if (!f.required || has(f.key)) return false;
      if (withDate && ["date", "year", "month"].includes(f.key)) return !periodOk && f.key === "date";
      return true;
    })
    .map((f) => (withDate && f.key === "date" ? { ...f, label: "Date (or Year and Month)" } : f));
}
