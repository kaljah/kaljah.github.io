// Message for a batch approve / reject: the server skips records the reviewer created or last
// edited (segregation of duties), so the count it returns may be lower than the selection.

export interface ReviewResult {
  type: "warning" | "success";
  text: string;
}

export interface ToastEmitter {
  warning?: (msg: string) => void;
  success: (msg: string) => void;
  error?: (msg: string) => void;
  info?: (msg: string) => void;
}

export function reviewResult(verb: string, done: number | string, requested?: number | null): ReviewResult {
  const n = Number(done) || 0;
  const plural = (k: number) => `${k} record${k === 1 ? "" : "s"}`;
  const why = "you created or last edited them; another reviewer must decide on them";
  if (n === 0) {
    return { type: "warning", text: `No records ${verb}: ${why}` };
  }
  const reqNum = requested != null ? Number(requested) : 0;
  const skipped = reqNum ? reqNum - n : 0;
  if (skipped > 0) {
    return { type: "warning", text: `${plural(n)} ${verb}; ${plural(skipped)} skipped (${why})` };
  }
  return { type: "success", text: `${plural(n)} ${verb}` };
}

export function showReviewResult(toast: ToastEmitter, verb: string, done: number | string, requested?: number | null): void {
  const r = reviewResult(verb, done, requested);
  const fn = (r.type === "warning" ? toast.warning : toast.success) || toast.success;
  if (fn) {
    fn(r.text);
  }
}
