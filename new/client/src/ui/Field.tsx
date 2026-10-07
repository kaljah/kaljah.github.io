import React, { createContext, useContext, useId } from "react";
import { cn } from "./cn";

export interface FieldContextValue {
  id: string;
  invalid: boolean;
  required: boolean;
  describedBy?: string;
}

const FieldContext = createContext<FieldContextValue | null>(null);

// eslint-disable-next-line react-refresh/only-export-components -- hook shared with Select
export const useFieldContext = (): FieldContextValue | null => useContext(FieldContext);

export interface FieldProps {
  label: React.ReactNode;
  hint?: React.ReactNode;
  error?: React.ReactNode;
  required?: boolean;
  className?: string;
  children: React.ReactNode;
}

/** Label, control and hint/error wiring. Child controls read id and ARIA attributes from context. */
export const Field: React.FC<FieldProps> = ({ label, hint, error, required = false, className, children }) => {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const ctx: FieldContextValue = {
    id,
    invalid: Boolean(error),
    required,
    describedBy: [hintId, errorId].filter(Boolean).join(" ") || undefined,
  };
  return (
    <FieldContext.Provider value={ctx}>
      <div className={cn("flex flex-col gap-1.5", className)}>
        <label htmlFor={id} className="text-sm font-medium text-text">
          {label}
          {required && (
            <span aria-hidden="true" className="ml-0.5 text-danger-fg">
              *
            </span>
          )}
        </label>
        {children}
        {hint && !error && (
          <p id={hintId} className="text-xs text-text-secondary">
            {hint}
          </p>
        )}
        {error && (
          <p id={errorId} className="text-xs font-medium text-danger-fg">
            {error}
          </p>
        )}
      </div>
    </FieldContext.Provider>
  );
};

interface ControlledProps {
  id?: string;
  "aria-invalid"?: boolean | "false" | "true" | "grammar" | "spelling";
  "aria-describedby"?: string;
  required?: boolean;
}

const useFieldProps = (props: ControlledProps) => {
  const ctx = useContext(FieldContext);
  return {
    id: props.id ?? ctx?.id,
    "aria-invalid": props["aria-invalid"] ?? (ctx?.invalid || undefined),
    "aria-describedby": props["aria-describedby"] ?? ctx?.describedBy,
    required: props.required ?? ctx?.required,
  };
};

export const controlClass =
  "w-full rounded-md border border-border bg-surface px-3 font-sans text-base text-text placeholder:text-text-disabled " +
  "transition-colors hover:border-ink-300 focus:border-brand-500 disabled:cursor-not-allowed disabled:bg-ink-50 " +
  "disabled:text-text-disabled aria-invalid:border-danger";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(function Input({ className, ...props }, ref) {
  return <input ref={ref} className={cn(controlClass, "h-10", className)} {...props} {...useFieldProps(props)} />;
});

export interface NumberInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  unit?: string;
}

/** Decimal input with an optional unit suffix. inputMode=decimal shows a numeric pad on phones. */
export const NumberInput = React.forwardRef<HTMLInputElement, NumberInputProps>(function NumberInput(
  { unit, className, ...props },
  ref,
) {
  const fieldProps = useFieldProps(props);
  return (
    <div className="relative">
      <input
        ref={ref}
        type="text"
        inputMode="decimal"
        className={cn(controlClass, "h-10 tabular-nums", unit && "pr-14", className)}
        {...props}
        {...fieldProps}
      />
      {unit && (
        <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-sm text-text-secondary">
          {unit}
        </span>
      )}
    </div>
  );
});

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { className, ...props },
  ref,
) {
  return (
    <textarea ref={ref} className={cn(controlClass, "min-h-24 py-2", className)} {...props} {...useFieldProps(props)} />
  );
});

export interface SwitchProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: React.ReactNode;
}

/** Toggle switch built on a native checkbox (role=switch). Pass label for the accessible name. */
export const Switch = React.forwardRef<HTMLInputElement, SwitchProps>(function Switch(
  { label, className, ...props },
  ref,
) {
  return (
    <label className={cn("inline-flex cursor-pointer items-center gap-2 text-base text-text", className)}>
      <input ref={ref} type="checkbox" role="switch" className="peer sr-only" {...props} />
      <span
        aria-hidden="true"
        className="relative h-6 w-11 rounded-full bg-ink-300 transition-colors after:absolute after:left-0.5 after:top-0.5 after:size-5 after:rounded-full after:bg-white after:transition-transform peer-checked:bg-primary peer-checked:after:translate-x-5 peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-focus peer-disabled:opacity-50"
      />
      {label}
    </label>
  );
});
