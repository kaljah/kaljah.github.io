import React, { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { fetchCsrfToken } from "./api";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { LayoutProvider } from "./context/LayoutContext";
import { ToastProvider } from "./components/Toast";
import ErrorBoundary from "./components/ErrorBoundary";
import Layout from "./components/layout/Layout";
import Login from "./pages/Login";
import LoadingSpinner from "./components/LoadingSpinner";

// Lazy loaded page components for optimal bundle splitting and fast load times
const DashboardEnhanced = React.lazy(() => import("./pages/DashboardEnhanced"));
const Emissions = React.lazy(() => import("./pages/Emissions"));
const ManageData = React.lazy(() => import("./pages/ManageData"));
const QADashboard = React.lazy(() => import("./pages/QADashboard"));
const Reports = React.lazy(() => import("./pages/Reports"));
const CarbonIntensity = React.lazy(() => import("./pages/CarbonIntensity"));
const MethaneIntensity = React.lazy(() => import("./pages/MethaneIntensity"));
const UncertaintyAssessment = React.lazy(() => import("./pages/UncertaintyAssessment"));
const ReferenceData = React.lazy(() => import("./pages/ReferenceData"));
const Diagnostics = React.lazy(() => import("./pages/Diagnostics"));
const AuditTrail = React.lazy(() => import("./pages/AuditTrail"));
const UserManagement = React.lazy(() => import("./pages/UserManagement"));
const Settings = React.lazy(() => import("./pages/Settings"));
const SbtiDashboard = React.lazy(() => import("./pages/SbtiDashboard"));
const EmissionsMap = React.lazy(() => import("./pages/MethaneExplorer"));

const PrivateRoute = ({ children }) => {
  const { user, loading } = useAuth();
  if (loading)
    return <LoadingSpinner fullScreen message="Authenticating Session..." />;
  return user ? children : <Navigate to="/login" />;
};

const NonITRoute = ({ children }) => {
  const { user, loading } = useAuth();
  if (loading) return <LoadingSpinner fullScreen />;
  if (!user) return <Navigate to="/login" />;
  if (user.role === "it_admin") return <Navigate to="/user-management" />;
  return children;
};

const ITRoute = ({ children }) => {
  const { user, loading } = useAuth();
  if (loading) return <LoadingSpinner fullScreen />;
  if (!user) return <Navigate to="/login" />;
  if (user.role !== "it_admin") return <Navigate to="/" />;
  return children;
};

const AdminRoute = ({ children }) => {
  const { user, loading } = useAuth();
  if (loading) return <LoadingSpinner fullScreen />;
  if (!user) return <Navigate to="/login" />;
  if (user.role !== "admin") return <Navigate to="/" />;
  return children;
};

const SuperuserRoute = ({ children }) => {
  const { user, loading } = useAuth();
  if (loading) return <LoadingSpinner fullScreen />;
  if (!user) return <Navigate to="/login" />;
  if (!["admin", "superuser"].includes(user.role)) return <Navigate to="/" />;
  return children;
};

const AuditRoute = ({ children }) => {
  const { user, loading } = useAuth();
  if (loading) return <LoadingSpinner fullScreen />;
  if (!user) return <Navigate to="/login" />;
  if (!["admin", "superuser", "it_admin"].includes(user.role))
    return <Navigate to="/" />;
  return children;
};

const AppRoutes = () => {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      <Route
        path="/"
        element={
          <PrivateRoute>
            <Layout />
          </PrivateRoute>
        }
      >
        <Route
          index
          element={
            <NonITRoute>
              <DashboardEnhanced />
            </NonITRoute>
          }
        />
        <Route
          path="emissions"
          element={
            <NonITRoute>
              <Emissions />
            </NonITRoute>
          }
        />
        <Route
          path="manage-data"
          element={
            <NonITRoute>
              <ManageData />
            </NonITRoute>
          }
        />
        <Route
          path="qa-dashboard"
          element={
            <SuperuserRoute>
              <QADashboard />
            </SuperuserRoute>
          }
        />
        <Route
          path="reports"
          element={
            <NonITRoute>
              <Reports />
            </NonITRoute>
          }
        />
        <Route
          path="carbon-intensity"
          element={
            <NonITRoute>
              <CarbonIntensity />
            </NonITRoute>
          }
        />
        <Route
          path="methane-intensity"
          element={
            <NonITRoute>
              <MethaneIntensity />
            </NonITRoute>
          }
        />
        <Route
          path="methane-explorer"
          element={
            <NonITRoute>
              <EmissionsMap />
            </NonITRoute>
          }
        />
        <Route
          path="sbti"
          element={
            <NonITRoute>
              <SbtiDashboard />
            </NonITRoute>
          }
        />
        <Route
          path="uncertainty"
          element={
            <NonITRoute>
              <UncertaintyAssessment />
            </NonITRoute>
          }
        />
        <Route
          path="reference-data"
          element={
            <NonITRoute>
              <ReferenceData />
            </NonITRoute>
          }
        />
        {/* Unified QA/QC & Diagnostics */}
        <Route
          path="diagnostics"
          element={<Navigate to="/qa-dashboard" replace />}
        />
        {/* NEW-01 FIX */}
        <Route
          path="audit-trail"
          element={
            <AuditRoute>
              <AuditTrail />
            </AuditRoute>
          }
        />
        <Route
          path="user-management"
          element={
            <ITRoute>
              <UserManagement />
            </ITRoute>
          }
        />
        <Route
          path="settings"
          element={
            <PrivateRoute>
              <Settings />
            </PrivateRoute>
          }
        />
      </Route>
    </Routes>
  );
};

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
