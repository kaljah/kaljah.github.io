import React from "react";
import { ConfirmDialog, type ConfirmDialogProps } from "../ui/Dialog";

export interface ConfirmModalProps extends Omit<ConfirmDialogProps, "open"> {
  isOpen?: boolean;
  open?: boolean;
  description?: React.ReactNode;
  variant?: ConfirmDialogProps["confirmVariant"];
}

// Adapter: keeps legacy modal props while rendering the unified ConfirmDialog.
const ConfirmModal: React.FC<ConfirmModalProps> = ({
  isOpen,
  open,
  description,
  message,
  variant,
  confirmVariant,
  ...props
}) => (
  <ConfirmDialog
    open={Boolean(open ?? isOpen)}
    message={description ?? message}
    confirmVariant={variant ?? confirmVariant}
    {...props}
  />
);

export default ConfirmModal;
