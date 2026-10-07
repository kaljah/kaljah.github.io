import { describe, it, expect } from "vitest";
import { reviewResult } from "../utils/reviewResult";
import { formatEmission } from "../utils/formatters";

describe("review results", () => {
  it("never reports the selection size as approved", () => {
    expect(reviewResult("approved", 0, 340)).toMatchObject({ type: "warning" });
    expect(reviewResult("approved", 0, 340).text).toMatch(/No records approved/);
    expect(reviewResult("approved", 200, 340).text).toBe(
      "200 records approved; 140 records skipped (you created or last edited them; another reviewer must decide on them)");
    expect(reviewResult("rejected", 3, 3)).toEqual({ type: "success", text: "3 records rejected" });
  });
});

describe("emission display", () => {
  it("shows small non-zero values instead of 0.000", () => {
    expect(formatEmission(0.00027, 3)).toBe("2.70e-4");
    expect(formatEmission(0, 3)).toBe("0.000");
    expect(formatEmission(12.3456, 3)).toBe("12.346");
    expect(formatEmission(0.0004, 3)).toBe("4.00e-4");
    expect(formatEmission(0.0005, 3)).toBe("0.001");
  });
});
