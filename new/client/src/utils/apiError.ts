// BUG-115: show the server's validation message instead of a generic "Failed to ..." text.

export interface ApiErrorResponseData {
  error?: string;
  message?: string;
  errors?: string[];
  [key: string]: unknown;
}

export function apiError(err: unknown, fallback: string = "Request failed"): string {
  const axiosError = err as { response?: { data?: ApiErrorResponseData } } | undefined;
  const d = axiosError?.response?.data;
  const msg = (d && (d.error || d.message || (Array.isArray(d.errors) && d.errors.join("; ")))) || "";
  return typeof msg === "string" && msg.trim() ? msg : fallback;
}
