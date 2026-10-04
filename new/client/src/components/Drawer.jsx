import React from "react";
import { Sheet } from "../ui/Dialog";

// Adapter: keeps the legacy props (iconColor/iconBg are ignored; the Sheet uses the brand tint).
const Drawer = ({ isOpen, onClose, title, subtitle, icon, children, footer, width = "560px" }) => (
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
