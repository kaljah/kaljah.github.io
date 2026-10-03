import React from "react";
import { Menu, Search } from "lucide-react";
import { useLayout } from "../../context/LayoutContext";
import NotificationCenter from "../../components/NotificationCenter";
import { IconButton } from "../../ui";
import AccountMenu from "./AccountMenu";
import Breadcrumbs from "./Breadcrumbs";
import "../../components/layout/TopBar.css";

const isMac = typeof navigator !== "undefined" && /Mac|iPhone|iPad/.test(navigator.platform);

const TopBar = ({ onOpenPalette }) => {
  const { topBarLeft, topBarRight, toggleMobileNav } = useLayout();
  const hasFilterRow = Boolean(topBarLeft || topBarRight);
  return (
    <header className="topbar sticky top-0 z-(--z-topbar) shrink-0 border-b border-border bg-surface/95 backdrop-blur">
      <div className="flex h-16 items-center gap-3 px-4 md:px-6">
        <IconButton label="Open navigation menu" onClick={toggleMobileNav} className="md:hidden">
          <Menu className="size-5" aria-hidden="true" />
        </IconButton>

        <div className="min-w-0 flex-1">
          <Breadcrumbs />
        </div>

        <div className="[display:flex]! [align-items:center] [gap:14px] [white-space:nowrap] [@media(max-width:900px)]:[gap:6px]! flex items-center gap-2">
          <button
            type="button"
            onClick={onOpenPalette}
            aria-label="Search pages and actions"
            aria-keyshortcuts="Control+K Meta+K"
            className="hidden h-9 cursor-pointer items-center gap-2 rounded-md border border-border bg-surface px-3 text-sm text-text-secondary transition-colors hover:bg-ink-100 sm:flex"
          >
            <Search className="size-4" aria-hidden="true" />
            <span>Search</span>
            <kbd className="rounded-sm border border-border bg-ink-50 px-1.5 font-[inherit] text-xs text-text-secondary">
              {isMac ? "⌘K" : "Ctrl K"}
            </kbd>
          </button>
          <IconButton label="Search" onClick={onOpenPalette} className="sm:hidden">
            <Search className="size-5" aria-hidden="true" />
          </IconButton>
          <NotificationCenter />
          <AccountMenu />
        </div>
      </div>

      {/* Page filter row. Pages still inject their filters through the layout context; they now get a
          full-width row instead of being squeezed into the title row. */}
      {hasFilterRow && (
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 border-t border-ink-100 bg-ink-50/60 px-4 py-2 md:px-6">
          <div className="top-bar-injected-left flex min-w-0 flex-wrap items-center gap-2">{topBarLeft}</div>
          <div className="flex flex-wrap items-center gap-2">{topBarRight}</div>
        </div>
      )}
    </header>
  );
};

export default TopBar;
