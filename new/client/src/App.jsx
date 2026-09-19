import React, { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { fetchCsrfToken } from "./api";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { LayoutProvider } from "./context/LayoutContext";
import { ToastProvider } from "./components/Toast";
import ErrorBoundary from "./components/ErrorBoundary";
import Layout from "./components/layout/Layout";
import Login from "./pages/Login";
import DashboardEnhanced from "./pages/DashboardEnhanced";
import Emissions from "./pages/Emissions";
import ManageData from "./pages/ManageData";
import QADashboard from "./pages/QADashboard";
import ReportsSync from "./pages/Reports";
import CarbonIntensity from "./pages/CarbonIntensity";
import MethaneIntensity from "./pages/MethaneIntensity";
import UncertaintyAssessment from "./pages/UncertaintyAssessment";
import ReferenceData from "./pages/ReferenceData";
import Diagnostics from "./pages/Diagnostics";
import AuditTrail from "./pages/AuditTrail";
import UserManagement from "./pages/UserManagement";
import Settings from "./pages/Settings";
import LoadingSpinner from "./components/LoadingSpinner";
// --- Lazy loaded heavy components ---
const EmissionsMap = React.lazy(() => import("./pages/MethaneExplorer"));
const Reports = React.lazy(() => import("./pages/Reports"));

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

const AppRoutes = () => {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      <Route
        path="/"
        element={
          <PrivateRoute>
            <React.Suspense fallback={<LoadingSpinner fullScreen message="Loading Component..." />}>
              <Layout />
            </React.Suspense>
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
            <AdminRoute>
              <QADashboard />
            </AdminRoute>
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
            <AdminRoute>
              <ReferenceData />
            </AdminRoute>
          }
        />
        {/* NEW-01 FIX */}
        <Route
          path="diagnostics"
          element={
            <AdminRoute>
              <Diagnostics />
            </AdminRoute>
          }
        />
        {/* NEW-01 FIX */}
        <Route
          path="audit-trail"
          element={
            <AdminRoute>
              <AuditTrail />
            </AdminRoute>
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
            <NonITRoute>
              <Settings />
            </NonITRoute>
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
        <LayoutProvider>
          <AuthProvider>
            <ToastProvider>
              <AppRoutes />
            </ToastProvider>
          </AuthProvider>
        </LayoutProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
};

export default App;
