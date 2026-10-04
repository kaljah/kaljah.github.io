import { useEffect } from "react";

export const useDocumentTitle = (title) => {
  useEffect(() => {
    document.title = title ? `${title} · Carbon Tech` : "Carbon Tech";
  }, [title]);
};
