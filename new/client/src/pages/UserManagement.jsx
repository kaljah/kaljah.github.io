import UserManagementBlock from "./user-management/UserManagementBlock";
import UserManagementBlock1205 from "./user-management/UserManagementBlock1205";
import UserManagementBlock1503 from "./user-management/UserManagementBlock1503";
import React, { useState, useEffect } from "react";
import { NativeSelect } from "../ui/NativeSelect";
import api from "../api";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../components/Toast";
import Drawer from "../components/Drawer";
import ConfirmModal from "../components/ConfirmModal";
import { UserPlus, UserCheck, KeyRound, Lock, Shield, Eye, EyeOff, Check, User, Mail, Briefcase, AlertCircle, CheckCircle2 } from "lucide-react";

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
    label: "IT Manager",
    color: "#f59e0b",
    bg: "#fffbeb",
    border: "rgba(245,158,11,.25)",
  },
  it_manager: {
    label: "IT Manager",
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
    fontSize: "var(--text-xl)",
    fontWeight: 700,
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
  roleBadge: (color, bg, border) => ({
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
    if (["it_admin", "it_manager", "it"].includes(user?.role)) fetchData();
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
        status: userToEdit.status || "active",
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
        status: "active",
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
          status: formData.status || "active",
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
                    status: payload.status,
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

  if (!["it_admin", "it_manager", "it"].includes(user?.role)) {
    return (
      <div style={{ ...S.page, textAlign: "center", paddingTop: "80px" }}>
        <div className="mb-[20px]! text-[color:#94a3b8]!">
          <Lock size="52" strokeWidth="1.5" aria-hidden="true" />
        </div>
        <h2 className="text-[color:var(--text-primary)]! m-[0_0_8px]!">
          Unauthorized
        </h2>
        <p className="text-[color:var(--text-secondary)]!">
          You do not have permission to access the IT Management portal.
        </p>
      </div>
    );
  }

  const isITOnly = user?.role === "it";

  /* derived stats */
  const totalUsers = users.length;
  const adminCount = users.filter((u) => u.role === "admin").length;
  const itAdminCount = users.filter((u) => ["it_admin", "it_manager"].includes(u.role)).length;
  const standardCount = users.filter((u) => u.role === "user").length;

  const filteredUsers = users.filter((u) => {
    const byRegion =
      !filterRegion ||
      u.location === filterRegion ||
      u.role === "admin" ||
      u.role === "it_admin" ||
      u.role === "it_manager" ||
      u.role === "it";
    const byRole =
      !filterRole ||
      u.role === filterRole ||
      (filterRole === "it_manager" && ["it_admin", "it_manager"].includes(u.role)) ||
      (filterRole === "it_admin" && ["it_admin", "it_manager"].includes(u.role));
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
            {isITOnly ? "IT CREDENTIALS CONSOLE" : "IT MANAGER CONSOLE"}
          </span>
          <h1 style={S.pageTitle}>User Management</h1>
          <p style={S.pageSubtitle}>
            {isITOnly
              ? "Modify user passwords and manage credentials"
              : "Manage identities, roles, and regional workspace access"}
          </p>
        </div>
        <div style={S.heroRight}>
          <NativeSelect
            id="um-filter-role"
            value={filterRole}
            onChange={(e) => setFilterRole(e.target.value)}
            style={S.select}
          >
            <option value="">All Roles</option>
            <option value="user">Standard User</option>
            <option value="superuser">Super User</option>
            <option value="admin">Admin</option>
            <option value="it_manager">IT Manager</option>
            <option value="it">IT</option>
          </NativeSelect>

          <NativeSelect
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
          </NativeSelect>

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
      <UserManagementBlock
        S={S}
        filteredUsers={filteredUsers}
        getRoleMeta={getRoleMeta}
        handleDelete={handleDelete}
        handleOpenModal={handleOpenModal}
        handleOpenResetPassword={handleOpenResetPassword}
        hoveredRow={hoveredRow}
        isITOnly={isITOnly}
        loading={loading}
        setHoveredRow={setHoveredRow}
        totalUsers={totalUsers}
      />

      {/* ── Slide-Over Drawer: Add / Edit User ── */}
      <UserManagementBlock1205
        S={S}
        editingUser={editingUser}
        focusProps={focusProps}
        focusedField={focusedField}
        formData={formData}
        handleSubmit={handleSubmit}
        inputStyle={inputStyle}
        isModalOpen={isModalOpen}
        regions={regions}
        setFormData={setFormData}
        setIsModalOpen={setIsModalOpen}
      />

      {/* ── Slide-Over Drawer: Reset Password ── */}
      <UserManagementBlock1503
        S={S}
        focusedField={focusedField}
        getRoleMeta={getRoleMeta}
        handleResetPasswordSubmit={handleResetPasswordSubmit}
        resetLoading={resetLoading}
        resetPwd={resetPwd}
        resetPwdConfirm={resetPwdConfirm}
        resetPwdShow={resetPwdShow}
        resetTarget={resetTarget}
        setFocusedField={setFocusedField}
        setResetPwd={setResetPwd}
        setResetPwdConfirm={setResetPwdConfirm}
        setResetPwdShow={setResetPwdShow}
        setResetTarget={setResetTarget}
      />

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
