import React, { useState, useRef, useEffect } from "react";
import "./CustomDropdown.css";

const CustomDropdown = ({
  options = [],
  value,
  onChange,
  placeholder = "Select...",
  renderOption,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const wrapperRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const selectedOption = options.find((opt) => opt.value === value);

  // Determine what to display in the closed dropdown
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
    <div className="custom-dropdown" ref={wrapperRef}>
      <div className="dropdown-selected" onClick={() => setIsOpen(!isOpen)}>
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
      {isOpen && (
        <div className="dropdown-options">
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
        </div>
      )}
    </div>
  );
};

export default CustomDropdown;
