import { useEffect } from "react";

export const useDocumentTitle = (title?: string | null): void => {
  useEffect(() => {
    document.title = title ? `${title} · Carbon Tech` : "Carbon Tech";
  }, [title]);
};
