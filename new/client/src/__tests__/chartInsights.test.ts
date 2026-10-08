import { describe, expect, it } from "vitest";
import { describeBridge, describeRanking } from "../utils/chartInsights";

const fmt = (v: number) => `${Math.round(v / 1000)}K`;

describe("describeBridge", () => {
  it("names the two biggest movers and the net change", () => {
    const s = describeBridge(
      1180000,
      1096000,
      [
        { name: "Combustion", delta: -62000 },
        { name: "Flaring", delta: -48000 },
        { name: "Venting", delta: 21000 },
        { name: "Scope 2", delta: -9000 },
      ],
      fmt,
    );
    expect(s).toBe("Scope 1+2 fell 7.1% (−84K tCO₂e), mainly Combustion (−62K) and Flaring (−48K).");
  });
  it("says rose for an increase and handles one mover", () => {
    expect(describeBridge(100000, 120000, [{ name: "Flaring", delta: 20000 }, { name: "Venting", delta: 0 }], fmt)).toBe(
      "Scope 1+2 rose 20.0% (+20K tCO₂e), mainly Flaring (+20K).",
    );
  });
  it("uses the scope label it is given", () => {
    expect(describeBridge(100000, 90000, [{ name: "Scope 3", delta: -10000 }], fmt, "Scope 1+2+3")).toBe(
      "Scope 1+2+3 fell 10.0% (−10K tCO₂e), mainly Scope 3 (−10K).",
    );
  });
  it("handles no change at all", () => {
    expect(describeBridge(5, 5, [{ name: "Flaring", delta: 0 }], fmt)).toBe("Scope 1+2 emissions did not change.");
  });
});

describe("describeRanking", () => {
  it("reports the leader and the top-two share", () => {
    expect(
      describeRanking(
        [
          { name: "Flaring", value: 24 },
          { name: "Combustion", value: 55 },
          { name: "Venting", value: 15 },
          { name: "Leaks", value: 6 },
        ],
        "source",
      ),
    ).toBe("Combustion is the largest source, 55% of the total; the top 2 make up 79%.");
  });
  it("ignores zero and negative values and tolerates empty input", () => {
    expect(describeRanking([{ name: "A", value: 0 }, { name: "B", value: -3 }])).toBe("");
    expect(describeRanking([{ name: "A", value: 4 }])).toBe("A is the only contributor.");
  });
});
