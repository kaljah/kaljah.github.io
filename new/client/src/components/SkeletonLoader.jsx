import React from "react";
import "./SkeletonLoader.css";

export const SkeletonRow = ({ columns = 5 }) => (
  <div className="skeleton-row" aria-hidden="true">
    {Array.from({ length: columns }).map((_, i) => (
      <div key={i} className="skeleton-block skeleton-cell" />
    ))}
  </div>
);

export const SkeletonTable = ({ rows = 5, columns = 5 }) => (
  <div className="skeleton-table" role="status" aria-label="Loading">
    {Array.from({ length: rows }).map((_, i) => (
      <SkeletonRow key={i} columns={columns} />
    ))}
  </div>
);

export const SkeletonCard = () => (
  <div className="skeleton-card" role="status" aria-label="Loading">
    <div className="skeleton-block skeleton-card-title" />
    <div className="skeleton-block skeleton-card-value" />
  </div>
);
