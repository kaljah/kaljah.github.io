// BUG-115: show the server's validation message instead of a generic "Failed to ..." text.
export function apiError(err, fallback = "Request failed") {
  const d = err?.response?.data;
  const msg = (d && (d.error || d.message || (Array.isArray(d.errors) && d.errors.join("; ")))) || "";
  return typeof msg === "string" && msg.trim() ? msg : fallback;
}
