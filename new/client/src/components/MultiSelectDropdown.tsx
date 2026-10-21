import React, { useState, useRef, useEffect, useCallback } from "react";
import { activateOnKey } from "../utils/a11yKeys";
import { createPortal } from "react-dom";
import "./CustomDropdown.css";
import { ChevronDown } from "lucide-react";
import { t } from "../i18n";

export interface MultiSelectDropdownOption {
  value: string | number;
  label: React.ReactNode;
  subLabel?: string;
  [key: string]: unknown;
}

export interface MultiSelectDropdownProps {
  options?: MultiSelectDropdownOption[];
  selectedValues?: (string | number)[];
  onChange?: (values: any[]) => void;
  label?: string;
  placeholder?: string;
  allSelectedLabel?: string;
  disabled?: boolean;
}

interface DropdownPosition {
  top: number;
  left: number;
  width: number;
  maxHeight: number;
  showAbove: boolean;
}

const MultiSelectDropdown: React.FC<MultiSelectDropdownProps> = ({
  options = [],
  selectedValues = [],
  onChange,
  label = t("Select..."),
  placeholder,
  allSelectedLabel,
  disabled = false,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [position, setPosition] = useState<DropdownPosition | null>(null);
  const dropdownRef = useRef<HTMLDivElement | null>(null);
  const portalRef = useRef<HTMLDivElement | null>(null);

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
    if (disabled) return;
    if (!isOpen) {
      updatePosition();
      setIsOpen(true);
    } else {
      setIsOpen(false);
    }
  };

  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node | null;
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(target) &&
        portalRef.current &&
        !portalRef.current.contains(target)
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

  const isSelected = (value: string | number) =>
    selectedValues.some((v) => String(v) === String(value));

  const toggleOption = (value: string | number) => {
    const stringVal = String(value);
    const newSelected = isSelected(value)
      ? selectedValues.filter((v) => String(v) !== stringVal)
      : [...selectedValues, value];
    onChange?.(newSelected);
  };

  const handleSelectAll = () => {
    if (selectedValues.length === options.length) {
      onChange?.([]);
    } else {
      onChange?.(options.map((o) => o.value));
    }
  };

  const getDisplayText = () => {
    if (selectedValues.length === 0) {
      return placeholder || label || t("Select...");
    }
    if (options.length > 0 && selectedValues.length === options.length) {
      return allSelectedLabel || label || t("All Selected");
    }
    if (selectedValues.length === 1) {
      const single = options.find((o) => String(o.value) === String(selectedValues[0]));
      return single ? single.label : `1 ${t("Selected")}`;
    }
    return `${selectedValues.length} ${t("Selected")}`;
  };

  return (
    <div
      className={`custom-dropdown ${isOpen ? "open" : ""}`}
      ref={dropdownRef}
    >
      <button
        type="button"
        disabled={disabled}
        className="dropdown-selected"
        onClick={handleToggle}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-label={placeholder || label}
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
      >
        <span className="[display:flex] [align-items:center] [overflow:hidden] [text-overflow:ellipsis] [white-space:nowrap]">
          {getDisplayText()}
        </span>
        <ChevronDown size={14} aria-hidden="true" />
      </button>

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
            <div
              role="button"
              tabIndex={0}
              onKeyDown={activateOnKey}
              className="dropdown-option p-[8px_12px]! [border-bottom:1px_solid_var(--border-color)]! font-semibold! cursor-pointer!"
              onClick={handleSelectAll}
            >
              {selectedValues.length === options.length
                ? t("Deselect All")
                : t("Select All")}
            </div>
            {options.map((opt) => {
              const checked = isSelected(opt.value);
              return (
                <div
                  role="button"
                  tabIndex={0}
                  onKeyDown={activateOnKey}
                  key={String(opt.value)}
                  className="dropdown-option"
                  onClick={() => toggleOption(opt.value)}
                  style={{
                    padding: "8px 12px",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    background: checked ? "var(--bg-hover)" : "transparent",
                  }}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    readOnly
                    className="cursor-pointer!"
                  />
                  <span className="[display:flex] [align-items:center] [gap:4px] [min-width:0] [overflow:hidden] [text-overflow:ellipsis] [white-space:nowrap]">
                    <span className="font-medium!">{opt.label}</span>
                    {opt.subLabel && (
                      <span className="text-[length:0.75rem]! text-[color:var(--color-ink-600)]! opacity-80">
                        ({opt.subLabel})
                      </span>
                    )}
                  </span>
                </div>
              );
            })}
          </div>,
          document.body,
        )}
    </div>
  );
};

export default MultiSelectDropdown;
