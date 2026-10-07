import React from "react";
import { type LucideIcon } from "lucide-react";
import { cn } from "./cn";

export interface EmptyStateProps {
  icon?: LucideIcon | React.ComponentType<{ className?: string; "aria-hidden"?: string | boolean }>;
  title: React.ReactNode;
  description?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({ icon: Icon, title, description, action, className }) => (
  <div className={cn("flex flex-col items-center gap-2 px-6 py-12 text-center", className)}>
    {Icon && <Icon className="size-8 text-ink-400" aria-hidden="true" />}
    <p className="text-md font-semibold text-text">{title}</p>
    {description && <p className="max-w-md text-base text-text-secondary">{description}</p>}
    {action && <div className="mt-2">{action}</div>}
  </div>
);
