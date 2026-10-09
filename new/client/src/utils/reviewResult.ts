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

export interface SkippedRecord {
  scope?: string;
  id?: number;
  reason: string;
}

const plural = (k: number) => `${k} record${k === 1 ? "" : "s"}`;

/** "2: you created or last changed them; 1: already Verified" from the server's per-record reasons. */
function groupedReasons(skipped: SkippedRecord[]): string {
  const counts = new Map<string, number>();
  skipped.forEach((s) => counts.set(s.reason, (counts.get(s.reason) || 0) + 1));
  return Array.from(counts, ([reason, k]) => (counts.size === 1 ? reason : `${k}: ${reason}`)).join("; ");
}

export function reviewResult(
  verb: string,
  done: number | string,
  requested?: number | null,
  skippedRecords?: SkippedRecord[] | null,
): ReviewResult {
  const n = Number(done) || 0;
  // the server explains each record it skipped (pilot check 2026-10-09, F7); without that list the
  // likely cause is segregation of duties
  if (skippedRecords && skippedRecords.length) {
    const why = groupedReasons(skippedRecords);
    if (n === 0) return { type: "warning", text: `No records ${verb}: ${why}` };
    return { type: "warning", text: `${plural(n)} ${verb}; ${plural(skippedRecords.length)} skipped (${why})` };
  }
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

export function showReviewResult(
  toast: ToastEmitter,
  verb: string,
  done: number | string,
  requested?: number | null,
  skippedRecords?: SkippedRecord[] | null,
): void {
  const r = reviewResult(verb, done, requested, skippedRecords);
  const fn = (r.type === "warning" ? toast.warning : toast.success) || toast.success;
  if (fn) {
    fn(r.text);
  }
}
