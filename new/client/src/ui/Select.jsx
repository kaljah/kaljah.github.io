import React from "react";
import CustomDropdown from "../components/CustomDropdown";
import MultiSelectDropdown from "../components/MultiSelectDropdown";
import { useFieldContext } from "./Field";

/**
 * Single-choice listbox. Evolved from CustomDropdown (same props and DOM hooks), so every existing call site
 * keeps working. Inside a Field it takes its id and accessible name from the label.
 */
export const Select = (props) => {
  const field = useFieldContext();
  return <CustomDropdown id={field?.id} {...props} />;
};

/** Multi-choice listbox (same component the pages already use). */
export const MultiSelect = (props) => <MultiSelectDropdown {...props} />;
