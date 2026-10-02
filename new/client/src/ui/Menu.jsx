import React from "react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { cn } from "./cn";

export const Menu = DropdownMenu.Root;
export const MenuTrigger = DropdownMenu.Trigger;

export const MenuContent = ({ className, align = "end", sideOffset = 6, ...props }) => (
  <DropdownMenu.Portal>
    <DropdownMenu.Content
      align={align}
      sideOffset={sideOffset}
      className={cn(
        "z-(--z-popover) min-w-48 rounded-md border border-border bg-surface p-1 shadow-overlay",
        className,
      )}
      {...props}
    />
  </DropdownMenu.Portal>
);

export const MenuItem = ({ className, icon: Icon, danger = false, children, ...props }) => (
  <DropdownMenu.Item
    className={cn(
      "flex cursor-pointer items-center gap-2 rounded-sm px-3 py-2 text-base outline-none",
      "data-highlighted:bg-ink-100 data-disabled:pointer-events-none data-disabled:opacity-50",
      danger ? "text-danger-fg" : "text-text",
      className,
    )}
    {...props}
  >
    {Icon && <Icon className="size-4 shrink-0 text-text-secondary" aria-hidden="true" />}
    {children}
  </DropdownMenu.Item>
);

export const MenuLabel = ({ className, ...props }) => (
  <DropdownMenu.Label
    className={cn("px-3 py-1.5 text-xs font-medium uppercase tracking-wide text-text-secondary", className)}
    {...props}
  />
);

export const MenuSeparator = ({ className }) => (
  <DropdownMenu.Separator className={cn("my-1 h-px bg-border", className)} />
);
