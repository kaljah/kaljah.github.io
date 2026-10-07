import React from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import LoadingSpinner from "../components/LoadingSpinner";
import { ACCESS, deniedRedirect, type AccessRule } from "./access";

export interface RequireRoleProps {
  rule?: AccessRule;
  children: React.ReactElement;
}

/** Route guard: signed in, and allowed by the named access rule (see access.js). */
const RequireRole: React.FC<RequireRoleProps> = ({ rule, children }) => {
  const { user, loading } = useAuth();
  if (loading) return <LoadingSpinner fullScreen />;
  if (!user) return <Navigate to="/login" replace />;
  if (rule && !ACCESS[rule](user)) return <Navigate to={deniedRedirect(user, rule)} replace />;
  return children;
};

export default RequireRole;
