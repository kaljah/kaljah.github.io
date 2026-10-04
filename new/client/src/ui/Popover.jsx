import React from "react";
import * as RadixPopover from "@radix-ui/react-popover";
import { cn } from "./cn";

export const Popover = RadixPopover.Root;
export const PopoverTrigger = RadixPopover.Trigger;

export const PopoverContent = ({ className, align = "end", sideOffset = 8, ...props }) => (
  <RadixPopover.Portal>
    <RadixPopover.Content
      align={align}
      sideOffset={sideOffset}
      className={cn("z-(--z-popover) rounded-lg border border-border bg-surface shadow-overlay", className)}
      {...props}
    />
  </RadixPopover.Portal>
);
