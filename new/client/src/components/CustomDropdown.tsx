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
import { ChevronDown } from "lucide-react";

export interface CustomDropdownOption {
  value: string | number;
  label: React.ReactNode;
  subLabel?: string;
  isHeader?: boolean;
  [key: string]: unknown;
}

export interface CustomDropdownProps {
  options?: CustomDropdownOption[];
  value?: string | number | null;
  onChange?: (value: any) => void;
  placeholder?: string;
  renderOption?: (option: CustomDropdownOption) => React.ReactNode;
  id?: string;
  disabled?: boolean;
  "aria-label"?: string;
  "aria-labelledby"?: string;
}

interface DropdownPosition {
  top: number;
  left: number;
  width: number;
  maxHeight: number;
  showAbove: boolean;
}

const CustomDropdown: React.FC<CustomDropdownProps> = ({
  options = [],
  value,
  onChange,
  placeholder = "Select...",
  renderOption,
  id,
  disabled = false,
  "aria-label": ariaLabel,
  "aria-labelledby": ariaLabelledBy,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [position, setPosition] = useState<DropdownPosition | null>(null);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [autoLabelId, setAutoLabelId] = useState<string | null>(null);
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const portalRef = useRef<HTMLDivElement | null>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const reactId = useId();
  const baseId = id || `dd-${reactId.replace(/[^a-zA-Z0-9_-]/g, "")}`;
  const listboxId = `${baseId}-listbox`;
  const optionId = (idx: number) => `${baseId}-opt-${idx}`;

  // BUG-107: give the trigger an accessible name. Most call sites render
  // `<label>Region</label><CustomDropdown/>` inside the same group, so when no
  // explicit aria-label / aria-labelledby is passed, associate the nearest
  // preceding <label> sibling (or the group's first label) with the trigger.
  useLayoutEffect(() => {
    if (ariaLabel || ariaLabelledBy || !wrapperRef.current) return;
    let label: HTMLLabelElement | null = null;
    let el: Element | null = wrapperRef.current.previousElementSibling;
    while (el && !label) {
      if (el.tagName === "LABEL") label = el as HTMLLabelElement;
      else label = (el.querySelector?.("label") as HTMLLabelElement | null) || null;
      el = el.previousElementSibling;
    }
    if (!label) {
      const parent = wrapperRef.current.parentElement;
      label = (parent && (parent.querySelector(":scope > label") as HTMLLabelElement | null)) || null;
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
    if (disabled) return;
    if (!isOpen) {
      openMenu();
    } else {
      closeMenu();
    }
  };

  const moveActive = (delta: number | "first" | "last") => {
    if (selectableIndexes.length === 0) return;
    const pos = selectableIndexes.indexOf(activeIndex);
    let next: number;
    if (delta === "first") next = 0;
    else if (delta === "last") next = selectableIndexes.length - 1;
    else if (pos < 0) next = delta > 0 ? 0 : selectableIndexes.length - 1;
    else
      next = Math.min(selectableIndexes.length - 1, Math.max(0, pos + delta));
    setActiveIndex(selectableIndexes[next]);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
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
    if (el && (el as HTMLElement).scrollIntoView) (el as HTMLElement).scrollIntoView({ block: "nearest" });
  }, [isOpen, activeIndex, baseId]);

  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node | null;
      if (
        wrapperRef.current &&
        !wrapperRef.current.contains(target) &&
        portalRef.current &&
        !portalRef.current.contains(target)
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

  let displayContent: React.ReactNode = placeholder;
  if (selectedOption) {
    if (renderOption) {
      displayContent = renderOption(selectedOption);
    } else if (selectedOption.subLabel) {
      displayContent = (
        <div className="[display:flex] [align-items:center] [gap:2px]">
          {selectedOption.label}{" "}
          <span className="[font-size:var(--text-xs)]! [color:var(--text-secondary,_var(--color-ink-500))]! [font-weight:600]! [display:inline-block] [margin-left:2px]"> - {selectedOption.subLabel}</span>
        </div>
      );
    } else {
      displayContent = selectedOption.label;
    }
  }

  function handleSelect(optionValue: any) {
    onChange?.(optionValue);
    closeMenu(true);
  }

  return (
    <div className={`custom-dropdown ${isOpen ? "open" : ""}`} ref={wrapperRef}>
      <button
        type="button"
        ref={triggerRef}
        id={id}
        disabled={disabled}
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
        <span className="[display:flex] [align-items:center] [overflow:hidden] [text-overflow:ellipsis] [white-space:nowrap]">{displayContent}</span>
        <ChevronDown size={14} aria-hidden="true" />
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
                    className="dropdown-header p-[5px_10px]! text-[length:0.8rem]! font-semibold! text-[color:var(--color-link)]! uppercase! bg-[color:rgba(255,255,255,0.02)]! [pointer-events:none]!"
                  >
                    {option.label}
                  </div>
                );
              }
              return (
                <div
                  key={String(option.value)}
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
                    <div className="[display:flex] [align-items:center] [gap:2px]">
                      {option.label}{" "}
                      <span className="[font-size:var(--text-xs)]! [color:var(--text-secondary,_var(--color-ink-500))]! [font-weight:600]! [display:inline-block] [margin-left:2px]"> - {option.subLabel}</span>
                    </div>
                  ) : (
                    option.label
                  )}
                </div>
              );
            })}
          </div>,
          document.body,
        )}
    </div>
  );
};

export default CustomDropdown;
