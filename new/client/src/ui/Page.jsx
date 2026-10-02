import React from "react";
import { cn } from "./cn";

/** Standard page container: max width, padding, vertical rhythm. */
export const Page = ({ className, ...props }) => (
  <div className={cn("mx-auto flex w-full max-w-[1600px] flex-col gap-6 p-4 sm:p-6", className)} {...props} />
);

/** Eyebrow, title, description, actions and an optional tabs slot. The title is the only h1 on a page. */
export const PageHeader = ({ eyebrow, title, description, actions, tabs, className }) => (
  <header className={cn("flex flex-col gap-4", className)}>
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div className="min-w-0">
        {eyebrow && (
          <p className="mb-1 text-xs font-medium uppercase tracking-wide text-text-secondary">{eyebrow}</p>
        )}
        <h1 className="text-xl font-bold text-text">{title}</h1>
        {description && <p className="mt-1 max-w-3xl text-base text-text-secondary">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
    {tabs}
  </header>
);
