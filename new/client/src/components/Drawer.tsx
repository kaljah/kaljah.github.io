import React from "react";
import { Sheet, type SheetProps } from "../ui/Dialog";

export interface DrawerProps {
  isOpen: boolean;
  onClose?: () => void;
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  icon?: SheetProps["icon"];
  iconColor?: string;
  iconBg?: string;
  children?: React.ReactNode;
  footer?: React.ReactNode;
  width?: string | number;
}

// Adapter: keeps the legacy props (iconColor/iconBg are ignored; the Sheet uses the brand tint).
const Drawer: React.FC<DrawerProps> = ({
  isOpen,
  onClose,
  title,
  subtitle,
  icon,
  children,
  footer,
  width = "560px",
}) => (
  <Sheet
    open={Boolean(isOpen)}
    onOpenChange={(open) => !open && onClose?.()}
    title={title}
    description={subtitle}
    icon={icon}
    footer={footer}
    width={width}
  >
    {children}
  </Sheet>
);

export default Drawer;
