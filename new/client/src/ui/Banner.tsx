import React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { AlertTriangle, CheckCircle2, Info, XCircle, type LucideIcon } from "lucide-react";
import { cn } from "./cn";

const banner = cva("flex items-start gap-3 rounded-md border px-4 py-3 text-base", {
  variants: {
    tone: {
      info: "border-blue-500/30 bg-info-bg text-info-fg",
      success: "border-green-500/30 bg-success-bg text-success-fg",
      warning: "border-amber-500/30 bg-warning-bg text-warning-fg",
      danger: "border-red-500/30 bg-danger-bg text-danger-fg",
    },
  },
  defaultVariants: { tone: "info" },
});

export type BannerTone = "info" | "success" | "warning" | "danger";

const ICONS: Record<BannerTone, LucideIcon> = {
  info: Info,
  success: CheckCircle2,
  warning: AlertTriangle,
  danger: XCircle,
};

export interface BannerProps
  extends Omit<React.HTMLAttributes<HTMLDivElement>, "title">,
    VariantProps<typeof banner> {
  tone?: BannerTone;
  title?: React.ReactNode;
  actions?: React.ReactNode;
  children?: React.ReactNode;
}

/** Inline message. Danger banners use role=alert; the rest use role=status. */
export const Banner: React.FC<BannerProps> = ({
  tone = "info",
  title,
  actions,
  className,
  children,
  ...props
}) => {
  const Icon = ICONS[tone];
  return (
    <div
      role={tone === "danger" ? "alert" : "status"}
      className={cn(banner({ tone }), className)}
      {...props}
    >
      <Icon className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      <div className="min-w-0 flex-1">
        {title && <p className="font-semibold">{title}</p>}
        {children && <div className={title ? "mt-0.5" : undefined}>{children}</div>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
};
