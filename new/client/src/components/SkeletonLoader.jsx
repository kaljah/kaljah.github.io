import React from 'react';

export const SkeletonRow = ({ columns = 5 }) => (
    <div className="flex w-full animate-pulse space-x-4 py-3 border-b border-[var(--border-color)]">
        {Array.from({ length: columns }).map((_, i) => (
            <div key={i} className="h-4 bg-[var(--surface-color)] rounded flex-1"></div>
        ))}
    </div>
);

export const SkeletonTable = ({ rows = 5, columns = 5 }) => (
    <div className="w-full">
        {Array.from({ length: rows }).map((_, i) => (
            <SkeletonRow key={i} columns={columns} />
        ))}
    </div>
);

export const SkeletonCard = () => (
    <div className="p-6 rounded-xl border border-[var(--border-color)] bg-[var(--surface-color)] animate-pulse">
        <div className="h-5 w-1/3 bg-[var(--border-color)] rounded mb-4"></div>
        <div className="h-10 w-1/2 bg-[var(--border-color)] rounded"></div>
    </div>
);
