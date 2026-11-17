// BUG-115: show the server's validation message instead of a generic "Failed to ..." text.
import { t } from "../i18n";

export interface ApiErrorResponseData {
  error?: string;
  message?: string;
  errors?: string[];
  [key: string]: unknown;
}

function extractMessageFromData(d: ApiErrorResponseData | undefined): string {
  const msg = (d && (d.error || d.message || (Array.isArray(d.errors) && d.errors.join("; ")))) || "";
  return typeof msg === "string" && msg.trim() ? msg : "";
}

export function apiError(err: unknown, fallback: string = t("Request failed")): string {
  const axiosError = err as { response?: { data?: ApiErrorResponseData } } | undefined;
  const msg = extractMessageFromData(axiosError?.response?.data);
  return msg || fallback;
}

export async function readApiError(err: unknown, fallback: string = t("Request failed")): Promise<string> {
  const axiosError = err as { response?: { data?: unknown }; message?: string } | undefined;
  const raw = axiosError?.response?.data;
  if (raw && typeof Blob !== "undefined" && raw instanceof Blob) {
    try {
      const text = await raw.text();
      const parsed = JSON.parse(text) as ApiErrorResponseData;
      const msg = extractMessageFromData(parsed);
      if (msg) return msg;
    } catch {
      // Non-JSON Blob payload falls back below
    }
  } else if (raw && typeof raw === "object") {
    const msg = extractMessageFromData(raw as ApiErrorResponseData);
    if (msg) return msg;
  } else if (typeof raw === "string" && raw.trim()) {
    try {
      const parsed = JSON.parse(raw) as ApiErrorResponseData;
      const msg = extractMessageFromData(parsed);
      if (msg) return msg;
    } catch {
      return raw.trim();
    }
  }
  const directMsg = axiosError?.message;
  if (!axiosError?.response && typeof directMsg === "string" && directMsg.trim()) {
    return directMsg;
  }
  return fallback;
}
