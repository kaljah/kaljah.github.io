import React from "react";
import { cn } from "./cn";

export const Skeleton = ({ className, ...props }) => (
  <div aria-hidden="true" className={cn("animate-pulse rounded-sm bg-ink-200", className)} {...props} />
);

/** Page-level loading placeholder: header plus a row of cards. */
export const PageSkeleton = () => (
  <div role="status" aria-label="Loading" className="flex flex-col gap-6 p-4 sm:p-6">
    <Skeleton className="h-8 w-64" />
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {[0, 1, 2, 3].map((i) => (
        <Skeleton key={i} className="h-28 rounded-lg" />
      ))}
    </div>
    <Skeleton className="h-72 rounded-lg" />
  </div>
);
