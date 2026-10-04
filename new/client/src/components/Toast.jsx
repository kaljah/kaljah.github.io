import React, { createContext, useContext, useState, useCallback } from "react";
import "./Toast.css";
import { CircleCheckBig, CircleX, Info, TriangleAlert } from "lucide-react";

const ToastContext = createContext();

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within ToastProvider");
  }
  return context;
};

export const ToastProvider = ({ children }) => {
  const [toasts, setToasts] = useState([]);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const addToast = useCallback((message, type = "info", duration = 3000) => {
    const id = Date.now() + Math.random();
    const toast = { id, message, type, duration };

    setToasts((prev) => [...prev, toast]);

    if (duration > 0) {
      setTimeout(() => {
        removeToast(id);
      }, duration);
    }

    return id;
  }, [removeToast]);

  const success = useCallback(
    (message, duration) => {
      return addToast(message, "success", duration);
    },
    [addToast],
  );

  const error = useCallback(
    (message, duration) => {
      return addToast(message, "error", duration);
    },
    [addToast],
  );

  const warning = useCallback(
    (message, duration) => {
      return addToast(message, "warning", duration);
    },
    [addToast],
  );

  const info = useCallback(
    (message, duration) => {
      return addToast(message, "info", duration);
    },
    [addToast],
  );

  const show = useCallback(
    (message, type = "info", duration = 3000) => {
      if (type === "success") return success(message, duration);
      if (type === "error") return error(message, duration);
      if (type === "warning") return warning(message, duration);
      return info(message, duration);
    },
    [success, error, warning, info],
  );

  return (
    <ToastContext.Provider
      value={{ success, error, warning, info, show, removeToast, addToast }}
    >
      {children}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </ToastContext.Provider>
  );
};

const ToastContainer = ({ toasts, onRemove }) => {
  return (
    <div className="toast-container" role="region" aria-label="Notifications" aria-live="polite">
      {toasts.map((toast) => (
        <Toast key={toast.id} toast={toast} onRemove={onRemove} />
      ))}
    </div>
  );
};

const Toast = ({ toast, onRemove }) => {
  const getIcon = () => {
    switch (toast.type) {
      case "success":
        return (
          <CircleCheckBig size={20} aria-hidden="true" />
        );
      case "error":
        return (
          <CircleX size={20} aria-hidden="true" />
        );
      case "warning":
        return (
          <TriangleAlert size={20} aria-hidden="true" />
        );
      default:
        return (
          <Info size={20} aria-hidden="true" />
        );
    }
  };

  return (
    <div className={`toast toast-${toast.type}`} role={toast.type === "error" ? "alert" : "status"}>
      <div className="toast-icon [flex-shrink:0] [width:24px] [height:24px] [display:flex] [align-items:center] [justify-content:center]">{getIcon()}</div>
      <div className="[flex:1] [font-size:var(--text-base)] [color:var(--text-primary)] [line-height:1.4]">{toast.message}</div>
      <button className="toast-close" onClick={() => onRemove(toast.id)} aria-label="Dismiss notification">
        ×
      </button>
    </div>
  );
};

export default ToastProvider;
