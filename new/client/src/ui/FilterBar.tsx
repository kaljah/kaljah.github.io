import React from "react";
import { RotateCcw } from "lucide-react";
import { Button } from "./Button";
import { cn } from "./cn";
import { t } from "../i18n";

export interface FilterBarProps {
  children?: React.ReactNode;
  activeCount?: number;
  onReset?: () => void;
  actions?: React.ReactNode;
  className?: string;
}

/** Row of filters with an active count and Reset. children are the controls; actions sit on the right. */
export const FilterBar: React.FC<FilterBarProps> = ({
  children,
  activeCount = 0,
  onReset,
  actions,
  className,
}) => (
  <div
    role="group"
    aria-label={t("Filters")}
    className={cn("flex flex-wrap items-center justify-between gap-x-4 gap-y-2", className)}
  >
    <div className="flex flex-wrap items-center gap-2">
      {children}
      {activeCount > 0 && onReset && (
        <Button variant="ghost" size="sm" onClick={onReset}>
          <RotateCcw className="size-3.5" aria-hidden="true" />
          {t("Reset (")}{activeCount})
        </Button>
      )}
    </div>
    {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
  </div>
);
