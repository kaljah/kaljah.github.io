import React, { useEffect, useRef } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../components/Toast";
import LoadingSpinner from "../components/LoadingSpinner";
import { ACCESS, deniedRedirect, type AccessRule } from "./access";
import { t } from "../i18n";

export interface RequireRoleProps {
  rule?: AccessRule;
  children: React.ReactElement;
}

/** Route guard: signed in, and allowed by the named access rule (see access.js). */
const RequireRole: React.FC<RequireRoleProps> = ({ rule, children }) => {
  const { user, loading } = useAuth();
  const toast = useToast();
  const warnedRef = useRef(false);

  const isDenied = Boolean(user && rule && !ACCESS[rule](user));

  useEffect(() => {
    if (isDenied && !warnedRef.current) {
      warnedRef.current = true;
      toast.warning(t("Access Denied: You do not have permission to view this page."));
    }
    if (!isDenied) {
      warnedRef.current = false;
    }
  }, [isDenied]);

  if (loading) return <LoadingSpinner fullScreen />;
  if (!user) return <Navigate to="/login" replace />;
  if (isDenied) return <Navigate to={deniedRedirect(user, rule!)} replace />;
  return children;
};

export default RequireRole;
