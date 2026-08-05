import React, { createContext, useContext, useState, useEffect } from 'react';
import api, { fetchCsrfToken } from '../api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [preferences, setPreferences] = useState({});
    const [loading, setLoading] = useState(true);

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
        // Default to dark if not specified, or respect preference
        // Since our CSS default is light, we need to set data-theme='dark' for dark mode.
        if (theme === 'dark') {
            document.documentElement.setAttribute('data-theme', 'dark');
        } else {
            document.documentElement.removeAttribute('data-theme');
        }
    };

    useEffect(() => {
        const checkAuth = async () => {
            try {
                const { data } = await api.get('/auth/me');
                setUser(data);

                // Fetch settings as well
                try {
                    const settingsRes = await api.get('/auth/settings');
                    if (settingsRes.data) {
                        setPreferences(settingsRes.data);
                        applyTheme(settingsRes.data.theme);
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
        const { data } = await api.post('/auth/login', { email, password });
        setUser(data.user);
        
        // Refresh CSRF token after login to sync session
        await fetchCsrfToken();

        // Fetch settings after login
        try {
            const settingsRes = await api.get('/auth/settings');
            if (settingsRes.data) {
                setPreferences(settingsRes.data);
                applyTheme(settingsRes.data.theme);
            }
        } catch (e) {
            console.error("Failed to fetch settings on login", e);
        }

        return data;
    };

    const register = async (userData) => {
        const { data } = await api.post('/auth/register', userData);
        return data;
    };

    const logout = async () => {
        await api.post('/auth/logout');
        setUser(null);
        setPreferences({});
        applyTheme('dark'); // Default reset
        // Refresh CSRF token after logout to sync session
        await fetchCsrfToken();
    };

    const updatePreferences = async (newPrefs) => {
        setPreferences(prev => ({ ...prev, ...newPrefs }));
        applyTheme(newPrefs.theme);
        // Persist
        try {
            await api.put('/auth/settings', newPrefs);
        } catch (e) {
            console.error("Failed to persist settings", e);
            // Revert? For now, assume success or user sees toast in Settings page
        }
    };

    return (
        <AuthContext.Provider value={{ user, preferences, updatePreferences, login, register, logout, loading }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => useContext(AuthContext);
