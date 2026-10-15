import { useEffect } from "react";
import { t } from "../i18n";

/**
 * Ask before a half-filled form is discarded (audit 2026-10-14 BUG-0056): on reload / tab close
 * (beforeunload) and on in-app link clicks. The app uses BrowserRouter, so react-router's
 * useBlocker (data routers only) is not available.
 */
export const useUnsavedChangesWarning = (dirty: boolean, message?: string): void => {
  useEffect(() => {
    if (!dirty) return undefined;
    const text = message || t("You have unsaved changes. Leave this page and discard them?");
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    const onClick = (e: MouseEvent) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const link = (e.target as Element | null)?.closest?.("a[href]") as HTMLAnchorElement | null;
      if (!link || link.target === "_blank" || link.hasAttribute("download")) return;
      const url = new URL(link.href, window.location.href);
      if (url.origin !== window.location.origin) return;
      if (url.pathname === window.location.pathname && url.search === window.location.search) return;
      if (!window.confirm(text)) {
        e.preventDefault();
        e.stopPropagation();
      }
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    document.addEventListener("click", onClick, true);
    return () => {
      window.removeEventListener("beforeunload", onBeforeUnload);
      document.removeEventListener("click", onClick, true);
    };
  }, [dirty, message]);
};
