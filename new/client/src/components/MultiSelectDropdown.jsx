import React, { useState, useRef, useEffect, useCallback } from "react";
import { activateOnKey } from "../utils/a11yKeys";
import { createPortal } from "react-dom";
import "./CustomDropdown.css";
import { ChevronDown } from "lucide-react";

const MultiSelectDropdown = ({
  options = [],
  selectedValues = [],
  onChange,
  label = "Select...",
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [position, setPosition] = useState(null);
  const dropdownRef = useRef(null);
  const portalRef = useRef(null);

  const updatePosition = useCallback(() => {
    if (!dropdownRef.current) return;
    const rect = dropdownRef.current.getBoundingClientRect();
    const spaceBelow = window.innerHeight - rect.bottom;
    const minMenuWidth = Math.max(rect.width, 200);
    const showAbove = spaceBelow < 240 && rect.top > 240;

    let left = rect.left;
    if (left + minMenuWidth > window.innerWidth - 10) {
      left = Math.max(10, window.innerWidth - minMenuWidth - 10);
    }
    if (left < 10) left = 10;

    const maxHeight = showAbove
      ? Math.min(280, rect.top - 16)
      : Math.min(280, spaceBelow - 16);

    setPosition({
      top: showAbove ? rect.top - 4 : rect.bottom + 4,
      left,
      width: minMenuWidth,
      maxHeight,
      showAbove,
    });
  }, []);

  const handleToggle = () => {
    if (!isOpen) {
      updatePosition();
      setIsOpen(true);
    } else {
      setIsOpen(false);
    }
  };

  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (event) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target) &&
        portalRef.current &&
        !portalRef.current.contains(event.target)
      ) {
        setIsOpen(false);
      }
    };

    const handleScrollOrResize = () => {
      if (dropdownRef.current) {
        const rect = dropdownRef.current.getBoundingClientRect();
        if (rect.bottom < 0 || rect.top > window.innerHeight) {
          setIsOpen(false);
        } else {
          updatePosition();
        }
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    window.addEventListener("scroll", handleScrollOrResize, true);
    window.addEventListener("resize", handleScrollOrResize);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      window.removeEventListener("scroll", handleScrollOrResize, true);
      window.removeEventListener("resize", handleScrollOrResize);
    };
  }, [isOpen, updatePosition]);

  const toggleOption = (value) => {
    const newSelected = selectedValues.includes(value)
      ? selectedValues.filter((v) => v !== value)
      : [...selectedValues, value];
    onChange(newSelected);
  };

  const handleSelectAll = () => {
    if (selectedValues.length === options.length) {
      onChange([]);
    } else {
      onChange(options.map((o) => o.value));
    }
  };

  return (
    <div
      className={`custom-dropdown ${isOpen ? "open" : ""}`}
      ref={dropdownRef}
      style={{ width: "100%", position: "relative" }}
    >
      <div
        className="dropdown-selected"
        onClick={handleToggle}
        role="button"
        tabIndex={0}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-label={label}
        onKeyDown={(e) => {
          // BUG-107: keyboard access to the multi-select trigger
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            handleToggle();
          } else if (e.key === "Escape" && isOpen) {
            e.preventDefault();
            handleToggle();
          }
        }}
        style={{
          padding: "10px 12px",
          border: "1px solid var(--border-color)",
          borderRadius: "6px",
          background: "var(--bg-card)",
          color: "var(--text-primary)",
          cursor: "pointer",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          minHeight: "42px",
        }}
      >
        <span
          className="whitespace-nowrap! overflow-hidden! [text-overflow:ellipsis]!"
        >
          {selectedValues.length === 0
            ? label
            : selectedValues.length === options.length
              ? "All Selected"
              : `${selectedValues.length} Selected`}
        </span>
        <ChevronDown size={14} aria-hidden="true" />
      </div>

      {isOpen &&
        position &&
        createPortal(
          <div
            ref={portalRef}
            className="dropdown-options dropdown-portal"
            style={{
              position: "fixed",
              top: position.showAbove ? "auto" : `${position.top}px`,
              bottom: position.showAbove
                ? `${window.innerHeight - position.top}px`
                : "auto",
              left: `${position.left}px`,
              width: `${position.width}px`,
              maxHeight: `${position.maxHeight}px`,
              zIndex: 999999,
              pointerEvents: "auto",
              overflowY: "auto",
            }}
          >
            <div role="button" tabIndex={0} onKeyDown={activateOnKey}
              className="dropdown-option"
              onClick={handleSelectAll}
              style={{
                padding: "8px 12px",
                borderBottom: "1px solid var(--border-color)",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              {selectedValues.length === options.length
                ? "Deselect All"
                : "Select All"}
            </div>
            {options.map((opt) => (
              <div role="button" tabIndex={0} onKeyDown={activateOnKey}
                key={opt.value}
                className="dropdown-option"
                onClick={() => toggleOption(opt.value)}
                style={{
                  padding: "8px 12px",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  background: selectedValues.includes(opt.value)
                    ? "var(--bg-hover)"
                    : "transparent",
                }}
              >
                <input
                  type="checkbox"
                  checked={selectedValues.includes(opt.value)}
                  readOnly
                  className="cursor-pointer!"
                />
                <span>
                  {opt.label}
                  {opt.subLabel && (
                    <span
                      className="text-[length:0.72rem]! text-[color:#475569]! ml-[4px]! font-medium!"
                    >
                      {" "}
                      - {opt.subLabel}
                    </span>
                  )}
                </span>
              </div>
            ))}
          </div>,
          document.body
        )}
    </div>
  );
};

export default MultiSelectDropdown;
