// Per-chart exports: the data as CSV and the rendered card as a PNG.

const save = (blob: Blob, filename: string): void => {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

const cell = (v: unknown): string => {
  const s = v === null || v === undefined ? "" : String(v);
  // Quote fields with separators/quotes/newlines, and neutralise spreadsheet formulas.
  const safe = /^[=+\-@]/.test(s) && Number.isNaN(Number(s)) ? `'${s}` : s;
  return /[",\r\n]/.test(safe) ? `"${safe.replace(/"/g, '""')}"` : safe;
};

export const toCsv = (header: string[], rows: unknown[][]): string =>
  [header, ...rows].map((r) => r.map(cell).join(",")).join("\r\n");

export const downloadCsv = (filename: string, header: string[], rows: unknown[][]): void =>
  save(new Blob(["﻿" + toCsv(header, rows)], { type: "text/csv;charset=utf-8;" }), `${filename}.csv`);

/** Renders an element to a PNG (elements marked data-html2canvas-ignore, such as the export buttons, are left out). */
export const downloadPng = async (element: HTMLElement, filename: string): Promise<void> => {
  const { default: html2canvas } = await import("html2canvas");
  const canvas = await html2canvas(element, { backgroundColor: "white", scale: 2, logging: false });
  await new Promise<void>((resolve, reject) =>
    canvas.toBlob((blob) => {
      if (!blob) return reject(new Error("PNG export failed"));
      save(blob, `${filename}.png`);
      resolve();
    }, "image/png"),
  );
};
