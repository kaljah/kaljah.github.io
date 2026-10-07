import React from "react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { type LucideIcon } from "lucide-react";
import { cn } from "./cn";

export const Menu = DropdownMenu.Root;
export const MenuTrigger = DropdownMenu.Trigger;

export interface MenuContentProps extends React.ComponentPropsWithoutRef<typeof DropdownMenu.Content> {
  className?: string;
  align?: "start" | "center" | "end";
  sideOffset?: number;
}

export const MenuContent: React.FC<MenuContentProps> = ({
  className,
  align = "end",
  sideOffset = 6,
  ...props
}) => (
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

export interface MenuItemProps extends React.ComponentPropsWithoutRef<typeof DropdownMenu.Item> {
  icon?: LucideIcon | React.ComponentType<{ className?: string; "aria-hidden"?: string | boolean }>;
  danger?: boolean;
}

export const MenuItem: React.FC<MenuItemProps> = ({
  className,
  icon: Icon,
  danger = false,
  children,
  ...props
}) => (
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

export interface MenuLabelProps extends React.ComponentPropsWithoutRef<typeof DropdownMenu.Label> {}

export const MenuLabel: React.FC<MenuLabelProps> = ({ className, ...props }) => (
  <DropdownMenu.Label
    className={cn("px-3 py-1.5 text-xs font-medium uppercase tracking-wide text-text-secondary", className)}
    {...props}
  />
);

export interface MenuSeparatorProps extends React.ComponentPropsWithoutRef<typeof DropdownMenu.Separator> {}

export const MenuSeparator: React.FC<MenuSeparatorProps> = ({ className, ...props }) => (
  <DropdownMenu.Separator className={cn("my-1 h-px bg-border", className)} {...props} />
);
