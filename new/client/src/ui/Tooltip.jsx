import React from "react";
import * as RadixTooltip from "@radix-ui/react-tooltip";

export const TooltipProvider = ({ children }) => (
  <RadixTooltip.Provider delayDuration={300}>{children}</RadixTooltip.Provider>
);

/** Wraps a single focusable child. The tip is also shown on keyboard focus. */
export const Tooltip = ({ content, children, side = "top" }) => {
  // If children has a functional className (e.g. React Router NavLink),
  // Radix Trigger's Slot will stringify it and break styling.
  // Wrapping in a span prevents Radix Slot from stringifying the child's className.
  const hasFunctionClassName = typeof children?.props?.className === "function";
  const trigger = hasFunctionClassName ? (
    <span className="block w-full">{children}</span>
  ) : (
    children
  );

  return (
    <RadixTooltip.Root>
      <RadixTooltip.Trigger asChild>{trigger}</RadixTooltip.Trigger>
      <RadixTooltip.Portal>
        <RadixTooltip.Content
          side={side}
          sideOffset={6}
          className="z-(--z-popover) max-w-xs rounded-md bg-ink-900 px-2.5 py-1.5 text-xs text-white shadow-overlay"
        >
          {content}
        </RadixTooltip.Content>
      </RadixTooltip.Portal>
    </RadixTooltip.Root>
  );
};
