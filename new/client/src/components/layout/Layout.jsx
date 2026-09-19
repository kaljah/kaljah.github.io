import React, { Suspense } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";
import LoadingSpinner from "../LoadingSpinner";
import { useAuth } from "../../context/AuthContext";
import { useLayout } from "../../context/LayoutContext";
import "./Layout.css";

const Layout = () => {
  const location = useLocation();
  const { sessionWarning } = useAuth() || {};
  const { isMobileNavOpen, closeMobileNav } = useLayout();
  const [isOnline, setIsOnline] = React.useState(
    typeof navigator !== "undefined" ? navigator.onLine : true
  );

  React.useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  const prevPathnameRef = React.useRef(location.pathname);
  React.useEffect(() => {
    if (prevPathnameRef.current !== location.pathname) {
      prevPathnameRef.current = location.pathname;
      if (closeMobileNav) {
        closeMobileNav();
      }
    }
  }, [location.pathname, closeMobileNav]);

  return (
    <div className="app-container">
      {isMobileNavOpen && (
        <div
          className="sidebar-backdrop"
          onClick={closeMobileNav}
          aria-label="Close navigation"
        />
      )}
      {!isOnline && (
        <div
          id="offline-banner"
          style={{
            position: "fixed",
            top: "16px",
            left: "50%",
            transform: "translateX(-50%)",
            zIndex: 10000,
            background: "#fef2f2",
            border: "1px solid #fecaca",
            color: "#991b1b",
            borderRadius: "12px",
            padding: "12px 24px",
            boxShadow: "0 8px 24px rgba(0, 0, 0, 0.15)",
            display: "flex",
            alignItems: "center",
            gap: "12px",
            fontSize: "0.88rem",
            fontWeight: 600,
          }}
        >
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              width: "22px",
              height: "22px",
              borderRadius: "50%",
              background: "#dc2626",
              color: "#ffffff",
              fontSize: "0.8rem",
              fontWeight: 800,
            }}
          >
            !
          </span>
          <span>
            Network connection lost. You are currently working offline — changes will not sync until connection is restored.
          </span>
        </div>
      )}
      {sessionWarning && (
        <div
          style={{
            position: "fixed",
            top: "16px",
            left: "50%",
            transform: "translateX(-50%)",
            zIndex: 9999,
            background: "#fffbeb",
            border: "1px solid #fde68a",
            color: "#92400e",
            borderRadius: "12px",
            padding: "12px 24px",
            boxShadow: "0 8px 24px rgba(0, 0, 0, 0.15)",
            display: "flex",
            alignItems: "center",
            gap: "12px",
            fontSize: "0.88rem",
            fontWeight: 600,
          }}
        >
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              width: "22px",
              height: "22px",
              borderRadius: "50%",
              background: "#d97706",
              color: "#ffffff",
              fontSize: "0.8rem",
              fontWeight: 800,
            }}
          >
            !
          </span>
          <span>
            Session timeout imminent: Your session will expire in 60 seconds due to inactivity. Move your mouse or click to stay logged in.
          </span>
        </div>
      )}
      <Sidebar />
      <main className="main-content">
        <TopBar />
        <div style={{ flex: 1, overflowY: "auto", overflowX: "hidden" }}>
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.15, ease: "easeOut" }}
              style={{ height: "100%" }}
            >
              <Suspense
                fallback={
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      minHeight: "60vh",
                    }}
                  >
                    <LoadingSpinner message="Loading view..." />
                  </div>
                }
              >
                <Outlet />
              </Suspense>
            </motion.div>
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
};

export default Layout;
