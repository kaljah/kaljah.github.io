import React from "react";
import { ConfirmDialog } from "../ui/Dialog";

// Adapter: keeps the legacy props while rendering the new ConfirmDialog.
const ConfirmModal = ({ isOpen, ...props }) => <ConfirmDialog open={Boolean(isOpen)} {...props} />;

export default ConfirmModal;
