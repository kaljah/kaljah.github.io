import { describe, it, expect } from "vitest";
import DOMPurify from "dompurify";
import pkg from "../../package.json";
import lock from "../../package-lock.json";

function semverGte(actual: string, minimum: string): boolean {
  const a = actual.split(".").map((n) => parseInt(n, 10));
  const b = minimum.split(".").map((n) => parseInt(n, 10));
  for (let i = 0; i < 3; i += 1) {
    if ((a[i] || 0) > (b[i] || 0)) return true;
    if ((a[i] || 0) < (b[i] || 0)) return false;
  }
  return true;
}

describe("Step 4 dependency security pinning & overrides", () => {
  it("pins dompurify and overrides vulnerable transitive packages to first patched versions", () => {
    const packages = lock.packages as Record<string, { version: string }>;

    expect(pkg.dependencies.dompurify).toBe("3.4.17");
    expect(pkg.overrides).toBeDefined();
    expect(pkg.overrides.dompurify).toBe("3.4.17");
    expect(pkg.overrides.undici).toBe("7.30.1");
    expect(pkg.overrides.zod).toBe("4.6.6");
    expect(pkg.overrides["follow-redirects"]).toBe("1.16.2");

    expect(semverGte(packages["node_modules/dompurify"].version, "3.4.17")).toBe(true);
    expect(semverGte(packages["node_modules/undici"].version, "7.30.1")).toBe(true);
    expect(semverGte(packages["node_modules/zod"].version, "4.6.6")).toBe(true);
    expect(semverGte(packages["node_modules/follow-redirects"].version, "1.16.2")).toBe(true);
  });

  it("sanitizes XSS payloads cleanly with pinned DOMPurify", () => {
    const cleaned = DOMPurify.sanitize('<p>Safe</p><svg onload="alert(1)"></svg>');
    expect(cleaned).toContain("<p>Safe</p>");
    expect(cleaned).not.toContain("onload");
  });
});
