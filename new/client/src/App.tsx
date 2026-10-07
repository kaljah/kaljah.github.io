import React, { useEffect } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { fetchCsrfToken } from "./api";
import { AuthProvider } from "./context/AuthContext";
import { LayoutProvider } from "./context/LayoutContext";
import { ToastProvider } from "./components/Toast";
import ErrorBoundary from "./components/ErrorBoundary";
import Login from "./pages/Login";
import AppShell from "./app/shell/AppShell";
import RequireRole from "./app/RequireRole";
import { ALIASES, ROUTES } from "./app/routes.config";

// Development-only component gallery (never part of production builds)
const UiGallery = import.meta.env.DEV
  ? React.lazy(() => import("./dev/UiGallery"))
  : null;

// Routes, guards, navigation and titles all come from app/routes.config.js.
const AppRoutes: React.FC = () => (
  <Routes>
    <Route path="/login" element={<Login />} />
    {UiGallery && (
      <Route
        path="/__ui"
        element={
          <React.Suspense fallback={null}>
            <div className="h-screen overflow-y-auto">
              {React.createElement(UiGallery)}
            </div>
          </React.Suspense>
        }
      />
    )}

    <Route
      path="/"
      element={
        <RequireRole>
          <AppShell />
        </RequireRole>
      }
    >
      {ROUTES.map(({ path, index, access, Component }) => {
        const element = (
          <RequireRole rule={access}>
            <Component />
          </RequireRole>
        );
        return index ? (
          <Route key={path} index element={element} />
        ) : (
          <Route key={path} path={path.slice(1)} element={element} />
        );
      })}
      {ALIASES.map(({ path, to }) => (
        <Route key={path} path={path.slice(1)} element={<Navigate to={to} replace />} />
      ))}
      {/* Unified QA/QC & Diagnostics */}
      <Route path="diagnostics" element={<Navigate to="/qa-dashboard" replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Route>
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes>
);

const App: React.FC = () => {
  useEffect(() => {
    fetchCsrfToken();
  }, []);

  return (
    <ErrorBoundary>
      <BrowserRouter basename={import.meta.env.BASE_URL}>
        <AuthProvider>
          <LayoutProvider>
            <ToastProvider>
              <AppRoutes />
            </ToastProvider>
          </LayoutProvider>
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
};

export default App;
