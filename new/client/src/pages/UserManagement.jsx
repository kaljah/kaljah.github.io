import React, { useState, useEffect } from "react";
import api from "../api";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../components/Toast";
import Drawer from "../components/Drawer";
import ConfirmModal from "../components/ConfirmModal";
import {
  UserPlus,
  UserCheck,
  KeyRound,
  Lock,
  Shield,
  Eye,
  EyeOff,
  Check,
  User,
  Mail,
  Briefcase,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";

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
  it: {
    label: "IT",
    color: "#0284c7",
    bg: "#f0f9ff",
    border: "rgba(2,132,199,.25)",
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
    maxWidth: "1600px",
    width: "100%",
    margin: "0 auto",
    animation: "um-fade-in .4s ease both",
    boxSizing: "border-box",
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
  drawerSection: {
    background: "var(--bg-card)",
    border: "1px solid var(--border-color)",
    borderRadius: "14px",
    padding: "16px 18px",
    marginBottom: "16px",
  },
  sectionHeader: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    marginBottom: "14px",
  },
  sectionIconBadge: (color) => ({
    width: "26px",
    height: "26px",
    borderRadius: "8px",
    background: `${color}18`,
    color: color,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
  }),
  sectionTitle: {
    fontSize: "0.82rem",
    fontWeight: 700,
    color: "var(--text-primary)",
    textTransform: "uppercase",
    letterSpacing: "0.5px",
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
    } catch {
      if (!silent) toast.error("Failed to load users");
    }

    // --- Regions call (independent) ---
    try {
      const regionsRes = await api.get("/facilities/all-regions");
      const data = regionsRes.data;
      setRegions(Array.isArray(data) ? data : []);
    } catch {
      setRegions([]);
      if (!silent) toast.error("Failed to load facility regions");
    }

    if (!silent) setLoading(false);
  };

  useEffect(() => {
    if (["it_admin", "it"].includes(user?.role)) fetchData();
  }, [user]);

  const handleOpenModal = (userToEdit = null) => {
    if (user?.role === "it") return;
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
    if (user?.role === "it") {
      toast.error("IT role cannot modify user accounts or profiles.");
      return;
    }
    try {
      if (editingUser) {
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

        const payload = {
          fullName: formData.fullName.trim(),
          email: formData.email.trim(),
          department: (formData.department || "").trim(),
          jobTitle: (formData.jobTitle || "").trim(),
          role: formData.role,
          location: formData.location,
        };
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
                ? {
                    ...u,
                    fullName: payload.fullName,
                    email: payload.email,
                    department: payload.department,
                    jobTitle: payload.jobTitle,
                    role: formData.role,
                    location: formData.location,
                  }
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
    if (user?.role === "it") {
      toast.error("IT role cannot delete users.");
      return;
    }
    // Accepts either user object or user id
    if (typeof target === "object" && target !== null) {
      setDeleteTargetUser(target);
    } else {
      const found = users.find((u) => u.id === target) || { id: target };
      setDeleteTargetUser(found);
    }
  };

  const handleConfirmDelete = async () => {
    if (user?.role === "it") {
      toast.error("IT role cannot delete users.");
      return;
    }
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
    setResetTarget({
      id: u.id,
      fullName: u.fullName,
      email: u.email,
      role: u.role,
      location: u.location,
      department: u.department,
    });
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
    if (!/[!@#$%^&*(),.?":{}<>\-_+=[\]\\/~`]/.test(resetPwd)) {
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

  if (!["it_admin", "it"].includes(user?.role)) {
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

  const isITOnly = user?.role === "it";

  /* derived stats */
  const totalUsers = users.length;
  const adminCount = users.filter((u) => u.role === "admin").length;
  const itAdminCount = users.filter((u) => u.role === "it_admin").length;
  const itCount = users.filter((u) => u.role === "it").length;
  const standardCount = users.filter((u) => u.role === "user").length;

  const filteredUsers = users.filter((u) => {
    const byRegion =
      !filterRegion ||
      u.location === filterRegion ||
      u.role === "admin" ||
      u.role === "it_admin" ||
      u.role === "it";
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
            {isITOnly ? "IT CREDENTIALS CONSOLE" : "IT ADMIN CONSOLE"}
          </span>
          <h1 style={S.pageTitle}>User Management</h1>
          <p style={S.pageSubtitle}>
            {isITOnly
              ? "Modify user passwords and manage credentials"
              : "Manage identities, roles, and regional workspace access"}
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
            <option value="it">IT</option>
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

          {!isITOnly && (
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
          )}
        </div>
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
                        ) : u.role === "it_admin" || u.role === "it" ? (
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
                        {!isITOnly && (
                          <button
                            id={`um-edit-btn-${u.id}`}
                            style={S.iconBtn("#6366f1")}
                            onClick={() => handleOpenModal(u)}
                            title="Edit User Information"
                            onMouseEnter={(e) =>
                              (e.currentTarget.style.background = "#eef2ff")
                            }
                            onMouseLeave={(e) =>
                              (e.currentTarget.style.background = "none")
                            }
                          >
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                          </button>
                        )}
                        <button
                          id={`um-reset-pwd-btn-${u.id}`}
                          style={S.iconBtn("#f59e0b")}
                          onClick={() => handleOpenResetPassword(u)}
                          title="Modify / Reset Password"
                          onMouseEnter={(e) =>
                            (e.currentTarget.style.background = "#fffbeb")
                          }
                          onMouseLeave={(e) =>
                            (e.currentTarget.style.background = "none")
                          }
                        >
                          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/></svg>
                        </button>
                        {!isITOnly && (
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
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Slide-Over Drawer: Add / Edit User ── */}
      <Drawer
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingUser ? "Edit User Information" : "Register New User"}
        subtitle={
          editingUser
            ? `Update profile details for ${editingUser.fullName || editingUser.email}`
            : "Provision a new system identity and configure role access"
        }
        icon={editingUser ? UserCheck : UserPlus}
        iconColor={editingUser ? "#6366f1" : "#ff6600"}
        iconBg={editingUser ? "rgba(99, 102, 241, 0.12)" : "rgba(255, 102, 0, 0.12)"}
        width="560px"
        footer={
          <>
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
              form="um-user-form"
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
                  <UserCheck size={16} />
                  Save Changes
                </span>
              ) : (
                <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <UserPlus size={16} />
                  Create User
                </span>
              )}
            </button>
          </>
        }
      >
        <form id="um-user-form" onSubmit={handleSubmit}>
          {/* Section 1: Profile & Identity */}
          <div style={S.drawerSection}>
            <div style={S.sectionHeader}>
              <span style={S.sectionIconBadge("#6366f1")}>
                <User size={14} />
              </span>
              <span style={S.sectionTitle}>Profile & Identity</span>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div style={S.formGroup}>
                <label style={S.label}>
                  Full Name <span style={{ color: "#ef4444" }}>*</span>
                </label>
                <input
                  id="um-modal-fullname"
                  type="text"
                  value={formData.fullName}
                  onChange={(e) =>
                    setFormData({ ...formData, fullName: e.target.value })
                  }
                  style={inputStyle("fullName")}
                  {...focusProps("fullName")}
                  placeholder="e.g. Jane Smith"
                />
              </div>

              <div style={S.formGroup}>
                <label style={S.label}>
                  Email Address <span style={{ color: "#ef4444" }}>*</span>
                </label>
                <input
                  id="um-modal-email"
                  type="email"
                  value={formData.email}
                  onChange={(e) =>
                    setFormData({ ...formData, email: e.target.value })
                  }
                  style={inputStyle("email")}
                  {...focusProps("email")}
                  placeholder="e.g. jane.smith@company.com"
                />
              </div>
            </div>
          </div>

          {/* Section 2: Organization & Title */}
          <div style={S.drawerSection}>
            <div style={S.sectionHeader}>
              <span style={S.sectionIconBadge("#0ea5e9")}>
                <Briefcase size={14} />
              </span>
              <span style={S.sectionTitle}>Organization & Title</span>
            </div>

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
                  placeholder="e.g. Lead Carbon Analyst"
                />
              </div>
            </div>
          </div>

          {/* Section 3: Access Governance & Scope */}
          <div style={S.drawerSection}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
              <div style={{ ...S.sectionHeader, marginBottom: 0 }}>
                <span style={S.sectionIconBadge("#f59e0b")}>
                  <Shield size={14} />
                </span>
                <span style={S.sectionTitle}>Access Governance & Scope</span>
              </div>
              {editingUser && (
                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "4px",
                    padding: "3px 8px",
                    borderRadius: "6px",
                    background: "rgba(100, 116, 139, 0.1)",
                    color: "var(--text-secondary)",
                    fontSize: "0.72rem",
                    fontWeight: 600,
                  }}
                >
                  <Lock size={11} /> Locked by Policy
                </span>
              )}
            </div>

            {editingUser && (
              <div
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: "8px",
                  padding: "10px 12px",
                  borderRadius: "8px",
                  background: "rgba(100, 116, 139, 0.06)",
                  border: "1px dashed var(--border-color)",
                  marginBottom: "14px",
                  fontSize: "0.76rem",
                  color: "var(--text-secondary)",
                  lineHeight: 1.4,
                }}
              >
                <Lock size={13} style={{ flexShrink: 0, marginTop: "2px", color: "var(--text-secondary)" }} />
                <span>
                  Role and regional assignments are fixed by administrative governance and locked against profile modification.
                </span>
              </div>
            )}

            <div style={S.formRow}>
              <div style={S.formGroup}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "7px" }}>
                  <label style={{ ...S.label, marginBottom: 0 }}>System Role</label>
                  {editingUser && (
                    <span style={{ fontSize: "0.7rem", color: "var(--text-secondary)", display: "inline-flex", alignItems: "center", gap: "3px" }}>
                      <Lock size={10} /> Locked
                    </span>
                  )}
                </div>
                <select
                  id="um-modal-role"
                  value={formData.role}
                  disabled={!!editingUser}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      role: e.target.value,
                      location: ["user", "superuser"].includes(e.target.value)
                        ? formData.location || regions[0] || ""
                        : "",
                    })
                  }
                  style={{
                    ...inputStyle("role"),
                    cursor: editingUser ? "not-allowed" : "pointer",
                    opacity: editingUser ? 0.75 : 1,
                    background: editingUser ? "var(--bg-body)" : "var(--bg-card)",
                  }}
                  {...(!editingUser ? focusProps("role") : {})}
                >
                  <option value="user">Standard User</option>
                  <option value="superuser">Super User</option>
                  <option value="admin">Admin (All Data)</option>
                  <option value="it_admin">IT Admin</option>
                  <option value="it">IT</option>
                </select>
              </div>

              {(["user", "superuser"].includes(formData.role) || formData.location) && (
                <div style={S.formGroup}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "7px" }}>
                    <label style={{ ...S.label, marginBottom: 0 }}>Assigned Region</label>
                    {editingUser && (
                      <span style={{ fontSize: "0.7rem", color: "var(--text-secondary)", display: "inline-flex", alignItems: "center", gap: "3px" }}>
                        <Lock size={10} /> Locked
                      </span>
                    )}
                  </div>
                  <select
                    id="um-modal-region"
                    value={formData.location}
                    disabled={!!editingUser}
                    onChange={(e) =>
                      setFormData({ ...formData, location: e.target.value })
                    }
                    style={{
                      ...inputStyle("location"),
                      cursor: editingUser ? "not-allowed" : "pointer",
                      opacity: editingUser ? 0.75 : 1,
                      background: editingUser ? "var(--bg-body)" : "var(--bg-card)",
                      borderColor:
                        !editingUser && !formData.location
                          ? "#ef4444"
                          : focusedField === "location"
                          ? "#ff6600"
                          : "var(--border-color)",
                    }}
                    {...(!editingUser ? focusProps("location") : {})}
                  >
                    <option value="">— Select a Region —</option>
                    {regions.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                  {!editingUser && !formData.location && (
                    <p style={{ fontSize: "0.72rem", color: "#ef4444", marginTop: "4px" }}>
                      ↑ Required — choose an assigned region
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Section 4: Initial Password (Register only) */}
          {!editingUser && (
            <div style={S.drawerSection}>
              <div style={S.sectionHeader}>
                <span style={S.sectionIconBadge("#10b981")}>
                  <KeyRound size={14} />
                </span>
                <span style={S.sectionTitle}>Initial Credentials</span>
              </div>

              <div style={S.formGroup}>
                <label style={S.label}>
                  Temporary Password <span style={{ color: "#ef4444" }}>*</span>
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
                  }}
                  {...focusProps("password")}
                  placeholder="Minimum 10 characters"
                />
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "6px" }}>
                  <span style={{ fontSize: "0.74rem", color: formData.password.length >= 10 ? "#10b981" : "#94a3b8" }}>
                    {formData.password.length >= 10 ? "✓ Meets minimum length requirement" : "Requires at least 10 characters"}
                  </span>
                  <span style={{ fontSize: "0.74rem", fontWeight: 600, color: formData.password.length >= 10 ? "#10b981" : "#ef4444" }}>
                    {formData.password.length}/10 chars
                  </span>
                </div>
              </div>
            </div>
          )}
        </form>
      </Drawer>

      {/* ── Slide-Over Drawer: Reset Password ── */}
      <Drawer
        isOpen={!!resetTarget}
        onClose={() => setResetTarget(null)}
        title="Reset User Password"
        subtitle={resetTarget ? `Administrative credential overwrite for ${resetTarget.email}` : ""}
        icon={KeyRound}
        iconColor="#f59e0b"
        iconBg="rgba(245, 158, 11, 0.12)"
        width="540px"
        footer={
          <>
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
              form="um-reset-pwd-form"
              disabled={resetLoading || resetPwd !== resetPwdConfirm || resetPwd.length < 10}
              style={{
                ...S.btnPrimary,
                background: "linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%)",
                boxShadow: "0 4px 12px rgba(245,158,11,.3)",
                opacity:
                  resetLoading || resetPwd !== resetPwdConfirm || resetPwd.length < 10
                    ? 0.6
                    : 1,
                cursor:
                  resetLoading || resetPwd !== resetPwdConfirm || resetPwd.length < 10
                    ? "not-allowed"
                    : "pointer",
              }}
            >
              {resetLoading ? (
                "Resetting…"
              ) : (
                <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <KeyRound size={16} />
                  Reset Password
                </span>
              )}
            </button>
          </>
        }
      >
        {resetTarget && (
          <form id="um-reset-pwd-form" onSubmit={handleResetPasswordSubmit}>
            {/* Target user info card */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "14px",
                padding: "14px 16px",
                borderRadius: "14px",
                background: "var(--bg-body)",
                border: "1px solid var(--border-color)",
                marginBottom: "20px",
              }}
            >
              <div
                style={{
                  width: "44px",
                  height: "44px",
                  borderRadius: "12px",
                  background: "rgba(245, 158, 11, 0.15)",
                  border: "1px solid rgba(245, 158, 11, 0.3)",
                  color: "#f59e0b",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontWeight: 800,
                  fontSize: "1.1rem",
                  flexShrink: 0,
                }}
              >
                {resetTarget.fullName?.charAt(0)?.toUpperCase() || "U"}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  style={{
                    fontWeight: 700,
                    color: "var(--text-primary)",
                    fontSize: "0.98rem",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                >
                  {resetTarget.fullName}
                </div>
                <div
                  style={{
                    fontSize: "0.8rem",
                    color: "var(--text-secondary)",
                    fontFamily: "monospace",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                >
                  {resetTarget.email}
                </div>
              </div>
              {resetTarget.role && (
                <span
                  style={S.roleBadge(
                    getRoleMeta(resetTarget.role).color,
                    getRoleMeta(resetTarget.role).bg,
                    getRoleMeta(resetTarget.role).border,
                  )}
                >
                  {getRoleMeta(resetTarget.role).label}
                </span>
              )}
            </div>

            {/* Security Notice */}
            <div
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: "10px",
                padding: "12px 14px",
                borderRadius: "10px",
                background: "rgba(239, 68, 68, 0.06)",
                border: "1px solid rgba(239, 68, 68, 0.2)",
                marginBottom: "22px",
                fontSize: "0.8rem",
                color: "#dc2626",
                lineHeight: 1.45,
              }}
            >
              <AlertCircle size={17} style={{ flexShrink: 0, marginTop: "2px" }} />
              <div>
                <strong>Security Impact:</strong> This will overwrite the user's password immediately. Active sessions will be terminated and the user must sign in with the new credentials.
              </div>
            </div>

            {/* New Password input */}
            <div style={{ ...S.formGroup, marginBottom: "20px" }}>
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
                      focusedField === "resetPwd"
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
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    padding: "4px",
                  }}
                  title={resetPwdShow ? "Hide password" : "Show password"}
                >
                  {resetPwdShow ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>

              {/* Password strength visual meter */}
              {resetPwd && (
                <div style={{ marginTop: "10px" }}>
                  <div style={{ display: "flex", gap: "4px", marginBottom: "8px" }}>
                    {[
                      resetPwd.length >= 10,
                      /[A-Z]/.test(resetPwd),
                      /[a-z]/.test(resetPwd),
                      /[0-9]/.test(resetPwd),
                      /[!@#$%^&*(),.?":{}<>\-_+=[\]\\/~`]/.test(resetPwd),
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

                  {/* Requirements breakdown tags */}
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                    {[
                      { label: "10+ Chars", ok: resetPwd.length >= 10 },
                      { label: "Uppercase (A-Z)", ok: /[A-Z]/.test(resetPwd) },
                      { label: "Lowercase (a-z)", ok: /[a-z]/.test(resetPwd) },
                      { label: "Number (0-9)", ok: /[0-9]/.test(resetPwd) },
                      { label: "Special symbol", ok: /[!@#$%^&*(),.?":{}<>\-_+=[\]\\/~`]/.test(resetPwd) },
                    ].map((req, idx) => (
                      <span
                        key={idx}
                        style={{
                          fontSize: "0.7rem",
                          padding: "2px 8px",
                          borderRadius: "4px",
                          background: req.ok ? "rgba(16, 185, 129, 0.1)" : "rgba(100, 116, 139, 0.08)",
                          color: req.ok ? "#10b981" : "var(--text-secondary)",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "3px",
                          fontWeight: req.ok ? 600 : 400,
                        }}
                      >
                        {req.ok ? <Check size={10} /> : "·"} {req.label}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Confirm Password input */}
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
                      : resetPwdConfirm && resetPwdConfirm === resetPwd
                      ? "#10b981"
                      : focusedField === "resetPwdConfirm"
                      ? "#f59e0b"
                      : "var(--border-color)",
                }}
                onFocus={() => setFocusedField("resetPwdConfirm")}
                onBlur={() => setFocusedField(null)}
                placeholder="Re-enter the new password"
                autoComplete="new-password"
              />
              {resetPwdConfirm && resetPwdConfirm !== resetPwd && (
                <p style={{ fontSize: "0.75rem", color: "#ef4444", marginTop: "6px", display: "flex", alignItems: "center", gap: "4px" }}>
                  <AlertCircle size={13} /> Passwords do not match
                </p>
              )}
              {resetPwdConfirm && resetPwdConfirm === resetPwd && resetPwd.length >= 10 && (
                <p style={{ fontSize: "0.75rem", color: "#10b981", marginTop: "6px", display: "flex", alignItems: "center", gap: "4px" }}>
                  <CheckCircle2 size={13} /> Passwords match
                </p>
              )}
            </div>
          </form>
        )}
      </Drawer>

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
