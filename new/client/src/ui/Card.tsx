import React from "react";
import { cn } from "./cn";

export interface CardProps extends React.HTMLAttributes<HTMLElement> {
  as?: React.ElementType;
}

export const Card: React.FC<CardProps> = ({ className, as: Comp = "section", ...props }) => (
  <Comp
    className={cn("rounded-lg border border-border bg-surface p-5 shadow-card", className)}
    {...props}
  />
);

export interface CardHeaderProps {
  title: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}

export const CardHeader: React.FC<CardHeaderProps> = ({ title, description, actions, className }) => (
  <div className={cn("mb-4 flex flex-wrap items-start justify-between gap-3", className)}>
    <div className="min-w-0">
      <h2 className="text-lg font-semibold text-text">{title}</h2>
      {description && <p className="mt-0.5 text-sm text-text-secondary">{description}</p>}
    </div>
    {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
  </div>
);
