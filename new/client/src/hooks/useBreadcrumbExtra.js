import { useEffect } from "react";
import { useLayout } from "../context/LayoutContext";

/** Pages call this to append a sub-stage, e.g. useBreadcrumbExtra("Scope 1 (Direct)"). */
export const useBreadcrumbExtra = (label) => {
  const { setBreadcrumbExtra } = useLayout();
  useEffect(() => {
    setBreadcrumbExtra(label || null);
    return () => setBreadcrumbExtra(null);
  }, [label, setBreadcrumbExtra]);
};
