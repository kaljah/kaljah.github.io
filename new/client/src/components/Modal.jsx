import React from "react";
import { Dialog } from "../ui/Dialog";
import "./Modal.css";

// Adapter: keeps the legacy props while rendering the accessible Radix-based Dialog
// (focus trap and return, Escape, scroll lock, aria-modal).
const Modal = ({ isOpen, onClose, title, children, maxWidth }) => (
  <Dialog
    open={Boolean(isOpen)}
    onOpenChange={(open) => !open && onClose?.()}
    title={title}
    maxWidth={maxWidth || "500px"}
  >
    {children}
  </Dialog>
);

export default Modal;
