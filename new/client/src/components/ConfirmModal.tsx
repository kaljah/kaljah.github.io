import React from "react";
import { ConfirmDialog, type ConfirmDialogProps } from "../ui/Dialog";

export interface ConfirmModalProps extends Omit<ConfirmDialogProps, "open"> {
  isOpen: boolean;
}

// Adapter: keeps the legacy props while rendering the new ConfirmDialog.
const ConfirmModal: React.FC<ConfirmModalProps> = ({ isOpen, ...props }) => (
  <ConfirmDialog open={Boolean(isOpen)} {...props} />
);

export default ConfirmModal;
