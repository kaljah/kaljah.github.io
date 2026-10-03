import React from "react";
import { NativeSelect } from "../ui/NativeSelect";
import "./FormField.css";

// Text Input Field
export const TextField = ({
  label,
  value,
  onChange,
  type = "text",
  placeholder = "",
  required = false,
  disabled = false,
  error = "",
  helperText = "",
  min,
  max,
  step,
}) => {
  return (
    <div className="[display:flex]! [flex-direction:column] [gap:6px] [margin-bottom:16px]!">
      {label && (
        <label className="field-label">
          {label}
          {required && <span className="[color:var(--color-red-700)]! [font-size:var(--text-base)]!">*</span>}
        </label>
      )}
      <input
        type={type}
        className={`field-input ${error ? "[border-color:var(--color-red-500)]! focus:[box-shadow:0_0_0_3px_rgba(239,_68,_68,_0.1)]!" : ""}`}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        disabled={disabled}
        required={required}
        min={min}
        max={max}
        step={step}
      />
      {error && <span className="error-text">{error}</span>}
      {helperText && !error && (
        <span className="[font-size:var(--text-sm)]! [color:var(--text-secondary)]! [margin-top:4px]!">{helperText}</span>
      )}
    </div>
  );
};

// Select/Dropdown Field
export const SelectField = ({
  label,
  value,
  onChange,
  options = [],
  placeholder = "Select...",
  required = false,
  disabled = false,
  error = "",
  helperText = "",
}) => {
  return (
    <div className="[display:flex]! [flex-direction:column] [gap:6px] [margin-bottom:16px]!">
      {label && (
        <label className="field-label">
          {label}
          {required && <span className="[color:var(--color-red-700)]! [font-size:var(--text-base)]!">*</span>}
        </label>
      )}
      <NativeSelect
        className={`field-select ${error ? "[border-color:var(--color-red-500)]! focus:[box-shadow:0_0_0_3px_rgba(239,_68,_68,_0.1)]!" : ""}`}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        required={required}
      >
        {placeholder && <option value="">{placeholder}</option>}
        {options.map((opt, idx) => (
          <option key={idx} value={opt.value} disabled={opt.disabled}>
            {opt.label}
          </option>
        ))}
      </NativeSelect>
      {error && <span className="error-text">{error}</span>}
      {helperText && !error && (
        <span className="[font-size:var(--text-sm)]! [color:var(--text-secondary)]! [margin-top:4px]!">{helperText}</span>
      )}
    </div>
  );
};

// Textarea Field
export const TextAreaField = ({
  label,
  value,
  onChange,
  placeholder = "",
  required = false,
  disabled = false,
  error = "",
  helperText = "",
  rows = 4,
}) => {
  return (
    <div className="[display:flex]! [flex-direction:column] [gap:6px] [margin-bottom:16px]!">
      {label && (
        <label className="field-label">
          {label}
          {required && <span className="[color:var(--color-red-700)]! [font-size:var(--text-base)]!">*</span>}
        </label>
      )}
      <textarea
        className={`field-textarea ${error ? "[border-color:var(--color-red-500)]! focus:[box-shadow:0_0_0_3px_rgba(239,_68,_68,_0.1)]!" : ""}`}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        disabled={disabled}
        required={required}
        rows={rows}
      />
      {error && <span className="error-text">{error}</span>}
      {helperText && !error && (
        <span className="[font-size:var(--text-sm)]! [color:var(--text-secondary)]! [margin-top:4px]!">{helperText}</span>
      )}
    </div>
  );
};

// Checkbox Field
export const CheckboxField = ({
  label,
  checked,
  onChange,
  disabled = false,
  error = "",
  helperText = "",
}) => {
  return (
    <div className="[display:flex]! [flex-direction:column] [gap:6px] [margin-bottom:16px]! [margin-bottom:12px]!">
      <label className="checkbox-label">
        <input
          type="checkbox"
          className="[width:18px]! [height:18px]! [cursor:pointer] [accent-color:var(--accent-color)] disabled:[cursor:not-allowed] disabled:[opacity:0.6]"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          disabled={disabled}
        />
        <span>{label}</span>
      </label>
      {error && <span className="error-text">{error}</span>}
      {helperText && !error && (
        <span className="[font-size:var(--text-sm)]! [color:var(--text-secondary)]! [margin-top:4px]!">{helperText}</span>
      )}
    </div>
  );
};

// Radio Group Field
export const RadioGroupField = ({
  label,
  value,
  onChange,
  options = [],
  required = false,
  disabled = false,
  error = "",
  helperText = "",
  layout = "vertical", // 'vertical' or 'horizontal'
}) => {
  return (
    <div className="[display:flex]! [flex-direction:column] [gap:6px] [margin-bottom:16px]!">
      {label && (
        <label className="field-label">
          {label}
          {required && <span className="[color:var(--color-red-700)]! [font-size:var(--text-base)]!">*</span>}
        </label>
      )}
      <div
        className={`radio-group ${layout === "horizontal" ? "[flex-direction:row] [flex-wrap:wrap]" : "[flex-direction:column]"}`}
      >
        {options.map((opt, idx) => (
          <label key={idx} className="[display:flex]! [align-items:center] [gap:8px] [cursor:pointer] [font-size:var(--text-base)]! [color:var(--text-primary)]!">
            <input
              type="radio"
              className="[width:16px]! [height:16px]! [cursor:pointer] [accent-color:var(--accent-color)] disabled:[cursor:not-allowed] disabled:[opacity:0.6]"
              value={opt.value}
              checked={value === opt.value}
              onChange={(e) => onChange(e.target.value)}
              disabled={disabled || opt.disabled}
            />
            <span>{opt.label}</span>
          </label>
        ))}
      </div>
      {error && <span className="error-text">{error}</span>}
      {helperText && !error && (
        <span className="[font-size:var(--text-sm)]! [color:var(--text-secondary)]! [margin-top:4px]!">{helperText}</span>
      )}
    </div>
  );
};

// Date Field
export const DateField = ({
  label,
  value,
  onChange,
  required = false,
  disabled = false,
  error = "",
  helperText = "",
  min,
  max,
}) => {
  return (
    <div className="[display:flex]! [flex-direction:column] [gap:6px] [margin-bottom:16px]!">
      {label && (
        <label className="field-label">
          {label}
          {required && <span className="[color:var(--color-red-700)]! [font-size:var(--text-base)]!">*</span>}
        </label>
      )}
      <input
        type="date"
        className={`field-input ${error ? "[border-color:var(--color-red-500)]! focus:[box-shadow:0_0_0_3px_rgba(239,_68,_68,_0.1)]!" : ""}`}
        value={value}
        onChange={onChange}
        disabled={disabled}
        required={required}
        min={min}
        max={max}
      />
      {error && <span className="error-text">{error}</span>}
      {helperText && !error && (
        <span className="[font-size:var(--text-sm)]! [color:var(--text-secondary)]! [margin-top:4px]!">{helperText}</span>
      )}
    </div>
  );
};

export default {
  TextField,
  SelectField,
  TextAreaField,
  CheckboxField,
  RadioGroupField,
  DateField,
};
