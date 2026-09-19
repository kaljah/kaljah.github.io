import { useState, useEffect, useCallback } from "react";

/**
 * Custom hook to manage form draft persistence in localStorage.
 * Automatically saves on value changes (debounced 1s) and provides
 * methods to load, update, and clear the saved draft.
 *
 * @param {string} draftKey - Unique identifier key (e.g., "scope1_form")
 * @param {object} initialValues - Default form state
 * @returns {object} { values, setValues, handleChange, clearDraft, hasDraft }
 */
export function useFormDraft(draftKey, initialValues = {}) {
  const [hasDraft, setHasDraft] = useState(false);

  const getSavedDraft = useCallback(() => {
    try {
      const item = localStorage.getItem(`draft_${draftKey}`);
      if (item) {
        const parsed = JSON.parse(item);
        return parsed && typeof parsed === "object" ? parsed : null;
      }
    } catch (e) {
      console.warn(`[useFormDraft] Error loading draft for ${draftKey}`, e);
    }
    return null;
  }, [draftKey]);

  const [values, setValues] = useState(() => {
    const saved = getSavedDraft();
    if (saved && Object.keys(saved).length > 0) {
      return { ...initialValues, ...saved };
    }
    return initialValues;
  });

  useEffect(() => {
    const saved = getSavedDraft();
    setHasDraft(!!saved && Object.keys(saved).length > 0);
  }, [getSavedDraft]);

  // Auto-save draft on values change with 1s debounce
  useEffect(() => {
    const timer = setTimeout(() => {
      try {
        if (values && Object.keys(values).length > 0) {
          localStorage.setItem(`draft_${draftKey}`, JSON.stringify(values));
          setHasDraft(true);
        }
      } catch (e) {
        console.warn(`[useFormDraft] Error saving draft for ${draftKey}`, e);
      }
    }, 1000);

    return () => clearTimeout(timer);
  }, [values, draftKey]);

  const handleChange = useCallback((e) => {
    const { name, value, type, checked } = e.target;
    setValues((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  }, []);

  const clearDraft = useCallback(() => {
    try {
      localStorage.removeItem(`draft_${draftKey}`);
      setHasDraft(false);
      setValues(initialValues);
    } catch (e) {
      console.warn(`[useFormDraft] Error clearing draft for ${draftKey}`, e);
    }
  }, [draftKey, initialValues]);

  return {
    values,
    setValues,
    handleChange,
    clearDraft,
    hasDraft,
  };
}

export default useFormDraft;
