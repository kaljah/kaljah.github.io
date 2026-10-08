import React from "react";

// Skipped rows grouped by cause: count, the column to fix and how (server: services/import_feedback.py)
export interface SkipGroup {
  title: string;
  count: number;
  column?: string;
  fix?: string;
  rows?: number[];
}

export interface SkipGroupListProps {
  groups?: SkipGroup[];
  scale?: number;
  approx?: boolean;
  limit?: number;
}

const fmt = (n: number) => Number(n || 0).toLocaleString("en-US");

export const SkipGroupList: React.FC<SkipGroupListProps> = ({ groups, scale = 1, approx = false, limit = 8 }) => {
  if (!groups || groups.length === 0) return null;
  return (
    <ul className="m-0 flex list-none flex-col gap-2 p-0">
      {groups.slice(0, limit).map((g, i) => (
        <li key={i} className="rounded-md border border-border bg-surface px-3 py-2 text-sm">
          <div className="flex flex-wrap items-baseline gap-x-2">
            <span className="font-bold tabular-nums text-warning-fg">
              {approx ? "≈ " : ""}
              {fmt(Math.round(g.count * scale))}
            </span>
            <span className="font-semibold text-text">{g.title}</span>
            {g.column && <span className="font-mono text-xs text-text-secondary">column: {g.column}</span>}
          </div>
          {g.fix && <p className="m-0 mt-1 text-text-secondary">How to fix: {g.fix}</p>}
          {g.rows && g.rows.length > 0 && (
            <p className="m-0 mt-1 text-xs text-text-secondary">
              e.g. file line{g.rows.length > 1 ? "s" : ""} {g.rows.slice(0, 6).join(", ")}
              {g.count > 6 ? " …" : ""}
            </p>
          )}
        </li>
      ))}
      {groups.length > limit && (
        <li className="text-xs text-text-secondary">
          + {groups.length - limit} other cause{groups.length - limit > 1 ? "s" : ""} (all are in the downloadable list after the import)
        </li>
      )}
    </ul>
  );
};

export default SkipGroupList;
