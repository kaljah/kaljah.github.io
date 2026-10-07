// Shared layout pieces for the Scope 1 entry form: one arrangement for every process type
// (numbered sections, responsive field grids, collapsible advanced options).
import React, { useState } from "react";
import { ChevronDown } from "lucide-react";
import "./ui.css";

export interface SectionProps {
  n: number | string;
  title: React.ReactNode;
  aside?: React.ReactNode;
  children: React.ReactNode;
}

export const Section: React.FC<SectionProps> = ({ n, title, aside, children }) => (
  <section className="s1-section [&+.s1-section]:[border-top:1px_solid_var(--s1-line)] [&+.s1-section]:[margin-top:20px] [&+.s1-section]:[padding-top:20px]">
    <header className="[display:flex] [align-items:center] [gap:10px] [margin-bottom:14px]">
      <span className="[width:24px] [height:24px] [border-radius:50%] [background:var(--color-primary)] [color:var(--color-white)] [font-size:var(--text-sm)] [font-weight:700] [display:inline-flex] [align-items:center] [justify-content:center] [flex:none]">
        {n}
      </span>
      <h3 className="[font-size:var(--text-md)] [font-weight:600] [color:var(--s1-ink)] [margin:0]">{title}</h3>
      {aside && <div className="[margin-left:auto]">{aside}</div>}
    </header>
    <div className="s1-section-body">{children}</div>
  </section>
);

export interface FieldGridProps {
  children: React.ReactNode;
  min?: number;
}

export const FieldGrid: React.FC<FieldGridProps> = ({ children, min = 200 }) => (
  <div className="s1-grid" style={{ "--s1-min": `${min}px` } as React.CSSProperties}>
    {children}
  </div>
);

export interface MoreOptionsProps {
  label?: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}

export const MoreOptions: React.FC<MoreOptionsProps> = ({
  label = "More options",
  defaultOpen = false,
  children,
}) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className={`[margin-top:16px] [&.open_.s1-more-chevron]:[transform:rotate(0deg)] ${open ? "open" : ""}`}>
      <button type="button" className="s1-more-toggle" aria-expanded={open} onClick={() => setOpen((o) => !o)}>
        <ChevronDown size={16} className="s1-more-chevron" />
        {label}
      </button>
      {open && (
        <div className="[margin-top:12px] [padding:16px] [background:var(--s1-soft)] [border:1px_solid_var(--s1-line)] [&&]:[border-radius:var(--radius-md)]">
          {children}
        </div>
      )}
    </div>
  );
};

export interface SegmentedOption {
  value: string;
  label: string;
  hint?: string;
}

export interface SegmentedProps {
  options: SegmentedOption[];
  value: string;
  onChange: (value: string) => void;
  ariaLabel?: string;
}

export const Segmented: React.FC<SegmentedProps> = ({ options, value, onChange, ariaLabel }) => (
  <div
    className="[display:inline-flex] [flex-wrap:wrap] [gap:4px] [padding:4px] [background:#f3f4f6] [border-radius:var(--radius-md)] [border:none]"
    role="radiogroup"
    aria-label={ariaLabel}
  >
    {options.map((o) => (
      <button
        key={o.value}
        type="button"
        role="radio"
        aria-checked={value === o.value}
        className={`s1-seg-btn ${value === o.value ? "active" : ""}`}
        onClick={() => onChange(o.value)}
        title={o.hint}
      >
        {o.label}
      </button>
    ))}
  </div>
);
