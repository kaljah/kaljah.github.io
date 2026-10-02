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

// Routes, guards, navigation and titles all come from app/routes.config.js.
const AppRoutes = () => (
  <Routes>
    <Route path="/login" element={<Login />} />

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
    </Route>
  </Routes>
);

const App = () => {
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
