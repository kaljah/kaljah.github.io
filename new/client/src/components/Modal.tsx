import React from "react";
import { Dialog } from "../ui/Dialog";
import "./Modal.css";

export interface ModalProps {
  isOpen: boolean;
  onClose?: () => void;
  title: React.ReactNode;
  children?: React.ReactNode;
  maxWidth?: string | number;
}

// Adapter: keeps the legacy props while rendering the accessible Radix-based Dialog
// (focus trap and return, Escape, scroll lock, aria-modal).
const Modal: React.FC<ModalProps> = ({ isOpen, onClose, title, children, maxWidth }) => (
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
