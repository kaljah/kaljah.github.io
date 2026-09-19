import React, { useEffect } from "react";
import { X } from "lucide-react";
import "./Drawer.css";

const Drawer = ({
  isOpen,
  onClose,
  title,
  subtitle,
  icon: Icon,
  iconColor = "#ff6600",
  iconBg = "rgba(255, 102, 0, 0.1)",
  children,
  footer,
  width = "560px",
}) => {
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = prevOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div className="drawer-backdrop" onClick={handleBackdropClick}>
      <div
        className="drawer-panel"
        style={{ width, maxWidth: "100vw" }}
        role="dialog"
        aria-modal="true"
      >
        <div className="drawer-header">
          <div className="drawer-header-left">
            {Icon && (
              <div
                className="drawer-icon-badge"
                style={{
                  background: iconBg,
                  color: iconColor,
                  border: `1px solid ${iconColor}33`,
                }}
              >
                <Icon size={20} />
              </div>
            )}
            <div className="drawer-title-group">
              <h3 className="drawer-title">{title}</h3>
              {subtitle && <p className="drawer-subtitle">{subtitle}</p>}
            </div>
          </div>
          <button
            type="button"
            className="drawer-close-btn"
            onClick={onClose}
            aria-label="Close drawer"
          >
            <X size={18} />
          </button>
        </div>

        <div className="drawer-body">{children}</div>

        {footer && <div className="drawer-footer">{footer}</div>}
      </div>
    </div>
  );
};

export default Drawer;
