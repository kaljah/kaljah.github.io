const RECENT_KEY = "ct.recentPages";

export const readRecent = () => {
  try {
    return JSON.parse(localStorage.getItem(RECENT_KEY) || "[]");
  } catch {
    return [];
  }
};

export const rememberPage = (path) => {
  try {
    const next = [path, ...readRecent().filter((p) => p !== path)].slice(0, 5);
    localStorage.setItem(RECENT_KEY, JSON.stringify(next));
  } catch {
    // storage unavailable: recents are simply not kept
  }
};
