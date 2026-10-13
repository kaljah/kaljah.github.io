import React, { createContext, useContext, useState, useCallback, useMemo } from "react";
import "./Toast.css";
import { CircleCheckBig, CircleX, Info, TriangleAlert } from "lucide-react";
import { t } from "../i18n";

export type ToastType = "info" | "success" | "error" | "warning";

export interface ToastItem {
  id: number;
  message: React.ReactNode;
  type: ToastType;
  duration: number;
}

export interface ToastContextType {
  success: (message: React.ReactNode, duration?: number) => number;
  error: (message: React.ReactNode, duration?: number) => number;
  warning: (message: React.ReactNode, duration?: number) => number;
  info: (message: React.ReactNode, duration?: number) => number;
  show: (message: React.ReactNode, type?: ToastType, duration?: number) => number;
  removeToast: (id: number) => void;
  addToast: (message: React.ReactNode, type?: ToastType, duration?: number) => number;
}

const noopToast: ToastContextType = {
  success: () => 0,
  error: () => 0,
  warning: () => 0,
  info: () => 0,
  show: () => 0,
  removeToast: () => {},
  addToast: () => 0,
};

const ToastContext = createContext<ToastContextType | null>(null);

export const useToast = (): ToastContextType => {
  const context = useContext(ToastContext);
  return context || noopToast;
};

export interface ToastProviderProps {
  children: React.ReactNode;
}

export const ToastProvider: React.FC<ToastProviderProps> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const removeToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const addToast = useCallback((message: React.ReactNode, type: ToastType = "info", duration = 3000) => {
    const id = Date.now() + Math.random();
    const toast: ToastItem = { id, message, type, duration };

    setToasts((prev) => [...prev, toast]);

    if (duration > 0) {
      setTimeout(() => {
        removeToast(id);
      }, duration);
    }

    return id;
  }, [removeToast]);

  const success = useCallback(
    (message: React.ReactNode, duration?: number) => {
      return addToast(message, "success", duration);
    },
    [addToast],
  );

  const error = useCallback(
    (message: React.ReactNode, duration?: number) => {
      return addToast(message, "error", duration);
    },
    [addToast],
  );

  const warning = useCallback(
    (message: React.ReactNode, duration?: number) => {
      return addToast(message, "warning", duration);
    },
    [addToast],
  );

  const info = useCallback(
    (message: React.ReactNode, duration?: number) => {
      return addToast(message, "info", duration);
    },
    [addToast],
  );

  const show = useCallback(
    (message: React.ReactNode, type: ToastType = "info", duration = 3000) => {
      if (type === "success") return success(message, duration);
      if (type === "error") return error(message, duration);
      if (type === "warning") return warning(message, duration);
      return info(message, duration);
    },
    [success, error, warning, info],
  );

  const contextValue = useMemo(
    () => ({ success, error, warning, info, show, removeToast, addToast }),
    [success, error, warning, info, show, removeToast, addToast],
  );

  return (
    <ToastContext.Provider value={contextValue}>
      {children}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </ToastContext.Provider>
  );
};

const ToastContainer: React.FC<{ toasts: ToastItem[]; onRemove: (id: number) => void }> = ({
  toasts,
  onRemove,
}) => {
  return (
    <div className="toast-container" role="region" aria-label={t("Notifications")} aria-live="polite">
      {toasts.map((toast) => (
        <Toast key={toast.id} toast={toast} onRemove={onRemove} />
      ))}
    </div>
  );
};

const Toast: React.FC<{ toast: ToastItem; onRemove: (id: number) => void }> = ({ toast, onRemove }) => {
  const getIcon = () => {
    switch (toast.type) {
      case "success":
        return <CircleCheckBig size={20} aria-hidden="true" />;
      case "error":
        return <CircleX size={20} aria-hidden="true" />;
      case "warning":
        return <TriangleAlert size={20} aria-hidden="true" />;
      default:
        return <Info size={20} aria-hidden="true" />;
    }
  };

  return (
    <div className={`toast toast-${toast.type}`} role={toast.type === "error" ? "alert" : "status"}>
      <div className="toast-icon [flex-shrink:0] [width:24px] [height:24px] [display:flex] [align-items:center] [justify-content:center]">
        {getIcon()}
      </div>
      <div className="[flex:1] [font-size:var(--text-base)] [color:var(--text-primary)] [line-height:1.4]">
        {toast.message}
      </div>
      <button className="toast-close" onClick={() => onRemove(toast.id)} aria-label={t("Dismiss notification")}>
        ×
      </button>
    </div>
  );
};

export default ToastProvider;
