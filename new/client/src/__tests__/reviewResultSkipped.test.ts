import { describe, it, expect } from "vitest";
import { reviewResult } from "../utils/reviewResult";

// Pilot check 2026-10-09 (F7): the message gives the server's reason for each skipped record.
describe("reviewResult with the server's skipped records", () => {
  it("groups the reasons", () => {
    const r = reviewResult("approved", 1, 4, [
      { id: 1, reason: "Already Verified" },
      { id: 2, reason: "Already Verified" },
      { id: 3, reason: "Outside your facilities or region" },
    ]);
    expect(r.type).toBe("warning");
    expect(r.text).toBe("1 record approved; 3 records skipped (2: Already Verified; 1: Outside your facilities or region)");
  });

  it("states the single reason when nothing was decided", () => {
    const r = reviewResult("approved", 0, 2, [
      { id: 1, reason: "You created or last changed this record; another reviewer must approve it" },
      { id: 2, reason: "You created or last changed this record; another reviewer must approve it" },
    ]);
    expect(r.text).toBe("No records approved: You created or last changed this record; another reviewer must approve it");
  });

  it("keeps the previous message when the server sends no list", () => {
    expect(reviewResult("approved", 3, 3).text).toBe("3 records approved");
  });
});
