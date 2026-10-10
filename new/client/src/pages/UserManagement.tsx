import UserManagementBlock, { type ManagedUser, type RoleMeta } from "./user-management/UserManagementBlock";
import { Globe, Plus, Shield as ShieldIcon, User as UserIcon, Users as UsersIcon, Wrench as WrenchIcon, Lock } from "lucide-react";
import UserManagementBlock1205, { type UserFormData } from "./user-management/UserManagementBlock1205";
import UserManagementBlock1503 from "./user-management/UserManagementBlock1503";
import React, { useState, useEffect } from "react";
import { NativeSelect } from "../ui/NativeSelect";
import api from "../api";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../components/Toast";
import ConfirmModal from "../components/ConfirmModal";
import { tint } from "../utils/colorMix";
import { t } from "../i18n";

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

// Darker text shades with at least 4.5:1 contrast on the matching 10% tint backgrounds
const AA_TEXT: Record<string, string> = {
  "var(--color-green-500)": "var(--color-green-700)",
  "var(--color-red-500)": "var(--color-red-700)",
  "var(--color-brand-500)": "var(--color-brand-700)",
  "var(--color-amber-500)": "var(--color-amber-700)",
  "var(--color-violet-500)": "var(--color-violet-700)",
  "var(--color-blue-500)": "var(--color-blue-700)",
  "var(--color-sky-600)": "var(--color-legacy-0369a1)",
};
const aa = (c: string) => AA_TEXT[c] || c;

/* ─── role metadata ────────────────────────────────────────────────────────── */
const ROLE_META: Record<string, RoleMeta> = {
  admin: {
    label: t("Admin"),
    color: "var(--color-green-700)",
    bg: "var(--color-green-50)",
    border: "rgba(16,185,129,.25)",
  },
  it_admin: {
    label: t("IT Manager"),
    color: "var(--color-amber-700)",
    bg: "var(--color-amber-50)",
    border: "rgba(245,158,11,.25)",
  },
  it_manager: {
    label: t("IT Manager"),
    color: "var(--color-amber-700)",
    bg: "var(--color-amber-50)",
    border: "rgba(245,158,11,.25)",
  },
  it: {
    label: "IT",
    color: "var(--color-legacy-0369a1)",
    bg: "var(--color-legacy-f0f9ff)",
    border: "rgba(2,132,199,.25)",
  },
  superuser: {
    label: t("Super User"),
    color: "var(--color-violet-700)",
    bg: "var(--color-legacy-f3e8ff)",
    border: "rgba(139,92,246,.25)",
  },
  user: {
    label: t("User"),
    color: "var(--color-blue-700)",
    bg: "var(--color-blue-50)",
    border: "rgba(59,130,246,.25)",
  },
};
const getRoleMeta = (role?: string): RoleMeta =>
  (role && ROLE_META[role]) || {
    label: role?.toUpperCase?.() || "UNKNOWN",
    color: "var(--color-ink-600)",
    bg: "var(--color-ink-100)",
    border: "var(--color-ink-200)",
  };

/* ─── shared inline style helpers ─────────────────────────────────────────── */
const S: Record<string, any> = {
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
    background: "var(--color-brand-50)",
    color: "var(--color-brand-700)",
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
    background: "var(--color-brand-500)",
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
    color: "var(--color-ink-600)",
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
  avatar: (color: string) => ({
    width: "34px",
    height: "34px",
    borderRadius: "10px",
    background: tint(color, "20"),
    border: `1px solid ${tint(color, "30")}`,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "0.85rem",
    fontWeight: 700,
    color: color,
    flexShrink: 0,
  }),

  /* region pill */
  regionPill: (color: string, bg: string, border: string) => ({
    display: "inline-flex",
    alignItems: "center",
    gap: "5px",
    padding: "3px 10px",
    borderRadius: "100px",
    background: bg,
    color: aa(color),
    border: `1px solid ${border}`,
    fontSize: "0.78rem",
    fontWeight: 700,
  }),
  roleBadge: (color: string, bg: string, border: string) => ({
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
    background: "linear-gradient(135deg, var(--color-brand-500) 0%, var(--color-brand-400) 100%)",
    color: "var(--color-white)",
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
  sectionIconBadge: (color: string) => ({
    width: "26px",
    height: "26px",
    borderRadius: "8px",
    background: tint(color, "18"),
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
const UserManagement: React.FC = () => {
  const { user } = useAuth();
  const toast = useToast();

  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [regions, setRegions] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [filterRegion, setFilterRegion] = useState<string>("");
  const [filterRole, setFilterRole] = useState<string>("");
  const [hoveredRow, setHoveredRow] = useState<number | string | null>(null);

  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [editingUser, setEditingUser] = useState<ManagedUser | null>(null);
  const [formData, setFormData] = useState<UserFormData>({
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
  const [focusedField, setFocusedField] = useState<string | null>(null);

  // ── Reset password modal state ───────────────────────────────────────────
  const [resetTarget, setResetTarget] = useState<ManagedUser | null>(null);
  const [resetPwd, setResetPwd] = useState<string>("");
  const [resetPwdConfirm, setResetPwdConfirm] = useState<string>("");
  const [resetPwdShow, setResetPwdShow] = useState<boolean>(false);
  const [resetLoading, setResetLoading] = useState<boolean>(false);

  // ── Delete confirmation modal state ──────────────────────────────────────
  const [deleteTargetUser, setDeleteTargetUser] = useState<ManagedUser | null>(null);
  const [deleteLoading, setDeleteLoading] = useState<boolean>(false);

  const fetchData = async (silent = false, keepOptimistic = false) => {
    if (!silent) setLoading(true);

    // --- Users call (independent) ---
    try {
      const usersRes = await api.get("/auth/users");
      const serverUsers: ManagedUser[] = usersRes.data;
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
      if (!silent) toast.error(t("Failed to load users"));
    }

    // --- Regions call (independent) ---
    try {
      const regionsRes = await api.get("/facilities/all-regions");
      const data = regionsRes.data;
      setRegions(Array.isArray(data) ? data : []);
    } catch {
      setRegions([]);
      if (!silent) toast.error(t("Failed to load facility regions"));
    }

    if (!silent) setLoading(false);
  };

  useEffect(() => {
    if (["it_admin", "it_manager", "it"].includes(user?.role || "")) fetchData();
  }, [user]);

  const handleOpenModal = (userToEdit: ManagedUser | null = null) => {
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (user?.role === "it") {
      toast.error(t("IT role cannot modify user accounts or profiles."));
      return;
    }
    try {
      if (editingUser) {
        if (!formData.fullName.trim()) {
          toast.error(t("Full Name is required."));
          return;
        }
        if (
          !formData.email.trim() ||
          !/^[^@]+@[^@]+\.[^@]+$/.test(formData.email)
        ) {
          toast.error(t("A valid Email address is required."));
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
        toast.success(t("User updated successfully"));
      } else {
        // ── All validation done in JS (no native HTML5 `required`) ──
        if (!formData.fullName.trim()) {
          toast.error(t("Full Name is required."));
          return;
        }
        if (
          !formData.email.trim() ||
          !/^[^@]+@[^@]+\.[^@]+$/.test(formData.email)
        ) {
          toast.error(t("A valid Email address is required."));
          return;
        }
        if (!formData.password || formData.password.length < 10) {
          toast.error(t("Password must be at least 10 characters."));
          return;
        }
        if (
          ["user", "superuser"].includes(formData.role) &&
          !formData.location
        ) {
          toast.error(
            regions.length === 0
              ? t("No regions loaded — restart the server and reload the page.")
              : t("Please select an Assigned Region for this user."),
          );
          return;
        }
        const createRes = await api.post("/auth/register", formData);
        // Optimistically prepend the new user so it shows immediately
        const newUser: ManagedUser = createRes.data?.user || {
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
        toast.success(t("User created successfully"));
      }
      setIsModalOpen(false);
      // Delay background sync slightly so optimistic row renders first,
      // then merge — keeping the new user visible even if the server
      // response is still filtered (e.g. before a server restart).
      setTimeout(() => fetchData(true, true), 800);
    } catch (error: any) {
      const status = error.response?.status;
      const errMsg =
        error.response?.data?.error || error.message || t("Failed to save user");
      console.error(
        "[UserManagement] handleSubmit failed:",
        status,
        error.response?.data,
      );
      toast.error(`${status ? `[${status}] ` : ""}${errMsg}`);
    }
  };

  const handleDelete = (target: number | string | ManagedUser) => {
    if (user?.role === "it") {
      toast.error(t("IT role cannot delete users."));
      return;
    }
    // Accepts either user object or user id
    if (typeof target === "object" && target !== null) {
      setDeleteTargetUser(target);
    } else {
      const found = users.find((u) => u.id === target) || { id: target, email: "" };
      setDeleteTargetUser(found);
    }
  };

  const handleConfirmDelete = async () => {
    if (user?.role === "it") {
      toast.error(t("IT role cannot delete users."));
      return;
    }
    if (!deleteTargetUser?.id) return;
    setDeleteLoading(true);
    const targetId = deleteTargetUser.id;
    try {
      await api.delete(`/auth/users/${targetId}`);
      setUsers((prev) => prev.filter((u) => u.id !== targetId));
      toast.success(t("User deleted"));
      setDeleteTargetUser(null);
      fetchData(true);
    } catch (error: any) {
      toast.error(error.response?.data?.error || t("Failed to delete user"));
      fetchData(true);
    } finally {
      setDeleteLoading(false);
    }
  };

  const handleOpenResetPassword = (u: ManagedUser) => {
    setResetTarget({
      id: u.id,
      fullName: u.fullName || "",
      email: u.email,
      role: u.role,
      location: u.location,
      department: u.department,
    });
    setResetPwd("");
    setResetPwdConfirm("");
    setResetPwdShow(false);
  };

  const handleResetPasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resetTarget) return;
    if (!resetPwd || resetPwd.length < 10) {
      toast.error(t("Password must be at least 10 characters."));
      return;
    }
    // Basic complexity
    if (!/[A-Z]/.test(resetPwd)) { toast.error(t("Password needs an uppercase letter.")); return; }
    if (!/[a-z]/.test(resetPwd)) { toast.error(t("Password needs a lowercase letter.")); return; }
    if (!/[0-9]/.test(resetPwd)) { toast.error(t("Password needs a digit.")); return; }
    if (!/[!@#$%^&*(),.?":{}<>\-_+=[\]\\/~`]/.test(resetPwd)) {
      toast.error(t("Password needs a special character.")); return;
    }
    if (resetPwd !== resetPwdConfirm) {
      toast.error(t("Passwords do not match."));
      return;
    }
    try {
      setResetLoading(true);
      await api.post(`/auth/users/${resetTarget.id}/reset-password`, { newPassword: resetPwd });
      toast.success(t("Password for {{name}} has been reset successfully.", { name: resetTarget.fullName ?? "" }));
      setResetTarget(null);
    } catch (err: any) {
      toast.error(err.response?.data?.error || t("Failed to reset password."));
    } finally {
      setResetLoading(false);
    }
  };

  if (!["it_admin", "it_manager", "it"].includes(user?.role || "")) {
    return (
      <div style={{ ...S.page, textAlign: "center", paddingTop: "80px" }}>
        <div className="mb-[20px]! text-[color:var(--color-ink-600)]!">
          <Lock size={52} strokeWidth={1.5} aria-hidden="true" />
        </div>
        <h2 className="text-[color:var(--text-primary)]! m-[0_0_8px]!">
          {t("Unauthorized")}
        </h2>
        <p className="text-[color:var(--text-secondary)]!">
          {t("You do not have permission to access the IT Management portal.")}
        </p>
      </div>
    );
  }

  const isITOnly = user?.role === "it";

  /* derived stats */
  const totalUsers = users.length;
  const adminCount = users.filter((u) => u.role === "admin").length;
  const itAdminCount = users.filter((u) => ["it_admin", "it_manager"].includes(u.role || "")).length;
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
      (filterRole === "it_manager" && ["it_admin", "it_manager"].includes(u.role || "")) ||
      (filterRole === "it_admin" && ["it_admin", "it_manager"].includes(u.role || ""));
    return byRegion && byRole;
  });

  const inputStyle = (field: string) => ({
    ...S.input,
    borderColor: focusedField === field ? "var(--color-brand-500)" : "var(--border-color)",
    boxShadow:
      focusedField === field ? "0 0 0 3px rgba(255,102,0,.12)" : "none",
  });

  const focusProps = (field: string) => ({
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
            {isITOnly ? t("IT CREDENTIALS CONSOLE") : t("IT MANAGER CONSOLE")}
          </span>
          <h1 style={S.pageTitle}>{t("User Management")}</h1>
          <p style={S.pageSubtitle}>
            {isITOnly
              ? t("Modify user passwords and manage credentials")
              : t("Manage identities, roles, and regional workspace access")}
          </p>
        </div>
        <div style={S.heroRight}>
          <NativeSelect
            id="um-filter-role"
            aria-label={t("Filter by role")}
            value={filterRole}
            onChange={(e) => setFilterRole(e.target.value)}
            style={S.select}
          >
            <option value="">{t("All Roles")}</option>
            <option value="user">{t("Standard User")}</option>
            <option value="superuser">{t("Super User")}</option>
            <option value="admin">{t("Admin")}</option>
            <option value="it_manager">{t("IT Manager")}</option>
            <option value="it">IT</option>
          </NativeSelect>

          <NativeSelect
            id="um-filter-region"
            aria-label={t("Filter by region")}
            value={filterRegion}
            onChange={(e) => setFilterRegion(e.target.value)}
            style={S.select}
          >
            <option value="">{t("All Regions")}</option>
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
              <Plus size={16} strokeWidth={2.5} aria-hidden="true" />
              {t("Add New User")}
            </button>
          )}
        </div>
      </div>

      {/* ── Stats Row ── */}
      <div style={S.statsRow}>
        {[
          {
            label: t("Total Users"),
            value: totalUsers,
            icon: <UsersIcon size={20} strokeWidth={2} aria-hidden="true" />,
            color: "var(--color-legacy-6366f1)",
            bg: "var(--color-legacy-eef2ff)",
          },
          {
            label: t("Standard Users"),
            value: standardCount,
            icon: <UserIcon size={20} strokeWidth={2} aria-hidden="true" />,
            color: "var(--color-blue-500)",
            bg: "var(--color-blue-50)",
          },
          {
            label: t("Admins"),
            value: adminCount,
            icon: <ShieldIcon size={20} strokeWidth={2} aria-hidden="true" />,
            color: "var(--color-green-500)",
            bg: "var(--color-green-50)",
          },
          {
            label: t("IT Admins"),
            value: itAdminCount,
            icon: <WrenchIcon size={20} strokeWidth={2} aria-hidden="true" />,
            color: "var(--color-amber-500)",
            bg: "var(--color-amber-50)",
          },
          {
            label: t("Regions"),
            value: regions.length,
            icon: <Globe size={20} aria-hidden="true" />,
            color: "var(--color-brand-500)",
            bg: "var(--color-brand-50)",
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
        title={t("Revoke User Access")}
        message={
          deleteTargetUser?.fullName
            ? t('Are you sure you want to permanently revoke access for "{{name}}" ({{email}})? This action cannot be undone.', {
                name: deleteTargetUser.fullName,
                email: deleteTargetUser?.email || t("selected account"),
              })
            : t("Are you sure you want to permanently revoke access for this user ({{email}})? This action cannot be undone.", {
                email: deleteTargetUser?.email || t("selected account"),
              })
        }
        confirmLabel={t("Revoke Access")}
        confirmVariant="danger"
        loading={deleteLoading}
        onConfirm={handleConfirmDelete}
        onCancel={() => setDeleteTargetUser(null)}
      />
    </div>
  );
};

export default UserManagement;
