import React, { useEffect, useRef, useState } from "react";
import { NavLink } from "react-router-dom";
import * as RadixDialog from "@radix-ui/react-dialog";
import { PanelLeftClose, PanelLeftOpen, X } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { useLayout } from "../../context/LayoutContext";
import { useMediaQuery } from "../../hooks/useMediaQuery";
import { Tooltip, cn } from "../../ui";
import { ACCESS } from "../access";
import { NAV_GROUPS, ROUTES } from "../routes.config";

const STORAGE_KEY = "ct.sidebar.collapsed";

const readCollapsed = () => {
  try {
    return localStorage.getItem(STORAGE_KEY) === "1";
  } catch {
    return false;
  }
};

const NavItem = ({ route, showLabel, onNavigate }) => {
  const Icon = route.icon;
  const link = (
    <NavLink
      to={route.path}
      end={route.path === "/"}
      onClick={onNavigate}
      aria-label={showLabel ? undefined : route.title}
      className={({ isActive }) =>
        cn(
          "relative flex h-10 items-center gap-3 rounded-md px-3 text-base font-medium no-underline transition-colors",
          isActive ? "bg-selected-bg text-selected-fg" : "text-text-secondary hover:bg-ink-100 hover:text-text",
        )
      }
    >
      {({ isActive }) => (
        <>
          {isActive && <span aria-hidden="true" className="absolute inset-y-2 left-0 w-[3px] rounded-full bg-brand-500" />}
          <Icon className={cn("size-[18px] shrink-0", isActive && "text-brand-500")} aria-hidden="true" />
          {showLabel && <span className="truncate">{route.title}</span>}
        </>
      )}
    </NavLink>
  );
  return showLabel ? link : <Tooltip content={route.title} side="right">{link}</Tooltip>;
};

const NavList = ({ user, showLabel, onNavigate }) => {
  const visible = ROUTES.filter((r) => ACCESS[r.access](user));
  const settings = visible.find((r) => r.group === null);
  return (
    <>
      <nav aria-label="Main" className="flex-1 overflow-y-auto overflow-x-hidden px-2 py-2">
        {NAV_GROUPS.map((group) => {
          const items = visible.filter((r) => r.group === group);
          if (!items.length) return null;
          return (
            <div key={group} className="mb-3">
              {showLabel ? (
                <p className="px-3 pb-1 pt-2 text-xs font-medium uppercase tracking-wide text-text-secondary">{group}</p>
              ) : (
                <div aria-hidden="true" className="mx-3 my-2 h-px bg-border" />
              )}
              <ul className="m-0 flex list-none flex-col gap-0.5 p-0">
                {items.map((r) => (
                  <li key={r.path}>
                    <NavItem route={r} showLabel={showLabel} onNavigate={onNavigate} />
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </nav>
      {settings && (
        <div className="border-t border-border px-2 py-2">
          <NavItem route={settings} showLabel={showLabel} onNavigate={onNavigate} />
        </div>
      )}
    </>
  );
};

const Brand = ({ showLabel }) => (
  <div className="flex h-16 shrink-0 items-center gap-3 px-4">
    <img src={`${import.meta.env.BASE_URL}carbon_tech.svg`} alt="" className="size-8 shrink-0" />
    {showLabel && <span className="truncate text-md font-bold text-text">Carbon tech</span>}
  </div>
);

const Sidebar = () => {
  const { user } = useAuth();
  const { isMobileNavOpen, setIsMobileNavOpen, closeMobileNav } = useLayout();
  const isMobile = useMediaQuery("(max-width: 899px)");
  const [collapsed, setCollapsed] = useState(readCollapsed);
  const [peek, setPeek] = useState(false);
  const peekTimer = useRef(null);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, collapsed ? "1" : "0");
    } catch {
      // storage unavailable: the choice is not remembered
    }
  }, [collapsed]);

  // "[" toggles the sidebar (ignored while typing)
  useEffect(() => {
    const onKey = (e) => {
      const tag = e.target?.tagName;
      if (e.key !== "[" || e.ctrlKey || e.metaKey || e.altKey) return;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || e.target?.isContentEditable) return;
      setCollapsed((c) => !c);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => () => clearTimeout(peekTimer.current), []);

  if (isMobile) {
    return (
      <RadixDialog.Root open={isMobileNavOpen} onOpenChange={setIsMobileNavOpen}>
        <RadixDialog.Portal>
          <RadixDialog.Overlay className="fixed inset-0 z-(--z-overlay) bg-ink-900/45" />
          <RadixDialog.Content
            aria-describedby={undefined}
            className="fixed inset-y-0 left-0 z-(--z-modal) flex w-72 max-w-[85vw] flex-col bg-surface shadow-overlay"
          >
            <RadixDialog.Title className="sr-only">Navigation</RadixDialog.Title>
            <div className="flex items-center justify-between pr-3">
              <Brand showLabel />
              <RadixDialog.Close aria-label="Close navigation" className="inline-flex size-9 cursor-pointer border-0 bg-transparent items-center justify-center rounded-md text-text-secondary hover:bg-ink-100">
                <X className="size-5" aria-hidden="true" />
              </RadixDialog.Close>
            </div>
            <NavList user={user} showLabel onNavigate={closeMobileNav} />
          </RadixDialog.Content>
        </RadixDialog.Portal>
      </RadixDialog.Root>
    );
  }

  const open = (value) => {
    clearTimeout(peekTimer.current);
    if (!value) return setPeek(false);
    peekTimer.current = setTimeout(() => setPeek(true), 150);
  };
  const expanded = !collapsed || peek;

  return (
    // The wrapper keeps a fixed width, so peeking over the content never reflows the page.
    <div className={cn("app-sidebar relative z-(--z-sidebar) shrink-0 transition-[width] duration-200", collapsed ? "w-16" : "w-60")}>
      <aside
        onMouseEnter={() => collapsed && open(true)}
        onMouseLeave={() => open(false)}
        onFocus={() => collapsed && open(true)}
        onBlur={(e) => !e.currentTarget.contains(e.relatedTarget) && open(false)}
        className={cn(
          "absolute inset-y-0 left-0 flex flex-col border-r border-border bg-surface transition-[width,box-shadow] duration-200",
          expanded ? "w-60" : "w-16",
          collapsed && peek && "shadow-raised",
        )}
      >
        <Brand showLabel={expanded} />
        <NavList user={user} showLabel={expanded} />
        <div className="border-t border-border px-2 py-2">
          <button
            type="button"
            onClick={() => {
              setCollapsed((c) => !c);
              setPeek(false);
            }}
            aria-label={collapsed ? "Pin sidebar open" : "Collapse sidebar"}
            aria-keyshortcuts="["
            className="flex h-10 w-full cursor-pointer items-center gap-3 rounded-md border-0 bg-transparent px-3 text-base font-medium text-text-secondary transition-colors hover:bg-ink-100 hover:text-text"
          >
            {collapsed ? (
              <PanelLeftOpen className="size-[18px] shrink-0" aria-hidden="true" />
            ) : (
              <PanelLeftClose className="size-[18px] shrink-0" aria-hidden="true" />
            )}
            {expanded && <span className="truncate">{collapsed ? "Pin open" : "Collapse"}</span>}
          </button>
        </div>
      </aside>
    </div>
  );
};

export default Sidebar;
