import axios from 'axios';

const api = axios.create({
    // FE-01 FIX: use env var so the URL can be configured per environment
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:5000/api',
    withCredentials: true,
    headers: {
        'Content-Type': 'application/json'
    }
});

let csrfToken = null;

export const fetchCsrfToken = async () => {
    try {
        const response = await api.get('/csrf-token');
        csrfToken = response.data.csrf_token;
    } catch (err) {
        console.error('Failed to fetch CSRF token:', err);
    }
};

api.interceptors.request.use((config) => {
    if (csrfToken && ['post', 'put', 'patch', 'delete'].includes(config.method)) {
        config.headers['X-CSRFToken'] = csrfToken;
    }
    return config;
}, (error) => Promise.reject(error));


api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const status = error.response?.status;
        const msg = error.response?.data?.error || '';

        // CSRF token expired/missing — refresh it and retry the request ONCE
        if (
            status === 400 &&
            (msg.toLowerCase().includes('csrf') || msg.toLowerCase().includes('token'))
        ) {
            try {
                await fetchCsrfToken();
                // Retry with the fresh token
                const originalConfig = error.config;
                originalConfig.headers['X-CSRFToken'] = csrfToken;
                return api(originalConfig);
            } catch (_) {
                /* retry also failed — fall through to rejection */
            }
        }

        if (status === 401) {
            if (typeof window.__authLogout === 'function') {
                window.__authLogout();
            }
        }
        return Promise.reject(error);
    }
);

export default api;
