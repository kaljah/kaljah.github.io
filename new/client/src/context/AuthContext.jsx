import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from "react";
import api, { fetchCsrfToken } from "../api";

const AuthContext = createContext(null);

// 10-minute idle session timeout, 9-minute warning
const IDLE_TIMEOUT_MS = 10 * 60 * 1000;
const IDLE_WARNING_MS = 9 * 60 * 1000;

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [preferences, setPreferences] = useState({});
  const [loading, setLoading] = useState(true);
  const [sessionExpired, setSessionExpired] = useState(false);
  const [sessionWarning, setSessionWarning] = useState(false);
  const idleTimerRef = useRef(null);
  const idleWarningRef = useRef(null);
  const lastActivityRef = useRef(Date.now());

  // BroadcastChannel for cross-tab auth synchronization
  const authChannelRef = useRef(null);

  useEffect(() => {
    if (typeof BroadcastChannel !== "undefined") {
      try {
        authChannelRef.current = new BroadcastChannel("ghg_auth_channel");
        authChannelRef.current.onmessage = (event) => {
          const msg = event.data;
          if (msg?.type === "LOGOUT") {
            setUser(null);
            setPreferences({});
            applyTheme("light");
            setSessionWarning(false);
            if (msg.isTimeout) {
              setSessionExpired(true);
            }
          } else if (msg?.type === "ACTIVITY") {
            lastActivityRef.current = msg.timestamp || Date.now();
            setSessionWarning(false);
          }
        };
      } catch (err) {
        console.warn("[Auth] BroadcastChannel not supported in this environment", err);
      }
    }

    // Storage event fallback for older browser tabs
    const handleStorage = (e) => {
      if (e.key === "ghg_auth_logout_event") {
        setUser(null);
        setPreferences({});
        applyTheme("light");
        setSessionWarning(false);
      }
    };
    window.addEventListener("storage", handleStorage);

    return () => {
      if (authChannelRef.current) {
        authChannelRef.current.close();
        authChannelRef.current = null;
      }
      window.removeEventListener("storage", handleStorage);
    };
  }, []);

  // Register global logout hook for API interceptor
  useEffect(() => {
    window.__authLogout = () => {
      setUser(null);
      setLoading(false);
    };
    return () => {
      delete window.__authLogout;
    };
  }, []);

  const applyTheme = (theme) => {
    // Enforce light theme only by removing data-theme attribute
    document.documentElement.removeAttribute("data-theme");
  };

  const logout = useCallback(async (isTimeout = false) => {
    try {
      await api.post("/auth/logout");
    } catch (e) {
      // Ignore network errors on logout
    }
    setUser(null);
    setPreferences({});
    applyTheme("light");
    setSessionWarning(false);
    if (isTimeout) {
      setSessionExpired(true);
    }

    // Broadcast logout to all sibling browser tabs
    if (authChannelRef.current) {
      try {
        authChannelRef.current.postMessage({ type: "LOGOUT", isTimeout });
      } catch (e) {}
    }
    try {
      localStorage.setItem("ghg_auth_logout_event", Date.now().toString());
    } catch (e) {}

    try {
      await fetchCsrfToken();
    } catch (e) {}
  }, []);

  // ── 10-Minute Idle Session Timeout & 9-Minute Warning ─────────────────────
  useEffect(() => {
    if (!user) {
      if (idleTimerRef.current) {
        clearTimeout(idleTimerRef.current);
        idleTimerRef.current = null;
      }
      if (idleWarningRef.current) {
        clearTimeout(idleWarningRef.current);
        idleWarningRef.current = null;
      }
      setSessionWarning(false);
      return;
    }

    const resetIdleTimer = () => {
      lastActivityRef.current = Date.now();
      setSessionWarning(false);
      if (authChannelRef.current) {
        try {
          authChannelRef.current.postMessage({ type: "ACTIVITY", timestamp: Date.now() });
        } catch (e) {}
      }
      if (idleTimerRef.current) {
        clearTimeout(idleTimerRef.current);
      }
      if (idleWarningRef.current) {
        clearTimeout(idleWarningRef.current);
      }
      idleWarningRef.current = setTimeout(() => {
        setSessionWarning(true);
      }, IDLE_WARNING_MS);
      idleTimerRef.current = setTimeout(() => {
        console.warn("[Auth] 10-minute idle session timeout reached. Logging out.");
        logout(true);
      }, IDLE_TIMEOUT_MS);
    };

    // Throttle user activity events (only reset once per 5 seconds on continuous mouse movements)
    let throttleTimeout = null;
    const handleUserActivity = () => {
      if (!throttleTimeout) {
        resetIdleTimer();
        throttleTimeout = setTimeout(() => {
          throttleTimeout = null;
        }, 5000);
      }
    };

    const activityEvents = ["mousemove", "mousedown", "keydown", "touchstart", "scroll", "click"];
    activityEvents.forEach((event) => {
      window.addEventListener(event, handleUserActivity, { passive: true });
    });

    // Initialize timer
    resetIdleTimer();

    return () => {
      if (idleTimerRef.current) {
        clearTimeout(idleTimerRef.current);
      }
      if (idleWarningRef.current) {
        clearTimeout(idleWarningRef.current);
      }
      if (throttleTimeout) {
        clearTimeout(throttleTimeout);
      }
      activityEvents.forEach((event) => {
        window.removeEventListener(event, handleUserActivity);
      });
    };
  }, [user, logout]);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const { data } = await api.get("/auth/me");
        if (data && data.authenticated !== false && data.id) {
          setUser(data);

          // Fetch settings as well
          try {
            const settingsRes = await api.get("/auth/settings");
            if (settingsRes.data) {
              setPreferences(settingsRes.data);
              applyTheme("light");
            }
          } catch (e) {
            console.error("Failed to fetch settings on auth check", e);
          }
        } else {
          setUser(null);
          setPreferences({});
        }
      } catch (err) {
        setUser(null);
        setPreferences({});
      } finally {
        setLoading(false);
      }
    };
    checkAuth();
  }, []);

  const login = async (email, password) => {
    setSessionExpired(false);
    setSessionWarning(false);
    const { data } = await api.post("/auth/login", { email, password });
    setUser(data.user);

    // Refresh CSRF token after login to sync session
    await fetchCsrfToken();

    // Fetch settings after login
    try {
      const settingsRes = await api.get("/auth/settings");
      if (settingsRes.data) {
        setPreferences(settingsRes.data);
        applyTheme("light");
      }
    } catch (e) {
      console.error("Failed to fetch settings on login", e);
    }

    return data;
  };

  const register = async (userData) => {
    const { data } = await api.post("/auth/register", userData);
    return data;
  };

  const updatePreferences = async (newPrefs) => {
    setPreferences((prev) => ({ ...prev, ...newPrefs }));
    applyTheme(newPrefs.theme);
    // Persist
    try {
      await api.put("/auth/settings", newPrefs);
    } catch (e) {
      console.error("Failed to persist settings", e);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        preferences,
        updatePreferences,
        login,
        register,
        logout,
        loading,
        sessionExpired,
        setSessionExpired,
        sessionWarning,
        setSessionWarning,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
