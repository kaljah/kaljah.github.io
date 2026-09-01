import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from "react";
import api, { fetchCsrfToken } from "../api";

const AuthContext = createContext(null);

// 10-minute idle session timeout
const IDLE_TIMEOUT_MS = 10 * 60 * 1000;

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [preferences, setPreferences] = useState({});
  const [loading, setLoading] = useState(true);
  const [sessionExpired, setSessionExpired] = useState(false);
  const idleTimerRef = useRef(null);
  const lastActivityRef = useRef(Date.now());

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
    if (isTimeout) {
      setSessionExpired(true);
    }
    try {
      await fetchCsrfToken();
    } catch (e) {}
  }, []);

  // ── 10-Minute Idle Session Timeout ─────────────────────────────────────────
  useEffect(() => {
    if (!user) {
      if (idleTimerRef.current) {
        clearTimeout(idleTimerRef.current);
        idleTimerRef.current = null;
      }
      return;
    }

    const resetIdleTimer = () => {
      lastActivityRef.current = Date.now();
      if (idleTimerRef.current) {
        clearTimeout(idleTimerRef.current);
      }
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
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
