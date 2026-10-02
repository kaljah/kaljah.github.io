import React from "react";
import { cva } from "class-variance-authority";
import { Slot } from "@radix-ui/react-slot";
import { Loader2 } from "lucide-react";
import { cn } from "./cn";

export const buttonVariants = cva(
  "inline-flex shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-md font-semibold " +
    "transition-colors disabled:pointer-events-none disabled:opacity-50 cursor-pointer",
  {
    variants: {
      variant: {
        primary: "bg-primary text-on-primary hover:bg-primary-hover",
        secondary: "border border-border bg-surface text-text hover:bg-selected-bg",
        ghost: "text-text-secondary hover:bg-ink-100 hover:text-text",
        danger: "bg-danger-fg text-white hover:bg-red-600",
        link: "px-0 text-link underline-offset-4 hover:underline",
      },
      size: {
        sm: "h-8 px-3 text-sm",
        md: "h-10 px-4 text-base",
        lg: "h-11 px-5 text-md",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

/** Primary action button. asChild renders the child element (e.g. a router Link) with button styles. */
export const Button = React.forwardRef(function Button(
  { className, variant, size, loading = false, asChild = false, disabled, children, type = "button", ...props },
  ref,
) {
  const Comp = asChild ? Slot : "button";
  return (
    <Comp
      ref={ref}
      type={asChild ? undefined : type}
      className={cn(buttonVariants({ variant, size }), className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {asChild ? (
        children
      ) : (
        <>
          {loading && <Loader2 className="size-4 animate-spin" aria-hidden="true" />}
          {children}
        </>
      )}
    </Comp>
  );
});

/** Icon-only button. label becomes the accessible name (required). */
export const IconButton = React.forwardRef(function IconButton(
  { label, className, variant = "ghost", size = "md", children, ...props },
  ref,
) {
  if (import.meta.env.DEV && !label) console.warn("IconButton requires a label for accessibility.");
  const box = { sm: "size-8", md: "size-10", lg: "size-11" }[size];
  return (
    <Button
      ref={ref}
      variant={variant}
      aria-label={label}
      title={label}
      className={cn("px-0", box, className)}
      {...props}
    >
      {children}
    </Button>
  );
});
