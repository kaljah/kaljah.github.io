// Message for a batch approve / reject: the server skips records the reviewer created or last
// edited (segregation of duties), so the count it returns may be lower than the selection.
export function reviewResult(verb, done, requested) {
  const n = Number(done) || 0;
  const plural = (k) => `${k} record${k === 1 ? "" : "s"}`;
  const why = "you created or last edited them; another reviewer must decide on them";
  if (n === 0) {
    return { type: "warning", text: `No records ${verb}: ${why}` };
  }
  const skipped = requested ? requested - n : 0;
  if (skipped > 0) {
    return { type: "warning", text: `${plural(n)} ${verb}; ${plural(skipped)} skipped (${why})` };
  }
  return { type: "success", text: `${plural(n)} ${verb}` };
}

export function showReviewResult(toast, verb, done, requested) {
  const r = reviewResult(verb, done, requested);
  (toast[r.type] || toast.success)(r.text);
}
