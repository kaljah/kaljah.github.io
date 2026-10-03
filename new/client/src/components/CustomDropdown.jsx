import React, {
  useState,
  useRef,
  useEffect,
  useCallback,
  useId,
  useLayoutEffect,
} from "react";
import { createPortal } from "react-dom";
import "./CustomDropdown.css";

const CustomDropdown = ({
  options = [],
  value,
  onChange,
  placeholder = "Select...",
  renderOption,
  id,
  "aria-label": ariaLabel,
  "aria-labelledby": ariaLabelledBy,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [position, setPosition] = useState(null);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [autoLabelId, setAutoLabelId] = useState(null);
  const wrapperRef = useRef(null);
  const portalRef = useRef(null);
  const triggerRef = useRef(null);
  const reactId = useId();
  const baseId = id || `dd-${reactId.replace(/[^a-zA-Z0-9_-]/g, "")}`;
  const listboxId = `${baseId}-listbox`;
  const optionId = (idx) => `${baseId}-opt-${idx}`;

  // BUG-107: give the trigger an accessible name. Most call sites render
  // `<label>Region</label><CustomDropdown/>` inside the same group, so when no
  // explicit aria-label / aria-labelledby is passed, associate the nearest
  // preceding <label> sibling (or the group's first label) with the trigger.
  useLayoutEffect(() => {
    if (ariaLabel || ariaLabelledBy || !wrapperRef.current) return;
    let label = null;
    let el = wrapperRef.current.previousElementSibling;
    while (el && !label) {
      if (el.tagName === "LABEL") label = el;
      else label = el.querySelector?.("label") || null;
      el = el.previousElementSibling;
    }
    if (!label) {
      const parent = wrapperRef.current.parentElement;
      label = (parent && parent.querySelector(":scope > label")) || null;
    }
    if (!label) return;
    if (!label.id) label.id = `${baseId}-label`;
    // the label is found in the rendered DOM, so this runs after render by necessity
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setAutoLabelId(label.id);
  }, [ariaLabel, ariaLabelledBy, baseId]);

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

  const selectableIndexes = options
    .map((opt, idx) => (opt && !opt.isHeader ? idx : -1))
    .filter((idx) => idx >= 0);

  const openMenu = () => {
    updatePosition();
    const selectedIdx = options.findIndex(
      (opt) => opt && !opt.isHeader && opt.value === value,
    );
    setActiveIndex(
      selectedIdx >= 0 ? selectedIdx : (selectableIndexes[0] ?? -1),
    );
    setIsOpen(true);
  };

  const closeMenu = (restoreFocus = false) => {
    setIsOpen(false);
    setActiveIndex(-1);
    if (restoreFocus && triggerRef.current) triggerRef.current.focus();
  };

  const handleToggle = () => {
    if (!isOpen) {
      openMenu();
    } else {
      closeMenu();
    }
  };

  const moveActive = (delta) => {
    if (selectableIndexes.length === 0) return;
    const pos = selectableIndexes.indexOf(activeIndex);
    let next;
    if (delta === "first") next = 0;
    else if (delta === "last") next = selectableIndexes.length - 1;
    else if (pos < 0) next = delta > 0 ? 0 : selectableIndexes.length - 1;
    else
      next = Math.min(selectableIndexes.length - 1, Math.max(0, pos + delta));
    setActiveIndex(selectableIndexes[next]);
  };

  const handleKeyDown = (e) => {
    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        if (!isOpen) openMenu();
        else moveActive(1);
        break;
      case "ArrowUp":
        e.preventDefault();
        if (!isOpen) openMenu();
        else moveActive(-1);
        break;
      case "Home":
        if (isOpen) {
          e.preventDefault();
          moveActive("first");
        }
        break;
      case "End":
        if (isOpen) {
          e.preventDefault();
          moveActive("last");
        }
        break;
      case "Enter":
      case " ":
        e.preventDefault();
        if (!isOpen) {
          openMenu();
        } else if (
          activeIndex >= 0 &&
          options[activeIndex] &&
          !options[activeIndex].isHeader
        ) {
          handleSelect(options[activeIndex].value);
        } else {
          closeMenu();
        }
        break;
      case "Escape":
        if (isOpen) {
          e.preventDefault();
          e.stopPropagation();
          closeMenu(true);
        }
        break;
      case "Tab":
        if (isOpen) closeMenu();
        break;
      default:
        break;
    }
  };

  // Keep the keyboard-highlighted option visible while navigating.
  useEffect(() => {
    if (!isOpen || activeIndex < 0 || !portalRef.current) return;
    const el = portalRef.current.querySelector(
      `[id="${baseId}-opt-${activeIndex}"]`,
    );
    if (el && el.scrollIntoView) el.scrollIntoView({ block: "nearest" });
  }, [isOpen, activeIndex, baseId]);

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
          <span className="[font-size:var(--text-xs)]! [color:var(--text-secondary,_var(--color-ink-500))]! [font-weight:600]! [display:inline-block]! [margin-left:2px]!"> - {selectedOption.subLabel}</span>
        </div>
      );
    } else {
      displayContent = selectedOption.label;
    }
  }

  function handleSelect(optionValue) {
    onChange(optionValue);
    closeMenu(true);
  }

  return (
    <div className={`custom-dropdown ${isOpen ? "open" : ""}`} ref={wrapperRef}>
      <button
        type="button"
        ref={triggerRef}
        id={id}
        className="dropdown-selected"
        data-testid="select-trigger"
        onClick={handleToggle}
        onKeyDown={handleKeyDown}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-controls={isOpen ? listboxId : undefined}
        aria-activedescendant={
          isOpen && activeIndex >= 0 ? optionId(activeIndex) : undefined
        }
        aria-label={ariaLabel}
        aria-labelledby={
          ariaLabel ? undefined : ariaLabelledBy || autoLabelId || undefined
        }
      >
        <span className="[display:flex]! [align-items:center] [overflow:hidden]! [text-overflow:ellipsis]! [white-space:nowrap]">{displayContent}</span>
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
      </button>

      {isOpen &&
        position &&
        createPortal(
          <div
            ref={portalRef}
            id={listboxId}
            role="listbox"
            aria-label={ariaLabel}
            aria-labelledby={
              ariaLabel ? undefined : ariaLabelledBy || autoLabelId || undefined
            }
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
            }}
          >
            {options.map((option, idx) => {
              if (option.isHeader) {
                return (
                  <div
                    key={`header-${idx}`}
                    role="presentation"
                    className="dropdown-header"
                    style={{
                      padding: "5px 10px",
                      fontSize: "0.8rem",
                      fontWeight: 600,
                      color: "var(--color-link)",
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
                  id={optionId(idx)}
                  role="option"
                  aria-selected={value === option.value}
                  data-testid="select-option"
                  className={`dropdown-option ${value === option.value ? "selected" : ""} ${activeIndex === idx ? "active" : ""}`}
                  onClick={() => handleSelect(option.value)}
                  onMouseEnter={() => setActiveIndex(idx)}
                >
                  {renderOption ? (
                    renderOption(option)
                  ) : option.subLabel ? (
                    <div className="option-with-sub">
                      {option.label}{" "}
                      <span className="[font-size:var(--text-xs)]! [color:var(--text-secondary,_var(--color-ink-500))]! [font-weight:600]! [display:inline-block]! [margin-left:2px]!"> - {option.subLabel}</span>
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
