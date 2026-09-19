import React, { useState, useRef, useEffect, useCallback } from "react";
import { createPortal } from "react-dom";
import "./CustomDropdown.css";

const CustomDropdown = ({
  options = [],
  value,
  onChange,
  placeholder = "Select...",
  renderOption,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [position, setPosition] = useState(null);
  const wrapperRef = useRef(null);
  const portalRef = useRef(null);

  const updatePosition = useCallback(() => {
    if (!wrapperRef.current) return;
    const rect = wrapperRef.current.getBoundingClientRect();
    const spaceBelow = window.innerHeight - rect.bottom;
    const minMenuWidth = Math.max(rect.width, 150);
    const showAbove = spaceBelow < 220 && rect.top > 220;

    // Constrain horizontal position within viewport boundaries
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
        wrapperRef.current &&
        !wrapperRef.current.contains(event.target) &&
        portalRef.current &&
        !portalRef.current.contains(event.target)
      ) {
        setIsOpen(false);
      }
    };

    const handleScrollOrResize = () => {
      if (wrapperRef.current) {
        const rect = wrapperRef.current.getBoundingClientRect();
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

  const selectedOption = options.find((opt) => opt.value === value);

  let displayContent = placeholder;
  if (selectedOption) {
    if (renderOption) {
      displayContent = renderOption(selectedOption);
    } else if (selectedOption.subLabel) {
      displayContent = (
        <div className="selected-with-sub">
          {selectedOption.label}{" "}
          <span className="sub-label"> - {selectedOption.subLabel}</span>
        </div>
      );
    } else {
      displayContent = selectedOption.label;
    }
  }

  const handleSelect = (optionValue) => {
    onChange(optionValue);
    setIsOpen(false);
  };

  return (
    <div className={`custom-dropdown ${isOpen ? "open" : ""}`} ref={wrapperRef}>
      <div className="dropdown-selected" onClick={handleToggle}>
        <span className="display-text">{displayContent}</span>
        <svg
          width="10"
          height="10"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
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
            }}
          >
            {options.map((option, idx) => {
              if (option.isHeader) {
                return (
                  <div
                    key={`header-${idx}`}
                    className="dropdown-header"
                    style={{
                      padding: "5px 10px",
                      fontSize: "0.8rem",
                      fontWeight: 600,
                      color: "var(--accent-color)",
                      textTransform: "uppercase",
                      background: "rgba(255,255,255,0.02)",
                      pointerEvents: "none",
                    }}
                  >
                    {option.label}
                  </div>
                );
              }
              return (
                <div
                  key={option.value}
                  className={`dropdown-option ${value === option.value ? "selected" : ""}`}
                  onClick={() => handleSelect(option.value)}
                >
                  {renderOption ? (
                    renderOption(option)
                  ) : option.subLabel ? (
                    <div className="option-with-sub">
                      {option.label}{" "}
                      <span className="sub-label"> - {option.subLabel}</span>
                    </div>
                  ) : (
                    option.label
                  )}
                </div>
              );
            })}
          </div>,
          document.body
        )}
    </div>
  );
};

export default CustomDropdown;
