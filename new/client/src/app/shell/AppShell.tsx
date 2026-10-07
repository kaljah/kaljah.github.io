import React, { Suspense, useCallback, useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { useDocumentTitle } from "../../hooks/useDocumentTitle";
import { useLayout } from "../../context/LayoutContext";
import { PageSkeleton, TooltipProvider } from "../../ui";
import { rememberPage } from "../recentPages";
import { findRoute } from "../routes.config";
import AnalyticsFiltersSync from "../../filters/AnalyticsFiltersSync";
import BannerStack from "./BannerStack";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";

const CommandPalette = React.lazy(() => import("./CommandPalette"));

const AppShell: React.FC = () => {
  const { pathname } = useLocation();
  const { closeMobileNav } = useLayout();
  const [paletteOpen, setPaletteOpen] = useState<boolean>(false);
  const [paletteMounted, setPaletteMounted] = useState<boolean>(false);
  const route = findRoute(pathname);

  useDocumentTitle(route?.title);

  useEffect(() => {
    closeMobileNav();
    if (route) rememberPage(route.path);
  }, [pathname, route, closeMobileNav]);

  const openPalette = useCallback(() => {
    setPaletteMounted(true);
    setPaletteOpen(true);
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        openPalette();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [openPalette]);

  return (
    <TooltipProvider>
      <div className="app-container flex h-screen w-full overflow-hidden max-md:h-dvh">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-(--z-banner) focus:rounded-md focus:bg-surface focus:px-4 focus:py-2 focus:shadow-overlay"
        >
          Skip to content
        </a>
        <AnalyticsFiltersSync />
        <BannerStack />
        <Sidebar />
        <main className="main-content relative z-0 flex min-w-0 flex-1 flex-col overflow-hidden">
          <TopBar onOpenPalette={openPalette} />
          <div id="main" tabIndex={-1} className="min-h-0 w-full flex-1 overflow-y-auto overflow-x-hidden outline-none">
            <Suspense fallback={<PageSkeleton />}>
              <Outlet />
            </Suspense>
          </div>
        </main>
        {paletteMounted && (
          <Suspense fallback={null}>
            <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} />
          </Suspense>
        )}
      </div>
    </TooltipProvider>
  );
};

export default AppShell;
