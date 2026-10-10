import React from "react";
import { Download, Image as ImageIcon } from "lucide-react";
import { downloadCsv, downloadPng } from "../../utils/chartExport";
import { t } from "../../i18n";

export interface ChartExportProps {
  /** File name without extension. */
  name: string;
  /** The element rendered to the PNG (the chart card). */
  targetRef: React.RefObject<HTMLElement | null>;
  header: string[];
  rows: unknown[][];
  className?: string;
}

const btn =
  "inline-flex h-7 cursor-pointer items-center gap-1 rounded-md border border-border bg-surface px-2 text-xs font-semibold text-text-secondary hover:bg-selected-bg hover:text-text disabled:cursor-wait disabled:opacity-60";

/** CSV + PNG buttons for one chart. data-html2canvas-ignore keeps them out of the PNG. */
export const ChartExport: React.FC<ChartExportProps> = ({ name, targetRef, header, rows, className = "" }) => {
  const [busy, setBusy] = React.useState(false);
  return (
    <div className={`flex justify-end gap-1.5 ${className}`} data-html2canvas-ignore="true">
      <button type="button" className={btn} onClick={() => downloadCsv(name, header, rows)} aria-label={t("Download {{name}} data as CSV", { name })}>
        <Download className="size-3.5" aria-hidden="true" /> CSV
      </button>
      <button
        type="button"
        className={btn}
        disabled={busy}
        aria-label={`Download ${name} as an image`}
        onClick={async () => {
          if (!targetRef.current) return;
          setBusy(true);
          try {
            await downloadPng(targetRef.current, name);
          } finally {
            setBusy(false);
          }
        }}
      >
        <ImageIcon className="size-3.5" aria-hidden="true" /> PNG
      </button>
    </div>
  );
};
