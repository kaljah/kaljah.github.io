// Deep links from charts into the Reports records table. Reports reads these once on arrival
// (see the deepLink state in pages/Reports.tsx). Charts only navigate; they never change the
// filters of the page they are on.
export interface RecordsLinkOptions {
  facilityId?: string | number | null;
  year?: string | number | null;
  month?: string | number | null;
  scope?: "1" | "2" | "3" | null;
  process?: string | null;
}

export const recordsLink = (o: RecordsLinkOptions): string => {
  const p = new URLSearchParams();
  const add = (k: string, v: unknown) => {
    if (v !== undefined && v !== null && v !== "" && v !== "all") p.set(k, String(v));
  };
  add("facility", o.facilityId);
  // "all" is kept for the year: Reports otherwise jumps to the most recent year, which would not match a chart showing all years.
  if (o.year !== undefined && o.year !== null && o.year !== "") p.set("year", String(o.year));
  add("month", o.month);
  add("scope", o.scope);
  add("process", o.process);
  const q = p.toString();
  return q ? `/reports?${q}` : "/reports";
};
