import React from "react";
import "./SkipGroupList.css";

// Skipped rows grouped by cause: count, the column to fix and how (server: services/import_feedback.py)
const fmt = (n) => Number(n || 0).toLocaleString("en-US");

export default function SkipGroupList({ groups, scale = 1, approx = false, limit = 8 }) {
  if (!groups || groups.length === 0) return null;
  return (
    <div className="s1w-skip-groups">
      {groups.slice(0, limit).map((g, i) => (
        <div key={i} className="s1w-skip-group">
          <div className="s1w-skip-group-head">
            <span className="s1w-skip-count">{approx ? "≈ " : ""}{fmt(Math.round(g.count * scale))}</span>
            <span className="s1w-skip-title">{g.title}</span>
            {g.column && <span className="s1w-skip-col">column: {g.column}</span>}
          </div>
          {g.fix && <div className="s1w-skip-fix">How to fix: {g.fix}</div>}
          {g.rows?.length > 0 && (
            <div className="s1w-skip-rows">e.g. file line{g.rows.length > 1 ? "s" : ""} {g.rows.slice(0, 6).join(", ")}{g.count > 6 ? " …" : ""}</div>
          )}
        </div>
      ))}
      {groups.length > limit && <div className="s1w-skip-rows">+ {groups.length - limit} other cause{groups.length - limit > 1 ? "s" : ""} (all are in the downloadable list after the import)</div>}
    </div>
  );
}
