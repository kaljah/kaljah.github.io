// Shared layout pieces for the Scope 1 entry form: one arrangement for every process type
// (numbered sections, responsive field grids, collapsible advanced options).
import React, { useState } from "react";
import { ChevronDown } from "lucide-react";
import "./ui.css";

export const Section = ({ n, title, aside, children }) => (
  <section className="s1-section">
    <header className="[display:flex]! [align-items:center] [gap:10px] [margin-bottom:14px]!">
      <span className="[width:24px]! [height:24px]! [border-radius:50%]! [background:var(--color-primary)]! [color:var(--color-white)]! [font-size:var(--text-sm)]! [font-weight:700]! [display:inline-flex]! [align-items:center] [justify-content:center] [flex:none]">{n}</span>
      <h3 className="[font-size:var(--text-md)]! [font-weight:600]! [color:var(--s1-ink)]! [margin:0]!">{title}</h3>
      {aside && <div className="[margin-left:auto]!">{aside}</div>}
    </header>
    <div className="s1-section-body">{children}</div>
  </section>
);

export const FieldGrid = ({ children, min = 200 }) => (
  <div className="[display:grid]! [grid-template-columns:repeat(auto-fit,_minmax(var(--s1-min,_200px),_1fr))] [gap:14px_16px] [align-items:end] max-[600px]:[grid-template-columns:1fr_1fr]" style={{ "--s1-min": `${min}px` }}>
    {children}
  </div>
);

export const MoreOptions = ({ label = "More options", defaultOpen = false, children }) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className={`s1-more ${open ? "open" : ""}`}>
      <button type="button" className="[display:inline-flex]! [align-items:center] [gap:6px] [background:none]! [border:none]! [padding:4px_0]! [font-size:var(--text-sm)]! [font-weight:600]! [color:var(--s1-muted)]! [cursor:pointer] hover:[color:var(--s1-ink)]!" aria-expanded={open} onClick={() => setOpen((o) => !o)}>
        <ChevronDown size={16} className="s1-more-chevron" />
        {label}
      </button>
      {open && <div className="[margin-top:12px]! [padding:16px]! [background:var(--s1-soft)]! [border:1px_solid_var(--s1-line)]! [border-radius:var(--radius-md)]!">{children}</div>}
    </div>
  );
};

export const Segmented = ({ options, value, onChange, ariaLabel }) => (
  <div className="[display:inline-flex]! [flex-wrap:wrap] [gap:4px] [padding:4px]! [background:#f3f4f6]! [border-radius:var(--radius-md)]! [border:none]!" role="radiogroup" aria-label={ariaLabel}>
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
