// Saved column mappings (import wizard): a mapping saved for one export is re-applied to the next file
// with the same columns, so a monthly file from the same system is never matched by hand twice.

export interface SavedMapping {
  id: number;
  name: string;
  scope?: string;
  headers: string[];
  mapping: Record<string, string>;
  updated_at?: string | null;
  last_used_at?: string | null;
}

/** Saved mappings that fit a file: every column the mapping uses is in the file. Best first:
 * the same set of columns, then the share of the saved columns found; ties keep the server's order
 * (most recently used first). */
export function fittingMappings(saved: SavedMapping[] | null | undefined, headers: string[] | null | undefined): SavedMapping[] {
  const have = new Set((headers || []).map((h) => String(h).trim()));
  if (!have.size) return [];
  return (saved || [])
    .map((m, i) => {
      const used = Object.values(m.mapping || {}).filter(Boolean);
      if (!used.length || !used.every((c) => have.has(String(c).trim()))) return null;
      const cols = (m.headers || []).map((h) => String(h).trim());
      const same = cols.length === have.size && cols.every((c) => have.has(c));
      const share = cols.length ? cols.filter((c) => have.has(c)).length / cols.length : 0;
      return { m, score: (same ? 2 : 0) + share, i };
    })
    .filter((x): x is { m: SavedMapping; score: number; i: number } => x !== null)
    .sort((a, b) => b.score - a.score || a.i - b.i)
    .map((x) => x.m);
}

/** The mapping a file opens with: the automatic one, with the best fitting saved mapping on top. */
export function withSavedMapping(
  autoMapping: Record<string, string>,
  saved: SavedMapping[] | null | undefined,
  headers: string[],
): { mapping: Record<string, string>; applied: SavedMapping | null } {
  const best = fittingMappings(saved, headers)[0] || null;
  return { mapping: best ? { ...autoMapping, ...best.mapping } : autoMapping, applied: best };
}
