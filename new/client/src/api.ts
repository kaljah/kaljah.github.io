import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from "axios";

interface CustomAxiosRequestConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

const api: AxiosInstance = axios.create({
  // FE-01 FIX: use env var so the URL can be configured per environment
  baseURL: import.meta.env.VITE_API_URL || "/api",
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

let csrfToken: string | null = null;

export const fetchCsrfToken = async (): Promise<string | null> => {
  try {
    const response = await api.get<{ csrf_token: string }>("/csrf-token");
    csrfToken = response.data.csrf_token;
    return csrfToken;
  } catch (err) {
    console.error("Failed to fetch CSRF token:", err);
    return null;
  }
};

api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (
      csrfToken &&
      config.method &&
      ["post", "put", "patch", "delete"].includes(config.method.toLowerCase())
    ) {
      config.headers["X-CSRFToken"] = csrfToken;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error.response?.status;
    const msg = error.response?.data?.error || "";

    // CSRF token expired/missing — refresh it and retry the request strictly ONCE
    const originalConfig = error.config as CustomAxiosRequestConfig | undefined;
    if (
      status === 400 &&
      originalConfig &&
      !originalConfig._retry &&
      typeof msg === "string" &&
      (msg.toLowerCase().includes("csrf") ||
        msg.toLowerCase().includes("csrf token") ||
        msg.toLowerCase().includes("token missing"))
    ) {
      originalConfig._retry = true;
      try {
        const freshToken = await fetchCsrfToken();
        originalConfig.headers = originalConfig.headers || {};
        originalConfig.headers["X-CSRFToken"] = freshToken || csrfToken;
        return api(originalConfig);
      } catch {
        /* retry also failed — fall through to rejection */
      }
    }

    if (status === 401) {
      if (typeof window.__authLogout === "function") {
        window.__authLogout();
      }
    }

    // Sanitize generic 500 internal server errors to avoid leaking stack traces
    if (
      status === 500 &&
      (!error.response?.data?.error ||
        typeof error.response.data.error !== "string")
    ) {
      if (error.response) {
        error.response.data = {
          error:
            "An unexpected server error occurred. Please try again or contact support.",
        };
      }
    }

    return Promise.reject(error);
  },
);

export default api;
