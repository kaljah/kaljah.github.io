import React from "react";
import CustomDropdown, { type CustomDropdownProps } from "../components/CustomDropdown";
import MultiSelectDropdown, { type MultiSelectDropdownProps } from "../components/MultiSelectDropdown";
import { useFieldContext } from "./Field";

export interface SelectOption {
  value: string | number;
  label: React.ReactNode;
  subLabel?: string;
  isHeader?: boolean;
}

export interface SelectProps extends CustomDropdownProps {
  className?: string;
  [key: string]: unknown;
}

export interface MultiSelectProps extends MultiSelectDropdownProps {
  className?: string;
  [key: string]: unknown;
}

/**
 * Single-choice listbox. Evolved from CustomDropdown (same props and DOM hooks), so every existing call site
 * keeps working. Inside a Field it takes its id and accessible name from the label.
 */
export const Select: React.FC<SelectProps> = (props) => {
  const field = useFieldContext();
  return <CustomDropdown id={props.id ?? field?.id} {...props} />;
};

/** Multi-choice listbox (same component the pages already use). */
export const MultiSelect: React.FC<MultiSelectProps> = (props) => <MultiSelectDropdown {...props} />;
