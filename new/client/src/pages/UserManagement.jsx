import React, { useState, useEffect } from "react";
import api from "../api";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../components/Toast";
import Modal from "../components/Modal";
import ConfirmModal from "../components/ConfirmModal";

/* ─── tiny keyframe injection ─────────────────────────────────────────────── */
const STYLE_ID = "um-keyframes";
if (!document.getElementById(STYLE_ID)) {
  const s = document.createElement("style");
  s.id = STYLE_ID;
  s.textContent = `
        @keyframes um-fade-in   { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: none; } }
        @keyframes um-slide-in  { from { opacity: 0; transform: translateX(-12px); } to { opacity: 1; transform: none; } }
        @keyframes um-pulse-dot { 0%,100% { transform: scale(1); opacity:.8; } 50% { transform: scale(2.2); opacity: 0; } }
    `;
  document.head.appendChild(s);
}

/* ─── role metadata ────────────────────────────────────────────────────────── */
const ROLE_META = {
  admin: {
    label: "Admin",
    color: "#10b981",
    bg: "#ecfdf5",
    border: "rgba(16,185,129,.25)",
  },
  it_admin: {
    label: "IT Admin",
    color: "#f59e0b",
    bg: "#fffbeb",
    border: "rgba(245,158,11,.25)",
  },
  superuser: {
    label: "Super User",
    color: "#8b5cf6",
    bg: "#f3e8ff",
    border: "rgba(139,92,246,.25)",
  },
  user: {
    label: "User",
    color: "#3b82f6",
    bg: "#eff6ff",
    border: "rgba(59,130,246,.25)",
  },
};
const getRoleMeta = (role) =>
  ROLE_META[role] || {
    label: role?.toUpperCase?.() || "UNKNOWN",
    color: "#64748b",
    bg: "#f1f5f9",
    border: "#e2e8f0",
  };

/* ─── shared inline style helpers ─────────────────────────────────────────── */
const S = {
  page: {
    padding: "32px",
    fontFamily: "'Outfit', Inter, system-ui, sans-serif",
    maxWidth: "1400px",
    margin: "0 auto",
    animation: "um-fade-in .4s ease both",
  },
  /* hero header */
  hero: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: "28px",
    gap: "16px",
    flexWrap: "wrap",
  },
  heroLeft: { display: "flex", flexDirection: "column", gap: "6px" },
  badge: {
    display: "inline-flex",
    alignItems: "center",
    gap: "7px",
    background: "#fff7ed",
    color: "#ff6600",
    border: "1px solid rgba(255,102,0,.15)",
    borderRadius: "100px",
    padding: "4px 12px",
    fontSize: "0.78rem",
    fontWeight: 700,
    letterSpacing: ".4px",
    width: "fit-content",
    marginBottom: "4px",
  },
  pulseDot: {
    width: "7px",
    height: "7px",
    borderRadius: "50%",
    background: "#ff6600",
    display: "inline-block",
    animation: "um-pulse-dot 2s infinite",
  },
  pageTitle: {
    margin: 0,
    fontSize: "1.9rem",
    fontWeight: 800,
    color: "var(--text-primary)",
    lineHeight: 1.1,
  },
  pageSubtitle: {
    margin: 0,
    fontSize: "0.9rem",
    color: "var(--text-secondary)",
    fontWeight: 500,
  },
  heroRight: {
    display: "flex",
    gap: "10px",
    alignItems: "center",
    flexWrap: "wrap",
  },

  /* stat cards row */
  statsRow: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
    gap: "16px",
    marginBottom: "24px",
  },
  statCard: {
    background: "var(--bg-card)",
    border: "1px solid var(--border-color)",
    borderRadius: "16px",
    padding: "18px 20px",
    display: "flex",
    flexDirection: "column",
    gap: "6px",
    boxShadow: "0 2px 8px rgba(0,0,0,.04)",
    transition: "transform .2s, box-shadow .2s",
  },
  statIcon: {
    width: "36px",
    height: "36px",
    borderRadius: "10px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "1.1rem",
    marginBottom: "4px",
  },
  statValue: {
    fontSize: "1.8rem",
    fontWeight: 800,
    color: "var(--text-primary)",
    lineHeight: 1,
  },
  statLabel: {
    fontSize: "0.78rem",
    fontWeight: 600,
    color: "var(--text-secondary)",
    textTransform: "uppercase",
    letterSpacing: ".6px",
  },

  /* table card */
  tableCard: {
    background: "var(--bg-card)",
    border: "1px solid var(--border-color)",
    borderRadius: "20px",
    overflow: "hidden",
    boxShadow: "0 4px 16px rgba(0,0,0,.05)",
  },
  tableToolbar: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "16px 20px",
    borderBottom: "1px solid var(--border-color)",
    gap: "12px",
    flexWrap: "wrap",
  },
  tableCardTitle: {
    margin: 0,
    fontSize: "1rem",
    fontWeight: 700,
    color: "var(--text-primary)",
  },
  tableCardSub: {
    margin: 0,
    fontSize: "0.8rem",
    color: "var(--text-secondary)",
    marginTop: "2px",
  },

  tableWrap: { overflowX: "auto" },
  table: { width: "100%", borderCollapse: "collapse", minWidth: "820px" },
  th: {
    textAlign: "left",
    padding: "11px 16px",
    background: "var(--bg-body)",
    color: "var(--text-secondary)",
    fontWeight: 700,
    fontSize: "0.72rem",
    textTransform: "uppercase",
    letterSpacing: ".7px",
    borderBottom: "1px solid var(--border-color)",
    whiteSpace: "nowrap",
  },
  td: {
    padding: "13px 16px",
    borderBottom: "1px solid var(--border-color)",
    fontSize: "0.875rem",
    color: "var(--text-primary)",
    verticalAlign: "middle",
  },

  /* avatar */
  avatar: (color) => ({
    width: "34px",
    height: "34px",
    borderRadius: "10px",
    background: color + "20",
    border: `1px solid ${color}30`,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "0.85rem",
    fontWeight: 700,
    color: color,
    flexShrink: 0,
  }),

  /* region pill */
  regionPill: (color, bg, border) => ({
    display: "inline-flex",
    alignItems: "center",
    gap: "5px",
    padding: "3px 10px",
    borderRadius: "100px",
    background: bg,
    color: color,
    border: `1px solid ${border}`,
    fontSize: "0.78rem",
    fontWeight: 700,
  }),

  /* action buttons */
  iconBtn: (color = "var(--text-secondary)") => ({
    background: "none",
    border: "none",
    cursor: "pointer",
    color,
    padding: "6px",
    borderRadius: "8px",
    fontSize: "1rem",
    transition: "background .15s, transform .15s",
    lineHeight: 1,
  }),

  /* select */
  select: {
    padding: "8px 12px",
    borderRadius: "10px",
    border: "1.5px solid var(--border-color)",
    background: "var(--bg-card)",
    color: "var(--text-primary)",
    fontSize: "0.85rem",
    fontWeight: 600,
    outline: "none",
    cursor: "pointer",
    transition: "border-color .2s",
  },

  /* primary button */
  btnPrimary: {
    background: "linear-gradient(135deg, #ff6600 0%, #ff8533 100%)",
    color: "#fff",
    border: "none",
    borderRadius: "10px",
    padding: "9px 18px",
    fontSize: "0.88rem",
    fontWeight: 700,
    cursor: "pointer",
    display: "inline-flex",
    alignItems: "center",
    gap: "7px",
    transition: "transform .15s, box-shadow .15s",
    boxShadow: "0 4px 12px rgba(255,102,0,.25)",
    whiteSpace: "nowrap",
  },
  btnSecondary: {
    background: "transparent",
    color: "var(--text-primary)",
    border: "1.5px solid var(--border-color)",
    borderRadius: "10px",
    padding: "9px 18px",
    fontSize: "0.88rem",
    fontWeight: 600,
    cursor: "pointer",
    transition: "background .15s",
  },

  /* form */
  formGroup: { marginBottom: "18px" },
  label: {
    display: "block",
    marginBottom: "7px",
    fontWeight: 700,
    fontSize: "0.82rem",
    color: "var(--text-secondary)",
    textTransform: "uppercase",
    letterSpacing: ".5px",
  },
  input: {
    width: "100%",
    padding: "10px 14px",
    background: "var(--bg-body)",
    border: "1.5px solid var(--border-color)",
    borderRadius: "10px",
    color: "var(--text-primary)",
    fontSize: "0.93rem",
    outline: "none",
    fontFamily: "inherit",
    transition: "border-color .2s, box-shadow .2s",
    boxSizing: "border-box",
  },
  formRow: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" },
  modalActions: {
    display: "flex",
    justifyContent: "flex-end",
    gap: "10px",
    marginTop: "24px",
    paddingTop: "16px",
    borderTop: "1px solid var(--border-color)",
  },

  /* empty / loading */
  emptyCell: {
    textAlign: "center",
    padding: "48px",
    color: "var(--text-secondary)",
    fontSize: "0.9rem",
  },
};

/* ─── component ────────────────────────────────────────────────────────────── */
const UserManagement = () => {
  const { user } = useAuth();
  const toast = useToast();

  const [users, setUsers] = useState([]);
  const [regions, setRegions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterRegion, setFilterRegion] = useState("");
  const [filterRole, setFilterRole] = useState("");
  const [hoveredRow, setHoveredRow] = useState(null);
  const [showDebug, setShowDebug] = useState(false);
  const [debugInfo, setDebugInfo] = useState({
    usersStatus: null,
    usersCount: null,
    usersError: null,
    regionsStatus: null,
    regionsData: null,
    regionsError: null,
    lastFetch: null,
  });

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [formData, setFormData] = useState({
    fullName: "",
    email: "",
    orgName: "Company",
    sector: "Energy",
    department: "",
    jobTitle: "",
    role: "user",
    location: "",
    password: "",
  });
  const [focusedField, setFocusedField] = useState(null);

  // ── Reset password modal state ───────────────────────────────────────────
  const [resetTarget, setResetTarget] = useState(null); // { id, fullName, email }
  const [resetPwd, setResetPwd] = useState("");
  const [resetPwdConfirm, setResetPwdConfirm] = useState("");
  const [resetPwdShow, setResetPwdShow] = useState(false);
  const [resetLoading, setResetLoading] = useState(false);

  // ── Delete confirmation modal state ──────────────────────────────────────
  const [deleteTargetUser, setDeleteTargetUser] = useState(null);
  const [deleteLoading, setDeleteLoading] = useState(false);



  const fetchData = async (silent = false, keepOptimistic = false) => {
    if (!silent) setLoading(true);
    const dbg = { lastFetch: new Date().toISOString() };

    // --- Users call (independent) ---
    try {
      const usersRes = await api.get("/auth/users");
      const serverUsers = usersRes.data;
      if (keepOptimistic) {
        // Merge: keep any optimistic users (temp Date.now() ids) not yet
        // returned by the server. This prevents a stale/filtered server
        // response from wiping locally-added rows before a server restart.
        const serverIds = new Set(serverUsers.map((u) => u.id));
        setUsers((prev) => {
          const optimistic = prev.filter((u) => !serverIds.has(u.id));
          return [...serverUsers, ...optimistic];
        });
      } else {
        setUsers(serverUsers);
      }
      dbg.usersStatus = usersRes.status;
      dbg.usersCount = usersRes.data?.length ?? 0;
      dbg.usersError = null;
    } catch (err) {
      dbg.usersStatus = err.response?.status ?? "NETWORK_ERR";
      dbg.usersCount = 0;
      dbg.usersError = err.response?.data?.error || err.message;
      if (!silent) toast.error("Failed to load users");
    }

    // --- Regions call (independent) ---
    try {
      const regionsRes = await api.get("/facilities/all-regions");
      const data = regionsRes.data;
      dbg.regionsStatus = regionsRes.status;
      dbg.regionsData = Array.isArray(data) ? data : JSON.stringify(data);
      dbg.regionsError = null;
      setRegions(Array.isArray(data) ? data : []);
    } catch (err) {
      dbg.regionsStatus = err.response?.status ?? "NETWORK_ERR";
      dbg.regionsData = null;
      dbg.regionsError = err.response?.data?.error || err.message;
      setRegions([]);
      // Show debug panel automatically on error so user sees it
      setShowDebug(true);
      if (!silent)
        toast.error(
          `Regions API failed (${dbg.regionsStatus}): ${dbg.regionsError}`,
        );
    }

    setDebugInfo(dbg);
    if (!silent) setLoading(false);
  };

  useEffect(() => {
    if (user?.role === "it_admin") fetchData();
  }, [user]);

  const handleOpenModal = (userToEdit = null) => {
    if (userToEdit) {
      setEditingUser(userToEdit);
      setFormData({
        fullName: userToEdit.fullName || "",
        email: userToEdit.email || "",
        orgName: userToEdit.orgName || "Company",
        sector: userToEdit.sector || "Energy",
        department: userToEdit.department || "",
        jobTitle: userToEdit.jobTitle || "",
        role: userToEdit.role || "user",
        location: userToEdit.location || "",
        password: "",
      });
    } else {
      setEditingUser(null);
      setFormData({
        fullName: "",
        email: "",
        orgName: "Company",
        sector: "Energy",
        department: "",
        jobTitle: "",
        role: "user",
        location: regions[0] || "",
        password: "",
      });
    }
    setIsModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingUser) {
        const payload = { role: formData.role, location: formData.location };
        const res = await api.put(`/auth/users/${editingUser.id}`, payload);
        const updated = res.data?.user;
        if (updated) {
          setUsers((prev) =>
            prev.map((u) => (u.id === updated.id ? { ...u, ...updated } : u)),
          );
        } else {
          setUsers((prev) =>
            prev.map((u) =>
              u.id === editingUser.id
                ? { ...u, role: formData.role, location: formData.location }
                : u,
            ),
          );
        }
        toast.success("User updated successfully");
      } else {
        // ── All validation done in JS (no native HTML5 `required`) ──
        if (!formData.fullName.trim()) {
          toast.error("Full Name is required.");
          return;
        }
        if (
          !formData.email.trim() ||
          !/^[^@]+@[^@]+\.[^@]+$/.test(formData.email)
        ) {
          toast.error("A valid Email address is required.");
          return;
        }
        if (!formData.password || formData.password.length < 10) {
          toast.error("Password must be at least 10 characters.");
          return;
        }
        if (
          ["user", "superuser"].includes(formData.role) &&
          !formData.location
        ) {
          toast.error(
            regions.length === 0
              ? "No regions loaded — restart the server and reload the page."
              : "Please select an Assigned Region for this user.",
          );
          return;
        }
        const createRes = await api.post("/auth/register", formData);
        // Optimistically prepend the new user so it shows immediately
        const newUser = createRes.data?.user || {
          id: Date.now(), // temp id, overwritten by fetchData
          fullName: formData.fullName,
          email: formData.email,
          orgName: formData.orgName,
          role: formData.role,
          location: formData.location,
          department: formData.department,
          jobTitle: formData.jobTitle,
          status: "active",
          created_at: new Date().toISOString(),
        };
        setUsers((prev) => [newUser, ...prev]);
        toast.success("User created successfully");
      }
      setIsModalOpen(false);
      // Delay background sync slightly so optimistic row renders first,
      // then merge — keeping the new user visible even if the server
      // response is still filtered (e.g. before a server restart).
      setTimeout(() => fetchData(true, true), 800);
    } catch (error) {
      const status = error.response?.status;
      const errMsg =
        error.response?.data?.error || error.message || "Failed to save user";
      console.error(
        "[UserManagement] handleSubmit failed:",
        status,
        error.response?.data,
      );
      toast.error(`${status ? `[${status}] ` : ""}${errMsg}`);
    }
  };

  const handleDelete = (target) => {
    // Accepts either user object or user id
    if (typeof target === "object" && target !== null) {
      setDeleteTargetUser(target);
    } else {
      const found = users.find((u) => u.id === target) || { id: target };
      setDeleteTargetUser(found);
    }
  };

  const handleConfirmDelete = async () => {
    if (!deleteTargetUser?.id) return;
    setDeleteLoading(true);
    const targetId = deleteTargetUser.id;
    try {
      await api.delete(`/auth/users/${targetId}`);
      setUsers((prev) => prev.filter((u) => u.id !== targetId));
      toast.success("User deleted");
      setDeleteTargetUser(null);
      fetchData(true);
    } catch (error) {
      toast.error(error.response?.data?.error || "Failed to delete user");
      fetchData(true);
    } finally {
      setDeleteLoading(false);
    }
  };

  const handleOpenResetPassword = (u) => {
    setResetTarget({ id: u.id, fullName: u.fullName, email: u.email });
    setResetPwd("");
    setResetPwdConfirm("");
    setResetPwdShow(false);
  };

  const handleResetPasswordSubmit = async (e) => {
    e.preventDefault();
    if (!resetPwd || resetPwd.length < 10) {
      toast.error("Password must be at least 10 characters.");
      return;
    }
    // Basic complexity
    if (!/[A-Z]/.test(resetPwd)) { toast.error("Password needs an uppercase letter."); return; }
    if (!/[a-z]/.test(resetPwd)) { toast.error("Password needs a lowercase letter."); return; }
    if (!/[0-9]/.test(resetPwd)) { toast.error("Password needs a digit."); return; }
    if (!/[!@#$%^&*(),.?":{}<>\-_+=\[\]\\/~`]/.test(resetPwd)) {
      toast.error("Password needs a special character."); return;
    }
    if (resetPwd !== resetPwdConfirm) {
      toast.error("Passwords do not match.");
      return;
    }
    try {
      setResetLoading(true);
      await api.post(`/auth/users/${resetTarget.id}/reset-password`, { newPassword: resetPwd });
      toast.success(`Password for ${resetTarget.fullName} has been reset successfully.`);
      setResetTarget(null);
    } catch (err) {
      toast.error(err.response?.data?.error || "Failed to reset password.");
    } finally {
      setResetLoading(false);
    }
  };

  if (user?.role !== "it_admin") {
    return (
      <div style={{ ...S.page, textAlign: "center", paddingTop: "80px" }}>
        <div style={{ marginBottom: "20px", color: "#94a3b8" }}>
          <svg width="52" height="52" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
        </div>
        <h2 style={{ color: "var(--text-primary)", margin: "0 0 8px" }}>
          Unauthorized
        </h2>
        <p style={{ color: "var(--text-secondary)" }}>
          You do not have permission to access the IT Management portal.
        </p>
      </div>
    );
  }

  /* derived stats */
  const totalUsers = users.length;
  const adminCount = users.filter((u) => u.role === "admin").length;
  const itAdminCount = users.filter((u) => u.role === "it_admin").length;
  const standardCount = users.filter((u) => u.role === "user").length;

  const filteredUsers = users.filter((u) => {
    const byRegion =
      !filterRegion ||
      u.location === filterRegion ||
      u.role === "admin" ||
      u.role === "it_admin";
    const byRole = !filterRole || u.role === filterRole;
    return byRegion && byRole;
  });

  const inputStyle = (field) => ({
    ...S.input,
    borderColor: focusedField === field ? "#ff6600" : "var(--border-color)",
    boxShadow:
      focusedField === field ? "0 0 0 3px rgba(255,102,0,.12)" : "none",
  });

  const focusProps = (field) => ({
    onFocus: () => setFocusedField(field),
    onBlur: () => setFocusedField(null),
  });

  return (
    <div style={S.page}>
      {/* ── Hero Header ── */}
      <div style={S.hero}>
        <div style={S.heroLeft}>
          <span style={S.badge}>
            <span style={S.pulseDot} />
            IT ADMIN CONSOLE
          </span>
          <h1 style={S.pageTitle}>User Management</h1>
          <p style={S.pageSubtitle}>
            Manage identities, roles, and regional workspace access
          </p>
        </div>
        <div style={S.heroRight}>
          <select
            id="um-filter-role"
            value={filterRole}
            onChange={(e) => setFilterRole(e.target.value)}
            style={S.select}
          >
            <option value="">All Roles</option>
            <option value="user">Standard User</option>
            <option value="superuser">Super User</option>
            <option value="admin">Admin</option>
            <option value="it_admin">IT Admin</option>
          </select>

          <select
            id="um-filter-region"
            value={filterRegion}
            onChange={(e) => setFilterRegion(e.target.value)}
            style={S.select}
          >
            <option value="">All Regions</option>
            {regions.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>

          <button
            id="um-add-user-btn"
            style={S.btnPrimary}
            onClick={() => handleOpenModal()}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = "translateY(-2px)";
              e.currentTarget.style.boxShadow =
                "0 8px 20px rgba(255,102,0,.35)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = "none";
              e.currentTarget.style.boxShadow =
                "0 4px 12px rgba(255,102,0,.25)";
            }}
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
            >
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            Add New User
          </button>
        </div>
      </div>

      {/* ── Debug Panel ── */}
      <div
        style={{
          marginBottom: "20px",
          border: `1.5px solid ${showDebug ? "#f59e0b" : "var(--border-color)"}`,
          borderRadius: "14px",
          overflow: "hidden",
          background: "var(--bg-card)",
          boxShadow: showDebug ? "0 0 0 3px rgba(245,158,11,.12)" : "none",
          transition: "all .2s",
        }}
      >
        <button
          onClick={() => {
            setShowDebug((s) => !s);
            if (!showDebug) fetchData(true);
          }}
          style={{
            width: "100%",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "11px 18px",
            background: showDebug ? "rgba(245,158,11,.08)" : "transparent",
            border: "none",
            cursor: "pointer",
            fontFamily: "inherit",
            fontSize: "0.82rem",
            fontWeight: 700,
            color: showDebug ? "#d97706" : "var(--text-secondary)",
            letterSpacing: ".4px",
            transition: "all .2s",
            textTransform: "uppercase",
          }}
        >
          <span style={{ display: "inline-flex", alignItems: "center", gap: "7px" }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
            API Debugger — click to{" "}
            {showDebug ? "hide" : "inspect live API calls"}
          </span>
          <span
            style={{
              fontSize: "1rem",
              transform: showDebug ? "rotate(180deg)" : "none",
              transition: "transform .2s",
            }}
          >
            ▾
          </span>
        </button>

        {showDebug && (
          <div
            style={{
              padding: "16px 20px",
              borderTop: "1px solid var(--border-color)",
              display: "flex",
              flexDirection: "column",
              gap: "14px",
            }}
          >
            {/* Refresh button */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <span
                style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}
              >
                Last fetch:{" "}
                <code
                  style={{
                    background: "var(--bg-body)",
                    padding: "2px 6px",
                    borderRadius: "4px",
                  }}
                >
                  {debugInfo.lastFetch || "not yet"}
                </code>
              </span>
              <button
                onClick={() => fetchData(true)}
                style={{
                  ...S.btnPrimary,
                  padding: "6px 14px",
                  fontSize: "0.78rem",
                  boxShadow: "none",
                }}
              >
                ↻ Re-run now
              </button>
            </div>

            {/* Users call */}
            {[
              {
                label: "GET /auth/users",
                status: debugInfo.usersStatus,
                ok: debugInfo.usersStatus === 200,
                detail: debugInfo.usersError
                  ? `Error: ${debugInfo.usersError}`
                  : `Returned ${debugInfo.usersCount} user(s)`,
              },
              {
                label: "GET /facilities/all-regions",
                status: debugInfo.regionsStatus,
                ok: debugInfo.regionsStatus === 200,
                detail: debugInfo.regionsError
                  ? `Error: ${debugInfo.regionsError}`
                  : `Returned ${Array.isArray(debugInfo.regionsData) ? debugInfo.regionsData.length : 0} region(s): ${Array.isArray(debugInfo.regionsData) ? debugInfo.regionsData.slice(0, 8).join(", ") + (debugInfo.regionsData.length > 8 ? "…" : "") : debugInfo.regionsData}`,
              },
            ].map((row) => (
              <div
                key={row.label}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: "12px",
                  padding: "12px 14px",
                  borderRadius: "10px",
                  background: row.ok
                    ? "rgba(16,185,129,.06)"
                    : row.status === null
                      ? "rgba(100,116,139,.06)"
                      : "rgba(239,68,68,.06)",
                  border: `1px solid ${row.ok ? "rgba(16,185,129,.2)" : row.status === null ? "rgba(100,116,139,.15)" : "rgba(239,68,68,.2)"}`,
                }}
              >
                <span
                  style={{
                    flexShrink: 0,
                    width: "52px",
                    textAlign: "center",
                    padding: "2px 0",
                    borderRadius: "6px",
                    fontWeight: 800,
                    fontSize: "0.8rem",
                    background: row.ok
                      ? "#ecfdf5"
                      : row.status === null
                        ? "#f1f5f9"
                        : "#fef2f2",
                    color: row.ok
                      ? "#059669"
                      : row.status === null
                        ? "#64748b"
                        : "#dc2626",
                  }}
                >
                  {row.status ?? "—"}
                </span>
                <div>
                  <div
                    style={{
                      fontWeight: 700,
                      fontSize: "0.82rem",
                      fontFamily: "monospace",
                      color: "var(--text-primary)",
                      marginBottom: "3px",
                    }}
                  >
                    {row.label}
                  </div>
                  <div
                    style={{
                      fontSize: "0.78rem",
                      color: row.ok
                        ? "#059669"
                        : row.status === null
                          ? "var(--text-secondary)"
                          : "#dc2626",
                    }}
                  >
                    {row.status === null ? "Not fetched yet" : row.detail}
                  </div>
                </div>
              </div>
            ))}

            <p
              style={{
                margin: 0,
                fontSize: "0.72rem",
                color: "var(--text-secondary)",
                fontStyle: "italic",
              }}
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ display: "inline", verticalAlign: "middle", marginRight: "4px" }}><line x1="9" y1="18" x2="15" y2="18"/><line x1="10" y1="22" x2="14" y2="22"/><path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 0 1 8.91 14"/></svg>
              If /facilities/all-regions returns 404 → server needs restart.
              If 403 → auth issue. If 200 but empty → no region values in DB.
            </p>
          </div>
        )}
      </div>

      {/* ── Stats Row ── */}

      <div style={S.statsRow}>
        {[
          {
            label: "Total Users",
            value: totalUsers,
            icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>,
            color: "#6366f1",
            bg: "#eef2ff",
          },
          {
            label: "Standard Users",
            value: standardCount,
            icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>,
            color: "#3b82f6",
            bg: "#eff6ff",
          },
          {
            label: "Admins",
            value: adminCount,
            icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>,
            color: "#10b981",
            bg: "#ecfdf5",
          },
          {
            label: "IT Admins",
            value: itAdminCount,
            icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>,
            color: "#f59e0b",
            bg: "#fffbeb",
          },
          {
            label: "Regions",
            value: regions.length,
            icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>,
            color: "#ff6600",
            bg: "#fff7ed",
          },
        ].map((stat) => (
          <div
            key={stat.label}
            style={S.statCard}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = "translateY(-3px)";
              e.currentTarget.style.boxShadow = "0 8px 24px rgba(0,0,0,.08)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = "none";
              e.currentTarget.style.boxShadow = "0 2px 8px rgba(0,0,0,.04)";
            }}
          >
            <div
              style={{ ...S.statIcon, background: stat.bg, color: stat.color }}
            >
              {stat.icon}
            </div>
            <div style={S.statValue}>{loading ? "—" : stat.value}</div>
            <div style={S.statLabel}>{stat.label}</div>
          </div>
        ))}
      </div>

      {/* ── Users Table ── */}
      <div style={S.tableCard}>
        <div style={S.tableToolbar}>
          <div>
            <p style={S.tableCardTitle}>Registered Users</p>
            <p style={S.tableCardSub}>
              {loading
                ? "Loading…"
                : `${filteredUsers.length} of ${totalUsers} users shown`}
            </p>
          </div>
        </div>

        <div style={S.tableWrap}>
          <table style={S.table}>
            <thead>
              <tr>
                {[
                  "User",
                  "Email",
                  "Department / Job Title",
                  "Role",
                  "Region Access",
                  "Joined",
                  "Actions",
                ].map((h) => (
                  <th key={h} style={S.th}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="7" style={S.emptyCell}>
                    <div
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        gap: "10px",
                      }}
                    >
                      <svg
                        width="32"
                        height="32"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="#ff6600"
                        strokeWidth="2"
                        style={{ animation: "spin 1s linear infinite" }}
                      >
                        <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
                      </svg>
                      Loading users…
                    </div>
                  </td>
                </tr>
              ) : filteredUsers.length === 0 ? (
                <tr>
                  <td colSpan="7" style={S.emptyCell}>
                    <div
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        gap: "8px",
                      }}
                    >
                      <span style={{ color: "var(--text-secondary)" }}><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg></span>
                      No users match the current filters.
                    </div>
                  </td>
                </tr>
              ) : (
                filteredUsers.map((u, idx) => {
                  const meta = getRoleMeta(u.role);
                  const initials = (u.fullName || "?")
                    .split(" ")
                    .map((n) => n[0])
                    .join("")
                    .slice(0, 2)
                    .toUpperCase();
                  const isHovered = hoveredRow === u.id;

                  return (
                    <tr
                      key={u.id}
                      onMouseEnter={() => setHoveredRow(u.id)}
                      onMouseLeave={() => setHoveredRow(null)}
                      style={{
                        background: isHovered
                          ? "var(--bg-hover)"
                          : "transparent",
                        transition: "background .15s",
                        animation: `um-slide-in .3s ease ${idx * 40}ms both`,
                      }}
                    >
                      {/* User */}
                      <td style={S.td}>
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "10px",
                          }}
                        >
                          <div style={S.avatar(meta.color)}>{initials}</div>
                          <div>
                            <div
                              style={{
                                fontWeight: 700,
                                color: "var(--text-primary)",
                                lineHeight: 1.2,
                              }}
                            >
                              {u.fullName}
                            </div>
                            <div
                              style={{
                                fontSize: "0.75rem",
                                color: "var(--text-secondary)",
                                marginTop: "2px",
                              }}
                            >
                              {u.orgName || "—"}
                            </div>
                          </div>
                        </div>
                      </td>

                      {/* Email */}
                      <td
                        style={{
                          ...S.td,
                          color: "var(--text-secondary)",
                          fontFamily: "monospace",
                          fontSize: "0.82rem",
                        }}
                      >
                        {u.email}
                      </td>

                      {/* Department / Job Title */}
                      <td style={S.td}>
                        {u.department || u.jobTitle ? (
                          <div>
                            {u.department && (
                              <div
                                style={{
                                  fontWeight: 600,
                                  color: "var(--text-primary)",
                                  fontSize: "0.85rem",
                                }}
                              >
                                {u.department}
                              </div>
                            )}
                            {u.jobTitle && (
                              <div
                                style={{
                                  fontSize: "0.75rem",
                                  color: "var(--text-secondary)",
                                  marginTop: "2px",
                                }}
                              >
                                {u.jobTitle}
                              </div>
                            )}
                          </div>
                        ) : (
                          <span
                            style={{
                              color: "var(--text-secondary)",
                              fontStyle: "italic",
                              fontSize: "0.8rem",
                            }}
                          >
                            Not set
                          </span>
                        )}
                      </td>

                      {/* Role */}
                      <td style={S.td}>
                        <span
                          style={S.regionPill(meta.color, meta.bg, meta.border)}
                        >
                          {meta.label}
                        </span>
                      </td>

                      {/* Region Access */}
                      <td style={S.td}>
                        {u.role === "admin" ? (
                          <span
                            style={S.regionPill(
                              "#10b981",
                              "#ecfdf5",
                              "rgba(16,185,129,.25)",
                            )}
                          >
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
                            All Regions
                          </span>
                        ) : u.role === "it_admin" ? (
                          <span
                            style={S.regionPill(
                              "#ef4444",
                              "#fef2f2",
                              "rgba(239,68,68,.25)",
                            )}
                          >
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                            No Data Access
                          </span>
                        ) : u.location ? (
                          <span
                            style={S.regionPill(
                              "#ff6600",
                              "#fff7ed",
                              "rgba(255,102,0,.25)",
                            )}
                          >
                            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
                            {u.location}
                          </span>
                        ) : (
                          <span
                            style={{
                              color: "var(--text-secondary)",
                              fontStyle: "italic",
                              fontSize: "0.8rem",
                            }}
                          >
                            None
                          </span>
                        )}
                      </td>

                      {/* Joined */}
                      <td
                        style={{
                          ...S.td,
                          color: "var(--text-secondary)",
                          fontSize: "0.8rem",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {u.created_at
                          ? new Date(u.created_at).toLocaleDateString("en-GB", {
                              day: "2-digit",
                              month: "short",
                              year: "numeric",
                            })
                          : "—"}
                      </td>

                      {/* Actions */}
                      <td style={{ ...S.td, whiteSpace: "nowrap" }}>
                        <button
                          id={`um-edit-btn-${u.id}`}
                          style={S.iconBtn("#6366f1")}
                          onClick={() => handleOpenModal(u)}
                          title="Edit Role / Region"
                          onMouseEnter={(e) =>
                            (e.currentTarget.style.background = "#eef2ff")
                          }
                          onMouseLeave={(e) =>
                            (e.currentTarget.style.background = "none")
                          }
                        >
                          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                        </button>
                        <button
                          id={`um-reset-pwd-btn-${u.id}`}
                          style={S.iconBtn("#f59e0b")}
                          onClick={() => handleOpenResetPassword(u)}
                          title="Reset Password"
                          onMouseEnter={(e) =>
                            (e.currentTarget.style.background = "#fffbeb")
                          }
                          onMouseLeave={(e) =>
                            (e.currentTarget.style.background = "none")
                          }
                        >
                          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/></svg>
                        </button>
                        <button
                          id={`um-delete-btn-${u.id}`}
                          style={S.iconBtn("#ef4444")}
                          onClick={() => handleDelete(u.id)}
                          title="Revoke Access"
                          onMouseEnter={(e) =>
                            (e.currentTarget.style.background = "#fef2f2")
                          }
                          onMouseLeave={(e) =>
                            (e.currentTarget.style.background = "none")
                          }
                        >
                          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Modal ── */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={
          editingUser ? "Edit User Permissions" : "Register New User"
        }
        maxWidth="540px"
      >
        <form onSubmit={handleSubmit}>
          {/* Identity section (disabled when editing) */}
          <div style={{ ...S.formRow, marginBottom: 0 }}>
            <div style={S.formGroup}>
              <label style={S.label}>Full Name</label>
              <input
                id="um-modal-fullname"
                type="text"
                value={formData.fullName}
                onChange={(e) =>
                  setFormData({ ...formData, fullName: e.target.value })
                }
                disabled={!!editingUser}
                style={{
                  ...inputStyle("fullName"),
                  opacity: editingUser ? 0.55 : 1,
                }}
                {...focusProps("fullName")}
                placeholder="Jane Smith"
              />
            </div>
            <div style={S.formGroup}>
              <label style={S.label}>Email Address</label>
              <input
                id="um-modal-email"
                type="text"
                value={formData.email}
                onChange={(e) =>
                  setFormData({ ...formData, email: e.target.value })
                }
                disabled={!!editingUser}
                style={{
                  ...inputStyle("email"),
                  opacity: editingUser ? 0.55 : 1,
                }}
                {...focusProps("email")}
                placeholder="jane@company.com"
              />
            </div>
          </div>

          {!editingUser && (
            <>
              <div style={S.formRow}>
                <div style={S.formGroup}>
                  <label style={S.label}>Department</label>
                  <input
                    id="um-modal-department"
                    type="text"
                    value={formData.department}
                    onChange={(e) =>
                      setFormData({ ...formData, department: e.target.value })
                    }
                    style={inputStyle("department")}
                    {...focusProps("department")}
                    placeholder="e.g. Engineering"
                  />
                </div>
                <div style={S.formGroup}>
                  <label style={S.label}>Job Title</label>
                  <input
                    id="um-modal-jobtitle"
                    type="text"
                    value={formData.jobTitle}
                    onChange={(e) =>
                      setFormData({ ...formData, jobTitle: e.target.value })
                    }
                    style={inputStyle("jobTitle")}
                    {...focusProps("jobTitle")}
                    placeholder="e.g. Data Analyst"
                  />
                </div>
              </div>

              <div style={S.formGroup}>
                <label style={S.label}>
                  Temporary Password (min 10 characters)
                </label>
                <input
                  id="um-modal-password"
                  type="text"
                  value={formData.password}
                  onChange={(e) =>
                    setFormData({ ...formData, password: e.target.value })
                  }
                  style={{
                    ...inputStyle("password"),
                    borderColor:
                      formData.password && formData.password.length < 10
                        ? "#ef4444"
                        : focusedField === "password"
                          ? "#ff6600"
                          : "var(--border-color)",
                    boxShadow:
                      formData.password && formData.password.length < 10
                        ? "0 0 0 3px rgba(239,68,68,.1)"
                        : focusedField === "password"
                          ? "0 0 0 3px rgba(255,102,0,.12)"
                          : "none",
                  }}
                  {...focusProps("password")}
                  placeholder="Minimum 10 characters"
                />
                {formData.password && formData.password.length < 10 && (
                  <p
                    style={{
                      fontSize: "0.75rem",
                      color: "#ef4444",
                      marginTop: "4px",
                    }}
                  >
                    {formData.password.length}/10 characters — need{" "}
                    {10 - formData.password.length} more
                  </p>
                )}
              </div>
            </>
          )}

          <div style={S.formRow}>
            <div style={S.formGroup}>
              <label style={S.label}>System Role</label>
              <select
                id="um-modal-role"
                value={formData.role}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    role: e.target.value,
                    location: ["user", "superuser"].includes(e.target.value)
                      ? formData.location || regions[0] || ""
                      : "",
                  })
                }
                style={{ ...inputStyle("role"), cursor: "pointer" }}
                {...focusProps("role")}
              >
                <option value="user">Standard User</option>
                <option value="superuser">Super User</option>
                <option value="admin">Admin (All Data)</option>
                <option value="it_admin">IT Admin</option>
              </select>
            </div>

            {["user", "superuser"].includes(formData.role) && (
              <div style={S.formGroup}>
                <label style={S.label}>Assigned Region</label>
                <select
                  id="um-modal-region"
                  value={formData.location}
                  onChange={(e) =>
                    setFormData({ ...formData, location: e.target.value })
                  }
                  style={{
                    ...inputStyle("location"),
                    cursor: "pointer",
                    // Red border highlight when empty to signal required
                    borderColor: !formData.location
                      ? "#ef4444"
                      : focusedField === "location"
                        ? "#ff6600"
                        : "var(--border-color)",
                    boxShadow: !formData.location
                      ? "0 0 0 3px rgba(239,68,68,.1)"
                      : focusedField === "location"
                        ? "0 0 0 3px rgba(255,102,0,.12)"
                        : "none",
                  }}
                  {...focusProps("location")}
                >
                  <option value="">— Select a Region —</option>
                  {regions.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
                {regions.length === 0 ? (
                  <p
                    style={{
                      fontSize: "0.75rem",
                      color: "#ef4444",
                      marginTop: "4px",
                      display: "flex",
                      alignItems: "center",
                      gap: "4px",
                    }}
                  >
                    ⚠️ No regions loaded — use the 🔧 API Debugger above to
                    diagnose.
                  </p>
                ) : !formData.location ? (
                  <p
                    style={{
                      fontSize: "0.75rem",
                      color: "#ef4444",
                      marginTop: "4px",
                    }}
                  >
                    ↑ Required — pick a region to proceed.
                  </p>
                ) : null}
              </div>
            )}
          </div>

          <div style={S.modalActions}>
            <button
              id="um-modal-cancel"
              type="button"
              style={S.btnSecondary}
              onClick={() => setIsModalOpen(false)}
              onMouseEnter={(e) =>
                (e.currentTarget.style.background = "var(--bg-hover)")
              }
              onMouseLeave={(e) =>
                (e.currentTarget.style.background = "transparent")
              }
            >
              Cancel
            </button>
            <button
              id="um-modal-submit"
              type="submit"
              style={S.btnPrimary}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = "translateY(-1px)";
                e.currentTarget.style.boxShadow =
                  "0 8px 20px rgba(255,102,0,.35)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = "none";
                e.currentTarget.style.boxShadow =
                  "0 4px 12px rgba(255,102,0,.25)";
              }}
            >
              {editingUser ? (
                <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
                  Save Changes
                </span>
              ) : (
                <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                  Create User
                </span>
              )}
            </button>
          </div>
        </form>
      </Modal>

      {/* ── Reset Password Modal ── */}
      <Modal
        isOpen={!!resetTarget}
        onClose={() => setResetTarget(null)}
        title="Reset User Password"
        maxWidth="480px"
      >
        {resetTarget && (
          <form onSubmit={handleResetPasswordSubmit}>
            {/* Target user info */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "12px",
                padding: "12px 14px",
                borderRadius: "12px",
                background: "rgba(245,158,11,.08)",
                border: "1px solid rgba(245,158,11,.25)",
                marginBottom: "20px",
              }}
            >
              <span style={{ color: "#f59e0b" }}><svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg></span>
              <div>
                <div style={{ fontWeight: 700, color: "var(--text-primary)", fontSize: "0.95rem" }}>
                  {resetTarget.fullName}
                </div>
                <div style={{ fontSize: "0.78rem", color: "var(--text-secondary)", fontFamily: "monospace" }}>
                  {resetTarget.email}
                </div>
              </div>
            </div>

            {/* Security warning */}
            <div
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: "8px",
                padding: "10px 14px",
                borderRadius: "10px",
                background: "rgba(239,68,68,.06)",
                border: "1px solid rgba(239,68,68,.2)",
                marginBottom: "20px",
                fontSize: "0.8rem",
                color: "#dc2626",
              }}
            >
              <span style={{ flexShrink: 0 }}><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg></span>
              <span>
                You are about to reset this user's password. They will receive a security notification
                and must use the new password immediately.
              </span>
            </div>

            {/* New password */}
            <div style={S.formGroup}>
              <label style={S.label}>New Password</label>
              <div style={{ position: "relative" }}>
                <input
                  id="um-reset-pwd-input"
                  type={resetPwdShow ? "text" : "password"}
                  value={resetPwd}
                  onChange={(e) => setResetPwd(e.target.value)}
                  style={{
                    ...S.input,
                    paddingRight: "44px",
                    borderColor:
                      resetPwd && resetPwd.length < 10
                        ? "#ef4444"
                        : focusedField === "resetPwd"
                        ? "#f59e0b"
                        : "var(--border-color)",
                    boxShadow:
                      resetPwd && resetPwd.length < 10
                        ? "0 0 0 3px rgba(239,68,68,.1)"
                        : focusedField === "resetPwd"
                        ? "0 0 0 3px rgba(245,158,11,.15)"
                        : "none",
                  }}
                  onFocus={() => setFocusedField("resetPwd")}
                  onBlur={() => setFocusedField(null)}
                  placeholder="Min 10 chars · Aa1!..."
                  autoComplete="new-password"
                />
                <button
                  type="button"
                  onClick={() => setResetPwdShow((s) => !s)}
                  style={{
                    position: "absolute",
                    right: "12px",
                    top: "50%",
                    transform: "translateY(-50%)",
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    color: "var(--text-secondary)",
                    fontSize: "1rem",
                    lineHeight: 1,
                    padding: 0,
                  }}
                  title={resetPwdShow ? "Hide" : "Show"}
                >
                  {resetPwdShow ? (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                  ) : (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                  )}
                </button>
              </div>
              {/* Strength indicator */}
              {resetPwd && (
                <div style={{ marginTop: "6px", display: "flex", gap: "4px" }}>
                  {[
                    resetPwd.length >= 10,
                    /[A-Z]/.test(resetPwd),
                    /[a-z]/.test(resetPwd),
                    /[0-9]/.test(resetPwd),
                    /[!@#$%^&*(),.?":{}<>\-_]/.test(resetPwd),
                  ].map((ok, i) => (
                    <div
                      key={i}
                      style={{
                        flex: 1,
                        height: "4px",
                        borderRadius: "2px",
                        background: ok ? "#10b981" : "var(--border-color)",
                        transition: "background .2s",
                      }}
                    />
                  ))}
                </div>
              )}
              {resetPwd && (
                <p style={{ fontSize: "0.72rem", color: "var(--text-secondary)", marginTop: "4px" }}>
                  Requirements: 10+ chars · Uppercase · Lowercase · Digit · Special char
                </p>
              )}
            </div>

            {/* Confirm password */}
            <div style={S.formGroup}>
              <label style={S.label}>Confirm New Password</label>
              <input
                id="um-reset-pwd-confirm"
                type={resetPwdShow ? "text" : "password"}
                value={resetPwdConfirm}
                onChange={(e) => setResetPwdConfirm(e.target.value)}
                style={{
                  ...S.input,
                  borderColor:
                    resetPwdConfirm && resetPwdConfirm !== resetPwd
                      ? "#ef4444"
                      : focusedField === "resetPwdConfirm"
                      ? "#f59e0b"
                      : "var(--border-color)",
                  boxShadow:
                    resetPwdConfirm && resetPwdConfirm !== resetPwd
                      ? "0 0 0 3px rgba(239,68,68,.1)"
                      : "none",
                }}
                onFocus={() => setFocusedField("resetPwdConfirm")}
                onBlur={() => setFocusedField(null)}
                placeholder="Re-enter the password"
                autoComplete="new-password"
              />
              {resetPwdConfirm && resetPwdConfirm !== resetPwd && (
                <p style={{ fontSize: "0.75rem", color: "#ef4444", marginTop: "4px" }}>
                  ✗ Passwords do not match
                </p>
              )}
              {resetPwdConfirm && resetPwdConfirm === resetPwd && resetPwd.length >= 10 && (
                <p style={{ fontSize: "0.75rem", color: "#10b981", marginTop: "4px" }}>
                  ✓ Passwords match
                </p>
              )}
            </div>

            <div style={S.modalActions}>
              <button
                id="um-reset-pwd-cancel"
                type="button"
                style={S.btnSecondary}
                onClick={() => setResetTarget(null)}
                onMouseEnter={(e) =>
                  (e.currentTarget.style.background = "var(--bg-hover)")
                }
                onMouseLeave={(e) =>
                  (e.currentTarget.style.background = "transparent")
                }
              >
                Cancel
              </button>
              <button
                id="um-reset-pwd-submit"
                type="submit"
                disabled={resetLoading || resetPwd !== resetPwdConfirm || resetPwd.length < 10}
                style={{
                  ...S.btnPrimary,
                  background: "linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%)",
                  boxShadow: "0 4px 12px rgba(245,158,11,.3)",
                  opacity: (resetLoading || resetPwd !== resetPwdConfirm || resetPwd.length < 10) ? 0.6 : 1,
                  cursor: (resetLoading || resetPwd !== resetPwdConfirm || resetPwd.length < 10) ? "not-allowed" : "pointer",
                }}
              >
                {resetLoading ? "Resetting…" : (
                  <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/></svg>
                    Reset Password
                  </span>
                )}
              </button>
            </div>
          </form>
        )}
      </Modal>

      <ConfirmModal
        isOpen={!!deleteTargetUser}
        title="Revoke User Access"
        message={`Are you sure you want to permanently revoke access for ${deleteTargetUser?.fullName ? `"${deleteTargetUser.fullName}"` : "this user"} (${deleteTargetUser?.email || "selected account"})? This action cannot be undone.`}
        confirmLabel="Revoke Access"
        confirmVariant="danger"
        loading={deleteLoading}
        onConfirm={handleConfirmDelete}
        onCancel={() => setDeleteTargetUser(null)}
      />
    </div>
  );
};

export default UserManagement;
