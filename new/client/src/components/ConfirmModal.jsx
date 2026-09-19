import React from "react";
import Modal from "./Modal";

const ConfirmModal = ({
  isOpen,
  title = "Confirm Action",
  message = "Are you sure you want to proceed?",
  confirmLabel = "Confirm",
  confirmVariant = "danger",
  cancelLabel = "Cancel",
  onConfirm,
  onCancel,
  loading = false,
}) => {
  if (!isOpen) return null;

  return (
    <Modal isOpen={isOpen} onClose={onCancel} title={title} maxWidth="450px">
      <div style={{ padding: "8px 0 4px 0" }}>
        <p
          style={{
            margin: "0 0 24px 0",
            color: "var(--text-secondary, #475569)",
            fontSize: "0.9375rem",
            lineHeight: "1.5",
          }}
        >
          {message}
        </p>
        <div
          style={{
            display: "flex",
            justifyContent: "flex-end",
            gap: "12px",
          }}
        >
          <button
            type="button"
            className="btn-secondary-unified"
            onClick={onCancel}
            disabled={loading}
            style={{
              padding: "8px 18px",
              borderRadius: "8px",
              fontWeight: 500,
              cursor: loading ? "not-allowed" : "pointer",
            }}
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={loading}
            style={{
              padding: "8px 20px",
              borderRadius: "8px",
              border: "none",
              background:
                confirmVariant === "danger"
                  ? "#ef4444"
                  : confirmVariant === "primary"
                  ? "var(--primary-color, #ff6600)"
                  : "#ca8a04",
              color: "#ffffff",
              fontWeight: 600,
              fontSize: "0.875rem",
              cursor: loading ? "not-allowed" : "pointer",
              boxShadow:
                confirmVariant === "danger"
                  ? "0 2px 6px rgba(239, 68, 68, 0.35)"
                  : "0 2px 6px rgba(255, 102, 0, 0.35)",
              transition: "all 0.15s ease",
            }}
          >
            {loading ? "Processing..." : confirmLabel}
          </button>
        </div>
      </div>
    </Modal>
  );
};

export default ConfirmModal;
