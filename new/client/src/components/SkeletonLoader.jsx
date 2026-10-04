import React from "react";
import "./SkeletonLoader.css";

export const SkeletonRow = ({ columns = 5 }) => (
  <div className="[display:flex] [gap:16px] [padding:12px_0] [border-bottom:1px_solid_var(--border-light)]" aria-hidden="true">
    {Array.from({ length: columns }).map((_, i) => (
      <div key={i} className="[background:var(--border-light)] [border-radius:var(--radius-sm)] [animation:skeleton-pulse_1.4s_ease-in-out_infinite] [flex:1] [height:16px]" />
    ))}
  </div>
);

export const SkeletonTable = ({ rows = 5, columns = 5 }) => (
  <div className="[width:100%]" role="status" aria-label="Loading">
    {Array.from({ length: rows }).map((_, i) => (
      <SkeletonRow key={i} columns={columns} />
    ))}
  </div>
);

export const SkeletonCard = () => (
  <div className="skeleton-card" role="status" aria-label="Loading">
    <div className="[background:var(--border-light)] [border-radius:var(--radius-sm)] [animation:skeleton-pulse_1.4s_ease-in-out_infinite] [width:33%] [height:20px] [margin-bottom:16px]" />
    <div className="[background:var(--border-light)] [border-radius:var(--radius-sm)] [animation:skeleton-pulse_1.4s_ease-in-out_infinite] [width:50%] [height:40px]" />
  </div>
);
