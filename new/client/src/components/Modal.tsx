import React, { useEffect } from "react";
import { Dialog } from "../ui/Dialog";
import "./Modal.css";

export interface ModalProps {
  isOpen?: boolean;
  onClose?: () => void;
  title: React.ReactNode;
  children?: React.ReactNode;
  maxWidth?: string | number;
}

// Adapter: keeps the legacy props while rendering the accessible Radix-based Dialog
// (focus trap and return, Escape, scroll lock, aria-modal).
const Modal: React.FC<ModalProps> = ({ isOpen = true, onClose, title, children, maxWidth }) => {
  useEffect(() => {
    if (!isOpen || !onClose) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  return (
    <Dialog
      open={Boolean(isOpen)}
      onOpenChange={(open) => !open && onClose?.()}
      title={title}
      maxWidth={maxWidth || "500px"}
    >
      {children}
    </Dialog>
  );
};

export default Modal;
