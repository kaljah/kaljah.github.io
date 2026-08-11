import React, { useState, useEffect } from "react";
import api from "../api";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../components/Toast";
import Modal from "../components/Modal";

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

  const handleDelete = async (id) => {
    if (
      !window.confirm("Are you sure you want to completely remove this user?")
    )
      return;
    try {
      await api.delete(`/auth/users/${id}`);
      setUsers((prev) => prev.filter((u) => u.id !== id));
      toast.success("User deleted");
      fetchData(true);
    } catch (error) {
      toast.error(error.response?.data?.error || "Failed to delete user");
      fetchData(true);
    }
  };

  if (user?.role !== "it_admin") {
    return (
      <div style={{ ...S.page, textAlign: "center", paddingTop: "80px" }}>
        <div style={{ fontSize: "3rem", marginBottom: "16px" }}>🔒</div>
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
          <span>
            🔧 API Debugger — click to{" "}
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
              💡 If /facilities/all-regions returns 404 → server needs restart.
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
            icon: "👥",
            color: "#6366f1",
            bg: "#eef2ff",
          },
          {
            label: "Standard Users",
            value: standardCount,
            icon: "👤",
            color: "#3b82f6",
            bg: "#eff6ff",
          },
          {
            label: "Admins",
            value: adminCount,
            icon: "🛡️",
            color: "#10b981",
            bg: "#ecfdf5",
          },
          {
            label: "IT Admins",
            value: itAdminCount,
            icon: "🔧",
            color: "#f59e0b",
            bg: "#fffbeb",
          },
          {
            label: "Regions",
            value: regions.length,
            icon: "🌍",
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
                      <span style={{ fontSize: "2rem" }}>🔍</span>
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
                            🌐 All Regions
                          </span>
                        ) : u.role === "it_admin" ? (
                          <span
                            style={S.regionPill(
                              "#ef4444",
                              "#fef2f2",
                              "rgba(239,68,68,.25)",
                            )}
                          >
                            🔒 No Data Access
                          </span>
                        ) : u.location ? (
                          <span
                            style={S.regionPill(
                              "#ff6600",
                              "#fff7ed",
                              "rgba(255,102,0,.25)",
                            )}
                          >
                            📍 {u.location}
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
                          ✏️
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
                          🗑️
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
          editingUser ? "✏️ Edit User Permissions" : "👤 Register New User"
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
              {editingUser ? "💾 Save Changes" : "✅ Create User"}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default UserManagement;
